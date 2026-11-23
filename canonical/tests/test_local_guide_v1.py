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
        # a single matching token is not a conclusion
        (self._tmp / "README.md").write_text(
            "dial lock cadence: the dial lock is not the goal here\n",
            encoding="utf-8")
        out = guide.lookup("how to use something entirely different",
                           root=self._tmp, min_tokens=2)
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
