from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from canonical.runtime import professional_quality_p1_router_v4 as r


def contract():
    return {
        "behavior_id": r.target_sem.BEHAVIOR_ID,
        "inputs": "User objective, audience, source evidence, artifact type, constraints and current draft/render",
        "environment_state": "professional state",
        "allowed_information": "constraints and evidence",
        "required_output_or_action": "choose a plan",
        "success_condition": "quality improves",
        "failure_condition": "quality does not improve",
        "terminal_consequence": "professional task outcome",
        "verification_route": "independent evaluation",
        "dependency_boundary": "declared dependencies",
        "scope": "professional artifacts",
    }


def registry():
    return {"active_contracted_residuals": [contract()]}


def profile():
    return {
        "schema": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_V3",
        "behavior_id": r.target_sem.BEHAVIOR_ID,
    }


def target():
    return {
        "objective": "Improve the report",
        "audience": "executives",
        "source_evidence": ["source-a"],
        "artifact_type": "DOCX",
        "constraints": ["no unsupported claims"],
        "current_draft_or_render": "draft-v1",
    }


def loader(root, rel, blob):
    if rel == r.PROFILE_PATH:
        return profile()
    if rel == r.CONTRACT_REGISTRY_PATH:
        return registry()
    raise AssertionError(rel)


class ProfessionalQualityP1RouterV4Tests(unittest.TestCase):
    def test_missing_target_instance_fails_closed(self):
        out = r.route({})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_INSTANCE_NOT_OBJECT")

    def test_missing_target_field_fails_closed(self):
        t = target()
        t.pop("audience")
        out = r.route({"target_instance": t})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_INSTANCE_MISSING_FIELDS:audience", out["reason"])

    def test_unknown_target_field_fails_closed(self):
        t = target()
        t["mystery"] = 1
        out = r.route({"target_instance": t})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_INSTANCE_UNKNOWN_FIELDS:mystery", out["reason"])

    @patch.object(r, "_load_json_bound", side_effect=loader)
    @patch.object(r.base, "route")
    def test_valid_target_binds_exact_instance_before_v3(self, base_route, _load):
        base_route.return_value = {
            "status": "ROUTE__P1_ORDINARY",
            "route": "P1",
            "quality_authority": False,
            "terminal_authority": False,
        }
        state = {"target_instance": target(), "detected_triggers": [], "step_results": {}}
        out = r.route(state)
        self.assertTrue(out["target_instance_bound"], out)
        self.assertEqual(
            out["target_instance_binding"]["target_instance_sha256"],
            r._digest(target()),
        )
        self.assertEqual(
            out["target_instance_binding"]["contract_sha256"],
            r.target_sem.digest(contract()),
        )
        delegated = base_route.call_args.args[0]
        self.assertNotIn("target_instance", delegated)
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    @patch.object(r, "_load_json_bound")
    def test_profile_behavior_drift_fails_closed(self, load):
        bad = profile()
        bad["behavior_id"] = "OTHER"
        load.side_effect = [bad, registry()]
        out = r.route({"target_instance": target()})
        self.assertEqual(out["reason"], "PROFILE_BEHAVIOR_ID_MISMATCH")

    @patch.object(r, "_load_json_bound", side_effect=loader)
    @patch.object(r.target_sem, "certify")
    def test_semantic_certificate_failure_blocks_routing(self, certify, _load):
        certify.return_value = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["CONTRACT_DRIFT"],
        }
        out = r.route({"target_instance": target()})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TARGET_SEMANTIC_CERTIFICATE_FAILED")


if __name__ == "__main__":
    unittest.main()
