"""A sentence that asks WHICH ONE, and to write ITS NAME, is not asking for a list.

Measured 2026-10-31 on the 28-task surface ladder (`hardcore_swe_surface_probe_20261030.py`):

    "The test suite in <d>/tests fails. Which function in <d>/app is at fault?
     Write its name to <d>/answer.json"

The answer gate classified that as ENUMERATE (aliases: functions / function_names / defs /
definitions) because the word `name` in "write its name" was read as the imperative "name them".
The adapter answered with a single `answer` field, the artifact was written and held the right
value (the probe's independent oracle agreed), and the door refused it with
`ANSWER_SHAPE_UNSERVED:NO_MATCHING_FIELD` -- four correct answers reported as refusals:
`localize_fault`, `find_flaky_test`, `uncovered_function`, `perf_regression`.

The plural object still means an enumeration; so do "name them/each/all", "list", and
"find/show/collect/write every|all". The singular noun phrase "its name" does not.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import answer_shape_v1 as shapes


class ASingleNamedAnswerIsNotAnEnumerationTests(unittest.TestCase):
    def test_which_one_and_write_its_name_states_no_list_shape(self):
        for goal in (
            "The test suite in a/tests fails. Which function in a/app is at fault? "
            "Write its name to a/answer.json",
            "Between HEAD~1 and HEAD in b, one function got much slower. Find it and write its "
            "name to b/answer.json",
            "One test in c/tests fails intermittently. Find it and write the test name to "
            "c/answer.json",
            "Which function in d/app is never called by the tests? Write the name to "
            "d/answer.json",
        ):
            self.assertIsNone(shapes.asked(goal),
                              "a single named answer was read as an enumeration: %r" % (goal,))

    def test_a_plural_object_is_still_an_enumeration(self):
        for goal in (
            "Find every caller of the function add in p/util.py",
            "List the functions defined in p/util.py",
            "Find all callers of build_plan and write the names to p/out.json",
            "Find all functions in p/util.py that no test calls",
        ):
            shape = shapes.asked(goal)
            self.assertIsNotNone(shape, "an enumeration stopped being one: %r" % (goal,))
            self.assertEqual(shape["kind"], "ENUMERATE", goal)

    def test_the_gate_stays_out_of_the_way_for_a_named_answer(self):
        """End to end: a correct single answer is delivered, not refused, and not re-shaped."""
        goal = ("The test suite in a/tests fails. Which function in a/app is at fault? "
                "Write its name to a/answer.json")
        result = {"execution": [{"capability_id": "python.fault.localize.v1",
                                 "result": {"answer": "apply_discount",
                                            "ranked_symbols": [{"symbol": "apply_discount"}]}}]}
        reasons = shapes.deliver(goal, result)
        self.assertEqual(reasons, [], "a correct single answer was refused: %r" % (reasons,))
        self.assertNotIn("answer", result,
                         "the gate invented a projection for a sentence that names one value")


if __name__ == "__main__":
    unittest.main()
