# PROJECT_BRAIN
"""A lookup is answered by what the row observed, not by nothing.

``asked()`` returns None for a state question -- "Show the status of the working tree" is not a
collection, and ``test_a_lookup_and_a_count_are_not_enumerations`` pins that.  But a None shape
used to mean *no delivery at all*: measured 2026-10-31, that sentence PASSed on
``git.repository.operate.v1`` with ``answer: null`` while the row's ``observed_effect`` held

    {"op": "status", "branch": "arena/80891605-brain", "entry_count": 0, "staged": 0, ...}

The answer had been produced.  It was dropped on the floor.  That is the "correct, but nothing
was handed over" class -- 6 of 61 PASSes in the V4 baseline -- and its cause is one missing
step, not a missing capability: every row already states what it observed.

Three laws:

1. AN OBSERVATION IS AN ANSWER.  A PASS that delivered nothing hands over ``observed_effect``
   under the same ``PROJECT_BRAIN_ANSWER_SHAPE_V1`` envelope, with ``noun: observation``.
2. AN ANSWER IS NEVER REPLACED.  If the projection (or the route) already set one, this step
   leaves it exactly as it was.
3. IT NEVER CHANGES A VERDICT.  ``deliver_observation`` reports no refusal reasons, so a PASS
   stays a PASS; only the payload the caller receives changes.
"""

from __future__ import annotations

import unittest

from canonical.runtime import answer_shape_v1 as shape


STATE_GOAL = "Show the status of the working tree"


def _result(**extra):
    base = {
        "pass": True,
        "status": "PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED",
        "execution": [{
            "capability_id": "git.repository.operate.v1",
            "result": {
                "schema": "PROJECT_BRAIN_GIT_REPOSITORY_OPERATE_V1",
                "op": "status",
                "row_count": 0,
                "rows": [],
                "observed_effect": {
                    "op": "status",
                    "branch": "arena/80891605-brain",
                    "entry_count": 0,
                    "staged": 0,
                    "unstaged": 0,
                    "untracked": 0,
                },
            },
        }],
    }
    base.update(extra)
    return base


class AnObservationIsAnAnswer(unittest.TestCase):
    def test_a_state_question_still_asks_for_no_collection(self) -> None:
        """The pinned law, restated here because this fix must not widen it."""
        self.assertIsNone(shape.asked(STATE_GOAL))

    def test_the_observation_is_delivered(self) -> None:
        result = _result()
        reasons = shape.deliver_observation(result)
        self.assertEqual(reasons, [])
        answer = result["answer"]
        self.assertEqual(answer["noun"], "observation")
        self.assertEqual(answer["field"], "observed_effect")
        self.assertEqual(answer["value"]["branch"], "arena/80891605-brain")
        self.assertFalse(answer["truncated"])

    def test_the_door_delivers_it_for_a_lookup(self) -> None:
        result = _result()
        self.assertEqual(shape.deliver(STATE_GOAL, result, None), [])
        self.assertEqual(result["answer"]["noun"], "observation")

    def test_a_counted_projection_is_not_disturbed(self) -> None:
        result = _result(answer={"schema": "SOMETHING_ELSE", "noun": "culprit"})
        shape.deliver_observation(result)  # type: ignore[arg-type]
        self.assertEqual(result["answer"], {"schema": "SOMETHING_ELSE", "noun": "culprit"})


class ItNeverChangesAVerdict(unittest.TestCase):
    def test_a_row_with_no_observation_leaves_everything_alone(self) -> None:
        result = _result()
        result["execution"][0]["result"].pop("observed_effect")
        self.assertEqual(shape.deliver_observation(result), [])
        self.assertIsNone(result.get("answer"))
        self.assertTrue(result["pass"])
        self.assertEqual(result["status"],
                         "PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED")

    def test_a_composed_step_is_read_too(self) -> None:
        result = {
            "pass": True,
            "status": "PASS__COMPOSED",
            "composer_execution": {"steps": [{
                "capability_id": "git.repository.operate.v1",
                "result": {"observed_effect": {"branch": "main"}},
            }]},
        }
        self.assertEqual(shape.deliver_observation(result), [])
        self.assertEqual(result["answer"]["value"], {"branch": "main"})


if __name__ == "__main__":
    unittest.main()
