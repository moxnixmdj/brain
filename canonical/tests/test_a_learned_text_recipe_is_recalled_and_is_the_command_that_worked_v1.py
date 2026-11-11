#!/usr/bin/env python3
"""Learning is only real if the SECOND call is a recall of the command that worked.

Three defects made that false while every surface said it was true, and each is
pinned here so it cannot come back:

  1. recall() re-verified without the goal, so every .txt plan failed
     carries_content_evidence and the recall path could never return.
  2. _verify_plan replayed on ComputerEnv() with no seed, so the plan ran against
     the one-line sandbox file and was compared to the caller's real input.
  3. _recipe_of reported a command it had derived without the goal, so a goal
     learned as `sort --unique {input}` handed back plain `sort {input}` -- a
     receipt that cannot do the job it claims.

Each symptom was a speedup with no replay. A speedup is not memory.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load(name: str, rel: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tv = _load("canonical.runtime.text_relation_verifier_v1",
           "canonical/runtime/text_relation_verifier_v1.py")


class LearnedTextRecipeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self._old = os.environ.get("BRAIN_TRANSFER_LEARNING_STATE")
        # A STORE PER TEST. transfer_learning_v1 reads its path at import time and
        # caches nothing per-call, so a shared store makes the FIRST call of a later
        # test a recall of an earlier test's result -- measured: test #1 reported
        # from_memory=True on its "first" call and failed for a reason that had
        # nothing to do with the code under test. A test whose result depends on the
        # order tests run in is not a test.
        os.environ["BRAIN_TRANSFER_LEARNING_STATE"] = tempfile.mkdtemp() + "/tl.json"
        import canonical.runtime.transfer_learning_v1 as tl
        tl.STATE_PATH = os.environ["BRAIN_TRANSFER_LEARNING_STATE"]
        tl._CACHE = {} if hasattr(tl, "_CACHE") else None
        for n in ("notes.txt", "emails.txt", "list.txt"):
            (self.d / n).write_bytes(tv.probe_seed()["input.txt"])
        self.cenv = _load("canonical.runtime.computer_env_v1",
                          "canonical/runtime/computer_env_v1.py")
        # the module reads its store path at import time
        import canonical.runtime.transfer_learning_v1 as tl  # noqa: F401

    def tearDown(self):
        if self._old is None:
            os.environ.pop("BRAIN_TRANSFER_LEARNING_STATE", None)
        else:
            os.environ["BRAIN_TRANSFER_LEARNING_STATE"] = self._old
        self._tmp.cleanup()

    def _discover(self, goal, src):
        return self.cenv.discover(goal, learn=True, seed_file=str(self.d / src))

    def test_the_second_call_is_a_recall_not_a_search(self):
        goal, src = "sort notes.txt into sorted.txt", "notes.txt"
        first = self._discover(goal, src)
        self.assertTrue(first.get("closed"), first)
        self.assertFalse(first.get("from_memory"),
                         "the first attempt cannot come from memory")
        second = self._discover(goal, src)
        self.assertTrue(second.get("closed"), second)
        self.assertTrue(second.get("from_memory"),
                        "the same problem was learned twice")
        self.assertEqual(second.get("status"), "PASS__RECALLED_AND_REVERIFIED")

    def test_the_recalled_receipt_is_the_command_that_actually_worked(self):
        # deduplication needs a FLAG. A recall that hands back plain `sort` is a
        # receipt for a command that does not deduplicate anything.
        goal, src = "deduplicate emails.txt into unique.txt", "emails.txt"
        self._discover(goal, src)
        second = self._discover(goal, src)
        self.assertTrue(second.get("closed"), second)
        argv = (second.get("recipe") or {}).get("argv") or []
        self.assertIn("--unique", argv,
                      "the recalled receipt must carry the flag that does the job")
        self.assertEqual((second.get("recipe") or {}).get("program"), "sort")

    def test_a_recalled_recipe_is_still_checked_against_real_bytes(self):
        # Memory must not become a licence to stop verifying: the file the recalled
        # plan produces is re-checked by the relation verifier every time.
        goal, src = "reverse each line of list.txt into rev.txt", "list.txt"
        self._discover(goal, src)
        second = self._discover(goal, src)
        self.assertTrue(second.get("closed"), second)
        self.assertEqual(second.get("verification"), "EACH_LINE_REVERSED")

    def test_different_goals_get_different_flags_from_the_same_program(self):
        sort_goal = self._discover("sort notes.txt into sorted.txt", "notes.txt")
        dedupe_goal = self._discover("deduplicate emails.txt into unique.txt", "emails.txt")
        self.assertEqual((sort_goal.get("recipe") or {}).get("program"), "sort")
        self.assertEqual((dedupe_goal.get("recipe") or {}).get("program"), "sort")
        self.assertNotEqual((sort_goal.get("recipe") or {}).get("argv"),
                            (dedupe_goal.get("recipe") or {}).get("argv"),
                            "one program, two jobs, must not use one argv for both")


if __name__ == "__main__":
    unittest.main(verbosity=2)
