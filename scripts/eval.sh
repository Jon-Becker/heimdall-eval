#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
EVALS_FILE="$ROOT_DIR/heimdall/evals.json"
LOCK_DIR="$ROOT_DIR/heimdall/.evals.lock"

usage() {
    echo "Usage: $0 <target>"
    echo ""
    echo "Available targets:"
    ls -d "$ROOT_DIR/evals"/*/ 2>/dev/null | xargs -n1 basename || echo "  (none found)"
    exit 0
}

update_evals_json() {
    local name="$1"
    local cfg_score="$2"
    local dec_score="$3"

    # Use mkdir for atomic locking (cross-platform)
    while ! mkdir "$LOCK_DIR" 2>/dev/null; do
        sleep 0.1
    done
    trap "rmdir '$LOCK_DIR' 2>/dev/null" EXIT

    # Initialize file if it doesn't exist
    if [[ ! -f "$EVALS_FILE" ]]; then
        echo '{}' > "$EVALS_FILE"
    fi

    # Update with flat structure
    jq --arg name "$name" \
       --argjson cfg "${cfg_score:-null}" \
       --argjson dec "${dec_score:-null}" \
       '. + {($name): {cfg: $cfg, decompilation: $dec}}' \
       "$EVALS_FILE" > "$EVALS_FILE.tmp" && mv "$EVALS_FILE.tmp" "$EVALS_FILE"

    rmdir "$LOCK_DIR" 2>/dev/null
    trap - EXIT
}

eval_contract() {
    local sol="$1"
    local output_dir="$2"

    local name
    name=$(basename "$sol" .sol)
    local decompiled="$output_dir/$name/decompiled.sol"
    local cfg="$output_dir/$name/cfg.dot"

    # Evaluate decompilation
    if [[ -f "$decompiled" ]]; then
        echo "=== Evaluating $name (decompilation) ==="
        local outfile="$output_dir/$name/eval.json"
        local prompt
        prompt="$(cat "$ROOT_DIR/prompts/DECOMPILATION_PROMPT.md")

<output_file>$outfile</output_file>

<original>
$(cat "$sol")
</original>

<decompiled>
$(cat "$decompiled")
</decompiled>"
        claude --dangerously-skip-permissions -p "$prompt"
        echo "Output written to $outfile"
    else
        echo "Skipping $name: no decompiled output found"
    fi

    # Evaluate CFG
    if [[ -f "$cfg" ]]; then
        echo "=== Evaluating $name (CFG) ==="
        local outfile="$output_dir/$name/cfg_eval.json"
        local prompt
        prompt="$(cat "$ROOT_DIR/prompts/CFG_PROMPT.md")

<output_file>$outfile</output_file>

<original_solidity>
$(cat "$sol")
</original_solidity>

<cfg format=\"dot\">
$(cat "$cfg")
</cfg>"
        claude --dangerously-skip-permissions -p "$prompt"
        echo "Output written to $outfile"
    else
        echo "Skipping $name CFG: no cfg.dot found"
    fi

    # Update evals.json (with locking)
    local dec_score cfg_score
    dec_score=$(jq -r '.score // empty' "$output_dir/$name/eval.json" 2>/dev/null || echo "")
    cfg_score=$(jq -r '.score // empty' "$output_dir/$name/cfg_eval.json" 2>/dev/null || echo "")

    if [[ -n "$dec_score" || -n "$cfg_score" ]]; then
        update_evals_json "$name" "$cfg_score" "$dec_score"
    fi

    echo "=== Done: $name ==="
}

eval_target() {
    local target="$1"
    local eval_dir="$ROOT_DIR/evals/$target"
    local output_dir="$ROOT_DIR/heimdall"

    if [[ ! -d "$eval_dir" ]]; then
        echo "Error: Target '$target' not found"
        exit 1
    fi

    # Run compilation and decompilation first
    "$SCRIPT_DIR/run.sh" "$target"

    echo ""
    echo "=== Evaluating $target contracts in parallel ==="

    local pids=()
    for sol in "$eval_dir"/src/*.sol; do
        [[ -f "$sol" ]] || continue
        eval_contract "$sol" "$output_dir" &
        pids+=($!)
    done

    # Wait for all background jobs
    for pid in "${pids[@]}"; do
        wait "$pid" || true
    done

    echo ""
    echo "=== Done: $target ==="
    echo "Updated $EVALS_FILE"
}

eval_all() {
    # Run all evals in parallel
    echo "=== Evaluating all targets in parallel ==="
    local pids=()
    for dir in $(ls -d "$ROOT_DIR/evals"/*/ 2>/dev/null | xargs -n1 basename); do
        eval_target "$dir" &
        pids+=($!)
    done

    for pid in "${pids[@]}"; do
        wait "$pid" || true
    done
    echo "=== All evaluations complete ==="
}

# Main
if [[ $# -eq 0 ]]; then
    usage
elif [[ "$1" == "--all" ]]; then
    eval_all
else
    eval_target "$1"
fi
