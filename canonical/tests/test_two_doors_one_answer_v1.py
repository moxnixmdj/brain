"""One machine, two front doors, and only one of them tells the truth about the number it returns.

Measured 2026-11-12 on this tree.  The owner's charge was that the system "cannot count different
things (if statements vs functions)".  It can count, and it returns a wrong number, through exactly
one of its two front doors:

    sentence                                  truth   solve()   run_raw_goal()
    count how many functions solve_v1.py          9        9              9    <- hides the defect
    how many functions astra_runtime.py         153      153            155
    how many classes astra_runtime.py             2        2            155
    count the classes goal_compiler.py            2        2            150
    count the functions goal_compiler.py        148      148            150
    list the functions solve_v1.py        9 names  9 names           None

`solve()` reconciles the sentence with the artifact: `answer_shape_v1.lift_named_answer` reads which
quantity the sentence named and hands over `function_count` or `class_count` accordingly.
`run_raw_goal()` never received that reconciliation, so it returns the adapter's summary field
`answer`, which `python_source_definition_count.py:137` computes as `functions + classes` no matter
what was asked.  The published demonstration passes only because `solve_v1.py` declares zero classes,
so the sum and the count are the same integer.

This is the sharpest form of the failure the tree already knows about: a certificate that says
`PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED` on top of a wrong number.  None of
these tests fix it.  They make it unpublishable to claim otherwise, and they pin the ONE property
that the fix must preserve: the primary door's correct behaviour.

They also pin the defect that produced the first false alarm in this round's own instrument: the
controller refuses to re-run a finished `task_id`, so a probe that reuses ids measures its own
history.  That is a property worth having; it is pinned so the next instrument cannot mistake it for
non-determinism.
"""
from __future__ import annotations

import ast
import pathlib
import unittest

from canonical.runtime import answer_shape_v1 as shape
from canonical.tools import two_doors_one_answer_v1 as probe

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _adapter_row(**fields):
    """A row shaped like `python.source.definition_count.v1`'s output."""
    base = {"schema": "PROJECT_BRAIN_PYTHON_SOURCE_DEFINITION_COUNT_V1",
            "capability_id": "python.source.definition_count.v1", "dependency": "local",
            "verified": True, "gate": "PASS", "answer": 155,
            "function_count": 153, "class_count": 2, "definition_count": 155}
    base.update(fields)
    return {"pass": True, "status": "PASS__MEASURED",
            "execution": [{"capability_id": "python.source.definition_count.v1",
                           "result": base}]}


class TheQuestionDecidesTheField(unittest.TestCase):
    """`lift_named_answer` must hand over the quantity the sentence named, not the sum."""

    def test_asking_for_functions_receives_the_function_count(self) -> None:
        result = _adapter_row()
        shape.lift_named_answer(result, "how many functions are in astra_runtime.py")
        self.assertEqual(result["answer"], 153)

    def test_asking_for_classes_receives_the_class_count(self) -> None:
        result = _adapter_row()
        shape.lift_named_answer(result, "how many classes are in astra_runtime.py")
        self.assertEqual(result["answer"], 2)

    def test_asking_for_definitions_receives_the_sum(self) -> None:
        result = _adapter_row()
        shape.lift_named_answer(result, "how many definitions are in astra_runtime.py")
        self.assertEqual(result["answer"], 155)

    def test_a_sentence_naming_both_quantities_gets_the_rows_own_answer(self) -> None:
        """Ambiguous is not the gate's business to resolve by guessing."""
        result = _adapter_row()
        shape.lift_named_answer(result, "compare the functions and classes in astra_runtime.py")
        self.assertEqual(result["answer"], 155)

    def test_the_sum_is_never_what_a_single_quantity_question_receives(self) -> None:
        """The exact defect: 155 is right for neither 'functions' nor 'classes'."""
        for sentence, wrong in (("how many functions are in x.py", 155),
                                ("how many classes are in x.py", 155)):
            result = _adapter_row()
            shape.lift_named_answer(result, sentence)
            self.assertNotEqual(result["answer"], wrong, sentence)


