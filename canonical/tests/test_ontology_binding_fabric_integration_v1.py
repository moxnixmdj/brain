import unittest

from canonical.runtime.ontology_binding_control_v1 import ONTOLOGY_SCHEMA, ontology_sha256
from canonical.runtime.unified_cognitive_fabric_v1 import run


class OntologyFabricIntegrationTests(unittest.TestCase):
    def test_auto_route_exact_alias(self):
        ontology = {
            "schema": ONTOLOGY_SCHEMA,
            "scheme_id": "reg-cap",
            "source_id": "authority:reg-cap",
            "scope_id": "finance:regulatory-capital:2026",
            "entries": [
                {
                    "concept_id": "CAPITAL_BUFFER_A",
                    "preferred_label": "Primary capital buffer",
                    "alt_labels": ["core capital cushion"],
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
                "mention_surface": "core capital cushion",
                "scope_id": "finance:regulatory-capital:2026",
                "ontology": ontology,
                "expected_ontology_sha256": ontology_sha256(ontology),
            }
        })
        self.assertTrue(out["auto_routed"], out)
        self.assertEqual(out["mode"], "ONTOLOGY_BINDING")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(out["result"]["concept_id"], "CAPITAL_BUFFER_A")
        self.assertFalse(out["result"]["semantic_truth_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
