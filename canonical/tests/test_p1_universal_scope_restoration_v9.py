from __future__ import annotations
import unittest
from canonical.runtime import p1_universal_scope_restoration_v9 as r

class Tests(unittest.TestCase):
    def test_live_restoration_passes(self):
        o=r.evaluate(); self.assertTrue(o["pass"],o)
        self.assertEqual(o["contract_accounting"]["whole_scope_pass_count"],12)
        self.assertEqual(o["behavioral_family_accounting"]["provisional_behavioral_pass_count"],19)
        self.assertEqual(o["source_fresh_reality_units_consumed"],0)
        self.assertFalse(o["quarantined_execution_used_as_proof"])
        self.assertEqual(o["opus55_acceptance_credit_delta"],0)
    def test_universal_scope_must_pass(self):
        x=r.load(r.UNIVERSAL_SCOPE); x["status"]="FAIL_CLOSED"
        o=r.evaluate(universal_scope=x); self.assertFalse(o["pass"]); self.assertIn("UNIVERSAL_SCOPE_NOT_PASS",o["errors"])
    def test_all_atoms_required(self):
        x=r.load(r.UNIVERSAL_SCOPE); x["verified"]["transport_requirements_discharged"]=x["verified"]["transport_requirements_discharged"][:-1]
        o=r.evaluate(universal_scope=x); self.assertFalse(o["pass"]); self.assertIn("UNIVERSAL_REQUIREMENT_SET",o["errors"])
    def test_quarantined_run_forbidden(self):
        x=r.load(r.UNIVERSAL_SCOPE); x["verified"]["quarantined_execution_used_as_proof"]=True
        o=r.evaluate(universal_scope=x); self.assertFalse(o["pass"]); self.assertIn("QUARANTINED_RUN_USED",o["errors"])
    def test_prior_residual_exact(self):
        x=r.load(r.V7_PROVENANCE); x["result"]["remaining_p1_information_residual"]="OTHER"
        o=r.evaluate(v7_provenance=x); self.assertFalse(o["pass"]); self.assertIn("PRETRANSPORT_RESIDUAL_NOT_EXACT",o["errors"])
    def test_mutation_set_cannot_shrink(self):
        x=r.load(r.BINDING); x["evaluator"]["required_mutations"]=x["evaluator"]["required_mutations"][:-1]
        o=r.evaluate(binding=x); self.assertFalse(o["pass"]); self.assertIn("FROZEN_MUTATION_SET",o["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
