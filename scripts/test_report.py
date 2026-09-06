#!/usr/bin/env python3
"""Unit tests for the static HTML evaluation report generator."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report  # noqa: E402


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def case(name="Sample", target=None, baseline=None, candidate=None):
    return report.Case(name, target, baseline or report.Side(), candidate or report.Side())


class UnifiedDiffTest(unittest.TestCase):
    def test_identical_input_produces_no_rows(self):
        self.assertEqual(report.unified_diff_rows(["a"], ["a"]), [])

    def test_rows_carry_kinds_and_line_numbers(self):
        rows = report.unified_diff_rows(["a", "b", "c"], ["a", "B", "c"])
        self.assertEqual(rows[0][0], "hunk")
        self.assertEqual(rows[2:], [("del", 2, None, "b"), ("add", None, 2, "B"), ("ctx", 3, 3, "c")])

    def test_context_is_bounded(self):
        before = [str(index) for index in range(20)]
        after = list(before)
        after[10] = "changed"
        rows = report.unified_diff_rows(before, after, context=2)
        self.assertEqual([row[3] for row in rows if row[0] == "ctx"], ["8", "9", "11", "12"])


class RenderTest(unittest.TestCase):
    def test_index_lists_only_compared_versions_and_detail_links(self):
        html = report.render_report(
            [case("One", candidate=report.Side(source="new")), case("Two")],
            "Report", "v1", "v2", "details",
        )
        self.assertIn("Comparing v1 → v2", html)
        self.assertIn('href="details/One.html"', html)
        self.assertIn('href="details/Two.html"', html)
        self.assertNotIn("LLM evaluation", html)
        self.assertNotIn("<table", html)
        self.assertNotIn("new", html)

    def test_detail_page_contains_one_case_and_full_evaluation(self):
        item = case(
            "Sample", "loops", report.Side(source="before\n", score=25, summary="old"),
            report.Side(source="after\n", score=65, summary="new", differences=["missing check"]),
        )
        html = report.render_case(item, "Report", "../report.html")
        self.assertIn('href="../report.html"', html)
        self.assertIn("Baseline", html)
        self.assertIn("Candidate", html)
        self.assertIn("old", html)
        self.assertIn("new", html)
        self.assertIn("<li>missing check</li>", html)
        self.assertIn("Unified diff", html)
        self.assertIn('class="diff-line diff-del">-before</span>', html)
        self.assertIn('class="diff-line diff-add">+after</span>', html)
        self.assertNotIn("<table", html)

    def test_detail_page_escapes_untrusted_values(self):
        html = report.render_case(case("<b>Name</b>", candidate=report.Side(source='<script>alert("x")</script>', summary="<em>x</em>", error="<u>boom</u>")), "<h9>Title</h9>")
        for raw in ("<b>Name</b>", "<script>", "<em>x</em>", "<u>boom</u>", "<h9>"):
            self.assertNotIn(raw, html)
        self.assertIn("&lt;script&gt;", html)

    def test_empty_index_and_self_contained_pages(self):
        html = report.render_report([], "Report")
        self.assertIn("No evaluations were found.", html)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertNotIn("<script", html)
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
        write(os.path.join(self.baseline, "Changed", "eval.json"), json.dumps({"score": 25, "summary": "old"}))
        write(os.path.join(self.candidate, "Changed", "decompiled.sol"), "function b() {}\n")
        write(os.path.join(self.candidate, "Changed", "eval.json"), json.dumps({"score": 65, "summary": "new", "differences": ["one"]}))
        write(os.path.join(self.candidate, "Broken", "error.txt"), "panic in decompiler\n")
        write(os.path.join(self.root, "evals", "loops", "src", "Changed.sol"), "// solidity\n")

    def test_cases_without_llm_results_are_filtered_by_default(self):
        cases = report.build_cases(self.baseline, self.candidate, os.path.join(self.root, "evals"))
        self.assertEqual([item.name for item in cases], ["Changed"])
        changed = cases[0]
        self.assertEqual(changed.target, "loops")
        self.assertEqual(changed.baseline.score, 25)
        self.assertEqual(changed.candidate.differences, ["one"])

        all_cases = report.build_cases(self.baseline, self.candidate, os.path.join(self.root, "evals"), include_unevaluated=True)
        self.assertEqual([item.name for item in all_cases], ["Broken", "Changed"])
        self.assertEqual(all_cases[0].status, "failed")

    def test_cli_writes_only_evaluated_detail_pages_and_removes_stale_pages(self):
        output = os.path.join(self.root, "reports", "comparison.html")
        stale_page = os.path.join(self.root, "reports", "comparison", "Broken.html")
        write(stale_page, "stale")
        self.assertEqual(report.main(["--baseline", self.baseline, "--candidate", self.candidate, "--evals-dir", os.path.join(self.root, "evals"), "--output", output]), 0)
        with open(output, encoding="utf-8") as handle:
            index = handle.read()
        self.assertIn("Comparing baseline → candidate", index)
        self.assertIn('href="comparison/Changed.html"', index)
        self.assertNotIn('href="comparison/Broken.html"', index)
        self.assertFalse(os.path.exists(stale_page))
        path = os.path.join(self.root, "reports", "comparison", "Changed.html")
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as handle:
            self.assertIn("Changed", handle.read())


if __name__ == "__main__":
    unittest.main()
