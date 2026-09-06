#!/usr/bin/env python3
"""Render static HTML pages comparing baseline and candidate decompilation runs.

The requested output path is an index page.  Its sibling directory (named after
that path without its extension) contains one self-contained detail page for
every evaluation.
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import os
import sys
from dataclasses import dataclass, field
from urllib.parse import quote

DIFF_CONTEXT = 3
STATUS_LABELS = {"pass": "pass", "failed": "failed", "missing": "missing output"}

# Deliberately small: reports should read like documents, rather than dashboards.
STYLES = """
body { max-width: 72rem; margin: 2rem auto; padding: 0 1rem; color: #222;
       font: 16px/1.5 system-ui, sans-serif; }
h1 { margin-bottom: .15rem; } h2 { margin-top: 2rem; } h3 { margin-bottom: .25rem; }
a { color: #0969da; } .muted { color: #57606a; } .meta { margin: 0; }
nav { margin: 1.5rem 0; } ul { padding-left: 1.25rem; }
section { margin: 1.5rem 0; } pre { border: 1px solid #d0d7de; }
pre { overflow-x: auto; padding: .75rem; background: #f6f8fa; white-space: pre-wrap; }
pre.diff { font: 12px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.diff-line { display: block; } .diff-add { background: #dafbe1; } .diff-del { background: #ffebe9; }
.diff-hunk { color: #57606a; } .error { color: #cf222e; }
"""


@dataclass
class Side:
    source: str | None = None
    score: int | None = None
    summary: str | None = None
    differences: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def has_comment(self) -> bool:
        return self.summary is not None or bool(self.differences) or self.score is not None


@dataclass
class Case:
    name: str
    target: str | None
    baseline: Side
    candidate: Side

    @property
    def status(self) -> str:
        if self.candidate.error or self.baseline.error:
            return "failed"
        if self.candidate.source is None:
            return "missing"
        return "pass"

    @property
    def changed(self) -> bool:
        return (self.baseline.source or "") != (self.candidate.source or "")

    @property
    def has_llm_result(self) -> bool:
        """Whether either compared run has a recorded LLM evaluation."""
        return self.baseline.has_comment or self.candidate.has_comment


def read_text(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def load_side(run_dir: str | None, name: str) -> Side:
    if run_dir is None:
        return Side()
    case_dir = os.path.join(run_dir, name)
    error = read_text(os.path.join(case_dir, "error.txt"))
    side = Side(source=read_text(os.path.join(case_dir, "decompiled.sol")), error=error.strip() or None if error else None)
    raw = read_text(os.path.join(case_dir, "eval.json"))
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            score = payload.get("score")
            side.score = score if isinstance(score, int) else None
            summary = payload.get("summary")
            side.summary = summary if isinstance(summary, str) and summary else None
            differences = payload.get("differences")
            if isinstance(differences, list):
                side.differences = [str(item) for item in differences]
    return side


def discover_cases(*run_dirs: str) -> list[str]:
    names: set[str] = set()
    for run_dir in run_dirs:
        try:
            entries = os.listdir(run_dir)
        except OSError:
            continue
        names.update(entry for entry in entries if not entry.startswith(".") and os.path.isdir(os.path.join(run_dir, entry)))
    return sorted(names)


def discover_targets(evals_dir: str) -> dict[str, str]:
    targets: dict[str, str] = {}
    try:
        entries = sorted(os.listdir(evals_dir))
    except OSError:
        return targets
    for target in entries:
        try:
            sources = sorted(os.listdir(os.path.join(evals_dir, target, "src")))
        except OSError:
            continue
        for source in sources:
            if source.endswith(".sol"):
                targets.setdefault(source[:-4], target)
    return targets


def split_lines(source: str | None) -> list[str]:
    return source.splitlines() if source else []


def unified_diff_rows(before: list[str], after: list[str], context: int = DIFF_CONTEXT) -> list[tuple]:
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    rows: list[tuple] = []
    for group in matcher.get_grouped_opcodes(context):
        old_start, old_end = group[0][1], group[-1][2]
        new_start, new_end = group[0][3], group[-1][4]
        rows.append(("hunk", None, None, f"@@ -{old_start + 1},{old_end - old_start} +{new_start + 1},{new_end - new_start} @@"))
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                rows.extend(("ctx", i1 + offset + 1, j1 + offset + 1, line) for offset, line in enumerate(before[i1:i2]))
            else:
                rows.extend(("del", i1 + offset + 1, None, line) for offset, line in enumerate(before[i1:i2]))
                rows.extend(("add", None, j1 + offset + 1, line) for offset, line in enumerate(after[j1:j2]))
    return rows


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def document(title: str, body: str) -> str:
    return ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{esc(title)}</title><style>{STYLES}</style></head><body>{body}</body></html>\n")


def render_comment(title: str, side: Side) -> str:
    if not side.has_comment:
        return f"<section><h3>{esc(title)}</h3><p class=\"muted\">No LLM evaluation was recorded.</p></section>"
    score = "not scored" if side.score is None else f"{side.score}/100"
    parts = [f"<section><h3>{esc(title)}</h3><p><strong>Score:</strong> {esc(score)}</p>"]
    parts.append(f"<p>{esc(side.summary)}</p>" if side.summary else '<p class="muted">No summary was recorded.</p>')
    if side.differences:
        parts.append("<ul>" + "".join(f"<li>{esc(item)}</li>" for item in side.differences) + "</ul>")
    return "".join(parts) + "</section>"


def render_diff(case: Case) -> str:
    rows = unified_diff_rows(split_lines(case.baseline.source), split_lines(case.candidate.source))
    if not rows:
        text = "Decompiled output is identical between baseline and candidate." if case.candidate.source is not None else "No decompiled output on either side, so there is nothing to diff."
        return f'<section><h2>Diff</h2><p class="muted">{esc(text)}</p></section>'
    signs = {"add": "+", "del": "-", "ctx": " ", "hunk": ""}
    # The spans are block elements; do not insert whitespace text nodes between
    # them, because <pre> would render those as blank lines.
    body = "".join(
        f'<span class="diff-line diff-{kind}">{esc(signs[kind] + text)}</span>'
        for kind, _old, _new, text in rows
    )
    return f"<section><h2>Unified diff</h2><pre class=\"diff\"><code>{body}</code></pre></section>"


def render_case(case: Case, title: str, index_href: str = "../report.html") -> str:
    details = []
    for label, side in (("Baseline error", case.baseline), ("Candidate error", case.candidate)):
        if side.error:
            details.append(f'<section class="error"><h2>{label}</h2><pre><code>{esc(side.error)}</code></pre></section>')
    target = f" · target: {esc(case.target)}" if case.target else ""
    score = f" · status: {esc(STATUS_LABELS[case.status])}"
    body = (f'<nav><a href="{esc(index_href)}">← All evaluations</a></nav><header><h1>{esc(case.name)}</h1>'
            f'<p class="meta muted">{esc(title)}{target}{score}</p></header>{"".join(details)}'
            f'<h2>LLM evaluation</h2>{render_comment("Baseline", case.baseline)}{render_comment("Candidate", case.candidate)}'
            f"{render_diff(case)}")
    return document(f"{title} — {case.name}", body)


def detail_filename(case: Case) -> str:
    return f"{quote(case.name, safe='')}.html"


def render_report(cases: list[Case], title: str, baseline: str = "baseline", candidate: str = "candidate", details_dir: str = "report") -> str:
    """Render the lightweight index page for a set of evaluation detail pages."""
    links = "".join(f'<li><a href="{esc(details_dir)}/{esc(detail_filename(case))}">{esc(case.name)}</a></li>' for case in cases)
    body = (f'<header><h1>{esc(title)}</h1><p class="meta muted">Comparing {esc(baseline)} → {esc(candidate)}</p></header><main><h2>Evaluations</h2>'
            + (f"<ul>{links}</ul>" if cases else '<p class="muted">No evaluations were found.</p>') + "</main>")
    return document(title, body)


def build_cases(baseline_dir: str, candidate_dir: str, evals_dir: str, include_unevaluated: bool = False) -> list[Case]:
    targets = discover_targets(evals_dir)
    cases = [Case(name, targets.get(name), load_side(baseline_dir, name), load_side(candidate_dir, name)) for name in discover_cases(baseline_dir, candidate_dir)]
    return cases if include_unevaluated else [case for case in cases if case.has_llm_result]


def clear_detail_pages(detail_dir: str) -> None:
    """Remove detail pages from a previous report so filtered cases cannot linger."""
    if not os.path.isdir(detail_dir):
        return
    for entry in os.listdir(detail_dir):
        if entry.endswith(".html"):
            try:
                os.remove(os.path.join(detail_dir, entry))
            except OSError:
                pass


def version_name(path: str) -> str:
    return os.path.basename(os.path.normpath(path)) or path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", required=True, help="baseline heimdall output directory")
    parser.add_argument("--candidate", required=True, help="candidate heimdall output directory")
    parser.add_argument("--output", required=True, help="path of the index HTML file to write")
    parser.add_argument("--evals-dir", default="evals", help="eval sources, used to label targets")
    parser.add_argument("--title", default="Heimdall Evaluation Report", help="report title")
    parser.add_argument("--include-unevaluated", action="store_true", help="include contracts with no LLM evaluation in either run")
    args = parser.parse_args(argv)
    cases = build_cases(args.baseline, args.candidate, args.evals_dir, args.include_unevaluated)
    output_dir = os.path.dirname(os.path.abspath(args.output))
    detail_dir_name = os.path.splitext(os.path.basename(args.output))[0]
    detail_dir = os.path.join(output_dir, detail_dir_name)
    os.makedirs(detail_dir, exist_ok=True)
    clear_detail_pages(detail_dir)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(render_report(cases, args.title, version_name(args.baseline), version_name(args.candidate), detail_dir_name))
    for item in cases:
        with open(os.path.join(detail_dir, detail_filename(item)), "w", encoding="utf-8") as handle:
            handle.write(render_case(item, args.title, f"../{os.path.basename(args.output)}"))
    print(f"Wrote {args.output} and {len(cases)} evaluation pages in {detail_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
