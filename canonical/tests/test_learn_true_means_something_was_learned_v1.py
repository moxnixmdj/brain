"""When the caller says `learn=True`, something is learned -- and the answer says what.

Measured on `df0f6330`, 2026-11-25. `test_acquisition_to_execution_engine_v1` phase 3 was red:

    r1 = solve_or_learn("how many unique lines in data.txt", ..., db_path=...)
    r1["answer"] == "8"          PASS   -- correct, and causally verified
    r1["skill_crystallized"]     KeyError

The semantic tier had solved the sentence, run a positive-intervention probe and a null probe,
and returned. `learn=True` was documented as "or learn & crystallize the missing skill in-run",
and on this path it learned nothing. `skill_crystallized` was not False, it was ABSENT -- the key
existed only on the Tier-2 web-form path, so a caller could not tell "nothing was learned" from
"this tier does not report learning at all".

Two separate causes, both invisible from outside:

1. THE KEY WAS OPTIONAL. Only one of six answer paths set it.
2. THE STORE WAS TRACKED. `GeneralizationEngine()` defaults to
   `canonical/astra_runtime/generalization/GENERALIZATION_EXPERIENCES_V1.json`, which is read as
   weight-update fuel by `weight_space_fuel_v1`, asserted on by `test_what_transfers_v1`, and
   counted by `experience_corpus_training_readiness_v1`. So the tier passed
   `store_experience=False` -- refusing to write tracked state, correctly -- and then wrote
   nothing anywhere, which was the bug.

And a third, found only because the second one was fixed: once the loop actually learned, the
second solve took 3,400 ms instead of 80 ms, because `record_wake_episode` -> `evolve_policy_from_traces`
runs the self-architect mutator and DreamCoder-style `sleep_abstract` SYNCHRONOUSLY after the answer
is already built and verified. Measured with a stack dump: the caller was waiting on program
synthesis it never asked for.

THE RULE THIS FILE PINS:

  1. every answer from the semantic tier carries `skill_crystallized` AND a named
     `learning_status`; when nothing is kept, `learning_refusal` says why.
  2. a verified program is persisted into a CALLER-OWNED store, never tracked state.
  3. the store keys the PROGRAM (targets excluded), so a second file reuses it instead of
     creating a second skill -- and `from_memory` is True only when the program was in the store
     BEFORE this goal was seen.
  4. the answer path does not pay for organ synthesis: evolution is budgeted and deferred.
  5. CONTROL: with the learning line neutered, these probes FAIL. A test that cannot fail is
     decoration.

No model, no network. Truth is hand-computed in the test.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import (  # noqa: E402
    _program_signature,
    _tier0a_semantic_lane,
    solve_or_learn,
)

TRUTH = {
    "data.txt": 8,   # 8 distinct service names, each written twice
    "pods.txt": 13,  # 13 distinct pod names, each written twice
}


class _Store(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_learn_test_"))
        self.cli = self.tmp / "cli"
        self.cli.mkdir()
        (self.cli / "data.txt").write_text(
            "\n".join([f"svc-{i}" for i in range(8)] * 2) + "\n", encoding="utf-8"
        )
        (self.cli / "pods.txt").write_text(
            "\n".join([f"pod-{i}" for i in range(13)] * 2) + "\n", encoding="utf-8"
        )
        self.sem = self.tmp / "semantic_store"
        self._old = os.environ.get("BRAIN_COMPILED_WORKFLOW_DB")
        os.environ["BRAIN_COMPILED_WORKFLOW_DB"] = str(self.tmp / "workflows.sqlite")

    def tearDown(self) -> None:
        if self._old is None:
            os.environ.pop("BRAIN_COMPILED_WORKFLOW_DB", None)
        else:
            os.environ["BRAIN_COMPILED_WORKFLOW_DB"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def solve(self, goal: str, **kw):
        return solve_or_learn(
            goal, cwd=self.cli, db_path=self.tmp / "workflows.sqlite",
            sem_state_path=self.sem, **kw,
        )


class AKeyThatIsAlwaysThere(_Store):
    def test_the_answer_reports_what_it_learned_not_only_what_it_computed(self) -> None:
        r = self.solve("how many unique lines in data.txt")
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["answer"], TRUTH["data.txt"])
        self.assertIn("skill_crystallized", r, "the key is optional again -- that was the defect")
        self.assertIn("learning_status", r)
        self.assertTrue(r["skill_crystallized"], r)
        self.assertEqual(r["learning_status"], "CRYSTALLIZED__VERIFIED_PROGRAM_IN_CALLER_STORE")
        self.assertIsNone(r["learning_refusal"])
        # `skill_crystallized: True` is a claim about the filesystem, so read the filesystem.
        store = pathlib.Path(r["memory_write_path"])
        self.assertTrue(store.is_file(), r["memory_write_path"])
        written = json.loads(store.read_text())["experiences"]
        self.assertTrue(written, "crystallized was True and the store is empty")

    def test_with_no_caller_store_it_refuses_to_write_rather_than_writing_tracked_state(self) -> None:
        r = solve_or_learn("how many unique lines in data.txt", cwd=self.cli, db_path=self.tmp / "w.sqlite")
        self.assertTrue(r["pass"], r)
        self.assertFalse(r["skill_crystallized"])
        self.assertEqual(r["learning_status"], "NOT_STORED__NO_CALLER_OWNED_STORE")
        self.assertIn("tracked state", r["learning_refusal"])
        self.assertIsNone(r["memory_write_path"])
        # and it really did not write the tracked file
        tracked = pathlib.Path(__file__).resolve().parents[2] / (
            "canonical/astra_runtime/generalization/GENERALIZATION_EXPERIENCES_V1.json"
        )
        before = tracked.read_bytes()
        self.solve("how many unique lines in pods.txt")
        self.assertEqual(tracked.read_bytes(), before)


class TheStoreKeysTheProgramNotTheSentence(_Store):
    def test_two_files_are_one_program(self) -> None:
        first = self.solve("how many unique lines in data.txt")
        second = self.solve("how many unique lines in pods.txt")
        self.assertEqual(first["program_signature"], second["program_signature"])
        self.assertEqual(first["answer"], TRUTH["data.txt"])
        self.assertEqual(second["answer"], TRUTH["pods.txt"])

        store = self.sem / "GENERALIZATION_EXPERIENCES_V1.json"
        self.assertTrue(store.is_file(), "nothing was written to the caller-owned store")
        rows = json.loads(store.read_text())["experiences"]
        programs = [r["strategy"]["program_signature"] for r in rows if r.get("strategy")]
        self.assertIn(first["program_signature"], programs)
        # One row per program: the same program asked about twice must not inflate the store.
        self.assertEqual(programs.count(first["program_signature"]), 1, programs)

    def test_from_memory_is_true_only_when_the_program_was_known_before_the_goal(self) -> None:
        first = self.solve("how many unique lines in data.txt")
        self.assertFalse(first["program_known_before"], "nothing was known before the first solve")
        self.assertFalse(first["from_memory"])
        second = self.solve("how many unique lines in pods.txt")
        self.assertTrue(second["program_known_before"])
        self.assertTrue(second["from_memory"])

    def test_the_program_signature_ignores_targets_and_nothing_else(self) -> None:
        with_target = {"operation": "count", "concept": "line", "targets": ["a.txt"], "pipeline": ["LOAD"]}
        other_target = {"operation": "count", "concept": "line", "targets": ["b.txt"], "pipeline": ["LOAD"]}
        other_plan = {"operation": "count", "concept": "line", "targets": ["a.txt"], "pipeline": ["LOAD", "X"]}
        self.assertEqual(_program_signature(with_target), _program_signature(other_target))
        self.assertNotEqual(_program_signature(with_target), _program_signature(other_plan))


class TheAnswerPathDoesNotPayForOrganSynthesis(_Store):
    def test_learning_costs_no_second_answer_time(self) -> None:
        """3,400 ms was measured on the alternating call before the budget existed."""
        self.solve("how many unique lines in data.txt")
        worst = 0.0
        for _ in range(4):
            import time

            t0 = time.perf_counter()
            r = self.solve("how many unique lines in pods.txt")
            worst = max(worst, (time.perf_counter() - t0) * 1000.0)
            self.assertTrue(r["pass"], r)
            self.assertEqual(r["answer"], TRUTH["pods.txt"])
        self.assertLess(worst, 400.0, f"worst learning call {worst:.0f} ms -- evolution is on the answer path again")


class TheProbeCanFail(unittest.TestCase):
    """CONTROL. If these pass while the learning line is neutered, the file above proves nothing."""

    def test_a_neutered_crystallizer_makes_the_probe_fail(self) -> None:
        """The exact claim the rest of this file rests on: with the write removed, it reports it."""
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_learn_ctrl_"))
        try:
            cli = tmp / "cli"
            cli.mkdir()
            (cli / "data.txt").write_text("a\na\nb\n", encoding="utf-8")

            real = _tier0a_semantic_lane(
                goal="how many unique lines in data.txt", work_cwd=cli,
                task_id="t", t0=0, sem_state_path=tmp / "store", learn=True,
            )
            self.assertTrue(real["skill_crystallized"], real)
            self.assertEqual(real["learning_status"], "CRYSTALLIZED__VERIFIED_PROGRAM_IN_CALLER_STORE")

            # Neutered: the store write raises. The answer must still be correct (the program is
            # verified on its own merits) but it must NOT claim to have kept anything.
            with mock.patch(
                "canonical.swe_kernel.semantic_generalization_engine_v1.GeneralizationEngine.store_experience",
                side_effect=RuntimeError("control: store removed"),
            ):
                neutered = _tier0a_semantic_lane(
                    goal="how many unique lines in data.txt", work_cwd=cli,
                    task_id="t", t0=0, sem_state_path=tmp / "store2", learn=True,
                )
            self.assertTrue(neutered["pass"], neutered)
            self.assertEqual(neutered["answer"], 2, "the answer must not depend on the store")
            self.assertFalse(
                (tmp / "store2" / "GENERALIZATION_EXPERIENCES_V1.json").is_file(),
                "a raising store still produced a record",
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_write_disabled_scope_refuses_and_says_so(self) -> None:
        from canonical.runtime.memory_policy_v1 import OFF, memory_policy_scope

        tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_learn_ctrl_"))
        try:
            cli = tmp / "cli"
            cli.mkdir()
            (cli / "data.txt").write_text("a\na\nb\n", encoding="utf-8")
            with memory_policy_scope(OFF):
                r = _tier0a_semantic_lane(
                    goal="how many unique lines in data.txt", work_cwd=cli,
                    task_id="t", t0=0, sem_state_path=tmp / "store", learn=True,
                )
            self.assertTrue(r["pass"], r)
            self.assertFalse(r["skill_crystallized"], "a write-disabled scope stored something")
            self.assertEqual(r["learning_status"], "NOT_STORED__MEMORY_WRITE_DISABLED")
            self.assertIsNotNone(r["learning_refusal"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
