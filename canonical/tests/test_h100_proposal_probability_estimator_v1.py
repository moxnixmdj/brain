from __future__ import annotations

import copy
import math
import unittest

from canonical.runtime.h100_proposal_probability_estimator_v1 import (
    ALPHA,
    INPUT_SCHEMA,
    ProposalProbabilityError,
    clopper_pearson_lower,
    estimate,
    n95_from_lower_bound,
)

GIT_SHA = "a" * 40


def receipt(name: str) -> dict:
    return {"path": f"canonical/verification/{name}.json", "git_blob_sha": GIT_SHA}


def task(task_id: str, outcomes: list[bool]) -> dict:
    return {
        "task_id": task_id,
        "preexposed_before_outcomes": True,
        "task_preexposure_receipt": receipt(f"pre-{task_id}"),
        "attempts": [
            {
                "proposal_index": i + 1,
                "useful_candidate": value,
                "outcome_verified": True,
                "verification_receipt": receipt(f"{task_id}-{i+1}"),
            }
            for i, value in enumerate(outcomes)
        ],
    }


def base() -> dict:
    return {
        "schema": INPUT_SCHEMA,
        "confidence_alpha": ALPHA,
        "task_population_frozen_before_outcomes": True,
        "population_preexposure_receipt": receipt("population"),
        "tasks": [
            task("A", [True, False, True, False, False, True]),
            task("B", [False, True, False, False, True, False]),
        ],
    }


class H100ProposalProbabilityEstimatorTests(unittest.TestCase):
    def test_exact_all_success_lower_bound(self):
        lower = clopper_pearson_lower(10, 10)
        self.assertAlmostEqual(lower, ALPHA ** 0.1, places=12)

    def test_zero_success_has_zero_lower_bound_and_infinite_n95(self):
        self.assertEqual(clopper_pearson_lower(0, 10), 0.0)
        self.assertIsNone(n95_from_lower_bound(0.0))

    def test_known_binomial_interval_sanity(self):
        lower = clopper_pearson_lower(5, 10)
        self.assertGreater(lower, 0.08)
        self.assertLess(lower, 0.23)
        tail = sum(
            math.comb(10, k) * lower**k * (1.0 - lower) ** (10-k)
            for k in range(5, 11)
        )
        self.assertAlmostEqual(tail, ALPHA, places=9)

    def test_estimate_returns_per_task_and_pooled_bounds(self):
        out = estimate(base())
        self.assertEqual(out["status"], "FINITE_PREEXPOSED_EVIDENCE")
        self.assertEqual(out["task_count"], 2)
        self.assertEqual(out["pooled_successes"], 5)
        self.assertEqual(out["pooled_trials"], 12)
        self.assertGreater(out["pooled_p_lower_95_one_sided"], 0.0)
        self.assertIsNotNone(out["worst_task_n95_from_p_lower"])

    def test_any_zero_success_task_keeps_finite_gate_open(self):
        d = base()
        d["tasks"][1] = task("B", [False] * 8)
        out = estimate(d)
        self.assertEqual(out["status"], "INSUFFICIENT_FINITE_EVIDENCE")
        self.assertEqual(out["worst_task_p_lower_95_one_sided"], 0.0)
        self.assertIsNone(out["worst_task_n95_from_p_lower"])

    def test_population_must_be_preexposed(self):
        d = base()
        d["task_population_frozen_before_outcomes"] = False
        with self.assertRaisesRegex(ProposalProbabilityError, "TASK_POPULATION_NOT_PREEXPOSED"):
            estimate(d)

    def test_attempts_must_be_complete_and_sequential(self):
        d = base()
        d["tasks"][0]["attempts"][1]["proposal_index"] = 9
        with self.assertRaisesRegex(ProposalProbabilityError, "ATTEMPT_SEQUENCE_INVALID"):
            estimate(d)

    def test_attempt_outcome_requires_independent_receipt(self):
        d = base()
        d["tasks"][0]["attempts"][0]["verification_receipt"]["git_blob_sha"] = "bad"
        with self.assertRaisesRegex(ProposalProbabilityError, "ATTEMPT_RECEIPT_INVALID"):
            estimate(d)

    def test_duplicate_task_ids_rejected(self):
        d = base()
        d["tasks"][1]["task_id"] = "A"
        with self.assertRaisesRegex(ProposalProbabilityError, "TASK_ID_DUPLICATE:A"):
            estimate(d)

    def test_alpha_is_frozen(self):
        d = base()
        d["confidence_alpha"] = 0.1
        with self.assertRaisesRegex(ProposalProbabilityError, "ALPHA_MUST_BE_FROZEN_0_05"):
            estimate(d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
