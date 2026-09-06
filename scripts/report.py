#!/usr/bin/env python3
"""Render a self-contained HTML report comparing baseline and candidate decompilation runs.

Each run directory is a heimdall output directory, as produced by scripts/run.sh and
scripts/eval.sh:

    <run>/<Contract>/decompiled.sol   decompiled source (absent when heimdall produced none)
    <run>/<Contract>/eval.json        judge result: {"score", "summary", "differences"}
    <run>/<Contract>/error.txt        error text, written when the run failed

Every case present in either run is rendered, including cases whose output did not change.
The report embeds its own styles and has no external asset, script or network dependency.
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import os
import sys
from dataclasses import dataclass, field

DIFF_CONTEXT = 3

STATUS_LABELS = {
    "pass": "pass",
    "failed": "failed",
    "missing": "missing output",
}

STYLES = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2rem 1.5rem; background: #ffffff; color: #24292f;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 14px; line-height: 1.5;
}
.wrap { max-width: 1100px; margin: 0 auto; }
h1 { font-size: 1.6rem; font-weight: 600; margin: 0 0 .25rem; }
h2 { font-size: 1.1rem; font-weight: 600; margin: 0; }
h3 { font-size: .8rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em;
     color: #57606a; margin: 0 0 .5rem; }
p { margin: .25rem 0; }
.subtitle { color: #57606a; margin-bottom: 1.5rem; }
.stats { display: flex; flex-wrap: wrap; gap: 1.5rem; margin: 0;
         border: 1px solid #d0d7de; border-radius: 6px; padding: 1rem 1.25rem; background: #f6f8fa; }
.stats div { margin: 0; }
.stats dt { font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; color: #57606a; }
.stats dd { margin: 0; font-size: 1.25rem; font-weight: 600; }
.case { border: 1px solid #d0d7de; border-radius: 6px; margin-top: 1.5rem; overflow: hidden; }
.case > header { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem;
                 padding: .75rem 1rem; background: #f6f8fa; border-bottom: 1px solid #d0d7de; }
.case > section { padding: 1rem; border-top: 1px solid #d0d7de; }
.case > section:first-of-type { border-top: none; }
.badge { font-size: .75rem; font-weight: 600; padding: .1rem .5rem; border-radius: 999px;
         border: 1px solid; text-transform: uppercase; letter-spacing: .03em; }
.badge-pass { color: #1a7f37; border-color: #aceebb; background: #dafbe1; }
.badge-failed { color: #cf222e; border-color: #ffcecb; background: #ffebe9; }
.badge-missing { color: #9a6700; border-color: #f5d90a; background: #fff8c5; }
.chip { font-size: .75rem; color: #57606a; border: 1px solid #d0d7de; border-radius: 999px;
        padding: .1rem .5rem; background: #ffffff; }
.panes { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 800px) { .panes { grid-template-columns: 1fr; } }
pre { margin: 0; padding: .75rem; background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px;
      overflow-x: auto; max-height: 30rem; font-size: 12px; line-height: 1.45;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
.empty { color: #57606a; font-style: italic; }
.comment { border: 1px solid #d0d7de; border-radius: 6px; padding: .75rem; background: #ffffff; }
.comment + .comment { margin-top: .75rem; }
.comment ul { margin: .5rem 0 0; padding-left: 1.25rem; }
.error { border: 1px solid #ffcecb; border-radius: 6px; background: #ffebe9; padding: .75rem; }
.error + .error { margin-top: .75rem; }
table.diff { width: 100%; border-collapse: collapse; border: 1px solid #d0d7de; border-radius: 6px;
             font-size: 12px; line-height: 1.45;
             font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
table.diff caption { text-align: left; color: #57606a; padding-bottom: .5rem; }
table.diff td { padding: 0 .5rem; vertical-align: top; white-space: pre-wrap; word-break: break-word; }
td.ln { width: 1%; min-width: 3rem; text-align: right; color: #57606a; background: #f6f8fa;
        border-right: 1px solid #d0d7de; user-select: none; }
td.sign { width: 1%; padding: 0 .25rem; color: #57606a; user-select: none; }
tr.add td { background: #e6ffec; }
tr.add td.ln { background: #ccffd8; }
tr.del td { background: #ffebe9; }
tr.del td.ln { background: #ffd7d5; }
tr.hunk td { background: #f6f8fa; color: #57606a; }
"""


@dataclass
class Side:
    """One side (baseline or candidate) of a single evaluation case."""

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


