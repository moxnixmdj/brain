#!/usr/bin/env python3
"""Tests for the local instant-knowledge tier (local_guide_v1).

The local tier is offline, completeness-gated, and never counted as Brain
capability. These tests fail closed.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import local_guide_v1 as guide


class LocalGuideTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="local-guide-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_matching_doc_returns_evidence(self):
        (self._tmp / "README.md").write_text(
            "# Dial Locks\n\nHow to use dial lock: turn dial 0, dial 1, dial 2.\n"
            "The lock accepts three dials. Open the dial lock by setting each dial.\n"
            "A successful open is observable: all dials equal the target.\n",
            encoding="utf-8")
        out = guide.lookup("how to use dial lock", root=self._tmp)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["status"], "PASS__LOCAL_GUIDE_FOUND")
        self.assertGreaterEqual(out["score"], 2)
        self.assertEqual(out["authority"], "EXTERNAL_LOCAL_DOCS_RETRIEVED")
        self.assertTrue(any("README" in d["path"] for d in out["documents"]))
        self.assertTrue(any(d.get("snippet") for d in out["documents"]))

    def test_no_matching_doc_is_honest_open(self):
        (self._tmp / "README.md").write_text(
            "# Unrelated\n\nNothing relevant here.\n", encoding="utf-8")
        out = guide.lookup("how to use dial lock", root=self._tmp)
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__LOCAL_GUIDE_NOT_FOUND")
        self.assertEqual(out["documents"], [])
        self.assertIn("NONE__LOCAL_GUIDE_UNANSWERED", out["authority"])

    def test_empty_query_fails_closed(self):
        (self._tmp / "README.md").write_text("# Doc\n", encoding="utf-8")
        out = guide.lookup("", root=self._tmp)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__LOCAL_GUIDE_EMPTY_QUERY")

    def test_thin_match_is_not_a_conclusion(self):
        # a single matching token among a big query is not a conclusion
        (self._tmp / "README.md").write_text(
            "something in the README\n",
            encoding="utf-8")
        out = guide.lookup("how to use something entirely different about the world",
                           root=self._tmp)
        self.assertFalse(out["pass"], out)

    def test_skipped_directories_are_never_scanned(self):
        for sub in (".git", "node_modules"):
            d = self._tmp / sub
            d.mkdir()
            (d / "README.md").write_text(
                "dial lock node_modules .git scan and observe\n", encoding="utf-8")
        (self._tmp / "README.md").write_text(
            "unrelated\n", encoding="utf-8")
        out = guide.lookup("how to use dial lock", root=self._tmp)
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["documents"], [])

    def test_max_files_bound_is_respected(self):
        for i in range(600):
            (self._tmp / f"doc_{i:03d}.md").write_text(
                f"dial lock doc {i}\n", encoding="utf-8")
        out = guide.lookup("how to use dial lock", root=self._tmp)
        # bound is 500; a pass must still come from real evidence, not fabricated
        self.assertLessEqual(out["documents_scanned"], 500)
        self.assertLessEqual(len(out["documents"]), 5)


class ToolGuideTierTests(unittest.TestCase):
    """The tool-help/man-page tier: the standardized offline contract between a
    tool and its user -- offline, version-matched, completeness-gated."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="local-guide-tool-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_help_tier_answers_for_a_real_short_tool_name(self):
        # jq is a real tool whose own --help output is a real guide. Short tool
        # names (2 chars) must survive the query tokenizer -- the honest bug
        # this pins.
        out = guide.lookup("how to use jq", tools=["jq"])
        self.assertTrue(out["pass"], out)
        self.assertIn("tool_help", out["sources_answered"])
        self.assertTrue(any(d["source"] == "tool_help" for d in out["documents"]))

    def test_help_tier_missing_tool_fails_closed(self):
        out = guide.lookup("how to use nosuchxyz", tools=["nosuchxyz"])
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["documents"], [])

    def test_help_tier_missing_output_falls_back_to_man_page(self):
        # a stub tool with no --help output honestly falls through to the man page
        stub = self._tmp / "nohelp-tool"
        stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        stub.chmod(0o755)
        man1 = self._tmp / "man1"
        man1.mkdir()
        (man1 / "nohelp-tool.1").write_text(
            ".TH NOHELP-TOOL 1 2026\n.SH NAME\n"
            "nohelp-tool - a stub with no help text\n.SH SYNOPSIS\n"
            "nohelp-tool <args>\n.SH DESCRIPTION\n"
            "nohelp-tool does the useful thing. Use nohelp-tool to run the job.\n",
            encoding="utf-8")
        out = guide.lookup("how to use nohelp-tool", tools=[str(stub)],
                           man_root=self._tmp)
        self.assertTrue(out["pass"], out)
        self.assertIn("man_page", out["sources_answered"])
        self.assertTrue(any(d["source"] == "man_page" for d in out["documents"]))

    def test_help_tier_tool_without_any_guide_fails_closed(self):
        # a genuinely broken tool still produces an honest OPEN (no help, no man page)
        stub = self._tmp / "ghost-tool"
        stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        stub.chmod(0o755)
        out = guide.lookup("how to use ghost-tool", tools=[str(stub)],
                           man_root=self._tmp)
        # the help tier found nothing and the man tier found nothing -> no evidence
        self.assertFalse(out["pass"], out)

    def test_tool_help_never_fabricates_a_plan(self):
        # the tool-guide tier orients; it must not itself become a plan
        out = guide.lookup("how to use jq", tools=["jq"])
        self.assertTrue(out["pass"], out)
        for d in out["documents"]:
            self.assertIn(d["source"], ("tool_help", "man_page", "local_md"))


