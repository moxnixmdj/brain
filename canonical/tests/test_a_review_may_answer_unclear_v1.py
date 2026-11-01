"""A review may answer UNCLEAR, and the oracle must not call that a broken review.

Measured 2026-10-31 on `bbc00a7`, unchanged tree, same case: the capability matrix reported
22 REAL once and 23 REAL six times.  The flickering case was `perf_review`, refused with
`REVIEW_RAN_AND_RETURNED_A_VERDICT`.  Seven isolated runs of the same sentence passed, and the
artifacts measured slowdown ratios of 0.90 / 0.98 / 0.99 / 1.01 against a 1.10 limit -- the band
is real, and machine contention occasionally pushes one run past it, where the gate honestly says
UNCLEAR.

The gate's own law is three-valued:

    ratio <= 1 + tolerance                    -> PASS
    patched min > anchor max (disjoint)        -> FAIL   (a real regression)
    otherwise, both sides measured            -> UNCLEAR

The matrix oracle required PASS.  So a review that measured both sides and said "the difference is
inside the noise" -- the correct answer for an unchanged file -- was scored as not having run, and
the headline number moved with the load on the box.

These tests pin the replacement, which is STRONGER about evidence and looser about the verdict:

  * PASS is a review that ran                       -> accepted
  * UNCLEAR with both sides timed is a review too   -> accepted
  * FAIL on an unchanged file is a false alarm      -> refused
  * a claim with no timed runs is not evidence      -> refused
  * an incomplete artifact is not a verdict         -> refused
  * falsification: put the old rule back and the honest UNCLEAR is refused again

The oracle here is the artifact, never the prose: each case is a synthetic artifact written to
disk exactly as the gate writes it, and the matrix parses it the same way it parses a real run.
"""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "swe_capability_matrix_v1", ROOT / "execution_guard/swe_capability_matrix_v1.py")
MATRIX = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(MATRIX)

SCHEMA = "PROJECT_BRAIN_DIFF_PERF_GATE_V1"
SPOOL = ROOT / "canonical/astra_runtime/tmp/test_perf_oracle"


def _artifact(case: str, **overrides) -> dict:
    doc = {
        "schema": SCHEMA,
        "complete": True,
        "gate": "PASS",
        "tolerance": 0.1,
        "slowdown_ratio": 0.98,
        "repeats": 5,
        "anchor_median_ns": 140_000,
        "patched_median_ns": 138_000,
        "anchor_runs_ns": [140_000, 141_000, 139_000, 145_000, 140_500],
        "patched_runs_ns": [138_000, 139_000, 137_500, 140_000, 138_200],
    }
    doc.update(overrides)
    SPOOL.mkdir(parents=True, exist_ok=True)
    path = SPOOL / ("%s.json" % case)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return {"execution": [{"result": {"output_path": str(path.relative_to(ROOT))}}]}


def _verdict(result: dict) -> bool:
    return MATRIX._perf_gate_compared_both_sides(ROOT, result)


class AReviewVerdictIsThreeValued(unittest.TestCase):
    def test_pass_is_a_review_that_ran(self) -> None:
        self.assertTrue(_verdict(_artifact("pass")))

    def test_unclear_with_both_sides_timed_is_also_a_review(self) -> None:
        self.assertTrue(_verdict(_artifact("unclear", gate="UNCLEAR", slowdown_ratio=1.24)))

    def test_fail_on_an_unchanged_file_is_a_false_alarm(self) -> None:
        self.assertFalse(_verdict(_artifact("fail", gate="FAIL", slowdown_ratio=1.9)))

    def test_a_claim_with_no_timed_runs_is_not_evidence(self) -> None:
        self.assertFalse(_verdict(_artifact("noruns", anchor_runs_ns=[], patched_runs_ns=[])))

    def test_two_runs_are_not_enough_to_take_a_median(self) -> None:
        self.assertFalse(_verdict(_artifact("tworuns",
                                            anchor_runs_ns=[1, 2], patched_runs_ns=[1, 2])))

    def test_an_incomplete_artifact_is_not_a_verdict(self) -> None:
        self.assertFalse(_verdict(_artifact("incomplete", complete=False)))

    def test_a_missing_median_is_not_a_verdict(self) -> None:
        self.assertFalse(_verdict(_artifact("nomedian", patched_median_ns=None)))

    def test_the_old_rule_would_have_refused_the_honest_answer(self) -> None:
        """Falsification: the previous rule is reproduced here and must reject UNCLEAR."""
        result = _artifact("old_rule", gate="UNCLEAR")
        doc = json.loads((ROOT / result["execution"][0]["result"]["output_path"]).read_text())

        def old_rule(artifact: dict) -> bool:
            if artifact.get("schema") != SCHEMA:
                return False
            if artifact.get("gate") != "PASS":
                return False
            return (isinstance(artifact.get("anchor_median_ns"), (int, float))
                    and isinstance(artifact.get("patched_median_ns"), (int, float)))

        self.assertFalse(old_rule(doc), "the old rule must refuse what the review honestly said")
        self.assertTrue(_verdict(result), "and the current rule must accept it")


if __name__ == "__main__":
    unittest.main()
