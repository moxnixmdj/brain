from __future__ import annotations
import copy
import unittest
from canonical.runtime import p1_terminal_archive_sufficiency_audit_v1 as audit

def fixture():
    p1=lambda portfolio:{
        "behavior_id":audit.P1,
        "case_id":f"{portfolio}::{audit.P1}::aggregate::30",
        "direct_instrumentation_pass":True,
    }
    r0=p1("T0"); r2=p1("T2")
    return {
        "schema":"PROJECT_BRAIN_TERMINAL_PARENT_PORTFOLIO_LAUNCHER_V1",
        "status":"PASS",
        "pass":True,
        "direct_routes_executed_once":[],
        "parent_portfolio_receipts":{"T0":[r0],"T1":[],"T2":[r2],"T3":[]},
        "parent_reduction":{"reductions":{audit.P1:{
            "behavior_id":audit.P1,
            "receipts":[
                {"behavior_id":audit.P1,"case_id":r0["case_id"]},
                {"behavior_id":audit.P1,"case_id":r2["case_id"]},
            ],
        }}},
    }

class Tests(unittest.TestCase):
    def test_aggregate_only_archive_requires_fresh_two_obligation_observation(self):
        out=audit.audit_document(fixture(),full_result_sha256=audit.EXPECTED_FULL_RESULT_SHA256)
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["archive_can_discharge_two_residuals"])
        self.assertTrue(out["new_observation_irreducible_for_two_residuals"])
        self.assertFalse(out["terminal_v3_replay_authorized"])

    def test_case_level_semantics_fail_closed_in_this_audit_mode(self):
        x=fixture()
        x["parent_portfolio_receipts"]["T0"][0]["trajectory"]=[]
        out=audit.audit_document(x,full_result_sha256=audit.EXPECTED_FULL_RESULT_SHA256)
        self.assertFalse(out["pass"])
        self.assertIn("P1_CASE_LEVEL_SEMANTICS_PRESENT",out["errors"])

    def test_wrong_archive_hash_fails_closed(self):
        out=audit.audit_document(fixture(),full_result_sha256="0"*64)
        self.assertFalse(out["pass"])
        self.assertIn("FULL_RESULT_SHA256_MISMATCH",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
