import unittest

from canonical.runtime.ontology_binding_control_v1 import ONTOLOGY_SCHEMA, ontology_sha256
from canonical.runtime.unified_cognitive_fabric_v1 import catalog, run


class OntologyFabricIntegrationTests(unittest.TestCase):
    def test_catalog_exposes_ontology_binding(self):
        self.assertIn("ONTOLOGY_BINDING", catalog()["engines"])

    def test_auto_route_exact_alias(self):
        ontology = {
            "schema": ONTOLOGY_SCHEMA,
            "scheme_id": "reg-cap",
            "source_id": "authority:reg-cap",
            "scope_id": "finance:regulatory-capital:2026",
            "entries": [
                {
                    "concept_id": "CET1",
                    "preferred_label": "Common Equity Tier 1 capital",
                    "alt_labels": ["capital cushion"],
                },
                {
                    "concept_id": "LCR",
                    "preferred_label": "liquidity coverage ratio",
                    "alt_labels": ["liquidity buffer"],
                },
            ],
        }
        out = run({
            "payload": {
                "mention_id": "m1",
                "mention_surface": "capital cushion",
                "scope_id": "finance:regulatory-capital:2026",
                "ontology": ontology,
                "expected_ontology_sha256": ontology_sha256(ontology),
            }
        })
        self.assertTrue(out["auto_routed"], out)
        self.assertEqual(out["mode"], "ONTOLOGY_BINDING")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(out["result"]["concept_id"], "CET1")
        self.assertFalse(out["result"]["semantic_truth_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
