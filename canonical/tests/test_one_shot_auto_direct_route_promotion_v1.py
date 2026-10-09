from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

fake_v1 = types.ModuleType("canonical.runtime.one_shot_verified_closure_v1")
fake_v1.run = lambda **kwargs: {}
sys.modules["canonical.runtime.one_shot_verified_closure_v1"] = fake_v1

from canonical.runtime import one_shot_reality_closure_v2 as v2


def closure(*, status, passed=False, internal=(), initial="i", final="f"):
    return {
        "schema": "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1",
        "status": status,
        "pass": passed,
        "fixed_point": True,
        "closure_class": "TEST",
        "initial_frontier_digest": initial,
        "final_frontier_digest": final,
        "final_state_sha256": "a" * 64,
        "irreducible_external_information_proved": False,
        "residual": {
            "internal_blockers": list(internal),
            "evidence_blockers": [],
            "irreducible_external_information_proved": False,
        },
    }


def provider_receipt(**extra):
    out = {
        "pass": True,
        "frontier_changed": True,
        "verification_authority_mutated": False,
        "receipt_sha256": "d" * 64,
        "reuse_or_search_trace_complete": True,
        "new_code_written": False,
        "verifier_generated_or_reused": True,
        "verifier_passed": True,
    }
    out.update(extra)
    return out


class OneShotAutoDirectRoutePromotionV1Tests(unittest.TestCase):
    def test_provider_without_route_proposal_preserves_existing_behavior(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",), initial="i0", final="f0")
        second = closure(status="PASS", passed=True, initial="i1", final="f1")
        with patch.object(v2.v1, "run", side_effect=[first, second]), patch.object(
            v2.r2_direct_route_promoter, "promote"
        ) as promote:
            out = v2.run(
                repo_root=".",
                capability_synthesis_provider=lambda contract: provider_receipt(),
            )
        self.assertTrue(out["pass"], out)
        promote.assert_not_called()
        row = out["transcript"][0]["r2_direct_route_promotion"]
        self.assertFalse(row["attempted"])

    def test_verified_candidate_and_receipt_are_promoted_before_retry(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",), initial="i0", final="f0")
        second = closure(status="PASS", passed=True, initial="i1", final="f1")
        receipt = provider_receipt(
            r2_direct_route_candidate_path="canonical/governance/CANDIDATE.json",
            r2_direct_route_independent_receipt_path="canonical/verification/RECEIPT.json",
        )
        promoted = {
            "pass": True,
            "status": "PASS__R2_DIRECT_ROUTE_PROMOTED_AND_CURRENT_POINTER_REPLAYED",
            "route_id": "DIRECT_ADEQUACY::TEST_V1",
            "frontier_changed": True,
            "new_manifest_git_blob_sha": "1" * 40,
            "receipt_sha256": "2" * 64,
            "verification_authority_mutated": False,
            "terminal_authority": False,
        }
        with patch.object(v2.v1, "run", side_effect=[first, second]), patch.object(
            v2.r2_direct_route_promoter, "promote", return_value=promoted
        ) as promote:
            out = v2.run(
                repo_root=".",
                capability_synthesis_provider=lambda contract: receipt,
            )
        self.assertTrue(out["pass"], out)
        promote.assert_called_once_with(
            candidate_path="canonical/governance/CANDIDATE.json",
            receipt_path="canonical/verification/RECEIPT.json",
            repo_root=".",
        )
        row = out["transcript"][0]["r2_direct_route_promotion"]
        self.assertTrue(row["attempted"])
        self.assertTrue(row["frontier_changed"])
        self.assertEqual(row["route_id"], "DIRECT_ADEQUACY::TEST_V1")

    def test_incomplete_route_binding_fails_closed(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",))
        receipt = provider_receipt(
            r2_direct_route_candidate_path="canonical/governance/CANDIDATE.json",
        )
        with patch.object(v2.v1, "run", return_value=first):
            out = v2.run(
                repo_root=".",
                capability_synthesis_provider=lambda contract: receipt,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__INTERNAL_UNSOLVED__INFRASTRUCTURE_OR_PROVIDER_FAILURE",
        )
        self.assertIn(
            "R2_DIRECT_ROUTE_PROMOTION_BINDING_INCOMPLETE",
            out["failure"]["reason"],
        )

    def test_promoter_rejection_cannot_be_laundered_into_provider_success(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",))
        receipt = provider_receipt(
            r2_direct_route_candidate_path="canonical/governance/CANDIDATE.json",
            r2_direct_route_independent_receipt_path="canonical/verification/RECEIPT.json",
        )
        with patch.object(v2.v1, "run", return_value=first), patch.object(
            v2.r2_direct_route_promoter,
            "promote",
            return_value={
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "BAD_RECEIPT",
                "verification_authority_mutated": False,
            },
        ):
            out = v2.run(
                repo_root=".",
                capability_synthesis_provider=lambda contract: receipt,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__INTERNAL_UNSOLVED__INFRASTRUCTURE_OR_PROVIDER_FAILURE",
        )
        self.assertIn("R2_DIRECT_ROUTE_PROMOTION_FAILED", out["failure"]["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
