from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from canonical.runtime import professional_quality_p1_router_v7 as r


def subject_state():
    return {
        "pass":True,
        "status":"PASS__DECLARED_SYSTEM_SUBJECT_CURRENT_AND_CONTENT_ADDRESSED",
        "subject_id":"SUBJECT-V7",
        "subject_sha256":"a"*64,
        "subject_git_blob_sha":"b"*40,
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
        r.SUBJECT_REF_KEY:{
            "path":"canonical/governance/subject.json",
            "git_blob_sha":"b"*40,
        },
        r.STEP_BINDINGS_KEY:{step:{"receipt":{},"verification":{}} for step in r.AUTHENTICATED_STEPS},
    }


def auth_pass(step):
    return {
        "pass":True,
        "status":"PASS__PROFESSIONAL_STEP_RESULT_AUTHENTICATED",
        "step_id":step,
        "receipt_path":"canonical/governance/"+step+".json",
        "receipt_git_blob_sha":"c"*40,
        "verification_path":"canonical/verification/"+step+".json",
        "verification_git_blob_sha":"d"*40,
        "evidence_sha256":"e"*64,
        "terminal_authority":False,
    }


class ProfessionalQualityP1RouterV7Tests(unittest.TestCase):
    def test_any_caller_step_result_is_forbidden(self):
        state=base_state()
        state["step_results"]={r.AUTHENTICATED_STEPS[0]:"PASS"}
        out=r.route(state)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"CALLER_STEP_RESULTS_FORBIDDEN")

    @patch.object(r,"_load_subject")
    def test_missing_step_bindings_abstains(self,load_subject):
        load_subject.return_value=({},subject_state())
        state=base_state(); state.pop(r.STEP_BINDINGS_KEY)
        out=r.route(state)
        self.assertEqual(out["status"],"ABSTAIN__P1_VERIFIED_STEP_BINDINGS_REQUIRED")
        self.assertEqual(set(out["blocking_steps"]),set(r.AUTHENTICATED_STEPS))

    @patch.object(r,"_load_subject")
    def test_unknown_step_binding_fails_closed(self,load_subject):
        load_subject.return_value=({},subject_state())
        state=base_state(); state[r.STEP_BINDINGS_KEY]["NOT_A_PROFILE_STEP"]={}
        out=r.route(state)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"UNKNOWN_PROFESSIONAL_STEP_BINDING")

    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_all_seven_authenticated_steps_are_derived_then_delegate(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        auth.side_effect=lambda binding,**kw: auth_pass(kw["step_id"])
        base.return_value={
            "status":"ROUTE__P1_ORDINARY",
            "route":"P1",
            "quality_authority":False,
            "terminal_authority":False,
        }
        state=base_state()
        out=r.route(state)
        self.assertEqual(out["status"],"ROUTE__P1_ORDINARY",out)
        self.assertEqual(auth.call_count,7)
        delegated=base.call_args.args[0]
        self.assertNotIn(r.STEP_BINDINGS_KEY,delegated)
        self.assertNotIn(r.SUBJECT_REF_KEY,delegated)
        self.assertEqual(delegated["step_results"],{step:"PASS" for step in r.AUTHENTICATED_STEPS})
        self.assertTrue(out["professional_step_bindings_authenticated"])
        self.assertFalse(out["caller_step_results_allowed"])
        self.assertEqual(set(out["authenticated_step_ids"]),set(r.AUTHENTICATED_STEPS))
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_one_invalid_binding_blocks_before_v6(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        def side(binding,**kw):
            if kw["step_id"]==r.AUTHENTICATED_STEPS[2]:
                return {"pass":False,"status":"FAIL_CLOSED__PROFESSIONAL_STEP_BINDING_INVALID","reason":"bad"}
            return auth_pass(kw["step_id"])
        auth.side_effect=side
        out=r.route(base_state())
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"PROFESSIONAL_STEP_BINDING_INVALID")
        self.assertEqual(out["blocking_step"],r.AUTHENTICATED_STEPS[2])
        base.assert_not_called()

    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_open_binding_abstains_before_v6(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        auth.return_value={"pass":False,"status":"OPEN__PROFESSIONAL_STEP_BINDING_REQUIRED"}
        out=r.route(base_state())
        self.assertEqual(out["status"],"ABSTAIN__P1_VERIFIED_STEP_BINDINGS_REQUIRED")
        base.assert_not_called()

    @patch.object(r,"_load_subject")
    def test_missing_subject_reference_stays_open(self,load_subject):
        load_subject.return_value=(None,r._open("DECLARED_SYSTEM_SUBJECT_REFERENCE_REQUIRED"))
        state=base_state(); state.pop(r.SUBJECT_REF_KEY)
        out=r.route(state)
        self.assertEqual(out["status"],"ABSTAIN__P1_VERIFIED_STEP_BINDINGS_REQUIRED")

    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_run_context_change_is_forwarded_to_every_binding(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        auth.side_effect=lambda binding,**kw: auth_pass(kw["step_id"])
        base.return_value={"status":"ABSTAIN__P1_INCOMPLETE","route":"ABSTAIN"}
        state=base_state()
        state["decision_payload"]={"context_id":"changed"}
        out=r.route(state)
        contexts={call.kwargs["run_context_sha256"] for call in auth.call_args_list}
        self.assertEqual(len(contexts),1)
        self.assertEqual(out["run_context_sha256"],next(iter(contexts)))


if __name__=="__main__":
    unittest.main()
