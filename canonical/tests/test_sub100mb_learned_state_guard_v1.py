from __future__ import annotations

import copy
import unittest

from canonical.runtime.sub100mb_learned_state_guard_v1 import (
    HYPOTHESIS_ID,
    INPUT_SCHEMA,
    MAX_LEARNED_BYTES,
    audit,
)

SHA = "a" * 64


def base() -> dict:
    return {
        "schema": INPUT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "max_persistent_learned_bytes": MAX_LEARNED_BYTES,
        "learned_artifacts": [
            {
                "id": "kernel",
                "path": "artifacts/kernel.bin",
                "bytes": 80_000_000,
                "sha256": SHA,
            }
        ],
        "runtime_dependencies": [
            {
                "id": "kernel-runtime",
                "kind": "learned_component",
                "artifact_id": "kernel",
            },
            {
                "id": "python",
                "kind": "executor",
            },
            {
                "id": "docs",
                "kind": "raw_knowledge_source",
            },
        ],
        "scored_execution": {
            "external_frontier_model_calls": 0,
            "external_learned_capability_calls": 0,
        },
        "capability_contract": {
            "accepted_families": 19,
            "verified_owned_families": 19,
            "total_families": 19,
            "proved_atomic": 38,
            "total_atomic": 38,
        },
    }


class Sub100MBLearnedStateGuardTests(unittest.TestCase):
    def test_exact_valid_candidate_closes(self):
        out = audit(base())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["status"], "H100_CLOSED")
        self.assertEqual(out["learned_bytes_total"], 80_000_000)

    def test_exact_100mb_is_allowed(self):
        d = base()
        d["learned_artifacts"][0]["bytes"] = 100_000_000
        out = audit(d)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["learned_bytes_headroom"], 0)

    def test_one_byte_over_budget_is_rejected(self):
        d = base()
        d["learned_artifacts"][0]["bytes"] = 100_000_001
        out = audit(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "CANDIDATE_REJECTED")
        self.assertFalse(out["budget_pass"])

    def test_external_frontier_model_dependency_is_forbidden(self):
        d = base()
        d["runtime_dependencies"].append(
            {"id": "remote-model", "kind": "external_frontier_model"}
        )
        out = audit(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "CANDIDATE_REJECTED")
        self.assertFalse(out["provider_boundary_pass"])
        self.assertEqual(out["forbidden_runtime_dependencies"], ["remote-model"])

    def test_external_learned_provider_call_is_forbidden(self):
        d = base()
        d["scored_execution"]["external_learned_capability_calls"] = 1
        out = audit(d)
        self.assertFalse(out["pass"])
        self.assertFalse(out["provider_boundary_pass"])

    def test_raw_knowledge_source_is_allowed(self):
        out = audit(base())
        self.assertTrue(out["provider_boundary_pass"], out)

    def test_learned_component_must_be_counted(self):
        d = base()
        d["runtime_dependencies"][0]["artifact_id"] = "unreported-model"
        out = audit(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("LEARNED_COMPONENT_NOT_COUNTED:kernel-runtime", out["errors"])

    def test_duplicate_learned_artifact_id_fails_closed(self):
        d = base()
        d["learned_artifacts"].append(copy.deepcopy(d["learned_artifacts"][0]))
        out = audit(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("LEARNED_ARTIFACT_ID_DUPLICATE:kernel", out["errors"])

    def test_invalid_sha256_fails_closed(self):
        d = base()
        d["learned_artifacts"][0]["sha256"] = "not-a-sha"
        out = audit(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("LEARNED_ARTIFACT_SHA256_INVALID:kernel", out["errors"])

    def test_budget_cannot_be_relaxed(self):
        d = base()
        d["max_persistent_learned_bytes"] = 101_000_000
        out = audit(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("BUDGET_NOT_FROZEN_EXACTLY_100000000", out["errors"])

    def test_incomplete_capability_contract_stays_open(self):
        d = base()
        d["capability_contract"].update(
            {
                "accepted_families": 5,
                "verified_owned_families": 5,
                "proved_atomic": 12,
            }
        )
        out = audit(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "EXPERIMENT_OPEN")
        self.assertTrue(out["budget_pass"])
        self.assertTrue(out["provider_boundary_pass"])
        self.assertFalse(out["capability_pass"])

    def test_denominators_cannot_be_shrunk(self):
        d = base()
        d["capability_contract"]["total_atomic"] = 12
        out = audit(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("ATOMIC_DENOMINATOR_CHANGED", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
