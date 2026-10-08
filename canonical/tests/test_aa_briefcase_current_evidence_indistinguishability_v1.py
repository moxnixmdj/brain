from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime import aa_briefcase_current_evidence_indistinguishability_v1 as cut

class AABriefcaseCurrentEvidenceIndistinguishabilityV1Tests(unittest.TestCase):
    def _w(self,root,rel,obj):
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj),encoding="utf-8")
    def _fixture(self,root):
        self._w(root,cut.TARGET_PATH,{"target":{"benchmark":"AA-Briefcase v1.1","current_owner_elo":1807}})
        self._w(root,cut.ROUTE_PATH,{"status":"ACTIVE_CANDIDATE_ROUTE__CURRENT_EPOCH_REFERENCE_1807__BRAIN_SCORE_MISSING__ZERO_CREDIT","current_target":{"benchmark":"AA-Briefcase v1.1","opus55_reference_elo":1807}})
        self._w(root,cut.SCAN_PATH,{"actual_score_receipts":{"count":0},"stronger_full_scope_certificate_scan":{"bound_certificate_count":0},"conclusion":{"current_internal_existing_evidence_search_exhausted":True}})
        self._w(root,cut.BOUNDARY_PATH,{"public_source":{"facts":["OFFICIAL_EVALUATION_IS_PRIVATE_DATASET","FOUR_SCORE_BEARING_PROJECT_SCENARIOS_ARE_PRIVATE","PUBLIC_FIFTH_SCENARIO_IS_DEMONSTRATIVE_ONLY","PUBLIC_FIFTH_SCENARIO_DOES_NOT_CONTRIBUTE_TO_OFFICIAL_AA_BRIEFCASE_ELO","OFFICIAL_AA_BRIEFCASE_SCORE_IS_NOT_PUBLICLY_SELF_SERVICE_AVAILABLE"]}})
        self._w(root,cut.BRIDGE_VERIFY_PATH,{"status":"PASS_ROUTE_SEMANTICS_ONLY__NO_BRAIN_SCORE__ZERO_ACCEPTANCE_CREDIT"})
    def test_pass_and_fail_worlds_are_both_open(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self._fixture(root);out=cut.certify(repo_root=root)
        self.assertTrue(out["pass"],out);self.assertTrue(out["information_theoretic_indistinguishability_proved"])
        self.assertFalse(out["fail_world"]["parity_pass"]);self.assertTrue(out["pass_world"]["parity_pass"])
        self.assertEqual(out["current_owner_reference_elo"],1807.0)
    def test_existing_receipt_reopens_and_fails_certificate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self._fixture(root);p=root/cut.SCAN_PATH;o=json.loads(p.read_text());o["actual_score_receipts"]["count"]=1;p.write_text(json.dumps(o));out=cut.certify(repo_root=root)
        self.assertFalse(out["pass"])
    def test_bound_stronger_certificate_reopens(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self._fixture(root);p=root/cut.SCAN_PATH;o=json.loads(p.read_text());o["stronger_full_scope_certificate_scan"]["bound_certificate_count"]=1;p.write_text(json.dumps(o));out=cut.certify(repo_root=root)
        self.assertFalse(out["pass"])
    def test_public_private_boundary_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self._fixture(root);p=root/cut.BOUNDARY_PATH;o=json.loads(p.read_text());o["public_source"]["facts"]=[];p.write_text(json.dumps(o));out=cut.certify(repo_root=root)
        self.assertFalse(out["pass"])
if __name__=="__main__": unittest.main(verbosity=2)
