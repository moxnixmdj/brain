from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_semantic_totality_reduction_v1 as r

ROOT=Path(__file__).resolve().parents[2]

class ProfessionalSemanticTotalityReductionV1Tests(unittest.TestCase):
    def current_ledger(self):
        return json.loads((ROOT / r.LEDGER_PATH).read_text())

    def current_catalog(self):
        return json.loads((ROOT / r.CATALOG_PATH).read_text())

    def test_current_semantic_frontier_reduces_to_twelve_claim_scoped_instances(self):
        out=r.analyze(self.current_ledger(),self.current_catalog())
        self.assertTrue(out["pass"])
        self.assertEqual(out["semantic_leaf_count"],12)
        self.assertEqual(out["claim_scoped_instance_count"],12)
        self.assertEqual(out["shared_adapter_count"],1)
        self.assertFalse(out["catalog_enumeration_sufficient"])
        self.assertFalse(out["current_totality_proved"])
        self.assertFalse(out["property_truth_authority"])
        self.assertFalse(out["new_primitive_required"])
        self.assertTrue(all(x["claim_scoped_totality_required"] for x in out["leaves"]))

    def test_missing_semantic_leaf_fails_closed(self):
        ledger=self.current_ledger()
        ledger["leaves"]=[
            x for x in ledger["leaves"]
            if x["leaf_id"]!="PQ::R9_TEMPORAL_DEPLOYMENT::SEMANTIC"
        ]
        out=r.analyze(ledger,self.current_catalog())
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SEMANTIC_LEAF_SET_NOT_12")

    def test_bounded_witness_must_not_self_promote_to_global_closure(self):
        ledger=self.current_ledger()
        row=next(x for x in ledger["leaves"] if x["leaf_id"].endswith("::SEMANTIC"))
        row["bounded_witnesses"][0]["global_leaf_closure"]=True
        out=r.analyze(ledger,self.current_catalog())
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"BOUNDED_WITNESS_GLOBAL_PROMOTION_FORBIDDEN")

    def test_catalog_claiming_completeness_does_not_replace_claim_scoped_totality(self):
        catalog=self.current_catalog()
        catalog["hard_nonclaims"]=[
            x for x in catalog.get("hard_nonclaims",[])
            if x!="NO_CLAIM_DEFEATER_SET_COMPLETE"
        ]
        catalog["closure_state"]="CLOSED"
        out=r.analyze(self.current_ledger(),catalog)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"CATALOG_COMPLETENESS_SELF_CLAIM_NOT_AUTHORITY")

if __name__=="__main__":
    unittest.main(verbosity=2)