def read_text(path: str) -> str | None:
    """Return the contents of `path`, or None when it is absent or unreadable."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def load_side(run_dir: str | None, name: str) -> Side:
    """Load one case's artifacts from a run directory."""
    if run_dir is None:
        return Side()

    case_dir = os.path.join(run_dir, name)
    error = read_text(os.path.join(case_dir, "error.txt"))
    side = Side(
        source=read_text(os.path.join(case_dir, "decompiled.sol")),
        error=error.strip() or None if error else None,
    )

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
    """Return the sorted union of case names across every run directory."""
    names: set[str] = set()
    for run_dir in run_dirs:
        try:
            entries = os.listdir(run_dir)
        except OSError:
            continue
        names.update(
            entry
            for entry in entries
            if not entry.startswith(".") and os.path.isdir(os.path.join(run_dir, entry))
        )
    return sorted(names)


def discover_targets(evals_dir: str) -> dict[str, str]:
    """Map contract name to the eval target that defines it."""
    targets: dict[str, str] = {}
    try:
        entries = sorted(os.listdir(evals_dir))
    except OSError:
        return targets
    for target in entries:
        src = os.path.join(evals_dir, target, "src")
        try:
            sources = sorted(os.listdir(src))
        except OSError:
            continue
        for sol in sources:
            if sol.endswith(".sol"):
                targets.setdefault(sol[: -len(".sol")], target)
    return targets


def split_lines(source: str | None) -> list[str]:
    if not source:
        return []
    return source.splitlines()


def unified_diff_rows(before: list[str], after: list[str], context: int = DIFF_CONTEXT) -> list[tuple]:
    """Build unified diff rows as (kind, old_lineno, new_lineno, text) tuples.

    `kind` is one of "hunk", "ctx", "add" or "del"; line numbers are 1-based, or None
    where the line does not exist on that side.
    """
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    rows: list[tuple] = []
    for group in matcher.get_grouped_opcodes(context):
        old_start, old_end = group[0][1], group[-1][2]
        new_start, new_end = group[0][3], group[-1][4]
        rows.append(
            (
                "hunk",
                None,
                None,
                f"@@ -{old_start + 1},{old_end - old_start} +{new_start + 1},{new_end - new_start} @@",
            )
        )
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                for offset, line in enumerate(before[i1:i2]):
                    rows.append(("ctx", i1 + offset + 1, j1 + offset + 1, line))
                continue
            for offset, line in enumerate(before[i1:i2]):
                rows.append(("del", i1 + offset + 1, None, line))
            for offset, line in enumerate(after[j1:j2]):
                rows.append(("add", None, j1 + offset + 1, line))
    return rows


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_source_pane(title: str, side: Side) -> str:
    if side.source is None:
        body = '<p class="empty">No decompiled output was produced.</p>'
    elif not side.source.strip():
        body = '<p class="empty">Decompiled output is empty.</p>'
    else:
        body = f"<pre><code>{esc(side.source)}</code></pre>"
    return f"<section><h3>{esc(title)}</h3>{body}</section>"


def render_comment(title: str, side: Side) -> str:
    if not side.has_comment:
        return (
            f'<div class="comment"><h3>{esc(title)}</h3>'
            '<p class="empty">No LLM evaluation was recorded for this case.</p></div>'
        )
    parts = [f'<div class="comment"><h3>{esc(title)}</h3>']
    score = "not scored" if side.score is None else f"{side.score}/100"
    parts.append(f"<p><strong>Score:</strong> {esc(score)}</p>")
    if side.summary:
        parts.append(f"<p>{esc(side.summary)}</p>")
    else:
        parts.append('<p class="empty">No summary was recorded.</p>')
    if side.differences:
        items = "".join(f"<li>{esc(item)}</li>" for item in side.differences)
        parts.append(f"<ul>{items}</ul>")
    parts.append("</div>")
    return "".join(parts)


