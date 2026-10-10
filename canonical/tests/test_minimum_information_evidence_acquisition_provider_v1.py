from __future__ import annotations

import unittest

from canonical.runtime import minimum_information_evidence_acquisition_provider_v1 as provider


def request(row):
    minimum = {
        "schema": provider.MINIMUM_INFORMATION_SCHEMA,
        "requests": [row],
        "request_count": 1,
    }
    return {
        "gap_class": "PENDING_ACQUISITION_OR_EXPERIMENT",
        "minimum_information_contract": minimum,
    }


class Tests(unittest.TestCase):
    def test_broad_r2_cell_declines_without_crawl(self):
        out = provider.acquire(request({
            "kind": "R2_STRUCTURED_POLICY_CHANGING_ACQUISITION",
            "r2_cell_id": "FINANCE_SEMANTIC_ADEQUACY_TAIL",
            "required_action": "ACQUIRE_ONLY_MINIMUM_POLICY_CHANGING_EVIDENCE",
            "remaining_boundary": "OPEN_WORLD_SEMANTIC_RESIDUAL",
        }))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], provider.NO_CONCRETE_TARGET_STATUS)
        self.assertTrue(provider.is_sound_nonactionable_decline(out))
        self.assertEqual(out["concrete_target_count"], 0)
        self.assertFalse(out["broad_acquisition_attempted"])
        self.assertFalse(out["frontier_changed"])
        self.assertFalse(out["verification_authority_mutated"])
        self.assertEqual(len(out["receipt_sha256"]), 64)

    def test_concrete_target_requires_source_specific_adapter(self):
        out = provider.acquire(request({
            "kind": "R2_STRUCTURED_POLICY_CHANGING_ACQUISITION",
            "r2_cell_id": "FINANCE_SEMANTIC_ADEQUACY_TAIL",
            "predicate_id": "predicate:example",
            "source_id": "source:example",
        }))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], provider.SOURCE_ADAPTER_REQUIRED_STATUS)
        self.assertTrue(provider.is_sound_nonactionable_decline(out))
        self.assertEqual(out["concrete_target_count"], 1)
        self.assertFalse(out["acquisition_or_experiment_attempted"])
        self.assertFalse(out["terminal_authority"])

    def test_invalid_request_fails_closed(self):
        out = provider.acquire(None)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__REQUEST_MAPPING_REQUIRED")
        self.assertFalse(provider.is_sound_nonactionable_decline(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
