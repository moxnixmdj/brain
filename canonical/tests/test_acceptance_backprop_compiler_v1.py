from __future__ import annotations

import unittest

from canonical.runtime.acceptance_backprop_compiler_v1 import (
    SCHEMA,
    evaluate,
    population_commitment_sha256,
)


def base(population_size: int = 600, threshold: float = 40.0):
    population_ids = [f"c{i:03d}" for i in range(population_size)]
    return {
        "schema": SCHEMA,
        "metric_semantics_frozen": True,
        "population_frozen": True,
        "scorer_identity_bound": True,
        "metric_type": "BINARY_RATE",
        "population_ids": population_ids,
        "population_commitment_sha256": population_commitment_sha256(population_ids),
        "threshold_percent": threshold,
        "partitions": [],
    }


def partition(payload, pid, outcome, ids):
    return {
        "partition_id": pid,
        "outcome": outcome,
        "slot_ids": list(ids),
        "population_commitment_sha256": payload["population_commitment_sha256"],
        "receipt_path": f"canonical/verification/{pid}.json",
        "receipt_sha": "a" * 40,
        "independent_verified": True,
        "scope_complete": True,
    }


class Tests(unittest.TestCase):
    def test_backpropagates_automationbench_threshold_without_execution(self):
        payload = base()
        out = evaluate(payload)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["threshold_success_count"], 240)
        self.assertEqual(out["minimum_additional_success_mass_required"], 240)
        self.assertEqual(out["decision"], "UNRESOLVED")
        self.assertEqual(out["new_reality_units_consumed"], 0)

    def test_scope_complete_class_proof_can_lock_pass(self):
        payload = base()
        payload["partitions"] = [
            partition(payload, "class-proof", "PROVED_PASS", payload["population_ids"][:240])
        ]
        out = evaluate(payload)
        self.assertEqual(out["proved_passes"], 240)
        self.assertEqual(out["observed_passes"], 0)
        self.assertEqual(out["decision"], "PASS_LOCKED")
        self.assertEqual(out["minimum_additional_success_mass_required"], 0)

    def test_proof_and_observation_mass_compose_exactly(self):
        payload = base()
        payload["partitions"] = [
            partition(payload, "formal", "PROVED_PASS", payload["population_ids"][:200]),
            partition(payload, "observed", "OBSERVED_PASS", payload["population_ids"][200:240]),
        ]
        out = evaluate(payload)
        self.assertEqual(out["credited_passes"], 240)
        self.assertEqual(out["decision"], "PASS_LOCKED")

    def test_remaining_mass_is_exact(self):
        payload = base()
        payload["partitions"] = [
            partition(payload, "formal", "PROVED_PASS", payload["population_ids"][:220]),
            partition(payload, "known-fail", "PROVED_FAIL", payload["population_ids"][220:260]),
        ]
        out = evaluate(payload)
        self.assertEqual(out["minimum_additional_success_mass_required"], 20)
        self.assertEqual(out["unknown_count"], 340)
        self.assertEqual(out["decision"], "UNRESOLVED")

    def test_fail_lock_from_proved_failures(self):
        payload = base(population_size=100, threshold=60)
        payload["partitions"] = [
            partition(payload, "fail-proof", "PROVED_FAIL", payload["population_ids"][:41])
        ]
        out = evaluate(payload)
        self.assertEqual(out["optimistic_success_upper_bound"], 59)
        self.assertEqual(out["decision"], "FAIL_LOCKED")

    def test_overlap_fails_closed(self):
        payload = base(population_size=10, threshold=50)
        payload["partitions"] = [
            partition(payload, "a", "PROVED_PASS", ["c000", "c001"]),
            partition(payload, "b", "OBSERVED_PASS", ["c001", "c002"]),
        ]
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertTrue(any("PARTITION_OVERLAP" in x for x in out["errors"]))

    def test_unverified_proof_fails_closed(self):
        payload = base(population_size=10, threshold=50)
        row = partition(payload, "a", "PROVED_PASS", ["c000"])
        row["independent_verified"] = False
        payload["partitions"] = [row]
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertIn("INDEPENDENT_VERIFICATION_REQUIRED:a", out["errors"])

    def test_missing_scope_completeness_fails_closed(self):
        payload = base(population_size=10, threshold=50)
        row = partition(payload, "a", "PROVED_PASS", ["c000"])
        row["scope_complete"] = False
        payload["partitions"] = [row]
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertIn("SCOPE_COMPLETENESS_REQUIRED:a", out["errors"])

    def test_population_commitment_mismatch_fails_closed(self):
        payload = base(population_size=10, threshold=50)
        payload["population_commitment_sha256"] = "0" * 64
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertIn("POPULATION_COMMITMENT_MISMATCH", out["errors"])

    def test_partition_commitment_mismatch_fails_closed(self):
        payload = base(population_size=10, threshold=50)
        row = partition(payload, "a", "PROVED_PASS", ["c000"])
        row["population_commitment_sha256"] = "0" * 64
        payload["partitions"] = [row]
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertIn("PARTITION_POPULATION_COMMITMENT_MISMATCH:a", out["errors"])

    def test_invalid_receipt_digest_fails_closed(self):
        payload = base(population_size=10, threshold=50)
        row = partition(payload, "a", "PROVED_PASS", ["c000"])
        row["receipt_sha"] = "not-content-addressed"
        payload["partitions"] = [row]
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertIn("CONTENT_ADDRESSED_RECEIPT_SHA_REQUIRED:a", out["errors"])

    def test_outside_population_fails_closed(self):
        payload = base(population_size=10, threshold=50)
        payload["partitions"] = [
            partition(payload, "a", "PROVED_PASS", ["not-a-case"])
        ]
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertTrue(any("PARTITION_OUTSIDE_POPULATION" in x for x in out["errors"]))

    def test_unsupported_metric_fails_closed(self):
        payload = base(population_size=10, threshold=50)
        payload["metric_type"] = "ELO"
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertIn("UNSUPPORTED_METRIC_TYPE", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
