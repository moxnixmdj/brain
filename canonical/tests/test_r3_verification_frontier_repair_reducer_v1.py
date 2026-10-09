from __future__ import annotations

import unittest

from canonical.runtime import r3_verification_frontier_repair_reducer_v1 as r


def base_context(proof):
    out = {
        "schema": "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_AUTHOR_CONTEXT_V1",
        "status": "PASS__REDACTED_ADAPTER_AUTHOR_CONTEXT_READY",
        "pass": True,
        "replay": {
            "mode": "specialized",
            "request_keys": ["task_id"],
            "request_shape": {"task_id": {"type": "string"}},
            "unmodeled_request_key_count": 0,
        },
        "proof": proof,
        "bindings": {
            "proof_capsule_sha256": "sha256:" + "a" * 64,
            "replay_capsule_sha256": "sha256:" + "b" * 64,
        },
        "redaction_policy": {
            "only_fixed_protocol_keys_and_sanitized_symbols_exposed": True,
            "structural_coverage_complete": True,
            "unmodeled_request_key_count": 0,
            "unmodeled_material_key_count": 0,
            "unmodeled_execution_key_count": 0,
        },
        "candidate_generation_authority": True,
        "source_write_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "context_sha256": "sha256:" + "c" * 64,
    }
    return out


class R3VerificationFrontierRepairReducerV1Tests(unittest.TestCase):
    def test_status_only_proof_requires_new_distinguishing_evidence(self):
        out = r.reduce_author_context(
            base_context(
                {
                    "material_keys": ["source_schema", "source_status"],
                    "selected_plan": [],
                    "selected_plan_count": 0,
                    "verified_target_effect_count": 0,
                    "controller_checkpoint_present": False,
                    "execution_rows": [],
                    "execution_count": 0,
                    "semantic_acceptance_complete": False,
                    "raw_goal_digest_present": False,
                    "raw_task_contract_digest_present": False,
                    "raw_acceptance_obligation_count": None,
                    "accepted_raw_obligation_id_count": 0,
                    "raw_goal_acceptance_present": False,
                    "structural_view_complete": True,
                }
            )
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["retained_proof_class"],
            "INSUFFICIENT_FOR_NONSELF_REFERENTIAL_VERIFICATION",
        )
        self.assertEqual(out["admissible_repair_classes"], [r.NEW_EVIDENCE])
        self.assertEqual(out["preferred_repair_order"], [r.NEW_EVIDENCE])
        self.assertTrue(out["must_acquire_new_distinguishing_evidence"])
        self.assertFalse(out["acquisition_authority"])
        self.assertFalse(out["verification_authority"])

    def test_complete_checkpointed_execution_keeps_adapter_and_verifier_routes(self):
        out = r.reduce_author_context(
            base_context(
                {
                    "selected_plan_count": 2,
                    "verified_target_effect_count": 1,
                    "controller_checkpoint_present": True,
                    "execution_count": 2,
                    "execution_rows": [
                        {
                            "pass": True,
                            "composition_digest_present": True,
                        },
                        {
                            "pass": True,
                            "composition_digest_present": True,
                        },
                    ],
                    "semantic_acceptance_complete": False,
                    "raw_goal_digest_present": False,
                    "raw_task_contract_digest_present": False,
                    "raw_acceptance_obligation_count": None,
                    "accepted_raw_obligation_id_count": 0,
                    "raw_goal_acceptance_present": False,
                    "structural_view_complete": True,
                }
            )
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["retained_proof_class"],
            "CHECKPOINTED_VERIFIED_EXECUTION",
        )
        self.assertEqual(
            out["admissible_repair_classes"],
            [r.ADAPTER, r.READONLY_VERIFIER, r.NEW_EVIDENCE],
        )
        self.assertEqual(out["preferred_repair_order"][0], r.ADAPTER)
        self.assertFalse(out["must_acquire_new_distinguishing_evidence"])

    def test_complete_raw_acceptance_keeps_adapter_and_verifier_routes(self):
        out = r.reduce_author_context(
            base_context(
                {
                    "selected_plan_count": 0,
                    "verified_target_effect_count": 0,
                    "controller_checkpoint_present": False,
                    "execution_count": 0,
                    "execution_rows": [],
                    "semantic_acceptance_complete": True,
                    "raw_goal_digest_present": True,
                    "raw_task_contract_digest_present": True,
                    "raw_acceptance_obligation_count": 3,
                    "accepted_raw_obligation_id_count": 3,
                    "raw_goal_acceptance_present": True,
                    "structural_view_complete": True,
                }
            )
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["retained_proof_class"],
            "SEMANTICALLY_ACCEPTED_RAW_SUCCESS",
        )
        self.assertEqual(
            out["admissible_repair_classes"],
            [r.ADAPTER, r.READONLY_VERIFIER, r.NEW_EVIDENCE],
        )
        self.assertFalse(out["must_acquire_new_distinguishing_evidence"])

    def test_partial_execution_does_not_get_adapter_or_verifier_credit(self):
        out = r.reduce_author_context(
            base_context(
                {
                    "selected_plan_count": 2,
                    "verified_target_effect_count": 1,
                    "controller_checkpoint_present": True,
                    "execution_count": 2,
                    "execution_rows": [
                        {"pass": True, "composition_digest_present": True},
                        {"pass": True, "composition_digest_present": False},
                    ],
                    "semantic_acceptance_complete": False,
                    "raw_goal_digest_present": False,
                    "raw_task_contract_digest_present": False,
                    "raw_acceptance_obligation_count": None,
                    "accepted_raw_obligation_id_count": 0,
                    "raw_goal_acceptance_present": False,
                    "structural_view_complete": True,
                }
            )
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["admissible_repair_classes"], [r.NEW_EVIDENCE])

    def test_incomplete_redacted_structure_cannot_eliminate_any_repair_class(self):
        ctx = base_context(
            {
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
                "structural_view_complete": False,
            }
        )
        ctx["redaction_policy"]["structural_coverage_complete"] = False
        ctx["redaction_policy"]["unmodeled_material_key_count"] = 1
        out = r.reduce_author_context(ctx)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["retained_proof_class"],
            "REDACTED_VIEW_STRUCTURALLY_INCOMPLETE",
        )
        self.assertEqual(
            out["admissible_repair_classes"],
            [r.ADAPTER, r.READONLY_VERIFIER, r.NEW_EVIDENCE],
        )
        self.assertFalse(out["must_acquire_new_distinguishing_evidence"])

    def test_untrusted_context_fails_closed(self):
        ctx = base_context({})
        ctx["pass"] = False
        out = r.reduce_author_context(ctx)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "AUTHOR_CONTEXT_NOT_AUTHENTICATED")
        self.assertEqual(out["admissible_repair_classes"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
