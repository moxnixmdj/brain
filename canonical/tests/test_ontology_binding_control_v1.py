import unittest

from canonical.runtime.ontology_binding_control_v1 import (
    ONTOLOGY_SCHEMA,
    context_facts_sha256,
    ontology_sha256,
    resolve,
)

SCOPE="finance:regulatory-capital:2026"

def onto(entries):
    return {
        "schema":ONTOLOGY_SCHEMA,
        "scheme_id":"reg-cap",
        "source_id":"authority:reg-cap",
        "scope_id":SCOPE,
        "entries":entries,
    }

class Tests(unittest.TestCase):
    def test_unique_alt_label_proves_identity(self):
        o=onto([
            {"concept_id":"CAPITAL_BUFFER_A","preferred_label":"Primary capital buffer","alt_labels":["core capital cushion"]},
            {"concept_id":"LCR","preferred_label":"liquidity coverage ratio","alt_labels":["liquidity buffer"]},
        ])
        out=resolve({
            "mention_id":"m1","mention_surface":"Core capital cushion","scope_id":SCOPE,
            "ontology":o,"expected_ontology_sha256":ontology_sha256(o),
        })
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["concept_id"],"CAPITAL_BUFFER_A")
        self.assertEqual(out["identity_basis"],"UNIQUE_EXACT_ONTOLOGY_LABEL_OR_ALT_LABEL")

    def test_ambiguous_surface_disambiguates_with_sufficient_fact(self):
        o=onto([
            {"concept_id":"PROFIT_MARGIN","preferred_label":"margin","sufficient_fact_sets":[["income-statement-context"]]},
            {"concept_id":"COLLATERAL_MARGIN","preferred_label":"margin","sufficient_fact_sets":[["collateral-call-context"]]},
        ])
        facts=["collateral-call-context"]
        out=resolve({
            "mention_id":"m2","mention_surface":"margin","scope_id":SCOPE,
            "ontology":o,"expected_ontology_sha256":ontology_sha256(o),
            "context_facts":facts,"expected_context_sha256":context_facts_sha256(facts),
        })
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["concept_id"],"COLLATERAL_MARGIN")
        self.assertEqual(out["identity_basis"],"AMBIGUOUS_EXACT_LABEL_DISAMBIGUATED_BY_ONTOLOGY_SUFFICIENT_FACT_SET")

    def test_ambiguous_mapping_returns_minimum_discriminators(self):
        o=onto([
            {"concept_id":"A","preferred_label":"buffer","sufficient_fact_sets":[["absorbs-losses"]]},
            {"concept_id":"B","preferred_label":"buffer","sufficient_fact_sets":[["covers-outflows"]]},
        ])
        out=resolve({
            "mention_id":"m3","mention_surface":"buffer","scope_id":SCOPE,
            "ontology":o,"expected_ontology_sha256":ontology_sha256(o),
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["surviving_candidate_ids"],["A","B"])
        self.assertEqual(
            {tuple(x["minimum_missing_sufficient_fact_set"]) for x in out["next_evidence_targets"]},
            {("absorbs-losses",),("covers-outflows",)},
        )

    def test_candidate_generator_has_zero_authority(self):
        o=onto([
            {"concept_id":"A","preferred_label":"alpha"},
            {"concept_id":"B","preferred_label":"beta"},
        ])
        out=resolve({
            "mention_id":"m4","mention_surface":"unknown phrase","scope_id":SCOPE,
            "ontology":o,"expected_ontology_sha256":ontology_sha256(o),
            "candidate_concept_ids":["A"],
            "candidate_relations":[{"concept_id":"A","score":0.999}],
        })
        self.assertFalse(out["pass"])
        self.assertFalse(out["candidate_concept_ids_are_authority"])
        self.assertFalse(out["candidate_relations_are_authority"])
        self.assertFalse(out["similarity_can_certify_identity"])

    def test_complete_equal_signatures_allow_decision_substitution_only(self):
        o=onto([
            {"concept_id":"A","preferred_label":"buffer","decision_signature_complete":True,"decision_signature":{"action":"HOLD"}},
            {"concept_id":"B","preferred_label":"buffer","decision_signature_complete":True,"decision_signature":{"action":"HOLD"}},
        ])
        out=resolve({
            "mention_id":"m5","mention_surface":"buffer","scope_id":SCOPE,
            "required_output":"CURRENT_DECISION_SUBSTITUTION",
            "ontology":o,"expected_ontology_sha256":ontology_sha256(o),
        })
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["identity_proved"])
        self.assertTrue(out["current_decision_substitution_proved"])
        self.assertEqual(out["strongest_proved_binding"],"CURRENT_DECISION_SUBSTITUTION")

    def test_equal_signatures_do_not_upgrade_to_identity(self):
        o=onto([
            {"concept_id":"A","preferred_label":"buffer","decision_signature_complete":True,"decision_signature":{"action":"HOLD"}},
            {"concept_id":"B","preferred_label":"buffer","decision_signature_complete":True,"decision_signature":{"action":"HOLD"}},
        ])
        out=resolve({
            "mention_id":"m6","mention_surface":"buffer","scope_id":SCOPE,
            "required_output":"CONCEPT_IDENTITY",
            "ontology":o,"expected_ontology_sha256":ontology_sha256(o),
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_binding"],"CURRENT_DECISION_SUBSTITUTION")

    def test_ontology_digest_mismatch_fails_closed(self):
        o=onto([{"concept_id":"A","preferred_label":"alpha"}])
        with self.assertRaisesRegex(Exception,"ONTOLOGY_CONTENT_ADDRESS_MISMATCH"):
            resolve({
                "mention_id":"m7","mention_surface":"alpha","scope_id":SCOPE,
                "ontology":o,"expected_ontology_sha256":"0"*64,
            })

    def test_context_digest_mismatch_fails_closed(self):
        o=onto([{"concept_id":"A","preferred_label":"alpha","sufficient_fact_sets":[["fact-a"]]}])
        with self.assertRaisesRegex(Exception,"CONTEXT_FACTS_CONTENT_ADDRESS_MISMATCH"):
            resolve({
                "mention_id":"m8","mention_surface":"other","scope_id":SCOPE,
                "ontology":o,"expected_ontology_sha256":ontology_sha256(o),
                "context_facts":["fact-a"],"expected_context_sha256":"0"*64,
            })

    def test_generic_verified_mapping_field_is_rejected(self):
        o=onto([{"concept_id":"A","preferred_label":"alpha"}])
        out=resolve({
            "mention_id":"m9","mention_surface":"alpha","scope_id":SCOPE,
            "ontology":o,"expected_ontology_sha256":ontology_sha256(o),
            "verified_mapping":"A",
        })
        self.assertFalse(out["pass"])
        self.assertIn("UNMODELED_FIELDS:verified_mapping",out["reason"])

if __name__=="__main__":
    unittest.main(verbosity=2)
