"""A bisect without a known-good commit has not attributed anything.

Measured 2026-10-31 in ``execution_guard/swe_capability_matrix_v1.py``, case
``bisect_regression``: the sentence

    "Bisect the regression that broke the test in <pkg>/test_calc.py."

reached ``git.history.bisect_regression.v1``, which really ran ``git bisect``, probed the single
commit the tree had, found no known-good side, and wrote

    breaking_commit: <repo HEAD>
    last_good_commit: null

-- and the front door certified the run ``PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED``.
A bisect with no good side is the failing half of a search nobody bounded: naming the commit you
started from is not an attribution, and the sentence asked for one.

The gate is placed in ``_close_observations``, the single function every exit of the door passes
through, so a new early return cannot bypass it.  This module pins the payload judgment (with a
synthetic artifact, so the verdict is tested and not the git plumbing) and the door-level status.
"""

import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

SCRATCH = ROOT / "canonical/astra_runtime/tmp/bisect_payload"
GOAL = "Bisect the regression that broke the test in pkg/test_calc.py."


def _artifact(case: str, **fields) -> dict:
    base = SCRATCH / case
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    doc = {"mode": "commit_bisect", "breaking_commit": "a" * 40, "last_good_commit": "b" * 40}
    doc.update(fields)
    path = base / "bisect.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return {"execution": [{"result": {"output_path": path.relative_to(ROOT).as_posix()}}],
            "status": "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
            "pass": True}


class TheArtifactMustCarryTheAnswer(unittest.TestCase):
    def test_no_known_good_commit_is_named_as_such(self):
        result = _artifact("no_good", last_good_commit=None)
        self.assertEqual(door.stated_answer_payload_errors(GOAL, result),
                         ["BISECT_WITHOUT_A_KNOWN_GOOD_COMMIT"])

    def test_no_commit_at_all_is_named_as_such(self):
        result = _artifact("no_commit", breaking_commit=None)
        self.assertEqual(door.stated_answer_payload_errors(GOAL, result),
                         ["BISECT_NAMED_NO_COMMIT"])

    def test_a_bracketed_commit_is_the_answer(self):
        self.assertEqual(door.stated_answer_payload_errors(GOAL, _artifact("bracketed")), [])

    def test_a_run_with_no_artifact_answers_nothing(self):
        self.assertEqual(door.stated_answer_payload_errors(GOAL, {"execution": [], "pass": True}), [])

    def test_an_unrelated_sentence_is_not_gated(self):
        result = _artifact("unrelated", last_good_commit=None)
        self.assertEqual(door.stated_answer_payload_errors(
            "Count the functions in pkg/calc.py.", result), [])


class TheDoorCannotCertifyIt(unittest.TestCase):
    def test_close_observations_withholds_the_pass(self):
        result = _artifact("close", last_good_commit=None)
        closed = door._close_observations(result, GOAL, None, [])
        self.assertIs(closed.get("pass"), False)
        self.assertEqual(closed.get("status"), "FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED")
        self.assertEqual(closed.get("failure_class"), "STATED_ANSWER_NOT_PROVIDED")
        self.assertEqual(closed.get("stated_answer_payload_errors"),
                         ["BISECT_WITHOUT_A_KNOWN_GOOD_COMMIT"])

    def test_a_real_bisect_is_left_alone(self):
        result = _artifact("left_alone")
        closed = door._close_observations(result, GOAL, None, [])
        self.assertIs(closed.get("pass"), True)


if __name__ == "__main__":
    unittest.main()
