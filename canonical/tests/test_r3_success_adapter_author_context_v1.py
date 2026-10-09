from __future__ import annotations

import unittest

from canonical.runtime import r3_success_adapter_author_context_v1 as ctx


class R3SuccessAdapterAuthorContextV1Tests(unittest.TestCase):
    def test_redacts_values_but_preserves_protocol_shape(self):
        proof = {
            "proof_capsule_sha256": "a" * 64,
            "material": {
                "source_schema": "PROJECT_BRAIN_TEST_SUCCESS_V1",
                "source_status": "PASS__SECRET_BEARING_SUCCESS",
                "task_id": "USER_PRIVATE_TASK_ID",
                "selected_plan": [
                    "python.tests.audit.unittest",
                    "weird capability with private phrase",
                ],
                "verified_target_effects": [
                    "effect.one",
                    "super secret user sentence",
                ],
                "controller_checkpoint": {
                    "path": "private/checkpoint/location.json",
                    "plan_sha256": "c" * 64,
                },
                "execution": [
                    {
                        "capability_id": "python.tests.audit.unittest",
                        "pass": True,
                        "status": "PASS",
                        "composition_capsule_head_hash": "d" * 64,
                    }
                ],
                "cognition_dependency_class": "DETERMINISTIC_ONLY",
                "model_dependency_count": 0,
                "semantic_acceptance_complete": True,
                "raw_goal_sha256": "e" * 64,
                "raw_task_contract_sha256": "f" * 64,
                "raw_acceptance_obligation_count": 2,
                "accepted_raw_obligation_ids": ["private-one", "private-two"],
                "compiled_capability_id": "archive.tar_gz.create_from_manifest",
                "raw_goal_acceptance": {
                    "goal_text": "TOP_SECRET_GOAL_TEXT",
                    "private_payload": "TOP_SECRET_ACCEPTANCE_PAYLOAD",
                },
            },
        }
        replay = {
            "replay_capsule_sha256": "b" * 64,
            "context": {
                "mode": "raw_bound",
                "request": {
                    "task_id": "PRIVATE_TASK",
                    "goal": "TOP_SECRET_GOAL_TEXT",
                    "initial_facts": ["PRIVATE_FACT"],
                    "target_effects": ["PRIVATE_EFFECT"],
                    "capability_inputs": {
                        "archive.tar_gz.create_from_manifest": {
                            "input": "PRIVATE_PATH"
                        }
                    },
                    "unknown_private_field_name": "DO_NOT_EXPOSE",
                },
            },
        }

        out = ctx.compile_context(proof, replay)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["replay"]["mode"], "raw_bound")
        self.assertEqual(
            out["replay"]["request_keys"],
            ["task_id", "goal", "initial_facts", "target_effects", "capability_inputs"],
        )
        self.assertEqual(out["replay"]["request_shape"]["goal"], {"type": "string"})
        self.assertEqual(
            out["replay"]["request_shape"]["capability_inputs"],
            {"type": "object", "size": 1},
        )
        self.assertEqual(out["proof"]["selected_plan_count"], 2)
        self.assertEqual(out["proof"]["verified_target_effect_count"], 2)
        self.assertTrue(out["proof"]["controller_checkpoint_present"])
        self.assertEqual(out["proof"]["execution_count"], 1)
        self.assertTrue(out["proof"]["semantic_acceptance_complete"])
        self.assertEqual(out["proof"]["accepted_raw_obligation_id_count"], 2)
        self.assertTrue(out["proof"]["raw_goal_acceptance_present"])

        rendered = repr(out)
        for secret in (
            "TOP_SECRET_GOAL_TEXT",
            "TOP_SECRET_ACCEPTANCE_PAYLOAD",
            "PRIVATE_TASK",
            "PRIVATE_FACT",
            "PRIVATE_EFFECT",
            "PRIVATE_PATH",
            "DO_NOT_EXPOSE",
            "private/checkpoint/location.json",
            "private-one",
            "private-two",
            "super secret user sentence",
            "weird capability with private phrase",
        ):
            self.assertNotIn(secret, rendered)
        self.assertNotIn("unknown_private_field_name", rendered)
        self.assertTrue(out["redaction_policy"]["raw_goal_text_exposed"] is False)
        self.assertFalse(out["source_write_authority"])
        self.assertFalse(out["verification_authority"])

    def test_context_digest_changes_when_safe_structural_shape_changes(self):
        proof = {
            "proof_capsule_sha256": "a" * 64,
            "material": {
                "source_schema": "TEST",
                "source_status": "PASS",
                "selected_plan": [],
            },
        }
        a = ctx.compile_context(
            proof,
            {
                "replay_capsule_sha256": "b" * 64,
                "context": {"mode": "specialized", "request": {"task_id": "x"}},
            },
        )
        b = ctx.compile_context(
            proof,
            {
                "replay_capsule_sha256": "b" * 64,
                "context": {
                    "mode": "specialized",
                    "request": {"task_id": "x", "goal": "secret"},
                },
            },
        )
        self.assertTrue(a["pass"])
        self.assertTrue(b["pass"])
        self.assertNotEqual(a["context_sha256"], b["context_sha256"])

    def test_unsafe_symbol_is_hashed_not_exposed(self):
        out = ctx.compile_context(
            {
                "proof_capsule_sha256": "a" * 64,
                "material": {
                    "source_schema": "schema with secret prose",
                    "source_status": "PASS",
                    "selected_plan": ["capability with secret prose"],
                },
            },
            {
                "replay_capsule_sha256": "b" * 64,
                "context": {"mode": "specialized", "request": {}},
            },
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["proof"]["source_schema"].startswith("sha256:"))
        self.assertTrue(out["proof"]["selected_plan"][0].startswith("sha256:"))
        rendered = repr(out)
        self.assertNotIn("schema with secret prose", rendered)
        self.assertNotIn("capability with secret prose", rendered)

    def test_invalid_context_fails_closed(self):
        out = ctx.compile_context({}, {})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "PROOF_OR_REPLAY_CONTEXT_SHAPE_INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
