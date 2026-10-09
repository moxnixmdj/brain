from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

fake_v1 = types.ModuleType("canonical.runtime.one_shot_verified_closure_v1")
fake_v1.run = lambda **kwargs: {}
sys.modules["canonical.runtime.one_shot_verified_closure_v1"] = fake_v1

from canonical.runtime import one_shot_reality_closure_v2 as v2


def closure(
    *,
    status,
    passed=False,
    internal=(),
    evidence=(),
    external=False,
    initial="i",
    final="f",
):
    return {
        "schema": "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1",
        "status": status,
        "pass": passed,
        "fixed_point": True,
        "closure_class": "x",
        "initial_frontier_digest": initial,
        "final_frontier_digest": final,
        "final_state_sha256": "a" * 64,
        "irreducible_external_information_proved": external,
        "residual": {
            "internal_blockers": list(internal),
            "evidence_blockers": list(evidence),
            "irreducible_external_information_proved": external,
        },
    }


class RealityClosureV2Tests(unittest.TestCase):
    def test_context_capacity_arithmetic_for_rank13_class(self):
        out = v2.certify_context_capacity_repair(
            observed_request_tokens=9202,
            configured_context_tokens=8192,
            candidate_context_tokens=16384,
            headroom_tokens=256,
        )
        self.assertTrue(out["arithmetic_capacity_pass"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["strict_required_context_tokens"], 9459)
        self.assertIn("LIVE_ZERO_EXPOSURE_RECEIPT_REQUIRED", out["status"])

    def test_context_capacity_live_gate_requires_exact_identity_and_zero_exposure(self):
        receipt = {
            "benchmark_exposure_count": 0,
            "observed_probe_tokens": 10000,
            "candidate_context_tokens": 16384,
            "live_probe_pass": True,
            "model_sha256": "model",
            "runtime_commit": "runtime",
            "receipt_sha256": "b" * 64,
        }
        out = v2.certify_context_capacity_repair(
            observed_request_tokens=9202,
            configured_context_tokens=8192,
            candidate_context_tokens=16384,
            headroom_tokens=256,
            live_probe_receipt=receipt,
            expected_model_sha256="model",
            expected_runtime_commit="runtime",
        )
        self.assertTrue(out["pass"])

    def test_internal_residual_compiles_to_constructive_gap(self):
        out = v2.compile_gap_contract(
            closure(status="OPEN", internal=("ROOT1_GAP",))
        )
        self.assertEqual(out["gap_class"], "CONSTRUCTIVE_CAPABILITY_GAP")
        self.assertFalse(out["verification_authority_mutation_allowed"])

    def test_external_acquisition_is_forbidden_without_irreducibility_proof(self):
        c = closure(
            status="OPEN",
            evidence=("MISSING_FACT",),
            external=False,
        )
        with patch.object(v2.v1, "run", return_value=c):
            out = v2.run(
                repo_root=".",
                reality_acquisition_provider=lambda contract: {
                    "pass": True,
                    "frontier_changed": True,
                    "verification_authority_mutated": False,
                    "receipt_sha256": "c" * 64,
                },
            )
        self.assertFalse(out["pass"])
        self.assertIn("EXTERNALITY_NOT_PROVED", out["status"])

    def test_constructive_gap_provider_then_verified_closure(self):
        first = closure(
            status="OPEN",
            internal=("ROOT1_GAP",),
            initial="i0",
            final="f0",
        )
        second = closure(
            status="PASS",
            passed=True,
            initial="i1",
            final="f1",
        )
        provider = lambda contract: {
            "pass": True,
            "frontier_changed": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "d" * 64,
        }
        with patch.object(v2.v1, "run", side_effect=[first, second]):
            out = v2.run(repo_root=".", capability_synthesis_provider=provider)
        self.assertTrue(out["pass"])
        self.assertEqual(out["status"], "PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT")

    def test_provider_false_progress_is_rejected_when_next_frontier_unchanged(self):
        first = closure(
            status="OPEN",
            internal=("ROOT1_GAP",),
            initial="i0",
            final="same",
        )
        second = closure(
            status="OPEN",
            internal=("ROOT1_GAP",),
            initial="same",
            final="same",
        )
        provider = lambda contract: {
            "pass": True,
            "frontier_changed": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "e" * 64,
        }
        with patch.object(v2.v1, "run", side_effect=[first, second]):
            out = v2.run(repo_root=".", capability_synthesis_provider=provider)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__PROVIDER_RECEIPT_WITHOUT_OBSERVED_FRONTIER_CHANGE",
        )

    def test_provider_cannot_mutate_verification_authority(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",))
        provider = lambda contract: {
            "pass": True,
            "frontier_changed": True,
            "verification_authority_mutated": True,
            "receipt_sha256": "f" * 64,
        }
        with patch.object(v2.v1, "run", return_value=first):
            with self.assertRaises(v2.RealityClosureError):
                v2.run(repo_root=".", capability_synthesis_provider=provider)

    def test_conservative_leverage_uses_probability_lower_bound(self):
        rows = v2.rank_candidates([
            {
                "id": "a",
                "success_probability_interval": [0.5, 0.9],
                "truth_reach_lower_bound": 10,
                "future_reuse_multiplier_lower_bound": 2,
                "critical_path_seconds": 10,
            },
            {
                "id": "b",
                "success_probability_interval": [0.9, 0.95],
                "truth_reach_lower_bound": 5,
                "future_reuse_multiplier_lower_bound": 1,
                "critical_path_seconds": 10,
            },
        ])
        self.assertEqual(rows[0]["id"], "a")
        self.assertAlmostEqual(rows[0]["conservative_leverage_score"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
