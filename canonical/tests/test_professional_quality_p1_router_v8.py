from __future__ import annotations
from unittest.mock import patch
import unittest
from canonical.runtime import professional_quality_p1_router_v8 as r

def subject_state():
    return {
        "pass":True,"status":"PASS__DECLARED_SYSTEM_SUBJECT_CURRENT_AND_CONTENT_ADDRESSED",
        "subject_id":"SUBJECT-V8","subject_sha256":"a"*64,"subject_git_blob_sha":"b"*40,
    }

def base_state():
    return {
        "goal":"Improve the report.",
        "decision_payload":{"context_id":"ctx"},
        "goal_to_decision_binding":{"receipt":{},"verification":{}},
        "artifact_paths":["a.docx"],
        "hard_defect_profile_id":"profile",
        "detected_triggers":[],
        "step_results":{},
        r.SUBJECT_REF_KEY:{"path":"canonical/governance/subject.json","git_blob_sha":"b"*40},
        r.STEP_BINDINGS_KEY:{step:{"receipt":{},"verification":{}} for step in r.AUTHENTICATED_STEPS},
    }

def auth_pass(step):
    out={
        "pass":True,"status":"PASS__PROFESSIONAL_STEP_RESULT_AUTHENTICATED",
        "step_id":step,"receipt_path":"canonical/governance/"+step+".json",
        "receipt_git_blob_sha":"c"*40,"verification_path":"canonical/verification/"+step+".json",
        "verification_git_blob_sha":"d"*40,"evidence_sha256":"e"*64,
    }
    if step==r.FINAL_STEP:
        out.update({
            "decision_outcome":"POSITIVE_CERTIFICATE",
            "positive_certification_authorized":True,
            "material_totality_proved":True,
            "material_totality_basis":"UNIVERSAL_FORMAL_SCOPE_PROOF",
            "material_totality_target_scope_id":"scope://exact",
        })
    else:
        out.update({"decision_outcome":"NOT_APPLICABLE","positive_certification_authorized":False,"material_totality_proved":False})
    return out

class Tests(unittest.TestCase):
    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_positive_requires_v2_totality_then_delegates(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        auth.side_effect=lambda binding,**kw: auth_pass(kw["step_id"])
        base.return_value={"status":"ROUTE__P1_ORDINARY","route":"P1"}
        out=r.route(base_state())
        self.assertEqual(auth.call_count,7)
        self.assertTrue(out["positive_certification_authorized"])
        self.assertTrue(out["material_totality_proved"])
        self.assertEqual(out["final_step_outcome"],"POSITIVE_CERTIFICATE")
        base.assert_called_once()

    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_authenticated_final_abstain_stops_before_delegate(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        def side(binding,**kw):
            o=auth_pass(kw["step_id"])
            if kw["step_id"]==r.FINAL_STEP:
                o.update({"decision_outcome":"ABSTAIN","positive_certification_authorized":False,"material_totality_proved":False})
            return o
        auth.side_effect=side
        out=r.route(base_state())
        self.assertEqual(out["route"],"ABSTAIN")
        self.assertFalse(out["positive_certification_authorized"])
        base.assert_not_called()

    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_generic_final_pass_without_positive_authority_fails(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        def side(binding,**kw):
            o=auth_pass(kw["step_id"])
            if kw["step_id"]==r.FINAL_STEP:
                o["positive_certification_authorized"]=False
            return o
        auth.side_effect=side
        out=r.route(base_state())
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"FINAL_POSITIVE_CERTIFICATION_NOT_AUTHORIZED")
        base.assert_not_called()

    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_positive_without_material_totality_fails(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        def side(binding,**kw):
            o=auth_pass(kw["step_id"])
            if kw["step_id"]==r.FINAL_STEP:
                o["material_totality_proved"]=False
            return o
        auth.side_effect=side
        out=r.route(base_state())
        self.assertEqual(out["reason"],"FINAL_POSITIVE_MATERIAL_TOTALITY_NOT_PROVED")
        base.assert_not_called()

    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_unknown_final_outcome_fails(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        def side(binding,**kw):
            o=auth_pass(kw["step_id"])
            if kw["step_id"]==r.FINAL_STEP:o["decision_outcome"]="NOT_APPLICABLE"
            return o
        auth.side_effect=side
        out=r.route(base_state())
        self.assertEqual(out["reason"],"FINAL_STEP_OUTCOME_NOT_MEDIATED")
        base.assert_not_called()

    @patch.object(r,"_load_subject")
    def test_caller_step_results_still_forbidden(self,load_subject):
        load_subject.return_value=({},subject_state())
        s=base_state();s["step_results"]={r.FINAL_STEP:"PASS"}
        out=r.route(s)
        self.assertEqual(out["reason"],"CALLER_STEP_RESULTS_FORBIDDEN")

    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_invalid_v2_final_binding_blocks(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        def side(binding,**kw):
            if kw["step_id"]==r.FINAL_STEP:
                return {"pass":False,"status":"FAIL_CLOSED__PROFESSIONAL_STEP_BINDING_V2_INVALID","reason":"MATERIAL_TOTALITY_SCOPE_NOT_COMPLETE"}
            return auth_pass(kw["step_id"])
        auth.side_effect=side
        out=r.route(base_state())
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["blocking_step"],r.FINAL_STEP)
        base.assert_not_called()

if __name__=="__main__": unittest.main(verbosity=2)
