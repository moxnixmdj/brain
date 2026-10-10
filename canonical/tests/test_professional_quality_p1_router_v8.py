from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from canonical.runtime import professional_quality_p1_router_v8 as r


SUBJECT_REF={
    "path":"canonical/governance/subject-v8.json",
    "git_blob_sha":"b"*40,
}
SUBJECT_STATE={
    "pass":True,
    "subject_id":"SUBJECT-V8",
    "subject_sha256":"a"*64,
}
SUBJECT_DOC={"system_material":{"components":[]}}

def state():
    return {
        "goal":"Improve report",
        "decision_payload":{"context_id":"x"},
        "artifact_paths":["a.docx"],
        "hard_defect_profile_id":"profile",
        "detected_triggers":[],
        r.SUBJECT_REF_KEY:deepcopy(SUBJECT_REF),
        r.STEP_BINDINGS_KEY:{step:{"dummy":step} for step in r.AUTHENTICATED_STEPS},
        "step_results":{},
    }

def binding_result(step,outcome="NOT_APPLICABLE",authorized=False,totality=False):
    return {
        "pass":True,
        "status":"PASS__TEST_BINDING",
        "step_id":step,
        "decision_outcome":outcome,
        "positive_certification_authorized":authorized,
        "material_totality_proved":totality,
        "material_totality_basis":"UNIVERSAL_FORMAL_SCOPE_PROOF" if totality else None,
        "receipt_path":"canonical/governance/x.json",
        "receipt_git_blob_sha":"c"*40,
        "verification_path":"canonical/verification/x.json",
        "verification_git_blob_sha":"d"*40,
        "evidence_sha256":"e"*64,
    }

def auth_side_effect(final_outcome,authorized=False,totality=False):
    def f(binding,*,behavior_id,subject_id,subject_sha256,step_id,run_context_sha256,repo_root):
        if step_id==r.AUTHENTICATED_STEPS[-1]:
            return binding_result(step_id,final_outcome,authorized,totality)
        return binding_result(step_id)
    return f


class ProfessionalQualityP1RouterV8Tests(unittest.TestCase):
    def test_abstention_is_not_delegated_as_pass(self):
        with patch.object(r,"_load_subject",return_value=(SUBJECT_DOC,SUBJECT_STATE)),              patch.object(r.step_auth,"authenticate_step_binding",side_effect=auth_side_effect("ABSTAIN")) as auth,              patch.object(r.base,"route") as delegated:
            out=r.route(state(),repo_root=".")
        self.assertEqual(auth.call_count,len(r.AUTHENTICATED_STEPS))
        delegated.assert_not_called()
        self.assertEqual(out["route"],"ABSTAIN")
        self.assertEqual(out["final_decision_outcome"],"ABSTAIN")
        self.assertFalse(out["positive_certification_authorized"])
        self.assertFalse(out["material_totality_proved"])

    def test_positive_without_totality_authority_fails_before_delegation(self):
        with patch.object(r,"_load_subject",return_value=(SUBJECT_DOC,SUBJECT_STATE)),              patch.object(r.step_auth,"authenticate_step_binding",side_effect=auth_side_effect("POSITIVE_CERTIFICATE",False,False)),              patch.object(r.base,"route") as delegated:
            out=r.route(state(),repo_root=".")
        delegated.assert_not_called()
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"FINAL_POSITIVE_CERTIFICATION_NOT_AUTHORIZED")

    def test_positive_with_totality_delegates_and_preserves_mediation(self):
        with patch.object(r,"_load_subject",return_value=(SUBJECT_DOC,SUBJECT_STATE)),              patch.object(r.step_auth,"authenticate_step_binding",side_effect=auth_side_effect("POSITIVE_CERTIFICATE",True,True)),              patch.object(r.base,"route",return_value={"status":"PASS__BASE","route":"PASS"}) as delegated:
            out=r.route(state(),repo_root=".")
        delegated.assert_called_once()
        delegated_state=delegated.call_args.args[0]
        self.assertEqual(set(delegated_state["step_results"]),set(r.AUTHENTICATED_STEPS))
        self.assertTrue(all(x=="PASS" for x in delegated_state["step_results"].values()))
        self.assertEqual(out["schema"],r.SCHEMA)
        self.assertEqual(out["final_decision_outcome"],"POSITIVE_CERTIFICATE")
        self.assertTrue(out["positive_certification_authorized"])
        self.assertTrue(out["material_totality_proved"])
        self.assertTrue(out["positive_certification_mediation_bound"])

    def test_unknown_final_outcome_fails_closed(self):
        with patch.object(r,"_load_subject",return_value=(SUBJECT_DOC,SUBJECT_STATE)),              patch.object(r.step_auth,"authenticate_step_binding",side_effect=auth_side_effect("UNKNOWN")),              patch.object(r.base,"route") as delegated:
            out=r.route(state(),repo_root=".")
        delegated.assert_not_called()
        self.assertEqual(out["reason"],"FINAL_STEP_OUTCOME_NOT_AUTHORIZED")

    def test_caller_step_results_still_forbidden(self):
        s=state(); s["step_results"]={"x":"PASS"}
        out=r.route(s,repo_root=".")
        self.assertEqual(out["reason"],"CALLER_STEP_RESULTS_FORBIDDEN")

    def test_missing_binding_still_abstains(self):
        s=state(); s[r.STEP_BINDINGS_KEY].pop(r.AUTHENTICATED_STEPS[0])
        with patch.object(r,"_load_subject",return_value=(SUBJECT_DOC,SUBJECT_STATE)):
            out=r.route(s,repo_root=".")
        self.assertEqual(out["route"],"ABSTAIN")
        self.assertIn(r.AUTHENTICATED_STEPS[0],out["blocking_steps"])


if __name__=="__main__":
    unittest.main(verbosity=2)