class LocalGuideIntegrationTests(unittest.TestCase):
    """The Perfect Algorithm's local tier: when the scan cannot plan, the
    receipt names the local tier and returns honestly."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="local-guide-int-"))
        self._mem = self._tmp / "memory.json"
        self._local = self._tmp / "docs"
        self._local.mkdir(parents=True)
        (self._local / "README.md").write_text(
            "# Dial Locks\n\nHow to use dial lock: turn dial 0, dial 1, dial 2.\n"
            "The lock accepts three dials; set each dial to its target value.\n",
            encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_local_guide_tier_answers_when_plan_fails(self):
        from canonical.swe_kernel import perfect_algorithm_v1 as pa
        from canonical.tests.test_perfect_algorithm_v1 import Lock, _lock_heuristic

        target = (7, 2, 9)
        env = Lock(target=target)
        goal_pred = lambda obs: obs == target
        # budget 1: the scan cannot see the goal state -> plan fails
        out = pa.run(env, "open dial lock", ["d0", "d1", "d2"],
                     goal_predicate=goal_pred,
                     goal_family="dial_lock", env_kind="dial_lock",
                     memory_path_=self._mem, budget=1, max_depth=1, seed=0,
                     heuristic=lambda obs: _lock_heuristic(obs, target),
                     allow_instant_knowledge=True, local_root=self._local)
        self.assertEqual(out["status"], "OPEN__NO_PLAN_AFTER_SCAN")
        instant = out["steps"]["instant_knowledge"]
        self.assertEqual(instant["status"], "PASS__LOCAL_GUIDE_FOUND", instant)
        self.assertEqual(instant["tier"], "local")
        self.assertEqual(instant["authority"], "EXTERNAL_LOCAL_DOCS_RETRIEVED")
        self.assertGreaterEqual(instant["documents_returned"], 1)
        self.assertEqual(instant["local_guide"]["status"], "PASS__LOCAL_GUIDE_FOUND")
        self.assertTrue(instant["local_guide"]["documents"])
        # the local-guide tier never fabricates a plan; the receipt says OPEN
        self.assertFalse(out.get("pass", False))

    def test_local_guide_misses_stay_open_and_do_not_fabricate(self):
        from canonical.swe_kernel import perfect_algorithm_v1 as pa
        from canonical.tests.test_perfect_algorithm_v1 import Lock, _lock_heuristic

        (self._local / "README.md").write_text(
            "# Unrelated guide\n\nNothing about dial locks here.\n", encoding="utf-8")
        target = (7, 2, 9)
        env = Lock(target=target)
        goal_pred = lambda obs: obs == target
        out = pa.run(env, "open dial lock", ["d0", "d1", "d2"],
                     goal_predicate=goal_pred,
                     goal_family="dial_lock", env_kind="dial_lock",
                     memory_path_=self._mem, budget=1, max_depth=1, seed=0,
                     heuristic=lambda obs: _lock_heuristic(obs, target),
                     allow_instant_knowledge=False, local_root=self._local)
        self.assertEqual(out["status"], "OPEN__NO_PLAN_AFTER_SCAN")
        instant = out["steps"]["instant_knowledge"]
        self.assertEqual(instant["local_guide"]["status"], "OPEN__LOCAL_GUIDE_NOT_FOUND", instant)
        self.assertFalse(instant.get("complete", False))
        # The web tier is NOT asked unless the caller explicitly passes the
        # gate; the run must not return PASS — it must remain an honest OPEN.
        self.assertEqual(instant.get("tier"), "local")
        self.assertFalse(out.get("pass", False))


if __name__ == "__main__":
    unittest.main()
