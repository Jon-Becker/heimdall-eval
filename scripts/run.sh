#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Use dev build if DEV=1 is passed
if [[ "${DEV:-}" == "1" ]]; then
    HEIMDALL="/Users/jonathanbecker/Documents/github/heimdall-rs/target/release/heimdall"
else
    HEIMDALL="heimdall"
fi

usage() {
    echo "Usage: $0 <target>"
    echo ""
    echo "Available targets:"
    ls -d "$ROOT_DIR/evals"/*/ 2>/dev/null | xargs -n1 basename || echo "  (none found)"
    exit 0
}

process_contract() {
    local json="$1"
    local output_dir="$2"

    local name
    name=$(basename "$json" .json)
    local bytecode
    bytecode=$(jq -r '.deployedBytecode.object // .deployedBytecode // empty' "$json" 2>/dev/null)

    if [[ -n "$bytecode" && "$bytecode" != "null" && "$bytecode" != "0x" ]]; then
        echo "Processing $name..."
        mkdir -p "$output_dir/$name"
        $HEIMDALL decompile "$bytecode" -d -vvv -o "$output_dir/$name" --include-sol 2>&1 || true
        $HEIMDALL cfg "$bytecode" -d -vvv -o "$output_dir/$name" 2>&1 || true
        echo "Done: $name"
    fi
}

run_target() {
    local target="$1"
    local eval_dir="$ROOT_DIR/evals/$target"
    local output_dir="$ROOT_DIR/heimdall"

    if [[ ! -d "$eval_dir" ]]; then
        echo "Error: Target '$target' not found"
        exit 1
    fi

    echo "=== Building $target ==="
    cd "$eval_dir" && forge build

    echo "=== Processing contracts in parallel ==="
    local pids=()
    for json in "$eval_dir"/out/*/*.json; do
        [[ -f "$json" ]] || continue
        process_contract "$json" "$output_dir" &
        pids+=($!)
    done

    # Wait for all background jobs
    for pid in "${pids[@]}"; do
        wait "$pid" || true
    done
    echo "=== Done: $target ==="
}

run_all() {
    echo "=== Running all evals in parallel ==="
    local pids=()
    for dir in $(ls -d "$ROOT_DIR/evals"/*/ 2>/dev/null | xargs -n1 basename); do
        run_target "$dir" &
        pids+=($!)
    done

    for pid in "${pids[@]}"; do
        wait "$pid" || true
    done
    echo "=== All evals complete ==="
}

# Main
if [[ $# -eq 0 ]]; then
    usage
elif [[ "$1" == "--all" ]]; then
    run_all
else
    run_target "$1"
fi
