#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/extracted_evidence_typed_quantity.py"
def load():
    s=importlib.util.spec_from_file_location("typedq",P)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); return m

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()
    def base(self,lits):
        return {
          "status":"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",
          "fresh_url":"https://example.org/x","page_sha256":"a"*64,
          "evidence_records":[{
            "text":"At 40 °C the viscosity is 0.653 mPa*s and at 20 °C it is 1.002 mPa*s.",
            "text_sha256":"b"*64,"source_url":"https://example.org/x",
            "matched_objective_tokens":["viscosity"],"numeric_literals":lits,
          }]
        }
    def test_types_values_and_literal_units_without_guessing(self):
        x=self.m.extract(self.base(["40 °C","0.653 mPa*s","20 °C","1.002 mPa*s"]))
        self.assertEqual(x["status"],"TYPED_QUANTITY_CANDIDATES_EXTRACTED",x)
        self.assertEqual(x["typed_quantity_candidate_count"],4,x)
        vals=[q["value"] for q in x["typed_quantity_candidates"]]
        self.assertEqual(vals,[40.0,0.653,20.0,1.002])
        self.assertEqual(x["unit_normalization_status"],"NOT_PERFORMED")
        self.assertTrue(all(q["semantic_role_status"]=="UNBOUND" for q in x["typed_quantity_candidates"]))
    def test_dimensionless_value_is_admitted_but_unbound(self):
        x=self.m.extract(self.base(["0.5"]))
        q=x["typed_quantity_candidates"][0]
        self.assertEqual(q["value"],0.5); self.assertIsNone(q["unit_surface"])
    def test_malformed_surface_fails_closed(self):
        x=self.m.extract(self.base(["not-a-number","nan m","4.2 m per second words"]))
        self.assertEqual(x["typed_quantity_candidate_count"],0,x)
        self.assertEqual(x["status"],"NO_TYPED_QUANTITY_CANDIDATES",x)

if __name__=="__main__": unittest.main(verbosity=2)