class TheAdapterSummaryIsTheRootCause(unittest.TestCase):
    """The adapter computes both counts and then returns their sum as `answer`."""

    def test_the_adapter_still_sums_and_that_is_the_defect(self) -> None:
        source = (ROOT / "canonical/runtime/bound_capabilities/python_source_definition_count.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertIn("function_count", source)
        self.assertIn("class_count", source)
        # The row carries a correct `function_count` and a correct `class_count`, and an `answer`
        # that is their sum. Nothing in the adapter reads the sentence -- that is the gate's job and
        # the gate lives elsewhere, which is why one door has the fix and the other does not.
        self.assertIn("functions + classes", source.replace(" ", " ").replace("functions+classes", "functions + classes"))

    def test_the_compiler_does_not_bind_the_asked_quantity(self) -> None:
        """Why the sum reaches the user: the front end never records which quantity was asked."""
        source = (ROOT / "canonical/runtime/goal_compiler.py").read_text(encoding="utf-8")
        self.assertNotIn("definition_count", source)


class BothDoorsAreStillDoors(unittest.TestCase):
    """The measurement itself, end to end, with ground truth computed by `ast`."""

    def test_ground_truth_is_computed_not_trusted(self) -> None:
        names = probe.ground_truth("canonical/runtime/solve_v1.py")
        self.assertEqual(len(names["function"]), 9)
        self.assertEqual(names["class"], [])
        astra = probe.ground_truth("canonical/runtime/astra_runtime.py")
        self.assertGreater(len(astra["function"]), 100)
        self.assertEqual(len(astra["class"]), 2)

    def test_the_primary_door_answers_the_quantity_asked(self) -> None:
        answer = probe.primary_door("how many classes are in canonical/runtime/astra_runtime.py")
        self.assertEqual(answer["answer"], 2, answer)

    def test_the_primary_door_enumerates_when_asked_to(self) -> None:
        answer = probe.primary_door("list the functions in canonical/runtime/solve_v1.py")
        self.assertIsInstance(answer["answer"], list, answer)
        self.assertEqual(sorted(answer["answer"]), sorted(probe.ground_truth("canonical/runtime/solve_v1.py")["function"]))

    def test_the_secondary_door_returns_the_sum_for_a_class_question(self) -> None:
        """Pinned as WRONG on purpose: this asserts the defect so it cannot be quietly published."""
        answer = probe.secondary_door("how many classes are in canonical/runtime/astra_runtime.py")
        self.assertEqual(answer["answer"], 155, answer)
        self.assertNotEqual(answer["answer"], 2)

    def test_the_secondary_door_is_silent_on_an_enumeration(self) -> None:
        answer = probe.secondary_door("list the functions in canonical/runtime/solve_v1.py")
        self.assertIsNone(answer["answer"], answer)


class AnAnswerIsGroundedOrItIsNothing(unittest.TestCase):
    """Zero must come back as zero.

    This exists because this round's own earlier probe reported a fabricated answer -- 11 functions in
    a file that does not exist -- and the "file" turned out to be an answer artifact (JSON, schema
    `PROJECT_BRAIN_PYTHON_DEFINITION_COUNT_V1`, `source_root` rewritten to
    `a_capability_that_cannot_know_this_machine_cannot_run_it_20261112.py`) that an even earlier
    probe had written to disk.  The machine was not fabricating; the instrument was reading its own
    output and calling it input.  Pinned so the distinction is recorded: an ungrounded reading is a
    property of the reader, and the reader here is a test fixture.
    """

    # A REAL file in this tree that declares ZERO functions and THREE classes -- the exact inverse of
    # the headline case, and no fixture required.
    #
    # Two failed attempts came first, and both are worth recording because they are traps:
    #   * a `tempfile.mkdtemp()` path is refused by the workspace boundary
    #     (`FAIL_CLOSED__STATED_PATH_OUTSIDE_THE_WORKSPACE`) -- correct, but it means a fixture must
    #     live inside the repository;
    #   * `canonical/astra_runtime/tmp/` is listed in `.gitignore` but has **464 tracked files**, so
    #     treating it as scratch deleted them (`git status` showed hundreds of `D` entries). Ignored
    #     does not mean untracked. Restored from HEAD, and the fixture idea abandoned in favour of a
    #     file that was already here.
    INVERSE = "canonical/capabilities/internalized/causal_falsification/agent_replay_v1/agent_replay/errors.py"

    def test_the_inverse_case_really_has_no_functions(self) -> None:
        names = probe.ground_truth(self.INVERSE)
        self.assertEqual(len(names["function"]), 0)
        self.assertEqual(len(names["class"]), 3)

    def test_zero_functions_is_answered_zero_not_a_refusal(self) -> None:
        answer = probe.primary_door(f"count how many functions {self.INVERSE} contains")
        self.assertEqual(answer["answer"], 0, answer)

    def test_zero_functions_is_the_CLASS_count_on_the_secondary_door(self) -> None:
        """The cleanest single proof of the defect: 0 asked, 3 returned, and 3 is the class count."""
        answer = probe.secondary_door(f"count how many functions {self.INVERSE} contains")
        self.assertEqual(answer["answer"], 3, answer)

    def test_the_secondary_door_looks_right_here_only_because_the_sum_coincides(self) -> None:
        """3 classes + 0 functions == 3, so asking for classes accidentally succeeds."""
        sentence = f"count how many classes {self.INVERSE} contains"
        self.assertEqual(probe.secondary_door(sentence)["answer"], 3)
        # The right answer arriving for the wrong reason is exactly how the headline case hid.


class AFinishedTaskIsNotRerun(unittest.TestCase):
    """The behaviour that produced this round's first false alarm, pinned as correct.

    `astra_runtime.py:5359` raises `MODEL_INDEPENDENT_CONTROLLER_PLAN_ALREADY_FINISHED` when the
    checkpoint for a `task_id` says the plan already ran to the end. The checkpoint path is
    `<mission_id>__<step>__CONTROLLER_CHECKPOINT.json` under `canonical/astra_runtime/state`, so the
    id is the key. An instrument that reuses ids reads `155`, then `None`, then a FAIL from three
    identical sentences and calls it non-determinism; it is history.
    """

    def test_a_reused_task_id_is_refused_rather_than_re_run(self) -> None:
        sentence = "how many classes are in canonical/runtime/astra_runtime.py"
        task_id = probe._task_id("pin-reuse")
        first = probe.secondary_door(sentence, "pin")  # fresh ids, must execute
        self.assertIsNotNone(first["status"])
        from canonical.runtime.live_integrated_brain_v1 import run_raw_goal
        a = run_raw_goal({"task_id": task_id, "goal": sentence}, record_experience=False)
        b = run_raw_goal({"task_id": task_id, "goal": sentence}, record_experience=False)
        self.assertIn("MODEL_INDEPENDENT_CONTROLLER_PLAN_ALREADY_FINISHED", str(b.get("reason") or ""),
                      f"first={a.get('status')} second={b.get('reason')}")

    def test_the_probe_mints_a_fresh_id_every_call(self) -> None:
        ids = {probe._task_id("same") for _ in range(20)}
        self.assertEqual(len(ids), 20)


class TheChargesThatAreFalse(unittest.TestCase):
    """Two of the owner's charges are contradicted by records already in the tree."""

    def test_other_files_are_served_at_full_precision(self) -> None:
        import json
        record = json.loads((ROOT / "canonical/verification/ACROSS_ENVIRONMENTS_20261112_V1.json").read_text(encoding="utf-8"))
        within = record["within_repository_control"]["exact"]
        self.assertEqual(within["precision"], 1.0)
        self.assertEqual(within["wrong"], 0)
        self.assertGreater(within["share_of_the_work"], 0.5)

    def test_other_repositories_are_served_at_full_precision(self) -> None:
        import json
        record = json.loads((ROOT / "canonical/verification/ACROSS_ENVIRONMENTS_20261112_V1.json").read_text(encoding="utf-8"))
        across = record["across_repository"]["exact"]
        self.assertEqual(across["precision"], 1.0)
        self.assertEqual(across["wrong"], 0)


if __name__ == "__main__":
    unittest.main()
