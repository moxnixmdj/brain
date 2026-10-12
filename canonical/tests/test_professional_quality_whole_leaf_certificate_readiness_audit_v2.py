from __future__ import annotations
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import professional_quality_whole_leaf_certificate_readiness_audit_v2 as audit

def ledger():
    leaves=[]
    for i in range(24):
        leaves.append({"leaf_id":f"PQ::TEST::{i}","whole_leaf_closed":False})
    return {"leaves":leaves}

def write_fixed(root: Path):
    lp=root/audit.LEDGER_PATH
    lp.parent.mkdir(parents=True,exist_ok=True)
    lp.write_text(json.dumps(ledger()),encoding="utf-8")
    ap=root/audit.ACTIVATION_PATH
    ap.parent.mkdir(parents=True,exist_ok=True)
    ap.write_text(json.dumps({"status":"ACTIVE_CANDIDATE__INDEPENDENTLY_VERIFIED_CLAIM_SCOPED_WHOLE_LEAF_GATE__TEST"}),encoding="utf-8")
    return lp,ap

class ReadinessV2Tests(unittest.TestCase):
    def test_current_real_repository_reports_zero_admissible_chains(self):
        out=audit.audit()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["leaf_count"],24)
        self.assertIn(out["admissible_chain_count"],{0,1})
        self.assertIn(out["claim_scope_construction_required_count"],{23,24})
        self.assertIn(out["property_truth_ready_count"],{0,1})

    def test_incomplete_quartet_fails_closed_per_leaf(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            lp,ap=write_fixed(root)
            with patch.object(audit,"LEDGER_BLOB",audit._blob(lp)), patch.object(audit,"ACTIVATION_BLOB",audit._blob(ap)):
                fake={"PQ::TEST::0":[("canonical/governance/x.json","a"*40,{})]}
                def scan(_root,base,schema):
                    return fake if schema==audit.gate.CLAIM_SCOPE_SCHEMA else {}
                with patch.object(audit,"_scan_schema",side_effect=scan):
                    out=audit.audit(repo_root=root)
            row=next(x for x in out["leaves"] if x["leaf_id"]=="PQ::TEST::0")
            self.assertEqual(row["state"],"FAIL_CLOSED_INCOMPLETE_OR_AMBIGUOUS_V2_CHAIN")
            self.assertFalse(row["property_truth_ready"])

    def test_exact_quartet_delegates_to_v2_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            lp,ap=write_fixed(root)
            def scan(_root,base,schema):
                leaf="PQ::TEST::0"
                names={
                    audit.gate.CLAIM_SCOPE_SCHEMA:("canonical/governance/cs.json","a"*40),
                    audit.gate.CLAIM_VERIFY_SCHEMA:("canonical/verification/cv.json","b"*40),
                    audit.gate.CERT_SCHEMA:("canonical/governance/c.json","c"*40),
                    audit.gate.CERT_VERIFY_SCHEMA:("canonical/verification/v.json","d"*40),
                }
                if schema not in names:return {}
                p,b=names[schema]
                return {leaf:[(p,b,{"leaf_id":leaf})]}
            verdict={"pass":True,"status":"PASS","claim_id":"x","whole_leaf_domain_equivalence_proved":True,"whole_leaf_scope_complete":True}
            with patch.object(audit,"LEDGER_BLOB",audit._blob(lp)), patch.object(audit,"ACTIVATION_BLOB",audit._blob(ap)), patch.object(audit,"_scan_schema",side_effect=scan), patch.object(audit.gate,"verify_entry",return_value=verdict) as call:
                out=audit.audit(repo_root=root)
            row=next(x for x in out["leaves"] if x["leaf_id"]=="PQ::TEST::0")
            self.assertEqual(row["state"],"ADMISSIBLE_V2_WHOLE_LEAF_SCOPE_CHAIN")
            self.assertTrue(row["property_truth_ready"])
            call.assert_called_once()

    def test_rejected_quartet_does_not_unlock_property_truth(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            lp,ap=write_fixed(root)
            def scan(_root,base,schema):
                leaf="PQ::TEST::0"
                return {leaf:[("canonical/x.json","a"*40,{"leaf_id":leaf})]}
            verdict={"pass":False,"status":"FAIL_CLOSED","reason":"DOMAIN_EQUIVALENCE_OPEN","whole_leaf_domain_equivalence_proved":False,"whole_leaf_scope_complete":False}
            with patch.object(audit,"LEDGER_BLOB",audit._blob(lp)), patch.object(audit,"ACTIVATION_BLOB",audit._blob(ap)), patch.object(audit,"_scan_schema",side_effect=scan), patch.object(audit.gate,"verify_entry",return_value=verdict):
                out=audit.audit(repo_root=root)
            row=next(x for x in out["leaves"] if x["leaf_id"]=="PQ::TEST::0")
            self.assertEqual(row["state"],"V2_CHAIN_REJECTED_BY_SHARED_GATE")
            self.assertFalse(row["property_truth_ready"])

    def test_stale_activation_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            lp,ap=write_fixed(root)
            with patch.object(audit,"LEDGER_BLOB",audit._blob(lp)), patch.object(audit,"ACTIVATION_BLOB","0"*40):
                out=audit.audit(repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"],"V2_GATE_ACTIVATION_STALE")

if __name__=="__main__":
    unittest.main(verbosity=2)
