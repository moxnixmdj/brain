from __future__ import annotations

import inspect
import unittest

import canonical.runtime.generic_tool_schema_discovery_v1 as discovery
from canonical.runtime.generic_tool_schema_discovery_v1 import discovery_queries


class GenericToolSchemaDiscoveryV1Tests(unittest.TestCase):
    def test_update_query_is_derived_from_action_and_resources(self):
        qs = discovery_queries(
            "Find the cobalt shipment record, then set the delivery status to complete."
        )
        joined = " | ".join(qs)
        self.assertIn("shipment", joined)
        self.assertIn("status", joined)
        self.assertTrue("search" in joined or "get" in joined)
        self.assertTrue("update" in joined or "patch" in joined)

    def test_notify_query_is_vendor_neutral(self):
        qs = discovery_queries("Send the approval notice to qa-team@example.test.")
        joined = " | ".join(qs)
        self.assertTrue("send" in joined or "message" in joined)
        self.assertIn("approval", joined)

    def test_negative_constraint_preserves_resource_and_action_terms(self):
        qs = discovery_queries("Do not delete the cobalt shipment record.")
        joined = " | ".join(qs)
        self.assertIn("shipment", joined)
        self.assertIn("delete", joined)

    def test_surface_renaming_preserves_generic_structure(self):
        left = discovery_queries("Find the cobalt shipment and update the status to complete.")
        right = discovery_queries("Find the amber parcel and update the state to complete.")
        self.assertEqual(len(left), len(right))
        self.assertTrue(any("update" in q or "patch" in q for q in left))
        self.assertTrue(any("update" in q or "patch" in q for q in right))

    def test_source_contains_no_known_benchmark_or_vendor_literals(self):
        source = inspect.getsource(discovery).lower()
        forbidden = (
            "automationbench","zapier","gmail","salesforce","asana",
            "google_sheets","slack","quickbooks","xero","wave",
        )
        for literal in forbidden:
            self.assertNotIn(literal, source)

    def test_invalid_max_queries_fails_closed(self):
        with self.assertRaises(ValueError):
            discovery_queries("Find the record.", max_queries=0)


    def test_compound_identity_is_searchable(self):
        qs = discovery_queries(
            "Find the NovaGraph customer and update the NovaGraph status.",
            max_queries=6,
        )
        joined = " | ".join(qs)
        self.assertIn("novagraph", joined)

    def test_round_robin_gives_each_intent_search_budget_first(self):
        qs = discovery_queries(
            "Find the NovaGraph customer. Send the BlueMesa summary.",
            max_queries=2,
        )
        self.assertEqual(len(qs), 2)
        self.assertIn("novagraph", qs[0])
        self.assertIn("bluemesa", qs[1])

    def test_focused_rounds_follow_broad_intent_round(self):
        qs = discovery_queries(
            "Find the NovaGraph customer. Update the AmberParcel status.",
            max_queries=4,
        )
        self.assertIn("novagraph", qs[0])
        self.assertIn("amberparcel", qs[1])
        self.assertTrue(any(q.startswith("search ") for q in qs[2:]))
        self.assertTrue(any(q.startswith("update ") for q in qs[2:]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
