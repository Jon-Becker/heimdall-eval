#!/usr/bin/env python3
"""Unit tests for the HTML evaluation report generator."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import report  # noqa: E402


def write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def case(name="Sample", target=None, baseline=None, candidate=None) -> report.Case:
    return report.Case(
        name=name,
        target=target,
        baseline=baseline or report.Side(),
        candidate=candidate or report.Side(),
    )


class UnifiedDiffTest(unittest.TestCase):
    def test_identical_input_produces_no_rows(self):
        lines = ["a", "b", "c"]
        self.assertEqual(report.unified_diff_rows(lines, list(lines)), [])

    def test_rows_carry_kinds_and_line_numbers(self):
        rows = report.unified_diff_rows(["a", "b", "c"], ["a", "B", "c"])
        self.assertEqual(rows[0][0], "hunk")
        self.assertEqual(
            [(kind, old, new, text) for kind, old, new, text in rows[1:]],
            [
                ("ctx", 1, 1, "a"),
                ("del", 2, None, "b"),
                ("add", None, 2, "B"),
                ("ctx", 3, 3, "c"),
            ],
        )

    def test_context_is_bounded(self):
        before = [str(index) for index in range(20)]
        after = list(before)
        after[10] = "changed"
        rows = report.unified_diff_rows(before, after, context=2)
        self.assertEqual([row[3] for row in rows if row[0] == "ctx"], ["8", "9", "11", "12"])

    def test_pure_addition_and_deletion(self):
        added = report.unified_diff_rows([], ["only"])
        self.assertEqual([(row[0], row[1], row[2]) for row in added[1:]], [("add", None, 1)])
        removed = report.unified_diff_rows(["only"], [])
        self.assertEqual([(row[0], row[1], row[2]) for row in removed[1:]], [("del", 1, None)])


class EscapingTest(unittest.TestCase):
    def test_source_is_escaped(self):
        payload = '<script>alert("x" & \'y\')</script>'
        html = report.render_report(
            [case(candidate=report.Side(source=payload), baseline=report.Side(source="clean"))],
            "Report",
        )
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot; &amp; &#x27;y&#x27;)", html)

    def test_comments_errors_and_names_are_escaped(self):
        html = report.render_report(
            [
                case(
                    name="<b>Name</b>",
                    target="<i>target</i>",
                    candidate=report.Side(
                        source="x",
                        summary="<em>summary</em>",
                        differences=["<hr>diff"],
                        error="<u>boom</u>",
                    ),
                )
            ],
            "<h9>Title</h9>",
        )
        for raw in ("<b>Name</b>", "<i>target</i>", "<em>summary</em>", "<hr>diff", "<u>boom</u>", "<h9>"):
            self.assertNotIn(raw, html)
        self.assertIn("&lt;em&gt;summary&lt;/em&gt;", html)
        self.assertIn("&lt;u&gt;boom&lt;/u&gt;", html)


class RenderCaseTest(unittest.TestCase):
    def test_unchanged_case_is_rendered_with_explicit_empty_diff(self):
        html = report.render_report(
            [
                case(
                    baseline=report.Side(source="same\n"),
                    candidate=report.Side(source="same\n"),
                )
            ],
            "Report",
        )
        self.assertIn("Sample", html)
        self.assertIn("unchanged", html)
        self.assertIn("Decompiled output is identical between baseline and candidate.", html)
        self.assertNotIn("<table", html)

    def test_changed_case_renders_diff_table_and_both_panes(self):
        html = report.render_report(
            [
                case(
                    baseline=report.Side(source="before\n"),
                    candidate=report.Side(source="after\n"),
                )
            ],
            "Report",
        )
        self.assertIn('<table class="diff">', html)
        self.assertIn('<tr class="del">', html)
        self.assertIn('<tr class="add">', html)
        self.assertIn("Before (baseline)", html)
        self.assertIn("After (candidate)", html)
        self.assertIn(">changed<", html)

    def test_failed_case_shows_badge_and_error(self):
        html = report.render_report(
            [case(candidate=report.Side(error="heimdall exited with 101"))], "Report"
        )
        self.assertIn('class="badge badge-failed"', html)
        self.assertIn("failed", html)
        self.assertIn("heimdall exited with 101", html)

    def test_missing_output_case_is_explicit(self):
        html = report.render_report([case(baseline=report.Side(source="before\n"))], "Report")
        self.assertIn('class="badge badge-missing"', html)
        self.assertIn("missing output", html)
        self.assertIn("No decompiled output was produced.", html)

    def test_comments_are_present_for_every_case(self):
        html = report.render_report(
            [
                case(
                    name="WithComment",
                    baseline=report.Side(source="a", score=25, summary="baseline summary"),
                    candidate=report.Side(
                        source="b", score=65, summary="candidate summary", differences=["missing check"]
                    ),
                ),
                case(name="NoComment", candidate=report.Side(source="b")),
            ],
            "Report",
        )
        self.assertIn("baseline summary", html)
        self.assertIn("candidate summary", html)
        self.assertIn("<li>missing check</li>", html)
        self.assertIn("score: 25 &rarr; 65", html)
        self.assertEqual(html.count("No LLM evaluation was recorded for this case."), 2)

    def test_empty_report_is_still_valid(self):
        html = report.render_report([], "Report")
        self.assertIn("No evaluations were found.", html)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))

    def test_report_is_self_contained(self):
        html = report.render_report([case(candidate=report.Side(source="a"))], "Report")
        self.assertNotIn("<script", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("<link", html)


class ArtifactLoadingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        self.baseline = os.path.join(self.root, "baseline")
        self.candidate = os.path.join(self.root, "candidate")

        write(os.path.join(self.baseline, "Changed", "decompiled.sol"), "function a() {}\n")
        write(
            os.path.join(self.baseline, "Changed", "eval.json"),
            json.dumps({"score": 25, "summary": "old", "differences": []}),
        )
        write(os.path.join(self.candidate, "Changed", "decompiled.sol"), "function b() {}\n")
        write(
            os.path.join(self.candidate, "Changed", "eval.json"),
            json.dumps({"score": 65, "summary": "new", "differences": ["one"]}),
        )

        write(os.path.join(self.baseline, "Unchanged", "decompiled.sol"), "same\n")
        write(os.path.join(self.candidate, "Unchanged", "decompiled.sol"), "same\n")

        write(os.path.join(self.baseline, "Broken", "decompiled.sol"), "old\n")
        write(os.path.join(self.candidate, "Broken", "error.txt"), "panic in decompiler\n")

        write(os.path.join(self.baseline, "Gone", "decompiled.sol"), "old\n")
        write(os.path.join(self.candidate, "Invalid", "decompiled.sol"), "new\n")
        write(os.path.join(self.candidate, "Invalid", "eval.json"), "not json")

        write(os.path.join(self.root, "evals", "loops", "src", "Changed.sol"), "// solidity\n")

    def build(self):
        return report.build_cases(
            self.baseline, self.candidate, os.path.join(self.root, "evals")
        )

    def test_cases_are_discovered_from_both_runs_in_sorted_order(self):
        self.assertEqual(
            [item.name for item in self.build()],
            ["Broken", "Changed", "Gone", "Invalid", "Unchanged"],
        )

    def test_statuses_and_metadata(self):
        cases = {item.name: item for item in self.build()}
        self.assertEqual(cases["Changed"].status, "pass")
        self.assertTrue(cases["Changed"].changed)
        self.assertEqual(cases["Changed"].target, "loops")
        self.assertEqual(cases["Changed"].baseline.score, 25)
        self.assertEqual(cases["Changed"].candidate.differences, ["one"])
        self.assertEqual(cases["Unchanged"].status, "pass")
        self.assertFalse(cases["Unchanged"].changed)
        self.assertEqual(cases["Broken"].status, "failed")
        self.assertEqual(cases["Broken"].candidate.error, "panic in decompiler")
        self.assertEqual(cases["Gone"].status, "missing")
        self.assertIsNone(cases["Invalid"].target)
        self.assertFalse(cases["Invalid"].candidate.has_comment)

    def test_missing_run_directory_yields_no_cases(self):
        self.assertEqual(report.discover_cases(os.path.join(self.root, "absent")), [])

    def test_cli_writes_a_stable_report_covering_every_case(self):
        outputs = []
        for name in ("first.html", "second.html"):
            path = os.path.join(self.root, "reports", name)
            self.assertEqual(
                report.main(
                    [
                        "--baseline", self.baseline,
                        "--candidate", self.candidate,
                        "--evals-dir", os.path.join(self.root, "evals"),
                        "--output", path,
                    ]
                ),
                0,
            )
            with open(path, encoding="utf-8") as handle:
                outputs.append(handle.read())

        self.assertEqual(outputs[0], outputs[1])
        html = outputs[0]
        for name in ("Broken", "Changed", "Gone", "Invalid", "Unchanged"):
            self.assertIn(f'id="case-{name}"', html)
        self.assertIn("panic in decompiler", html)
        self.assertIn("Decompiled output is identical between baseline and candidate.", html)


if __name__ == "__main__":
    unittest.main()
