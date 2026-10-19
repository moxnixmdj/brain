#!/usr/bin/env python3
"""The computer as an environment: find out by acting.

Every other channel needs something given -- a registered capability, a
format in a table, a module the goal named, a source that answered. This one
needs only a directory it may act in, and it discovers which program does
the job by running them and watching.

These use a real directory, real subprocesses and the real learner. A
sabotaged environment -- one that does not really reset, or whose state
ignores content -- must fail here.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile
import unittest

from canonical.runtime import computer_env_v1 as cenv

ROOT = pathlib.Path(__file__).resolve().parents[2]


class EnvCase(unittest.TestCase):
    def setUp(self) -> None:
        # Both modules resolve STATE_PATH at import time, so the env var is
        # useless once imported: patch the attribute, and never let a test
        # write into the repository's real state.
        from canonical.runtime import curriculum_v1
        from canonical.runtime import transfer_learning_v1
        self.tmp = tempfile.mkdtemp(prefix="brain-cenv-")
        self._saved = (curriculum_v1.STATE_PATH,
                       transfer_learning_v1.STATE_PATH)
        curriculum_v1.STATE_PATH = os.path.join(self.tmp, "curriculum.json")
        transfer_learning_v1.STATE_PATH = os.path.join(self.tmp, "transfer.json")

    def tearDown(self) -> None:
        from canonical.runtime import curriculum_v1
        from canonical.runtime import transfer_learning_v1
        curriculum_v1.STATE_PATH, transfer_learning_v1.STATE_PATH = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def env(self, **kw) -> cenv.ComputerEnv:
        e = cenv.ComputerEnv(**kw)
        self.addCleanup(e.close)
        return e


# --------------------------------------------------------------------------- #
# the environment must be real
# --------------------------------------------------------------------------- #
class EnvironmentTests(EnvCase):
    def test_programs_are_discovered_from_path_not_written_down(self):
        found = cenv.installed_programs(limit=400)
        self.assertGreater(len(found), 20, "almost nothing was discovered")
        for name in ("python3",):
            self.assertIn(name, found)

    def test_dangerous_programs_are_never_offered_as_actions(self):
        found = set(cenv.installed_programs(limit=400))
        for bad in ("rm", "shutdown", "mkfs", "dd"):
            self.assertNotIn(bad, found, "%s must never be an action" % bad)

    def test_reset_restores_the_same_state_every_time(self):
        e = self.env()
        first = e.state()
        e.act("run_true") if "run_true" in e.action_names else None
        e.reset()
        self.assertEqual(e.state(), first, "reset did not restore the state")

    def test_the_state_depends_on_content_not_only_names(self):
        """Two files with the same name and different bytes are not the same
        state. A learner that cannot tell them apart 'achieves' goals it
        never achieved."""
        e = self.env()
        (e.root / "x.txt").write_bytes(b"aaa")
        a = e.state()
        e.reset()
        (e.root / "x.txt").write_bytes(b"bbb")
        b = e.state()
        self.assertNotEqual(a, b, "content was ignored by the state")

    def test_snapshot_really_undoes_an_action(self):
        e = self.env()
        e.register(cenv.program_actions(e, programs=["gzip"]))
        before = e.listing()
        token = e.snapshot()
        e.act("run_gzip")
        self.assertNotEqual(e.listing(), before, "the action changed nothing")
        e.restore(token)
        self.assertEqual(e.listing(), before, "restore did not undo it")

    def test_an_unknown_action_changes_nothing(self):
        e = self.env()
        before = e.state()
        self.assertFalse(e.act("no_such_action"))
        self.assertEqual(e.state(), before)

    def test_an_action_that_raises_is_data_not_a_crash(self):
        e = self.env()
        e.register([("boom", lambda env: (_ for _ in ()).throw(RuntimeError("x")))])
        self.assertFalse(e.act("boom"), "a raising action returned True")


# --------------------------------------------------------------------------- #
# learning by acting
# --------------------------------------------------------------------------- #
class LearningTests(EnvCase):
    PROGRAMS = ["gzip", "bzip2", "cat", "zip", "tar"]

    def drive_to(self, target: str, budget: int = 120, seed: int = 11):
        from canonical.runtime import environment_learning_v1 as el
        e = self.env()
        e.register(cenv.program_actions(e, programs=self.PROGRAMS))
        self.addCleanup(e.close)
        return e, el.drive(e, e.action_names,
                           is_goal=lambda snap: target in str(snap),
                           budget=budget, seed=seed)

    def test_the_learner_discovers_which_program_produces_the_format(self):
        _, r = self.drive_to("input.txt.gz")
        self.assertTrue(r.get("reached"), r.get("status"))
        self.assertIn("run_gzip", r.get("plan") or [],
                      "the learner did not find gzip")

    def test_the_plan_found_is_short(self):
        """'fastest way with minimal actions' -- one program is one step."""
        _, r = self.drive_to("input.txt.gz")
        self.assertTrue(r.get("reached"), r.get("status"))
        self.assertLessEqual(len(r.get("plan") or []), 2,
                             "the plan was not minimal: %s" % (r.get("plan"),))

    def test_a_different_format_finds_a_different_program(self):
        _, r = self.drive_to("input.txt.bz2")
        self.assertTrue(r.get("reached"), r.get("status"))
        self.assertIn("run_bzip2", r.get("plan") or [])

    def test_an_unreachable_goal_is_reported_not_invented(self):
        _, r = self.drive_to("input.txt.qqzz")
        self.assertFalse(r.get("reached"))
        self.assertIsNone(r.get("plan"))

    def test_learning_really_ran_the_program(self):
        """Not a plan on paper: the file was produced."""
        e, r = self.drive_to("input.txt.gz")
        self.assertTrue(r.get("reached"), r.get("status"))
        produced = [n for n in e.listing() if n.endswith(".gz")]
        self.assertTrue(produced, "no gz file exists in the directory")


# --------------------------------------------------------------------------- #
# the point of learning is not to do it twice
# --------------------------------------------------------------------------- #
class TransferTests(EnvCase):
    def study(self, goal):
        from canonical.runtime import curriculum_v1 as cur
        return cur.study(goal, channels=["explore"])

    def test_the_first_time_learns_and_the_second_does_not(self):
        first = self.study("compress the input into out.gz")
        self.assertTrue(first["pass"], first)
        self.assertFalse(first["attempts"][0].get("from_memory"),
                         "the first attempt cannot come from memory")

        second = self.study("compress the input into out.gz")
        self.assertTrue(second["pass"], second)
        self.assertTrue(second["attempts"][0].get("from_memory"),
                        "the same problem was learned twice")

    def test_what_was_learned_is_replayed_not_guessed(self):
        first = self.study("compress the input into out.gz")
        second = self.study("compress the input into out.gz")
        self.assertEqual(first["attempts"][0].get("plan"),
                         second["attempts"][0].get("plan"))

    def test_the_channel_reports_how_many_actions_it_tried(self):
        r = self.study("compress the input into out.gz")
        self.assertGreater(r["attempts"][0].get("actions_tried", 0), 1)

    def test_a_goal_naming_no_format_is_refused_by_the_channel(self):
        r = self.study("extract text from a pdf file")
        self.assertFalse(r["pass"])
        self.assertEqual(r["attempts"][0]["status"],
                         "OPEN__NO_OUTPUT_FORMAT_IN_GAP")


if __name__ == "__main__":
    unittest.main()
