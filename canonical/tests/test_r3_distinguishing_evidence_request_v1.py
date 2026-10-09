from __future__ import annotations

import unittest

from canonical.runtime import r3_distinguishing_evidence_request_v1 as req
from canonical.runtime import r3_success_adapter_author_context_v1 as author_context


def context(proof: dict, *, complete: bool = True) -> dict:
    out = {
        "schema": "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_AUTHOR_CONTEXT_V1",
        "status": "PASS__REDACTED_ADAPTER_AUTHOR_CONTEXT_READY",
        "pass": True,
        "replay": {
            "mode": "specialized",
            "request_keys": ["task_id"],
            "request_shape": {"task_id": {"type": "string"}},
            "unmodeled_request_key_count": 0 if complete else 1,
        },
        "proof": {
            **proof,
            "structural_view_complete": complete,
        },
        "bindings": {
            "proof_capsule_sha256": "sha256:" + "a" * 64,
            "replay_capsule_sha256": "sha256:" + "b" * 64,
        },
        "redaction_policy": {
            "only_fixed_protocol_keys_and_sanitized_symbols_exposed": True,
            "structural_coverage_complete": complete,
            "unmodeled_request_key_count": 0 if complete else 1,
            "unmodeled_material_key_count": 0,
            "unmodeled_execution_key_count": 0,
        },
        "candidate_generation_authority": True,
        "source_write_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }
    out["context_sha256"] = author_context.context_sha256(out)
    return out


def status_only() -> dict:
    return {
        "selected_plan_count": 0,
        "verified_target_effect_count": 0,
        "controller_checkpoint_present": False,
        "execution_count": 0,
        "execution_rows": [],
        "semantic_acceptance_complete": False,
        "raw_goal_digest_present": False,
        "raw_task_contract_digest_present": False,
        "raw_acceptance_obligation_count": None,
        "accepted_raw_obligation_id_count": 0,
        "raw_goal_acceptance_present": False,
    }


class R3DistinguishingEvidenceRequestV1Tests(unittest.TestCase):
    def test_status_only_emits_tied_six_obligation_routes(self):
        out = req.compile_request(context(status_only()))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["minimum_missing_obligation_count"], 6)
        self.assertEqual(
            {row["route"] for row in out["candidate_evidence_bundles"]},
            {req.CHECKPOINT_ROUTE, req.RAW_ROUTE},
        )
        self.assertEqual(len(out["candidate_evidence_bundles"]), 2)
        self.assertFalse(out["acquisition_authority"])
        self.assertFalse(out["provider_truth_authority"])
        self.assertFalse(out["verification_authority"])

    def test_one_missing_composition_digest_selects_checkpoint_route(self):
        proof = {
            **status_only(),
            "selected_plan_count": 2,
            "verified_target_effect_count": 1,
            "controller_checkpoint_present": True,
            "execution_count": 2,
            "execution_rows": [
                {"pass": True, "composition_digest_present": True},
                {"pass": True, "composition_digest_present": False},
            ],
        }
        out = req.compile_request(context(proof))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["minimum_missing_obligation_count"], 1)
        self.assertEqual(len(out["candidate_evidence_bundles"]), 1)
        bundle = out["candidate_evidence_bundles"][0]
        self.assertEqual(bundle["route"], req.CHECKPOINT_ROUTE)
        self.assertEqual(
            bundle["missing_obligations"],
            ["COMPOSITION_DIGEST_PRESENT_FOR_EVERY_EXECUTION_ROW"],
        )

    def test_one_missing_raw_acceptance_flag_selects_raw_route(self):
        proof = {
            **status_only(),
            "semantic_acceptance_complete": False,
            "raw_goal_digest_present": True,
            "raw_task_contract_digest_present": True,
            "raw_acceptance_obligation_count": 2,
            "accepted_raw_obligation_id_count": 2,
            "raw_goal_acceptance_present": True,
        }
        out = req.compile_request(context(proof))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["minimum_missing_obligation_count"], 1)
        self.assertEqual(out["candidate_evidence_bundles"][0]["route"], req.RAW_ROUTE)
        self.assertEqual(
            out["candidate_evidence_bundles"][0]["missing_obligations"],
            ["SEMANTIC_ACCEPTANCE_COMPLETE"],
        )

    def test_context_digest_tamper_fails_closed(self):
        ctx = context(status_only())
        ctx["proof"]["selected_plan_count"] = 1
        out = req.compile_request(ctx)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "AUTHOR_CONTEXT_DIGEST_MISMATCH")

    def test_incomplete_structural_view_cannot_claim_minimum(self):
        out = req.compile_request(context(status_only(), complete=False))
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "STRUCTURAL_VIEW_INCOMPLETE__MINIMUM_REQUEST_UNPROVED",
        )

    def test_complete_checkpoint_route_is_not_evidence_only(self):
        proof = {
            **status_only(),
            "selected_plan_count": 1,
            "verified_target_effect_count": 1,
            "controller_checkpoint_present": True,
            "execution_count": 1,
            "execution_rows": [
                {"pass": True, "composition_digest_present": True},
            ],
        }
        out = req.compile_request(context(proof))
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "NEW_DISTINGUISHING_EVIDENCE_NOT_THE_ONLY_ADMISSIBLE_REPAIR_CLASS",
        )

    def test_request_digest_is_self_consistent(self):
        out = req.compile_request(context(status_only()))
        self.assertTrue(out["pass"], out)
        expected = dict(out)
        digest = expected.pop("request_sha256")
        self.assertEqual(digest, req._digest(expected))


if __name__ == "__main__":
    unittest.main(verbosity=2)
