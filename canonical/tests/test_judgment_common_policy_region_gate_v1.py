import copy
import unittest

from canonical.runtime.judgment_control_envelope_v1 import (
    FINANCE_SUPERVISORY,
    _base_bundle,
)
from canonical.runtime.judgment_common_policy_region_gate_v1 import (
    configured_terminal_decision_with_common_policy,
)


def ambiguous_bundle():
    text = "Every applicable rule must not omit a material exception before execution."
    b = _base_bundle(text, "f", ["rule", "exception"], "APPLY_RULE")
    b["interpretations"] = [
        {
            "id": "i1", "meaning": "reading one",
            "consistent_with_source": True,
            "consistent_with_authorized_context": True,
            "materially_distinct": True,
            "discriminator": "d",
        },
        {
            "id": "i2", "meaning": "reading two",
            "consistent_with_source": True,
            "consistent_with_authorized_context": True,
            "materially_distinct": True,
            "discriminator": "d",
        },
    ]
    return b


def proposal():
    return {
        "decision": "CONCLUDE",
        "leaf_id": FINANCE_SUPERVISORY,
        "selected_alternative": "APPLY_RULE",
        "rule_evidence_ids": ["rule"],
        "exception_evidence_ids": ["exception"],
        "reconciliation_checks": [],
    }


def binding(*, second_policy="APPLY_RULE", certified=True):
    return {
        "schema": "PROJECT_BRAIN_COMMON_POLICY_POSITIVE_ADEQUACY_BINDING_V1",
        "positive_edges_independently_certified": certified,
        "worlds": ["i1", "i2"],
        "policies": ["APPLY_RULE", "OTHER"],
        "certified_adequate": {
            "i1": ["APPLY_RULE"],
            "i2": [second_policy],
        },
    }


class Tests(unittest.TestCase):
    def test_unique_v1_route_is_preserved_without_common_policy_binding(self):
        b = _base_bundle(
            "Every applicable rule must not omit a material exception before execution.",
            "f", ["rule", "exception"], "APPLY_RULE"
        )
        out = configured_terminal_decision_with_common_policy(proposal(), b, None, mode="FINANCE")
        self.assertTrue(out["accepted"], out)
        self.assertEqual(out["route"], "V1_UNIQUE")

    def test_ambiguous_common_policy_is_accepted(self):
        out = configured_terminal_decision_with_common_policy(
            proposal(), ambiguous_bundle(), binding(), mode="FINANCE"
        )
        self.assertTrue(out["accepted"], out)
        self.assertEqual(out["selected_policy"], "APPLY_RULE")
        self.assertEqual(out["surviving_interpretation_ids"], ["i1", "i2"])
        self.assertFalse(out["semantic_world_identification_required"])

    def test_different_required_policies_without_discriminator_block(self):
        out = configured_terminal_decision_with_common_policy(
            proposal(), ambiguous_bundle(), binding(second_policy="OTHER"), mode="FINANCE"
        )
        self.assertFalse(out["accepted"])
        self.assertEqual(out["reason"], "NO_COMMON_CERTIFIED_POLICY")

    def test_caller_asserted_edges_without_independent_authority_block(self):
        out = configured_terminal_decision_with_common_policy(
            proposal(), ambiguous_bundle(), binding(certified=False), mode="FINANCE"
        )
        self.assertFalse(out["accepted"])
        self.assertEqual(out["reason"], "POSITIVE_ADEQUACY_PROOF_AUTHORITY_MISSING")

    def test_world_domain_mismatch_blocks(self):
        x = binding()
        x["worlds"] = ["i1"]
        out = configured_terminal_decision_with_common_policy(
            proposal(), ambiguous_bundle(), x, mode="FINANCE"
        )
        self.assertFalse(out["accepted"])
        self.assertEqual(out["reason"], "COMMON_POLICY_WORLD_DOMAIN_MISMATCH")

    def test_other_v1_error_cannot_be_bypassed(self):
        p = proposal()
        p["exception_evidence_ids"] = ["missing"]
        out = configured_terminal_decision_with_common_policy(
            p, ambiguous_bundle(), binding(), mode="FINANCE"
        )
        self.assertFalse(out["accepted"])
        self.assertEqual(out["reason"], "BASE_V1_HAS_NON_UNIQUENESS_ERRORS")

    def test_common_policy_must_match_recomputed_decision(self):
        x = binding(second_policy="OTHER")
        x["certified_adequate"]["i1"] = ["OTHER"]
        p = proposal()
        out = configured_terminal_decision_with_common_policy(p, ambiguous_bundle(), x, mode="FINANCE")
        self.assertFalse(out["accepted"])
        self.assertEqual(out["reason"], "COMMON_POLICY_DOES_NOT_MATCH_RECOMPUTED_TERMINAL_DECISION")


if __name__ == "__main__":
    unittest.main(verbosity=2)
