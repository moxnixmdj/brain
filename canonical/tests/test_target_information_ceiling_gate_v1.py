from __future__ import annotations

import unittest

from canonical.runtime.target_information_ceiling_gate_v1 import (
    CERT_SCHEMA,
    verify_ceiling_certificate,
)

SHA = "a" * 40


def receipt(**kw):
    base = {
        "path": "canonical/verification/example.json",
        "git_blob_sha": SHA,
        "scope_complete": True,
        "acceptance_preorder_monotone": True,
        "metric_bounds_objective": True,
        "independent_or_objective": True,
    }
    base.update(kw)
    return base


def cert(coords):
    return {
        "schema": CERT_SCHEMA,
        "predicate_id": "P",
        "parent_target_information_cut_sha": "b" * 40,
        "scope_id": "frozen_scope_v1",
        "semantic_receipt": receipt(),
        "coordinates": coords,
    }


class Tests(unittest.TestCase):
    def test_success_ceiling_eliminates_target(self):
        verdict = verify_ceiling_certificate(
            cert(
                [
                    {
                        "name": "success",
                        "direction": "benefit",
                        "lower_bound": 0,
                        "upper_bound": 1,
                        "brain_value": 1,
                    }
                ]
            )
        )
        self.assertEqual(
            verdict["status"],
            "PASS__TARGET_OUTPUT_NOT_REQUIRED_FOR_THIS_PREDICATE_SCOPE",
        )
        self.assertFalse(verdict["target_output_required"])
        self.assertFalse(verdict["predicate_closed"])

    def test_loss_floor_eliminates_target(self):
        verdict = verify_ceiling_certificate(
            cert(
                [
                    {
                        "name": "violations",
                        "direction": "loss",
                        "lower_bound": 0,
                        "upper_bound": 100,
                        "brain_value": 0,
                    }
                ]
            )
        )
        self.assertTrue(verdict["status"].startswith("PASS__"), verdict)

    def test_vector_requires_every_coordinate_top(self):
        verdict = verify_ceiling_certificate(
            cert(
                [
                    {
                        "name": "success",
                        "direction": "benefit",
                        "lower_bound": 0,
                        "upper_bound": 1,
                        "brain_value": 1,
                    },
                    {
                        "name": "violations",
                        "direction": "loss",
                        "lower_bound": 0,
                        "upper_bound": 10,
                        "brain_value": 1,
                    },
                ]
            )
        )
        self.assertEqual(
            verdict["status"],
            "OPEN__TARGET_INFORMATION_NOT_ELIMINATED",
        )

    def test_near_ceiling_is_not_ceiling(self):
        verdict = verify_ceiling_certificate(
            cert(
                [
                    {
                        "name": "success",
                        "direction": "benefit",
                        "lower_bound": 0,
                        "upper_bound": 1,
                        "brain_value": "0.999",
                    }
                ]
            )
        )
        self.assertEqual(
            verdict["status"],
            "OPEN__TARGET_INFORMATION_NOT_ELIMINATED",
        )

    def test_missing_scope_completeness_fails(self):
        candidate = cert(
            [
                {
                    "name": "success",
                    "direction": "benefit",
                    "lower_bound": 0,
                    "upper_bound": 1,
                    "brain_value": 1,
                }
            ]
        )
        candidate["semantic_receipt"]["scope_complete"] = False
        self.assertEqual(
            verify_ceiling_certificate(candidate)["status"],
            "FAIL_CLOSED",
        )

    def test_missing_monotonicity_fails(self):
        candidate = cert(
            [
                {
                    "name": "success",
                    "direction": "benefit",
                    "lower_bound": 0,
                    "upper_bound": 1,
                    "brain_value": 1,
                }
            ]
        )
        candidate["semantic_receipt"]["acceptance_preorder_monotone"] = False
        self.assertEqual(
            verify_ceiling_certificate(candidate)["status"],
            "FAIL_CLOSED",
        )

    def test_out_of_bounds_fails(self):
        verdict = verify_ceiling_certificate(
            cert(
                [
                    {
                        "name": "success",
                        "direction": "benefit",
                        "lower_bound": 0,
                        "upper_bound": 1,
                        "brain_value": 2,
                    }
                ]
            )
        )
        self.assertEqual(verdict["status"], "FAIL_CLOSED")

    def test_duplicate_coordinate_fails(self):
        verdict = verify_ceiling_certificate(
            cert(
                [
                    {
                        "name": "x",
                        "direction": "benefit",
                        "lower_bound": 0,
                        "upper_bound": 1,
                        "brain_value": 1,
                    },
                    {
                        "name": "x",
                        "direction": "loss",
                        "lower_bound": 0,
                        "upper_bound": 1,
                        "brain_value": 0,
                    },
                ]
            )
        )
        self.assertEqual(verdict["status"], "FAIL_CLOSED")

    def test_unknown_direction_fails(self):
        verdict = verify_ceiling_certificate(
            cert(
                [
                    {
                        "name": "x",
                        "direction": "magic",
                        "lower_bound": 0,
                        "upper_bound": 1,
                        "brain_value": 1,
                    }
                ]
            )
        )
        self.assertEqual(verdict["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
