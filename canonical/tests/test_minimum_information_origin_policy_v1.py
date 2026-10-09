import unittest

from canonical.runtime.minimum_information_origin_policy_v1 import route


class Tests(unittest.TestCase):
    def test_reuses_existing_context_before_any_question_or_research(self):
        out = route({
            "decision_relevant": True,
            "context_value_bound": True,
            "information_owner": "UNKNOWN",
            "context_binding_id": "conversation:product-and-seller",
        })
        self.assertEqual(out["action"], "REUSE_BOUND_CONTEXT")
        self.assertFalse(out["external_research_authorized"])
        self.assertFalse(out["ask_user_required"])

    def test_missing_user_purchase_specification_asks_user_not_web(self):
        out = route({
            "decision_relevant": True,
            "context_value_bound": False,
            "information_owner": "USER_SPECIFICATION",
            "clarification_key": "product_and_vendor",
        })
        self.assertEqual(out["action"], "ASK_USER_MINIMUM_CLARIFICATION")
        self.assertTrue(out["ask_user_required"])
        self.assertFalse(out["external_research_authorized"])

    def test_bound_amazon_listing_is_the_only_observation_source(self):
        out = route({
            "decision_relevant": True,
            "context_value_bound": False,
            "information_owner": "EXTERNAL_WORLD",
            "source_scope": {"kind": "BOUND_SOURCE", "source_id": "amazon:listing:vendor-x"},
            "discovery_delegated": False,
        })
        self.assertEqual(out["action"], "OBSERVE_BOUND_SOURCE_ONLY")
        self.assertTrue(out["bound_source_only"])
        self.assertEqual(out["source_id"], "amazon:listing:vendor-x")
        self.assertFalse(out["external_research_authorized"])

    def test_explicit_search_delegation_authorizes_minimum_research(self):
        out = route({
            "decision_relevant": True,
            "context_value_bound": False,
            "information_owner": "EXTERNAL_WORLD",
            "source_scope": {"kind": "UNBOUND_SOURCE"},
            "discovery_delegated": True,
        })
        self.assertEqual(out["action"], "RESEARCH_MINIMUM_AUTHENTICATED_FACT")
        self.assertTrue(out["external_research_authorized"])

    def test_external_fact_without_source_or_discovery_delegation_asks_scope(self):
        out = route({
            "decision_relevant": True,
            "context_value_bound": False,
            "information_owner": "EXTERNAL_WORLD",
            "source_scope": {"kind": "UNBOUND_SOURCE"},
            "discovery_delegated": False,
        })
        self.assertEqual(out["action"], "ASK_USER_SOURCE_OR_SCOPE")
        self.assertTrue(out["ask_user_required"])
        self.assertFalse(out["external_research_authorized"])

    def test_unknown_origin_never_defaults_to_research(self):
        out = route({
            "decision_relevant": True,
            "context_value_bound": False,
            "information_owner": "UNKNOWN",
        })
        self.assertEqual(out["action"], "ASK_USER_MINIMUM_CLARIFICATION")
        self.assertFalse(out["external_research_authorized"])

    def test_irrelevant_missing_fact_is_ignored(self):
        out = route({
            "decision_relevant": False,
            "context_value_bound": False,
            "information_owner": "EXTERNAL_WORLD",
            "discovery_delegated": True,
        })
        self.assertEqual(out["action"], "IGNORE_NO_INFORMATION_NEEDED")
        self.assertFalse(out["external_research_authorized"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