def render_diff(case: Case) -> str:
    rows = unified_diff_rows(split_lines(case.baseline.source), split_lines(case.candidate.source))
    if not rows:
        note = (
            "Decompiled output is identical between baseline and candidate."
            if case.candidate.source is not None
            else "No decompiled output on either side, so there is nothing to diff."
        )
        return f'<section><h3>Unified diff</h3><p class="empty">{esc(note)}</p></section>'

    signs = {"add": "+", "del": "-", "ctx": " ", "hunk": ""}
    body = []
    for kind, old_no, new_no, text in rows:
        body.append(
            f'<tr class="{kind}">'
            f'<td class="ln">{esc(old_no) if old_no else ""}</td>'
            f'<td class="ln">{esc(new_no) if new_no else ""}</td>'
            f'<td class="sign">{signs[kind]}</td>'
            f"<td>{esc(text)}</td>"
            "</tr>"
        )
    return (
        "<section><h3>Unified diff</h3>"
        f'<table class="diff"><caption>Unified diff of {esc(case.name)}, baseline to candidate. '
        "Columns: baseline line, candidate line, change marker, content.</caption>"
        f"<tbody>{''.join(body)}</tbody></table></section>"
    )


def render_case(case: Case) -> str:
    status = case.status
    chips = [f'<span class="chip">{esc("changed" if case.changed else "unchanged")}</span>']
    if case.target:
        chips.insert(0, f'<span class="chip">target: {esc(case.target)}</span>')
    if case.baseline.score is not None or case.candidate.score is not None:
        before = "n/a" if case.baseline.score is None else case.baseline.score
        after = "n/a" if case.candidate.score is None else case.candidate.score
        chips.append(f'<span class="chip">score: {esc(before)} &rarr; {esc(after)}</span>')

    errors = []
    for label, side in (("Baseline error", case.baseline), ("Candidate error", case.candidate)):
        if side.error:
            errors.append(
                f'<div class="error"><h3>{esc(label)}</h3><pre><code>{esc(side.error)}</code></pre></div>'
            )

    slug = esc(case.name)
    return (
        f'<article class="case" id="case-{slug}" aria-labelledby="heading-{slug}">'
        f'<header><h2 id="heading-{slug}">{slug}</h2>'
        f'<span class="badge badge-{status}">{esc(STATUS_LABELS[status])}</span>'
        f"{''.join(chips)}</header>"
        + (f"<section>{''.join(errors)}</section>" if errors else "")
        + "<section><h3>LLM evaluation</h3>"
        + render_comment("Baseline", case.baseline)
        + render_comment("Candidate", case.candidate)
        + "</section>"
        + '<section><div class="panes">'
        + render_source_pane("Before (baseline)", case.baseline)
        + render_source_pane("After (candidate)", case.candidate)
        + "</div></section>"
        + render_diff(case)
        + "</article>"
    )


def render_summary(cases: list[Case]) -> str:
    counts = {
        "Evaluations": len(cases),
        "Passing": sum(1 for case in cases if case.status == "pass"),
        "Failed": sum(1 for case in cases if case.status == "failed"),
        "Missing output": sum(1 for case in cases if case.status == "missing"),
        "Changed": sum(1 for case in cases if case.changed),
    }
    items = "".join(
        f"<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>" for label, value in counts.items()
    )
    return f'<section aria-label="Summary"><dl class="stats">{items}</dl></section>'


def render_report(cases: list[Case], title: str) -> str:
    """Render the full HTML document. Output depends only on the given cases and title."""
    body = (
        "".join(render_case(case) for case in cases)
        if cases
        else '<p class="empty">No evaluations were found.</p>'
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n<style>{STYLES}</style>\n</head>\n<body>\n"
        f'<div class="wrap">\n<header><h1>{esc(title)}</h1>'
        '<p class="subtitle">Baseline versus candidate decompilation for every evaluation case.</p>'
        "</header>\n"
        f"{render_summary(cases)}\n<main>{body}</main>\n</div>\n</body>\n</html>\n"
    )


def build_cases(baseline_dir: str, candidate_dir: str, evals_dir: str) -> list[Case]:
    targets = discover_targets(evals_dir)
    return [
        Case(
            name=name,
            target=targets.get(name),
            baseline=load_side(baseline_dir, name),
            candidate=load_side(candidate_dir, name),
        )
        for name in discover_cases(baseline_dir, candidate_dir)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", required=True, help="baseline heimdall output directory")
    parser.add_argument("--candidate", required=True, help="candidate heimdall output directory")
    parser.add_argument("--output", required=True, help="path of the HTML file to write")
    parser.add_argument("--evals-dir", default="evals", help="eval sources, used to label targets")
    parser.add_argument("--title", default="Heimdall Evaluation Report", help="report title")
    args = parser.parse_args(argv)

    cases = build_cases(args.baseline, args.candidate, args.evals_dir)
    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(render_report(cases, args.title))

    print(f"Wrote {args.output} ({len(cases)} evaluations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
