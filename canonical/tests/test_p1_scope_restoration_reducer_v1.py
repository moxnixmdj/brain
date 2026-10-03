from __future__ import annotations
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/p1_scope_restoration_reducer_v1.py"
spec=importlib.util.spec_from_file_location("r",P)
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

class TestP1ScopeRestorationReducer(unittest.TestCase):
    def inputs(self):
        return (
            load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
            load("canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"),
            load("canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json"),
            load("canonical/verification/P1_PUBLIC_RECOVERY_EXECUTION_OBSERVATION_20261003_V1.json"),
            load("canonical/verification/P1_POSTRUN_VERIFIER_RECEIPT_20261003_V1.json"),
        )

    def test_current_exact_inputs_restore_only_behavioral_scope(self):
        out=r.evaluate(*self.inputs())
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["p1_scope_quarantine_active"])
        self.assertEqual(out["contract_accounting"]["whole_scope_pass_count"],12)
        self.assertEqual(out["behavioral_family_accounting"]["behavioral_pass_count"],19)
        self.assertEqual(out["behavioral_family_accounting"]["restored_family_count"],8)
        self.assertEqual(out["opus55_acceptance_accounting"],{
            "accepted_families":3,
            "open_families":16,
            "atomic_proved":8,
            "atomic_unresolved":30,
            "atomic_total":38,
            "acceptance_delta":0,
        })
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

    def test_transport_adjudication_missing_fails_closed(self):
        vals=list(self.inputs())
        vals[4]=copy.deepcopy(vals[4])
        vals[4]["verified_transport_requirements"]=False
        out=r.evaluate(*vals)
        self.assertFalse(out["pass"])
        self.assertIn("TRANSPORT_SCOPE_NOT_VERIFIED",out["errors"])
        self.assertTrue(out["p1_scope_quarantine_active"])
        self.assertEqual(out["behavioral_scope_restoration_delta"],0)

    def test_any_failed_case_fails_closed(self):
        vals=list(self.inputs())
        vals[3]=copy.deepcopy(vals[3])
        vals[3]["result"]["passes"]=191
        vals[3]["result"]["failures"]=1
        out=r.evaluate(*vals)
        self.assertFalse(out["pass"])
        self.assertIn("EXECUTION_NOT_192_OF_192",out["errors"])

    def test_family_mapping_drift_fails_closed(self):
        vals=list(self.inputs())
        vals[0]=copy.deepcopy(vals[0])
        fam=r.EXPECTED_AFFECTED[0]
        vals[0]["family_to_residual_contracts"][fam]=[
            x for x in vals[0]["family_to_residual_contracts"][fam] if x!=r.BEHAVIOR
        ]
        out=r.evaluate(*vals)
        self.assertFalse(out["pass"])
        self.assertIn("P1_DEPENDENT_FAMILY_SET_DRIFT",out["errors"])

if __name__=="__main__":
    unittest.main()
