from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import professional_quality_p1_router_v6 as r


def target():
    return {
        "objective": "Improve the report",
        "audience": "executives",
        "source_evidence": ["source-a"],
        "artifact_type": "DOCX",
        "constraints": ["no unsupported claims"],
        "current_draft_or_render": "draft-v1",
    }


def decision_payload():
    return {
        "context_id": "professional-test",
        r.TARGET_KEY: target(),
    }


def base_state():
    return {
        "goal": "Improve the report for executives without unsupported claims.",
        "decision_payload": decision_payload(),
        "goal_to_decision_binding": {"receipt": {}, "verification": {}},
        "step_results": {},
        "detected_triggers": [],
    }


class ProfessionalQualityP1RouterV5Tests(unittest.TestCase):
    def test_unbound_top_level_target_is_forbidden(self):
        state = base_state()
        state["target_instance"] = target()
        out = r.route(state)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "UNBOUND_TOP_LEVEL_TARGET_INSTANCE_FORBIDDEN")

    def test_target_step_cannot_be_self_attested(self):
        state = base_state()
        state["step_results"][r.TARGET_STEP] = "PASS"
        out = r.route(state)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_COMPILATION_SELF_ATTESTATION_FORBIDDEN")

    def test_missing_binding_abstains(self):
        state = base_state()
        state.pop("goal_to_decision_binding")
        out = r.route(state)
        self.assertEqual(out["status"], "ABSTAIN__P1_AUTHENTICATED_TARGET_REQUIRED")
        self.assertEqual(out["route"], "ABSTAIN")
        self.assertFalse(out["target_instance_bound"])

    def test_target_must_come_from_bound_decision_payload(self):
        state = base_state()
        state["decision_payload"] = {"context_id": "professional-test"}
        out = r.route(state)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_INSTANCE_NOT_OBJECT")

    @patch.object(r.binding_authority, "authenticate_goal_binding")
    def test_failed_shared_goal_binding_blocks_before_v4(self, auth):
        auth.return_value = {
            "pass": False,
            "status": "FAIL_CLOSED__GOAL_TO_DECISION_BINDING_INVALID",
            "reason": "test",
        }
        state = base_state()
        out = r.route(state)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_GOAL_TO_DECISION_BINDING_INVALID")

    def _write_real_binding(
        self,
        root: Path,
        *,
        goal: str,
        payload: dict,
        producer_id: str = "producer-a",
        verifier_id: str = "verifier-b",
    ) -> dict:
        gov = root / "canonical/governance"
        ver = root / "canonical/verification"
        gov.mkdir(parents=True)
        ver.mkdir(parents=True)

        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        decision_sha = r.binding_authority.digest(payload)
        receipt = {
            "schema": r.binding_authority.GOAL_BINDING_SCHEMA,
            "goal_sha256": goal_sha,
            "decision_payload_sha256": decision_sha,
            "binding_proved": True,
            "load_bearing_constraints_preserved": True,
            "decision_context_semantically_sufficient": True,
            "producer_id": producer_id,
        }
        rp = gov / "goal_binding.json"
        rp.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
        receipt_blob = r.binding_authority.git_blob_sha(rp)

        verify = {
            "schema": r.binding_authority.GOAL_BINDING_VERIFY_SCHEMA,
            "subject_git_blob_sha": receipt_blob,
            "goal_sha256": goal_sha,
            "decision_payload_sha256": decision_sha,
            "pass": True,
            "independent_verified": True,
            "semantic_preservation_verified": True,
            "independent_verifier_id": verifier_id,
        }
        vp = ver / "goal_binding_verify.json"
        vp.write_text(json.dumps(verify, sort_keys=True), encoding="utf-8")

        return {
            "receipt": {
                "path": "canonical/governance/goal_binding.json",
                "git_blob_sha": receipt_blob,
            },
            "verification": {
                "path": "canonical/verification/goal_binding_verify.json",
                "git_blob_sha": r.binding_authority.git_blob_sha(vp),
            },
        }

    @patch.object(r.base, "route")
    def test_exact_bound_target_injects_target_step_and_delegates(self, v4):
        v4.return_value = {
            "status": "ROUTE__P1_ORDINARY",
            "route": "P1",
            "target_instance_bound": True,
            "quality_authority": False,
            "terminal_authority": False,
        }
        state = base_state()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state["goal_to_decision_binding"] = self._write_real_binding(
                root,
                goal=state["goal"],
                payload=state["decision_payload"],
            )
            out = r.route(state, repo_root=root)

        self.assertEqual(out["status"], "ROUTE__P1_ORDINARY", out)
        self.assertTrue(out["target_step_injected_by_authenticated_binding"])
        self.assertEqual(out["target_instance_source"], "AUTHENTICATED_DECISION_PAYLOAD")
        self.assertEqual(out["target_binding_producer_id"], "producer-a")
        self.assertEqual(out["target_binding_independent_verifier_id"], "verifier-b")
        delegated = v4.call_args.args[0]
        self.assertNotIn("goal", delegated)
        self.assertNotIn("decision_payload", delegated)
        self.assertNotIn("goal_to_decision_binding", delegated)
        self.assertEqual(delegated["target_instance"], target())
        self.assertEqual(delegated["step_results"][r.TARGET_STEP], "PASS")
        self.assertFalse(out["terminal_authority"])

    @patch.object(r.base, "route")
    def test_goal_or_payload_tamper_breaks_exact_binding(self, v4):
        v4.return_value = {"status": "ROUTE__P1_ORDINARY"}
        state = base_state()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state["goal_to_decision_binding"] = self._write_real_binding(
                root,
                goal=state["goal"],
                payload=state["decision_payload"],
            )
            state["decision_payload"] = deepcopy(state["decision_payload"])
            state["decision_payload"][r.TARGET_KEY] = deepcopy(target())
            state["decision_payload"][r.TARGET_KEY]["audience"] = "engineers"
            out = r.route(state, repo_root=root)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_GOAL_TO_DECISION_BINDING_INVALID")
        v4.assert_not_called()

    @patch.object(r.base, "route")
    def test_anonymous_verifier_is_rejected_even_if_shared_authenticator_passes(self, v4):
        v4.return_value = {"status": "ROUTE__P1_ORDINARY"}
        state = base_state()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state["goal_to_decision_binding"] = self._write_real_binding(
                root,
                goal=state["goal"],
                payload=state["decision_payload"],
                verifier_id="",
            )
            out = r.route(state, repo_root=root)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_BINDING_INDEPENDENT_VERIFIER_ID_REQUIRED")
        v4.assert_not_called()

    @patch.object(r.base, "route")
    def test_same_producer_and_verifier_is_rejected(self, v4):
        v4.return_value = {"status": "ROUTE__P1_ORDINARY"}
        state = base_state()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state["goal_to_decision_binding"] = self._write_real_binding(
                root,
                goal=state["goal"],
                payload=state["decision_payload"],
                producer_id="same",
                verifier_id="same",
            )
            out = r.route(state, repo_root=root)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_BINDING_PRODUCER_VERIFIER_NOT_INDEPENDENT")
        v4.assert_not_called()


    def test_v6_source_has_no_general_controller_dependency(self):
        source = Path(r.__file__).read_text(encoding="utf-8")
        self.assertNotIn("general_adequate_decision_controller_v1", source)
        self.assertIn("goal_to_decision_binding_authority_v1", source)


if __name__ == "__main__":
    unittest.main()
