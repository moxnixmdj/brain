import unittest
from canonical.runtime.semantic_identifiability_gate import adjudicate

class SemanticIdentifiabilityGateTests(unittest.TestCase):
    def row(self,i,meaning,src=True,ctx=True,material=True,disc="ask authority"):
        return {
            "id":i,
            "meaning":meaning,
            "consistent_with_source":src,
            "consistent_with_authorized_context":ctx,
            "materially_distinct":material,
            "discriminator":disc,
        }

    def test_unique(self):
        out=adjudicate([
            self.row("A","must emit JSON"),
            self.row("B","may emit YAML",src=False),
        ],authorized_context_ids=["source"])
        self.assertEqual(out["status"],"UNIQUE")
        self.assertEqual(out["interpretation"]["id"],"A")

    def test_two_viable_are_ambiguous_not_ranked(self):
        out=adjudicate([
            self.row("A","inclusive bound",disc="explicit boundary statement"),
            self.row("B","exclusive bound",disc="explicit boundary statement"),
        ])
        self.assertEqual(out["status"],"AMBIGUOUS")
        self.assertEqual({x["id"] for x in out["ambiguity_witness"]},{"A","B"})

    def test_missing_discriminator_is_reported(self):
        out=adjudicate([
            self.row("A","left",disc=""),
            self.row("B","right",disc="new source"),
        ])
        self.assertEqual(out["status"],"AMBIGUOUS")
        self.assertEqual(out["missing_discriminators"],["A"])

    def test_unknown_source_consistency_fails_closed(self):
        r=self.row("A","x"); r["consistent_with_source"]=None
        out=adjudicate([r])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("SOURCE_CONSISTENCY_UNKNOWN:A",out["errors"])

    def test_unknown_context_consistency_fails_closed(self):
        r=self.row("A","x"); r["consistent_with_authorized_context"]=None
        out=adjudicate([r])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("CONTEXT_CONSISTENCY_UNKNOWN:A",out["errors"])

    def test_unknown_materiality_fails_closed(self):
        r=self.row("A","x"); r["materially_distinct"]=None
        out=adjudicate([r])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("MATERIALITY_UNKNOWN:A",out["errors"])

    def test_duplicate_ids_fail_closed(self):
        out=adjudicate([self.row("A","x"),self.row("A","y")])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("DUPLICATE_INTERPRETATION_ID:A",out["errors"])

    def test_no_viable_interpretation_fails_closed(self):
        out=adjudicate([self.row("A","x",src=False)])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"NO_SOURCE_AND_CONTEXT_CONSISTENT_MATERIAL_INTERPRETATION")

    def test_nonmaterial_alternative_does_not_create_false_ambiguity(self):
        out=adjudicate([
            self.row("A","canonical wording"),
            self.row("B","same semantics rephrased",material=False),
        ])
        self.assertEqual(out["status"],"UNIQUE")
        self.assertEqual(out["interpretation"]["id"],"A")

if __name__=="__main__":
    unittest.main()
