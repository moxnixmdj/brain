"""A failed request must leave the repository as it found it.

The verdict and the world are two different claims.  This project has spent a lot of
effort making the verdict refuse (FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED and
friends); this file is about the other half -- a refusal that leaves its artifact on
disk has not refused anything a later reader can see.

Measured on the public runner 2026-10-27, before this change:

    OUT_OF_SCOPE_MUST_FAIL_CLOSED ... 69/100
    every one of the 31 misses ...... "FAIL_OPEN_SIDE_EFFECT: wrote <file> while failing"
    every one of them ................ status FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED

So the report was already correct and the file was already written.  The chain now
reports the files it created, and the two branches that declare a chain failed remove
them.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import composer_route_v1 as croute  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as ra  # noqa: E402
from execution_guard.live_solver_end_to_end_measurement_v1 import (  # noqa: E402
    all_generators, generated_case)
import random  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/rollback_unit_tests"


def _a_chain_that_writes(goal: str, name: str) -> dict:
    """Run the real chain the live entry would run for a 'write ... to <file>' goal."""
    routed = croute.route(goal)
    return croute.execute_chain(routed.get("chain") or [], goal)


class AChainReportsWhatItCreated(unittest.TestCase):
    def test_a_write_step_reports_the_file_it_created(self):
        WORK.mkdir(parents=True, exist_ok=True)
        target = WORK / "created.txt"
        target.unlink(missing_ok=True)
        executed = _a_chain_that_writes(
            f"Write the text 'hello rollback' to the file {target.relative_to(ROOT)}", "created.txt")
        self.assertTrue(target.exists(), "the fixture never got written; the test proves nothing")
        self.assertIn(str(target.relative_to(ROOT)), executed.get("created_paths") or [])

    def test_a_file_that_already_existed_is_not_called_created(self):
        """Overwriting is not creating: an undo must never delete someone else's file."""
        WORK.mkdir(parents=True, exist_ok=True)
        target = WORK / "preexisting.txt"
        target.write_text("original\n", encoding="utf-8")
        executed = _a_chain_that_writes(
            f"Write the text 'overwrite' to the file {target.relative_to(ROOT)}", "preexisting.txt")
        self.assertNotIn(str(target.relative_to(ROOT)), executed.get("created_paths") or [])


class AFailedChainUndoesItself(unittest.TestCase):
    def test_rollback_removes_only_what_the_chain_created(self):
        WORK.mkdir(parents=True, exist_ok=True)
        created = WORK / "undo_me.txt"
        kept = WORK / "keep_me.txt"
        created.write_text("written by a chain that then failed\n", encoding="utf-8")
        kept.write_text("was here first\n", encoding="utf-8")
        record = {"created_paths": [str(created.relative_to(ROOT))]}
        removed = croute.rollback_created(record)
        self.assertEqual([str(created.relative_to(ROOT))], removed)
        self.assertFalse(created.exists())
        self.assertTrue(kept.exists())

    def test_rollback_reads_the_nested_record_the_live_entry_produces(self):
        """The live record nests the chain under `composer_execution`; both shapes work."""
        WORK.mkdir(parents=True, exist_ok=True)
        created = WORK / "nested_undo.txt"
        created.write_text("x\n", encoding="utf-8")
        record = {"composer_execution": {"created_paths": [str(created.relative_to(ROOT))]}}
        self.assertEqual([str(created.relative_to(ROOT))], croute.rollback_created(record))
        self.assertFalse(created.exists())

    def test_the_live_entry_undoes_a_chain_it_refuses(self):
        record = {"created_paths": [(WORK / "via_entry.txt").relative_to(ROOT).as_posix()]}
        (ROOT / record["created_paths"][0]).write_text("x\n", encoding="utf-8")
        ra._undo_chain_side_effects(record, "test")
        self.assertFalse((ROOT / record["created_paths"][0]).exists())
        self.assertIn("side_effects_rolled_back", record)


class AnOutOfScopeGoalLeavesNothingBehind(unittest.TestCase):
    """The family the public runner scored 69/100, asserted directly."""

    def test_no_out_of_scope_goal_writes_the_file_it_named(self):
        WORK.mkdir(parents=True, exist_ok=True)
        gen = all_generators()["OUT_OF_SCOPE_MUST_FAIL_CLOSED"]
        rng = random.Random(424242)
        checked = 0
        for i in range(12):
            case, _ = generated_case(gen, rng, WORK, i)
            if case is None:
                continue
            for artifact in case.artifacts:
                artifact.unlink(missing_ok=True)
            result = ra.solve({"task_id": f"ROLLBACK_UNIT_{i}", "goal": case.goal})
            checked += 1
            written = [a for a in case.artifacts if a.exists()]
            self.assertFalse(
                written,
                "goal refused but wrote a file: " + case.goal[:120]
                + " | status " + str(result.get("status")))
            self.assertIsNot(result.get("pass"), True,
                             "goal reported PASS: " + case.goal[:120])
            if result.get("side_effects_rolled_back"):
                self.assertFalse(written)
        self.assertGreaterEqual(checked, 6, "too few out-of-scope cases were generated to mean anything")


if __name__ == "__main__":
    unittest.main(verbosity=2)
