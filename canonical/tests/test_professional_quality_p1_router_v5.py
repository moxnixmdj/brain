from __future__ import annotations

from unittest.mock import patch
import unittest

from canonical.runtime import professional_quality_p1_router_v5 as r


def target():
    return {
        "objective": "Improve the report",
        "audience": "executives",
        "source_evidence": ["source-a"],
        "artifact_type": "DOCX",
        "constraints": ["no unsupported claims"],
        "current_draft_or_render": "draft-v1",
    }


def model_same():
    return {
        "ambiguity_owner": "USER_INTENT",
        "hypothesis_set_complete": True,
        "worlds": [
            {"world_id": "a", "terminal_signature_complete": True, "terminal_signature": {"action": "SAME"}},
            {"world_id": "b", "terminal_signature_complete": True, "terminal_signature": {"action": "SAME"}},
        ],
        "observations": [],
    }


def model_distinct_with_observation():
    return {
        "ambiguity_owner": "USER_INTENT",
        "hypothesis_set_complete": True,
        "worlds": [
            {"world_id": "a", "terminal_signature_complete": True, "terminal_signature": {"action": "A"}},
            {"world_id": "b", "terminal_signature_complete": True, "terminal_signature": {"action": "B"}},
        ],
        "observations": [{
            "observation_id": "prior_binding",
            "cost_units": 0,
            "outcome_map_complete": True,
            "outcomes": {"a": "A", "b": "B"},
        }],
    }


def model_distinct_no_observation():
    m = model_distinct_with_observation()
    m["observations"] = []
    return m


class ProfessionalQualityP1RouterV5Tests(unittest.TestCase):
    def test_interpretation_model_is_required(self):
        out = r.route({"target_instance": target()})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "INTERPRETATION_MODEL_REQUIRED")

    def test_incomplete_interpretation_universe_fails_closed(self):
        m = model_same()
        m["hypothesis_set_complete"] = False
        out = r.route({"target_instance": target(), "interpretation_model": m})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "INTERPRETATION_MODEL_INSUFFICIENT")
        self.assertFalse(out["root_subject_binding_authority"])

    @patch.object(r.base, "route")
    def test_terminally_equivalent_interpretations_delegate_to_v4(self, base_route):
        base_route.return_value = {
            "status": "ROUTE__P1_ORDINARY",
            "route": "P1",
            "target_instance_bound": True,
            "quality_authority": False,
            "terminal_authority": False,
        }
        state = {"target_instance": target(), "interpretation_model": model_same()}
        out = r.route(state)
        self.assertEqual(out["status"], "ROUTE__P1_ORDINARY", out)
        self.assertTrue(out["interpretation_model_bound"])
        self.assertTrue(out["interpretation_binding"]["terminally_equivalent"])
        delegated = base_route.call_args.args[0]
        self.assertNotIn("interpretation_model", delegated)
        self.assertFalse(out["root_subject_binding_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    @patch.object(r.base, "route")
    def test_decision_relevant_ambiguity_uses_minimum_discriminator_without_delegating(self, base_route):
        out = r.route({
            "target_instance": target(),
            "interpretation_model": model_distinct_with_observation(),
        })
        self.assertEqual(out["status"], "ABSTAIN__R1_DECISION_RELEVANT_INTERPRETATION_AMBIGUITY", out)
        self.assertEqual(out["ambiguity_action"], "ACQUIRE_MINIMUM_TERMINALLY_RELEVANT_DISCRIMINATOR")
        self.assertEqual(out["next_observation_id"], "prior_binding")
        base_route.assert_not_called()

    @patch.object(r.base, "route")
    def test_inseparable_user_intent_requests_minimum_clarification(self, base_route):
        out = r.route({
            "target_instance": target(),
            "interpretation_model": model_distinct_no_observation(),
        })
        self.assertEqual(out["status"], "ABSTAIN__R1_DECISION_RELEVANT_INTERPRETATION_AMBIGUITY", out)
        self.assertTrue(out["ask_user_required"])
        self.assertTrue(out["clarification_required"])
        base_route.assert_not_called()

    def test_external_world_ambiguity_does_not_ask_user(self):
        m = model_distinct_no_observation()
        m["ambiguity_owner"] = "EXTERNAL_WORLD"
        out = r.route({"target_instance": target(), "interpretation_model": m})
        self.assertEqual(out["status"], "ABSTAIN__R1_DECISION_RELEVANT_INTERPRETATION_AMBIGUITY", out)
        self.assertFalse(out["ask_user_required"])
        self.assertEqual(out["ambiguity_action"], "ABSTAIN_OR_ACQUIRE_STRONGER_AUTHENTIC_INFORMATION")

    @patch.object(r.base, "route")
    def test_interpretation_model_is_content_bound(self, base_route):
        base_route.return_value = {"status": "ROUTE__P1_ORDINARY", "route": "P1"}
        m = model_same()
        out1 = r.route({"target_instance": target(), "interpretation_model": m})
        m2 = model_same()
        m2["worlds"][0]["world_id"] = "changed"
        out2 = r.route({"target_instance": target(), "interpretation_model": m2})
        self.assertNotEqual(
            out1["interpretation_binding"]["interpretation_model_sha256"],
            out2["interpretation_binding"]["interpretation_model_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
