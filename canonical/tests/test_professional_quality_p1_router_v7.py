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
    state={
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
    ctx=r.step_auth.run_context_digest(
        goal=state["goal"],
        decision_payload=state["decision_payload"],
        artifact_paths=state["artifact_paths"],
        hard_defect_profile_id=state["hard_defect_profile_id"],
        detected_triggers=state["detected_triggers"],
    )
    state[r.CANDIDATE_UNIVERSE_KEY]=r.candidate_universe.freeze({
        "behavior_id":r.BEHAVIOR_ID,
        "subject_id":"SUBJECT-V7",
        "subject_sha256":"a"*64,
        "run_context_sha256":ctx,
        "incumbent_candidate_id":"inc",
        "candidates":[
            {
                "candidate_id":"inc",
                "content_sha256":"1"*64,
                "source_kind":"INCUMBENT",
                "artifact_type":"docx",
                "generator_trace_sha256":None,
            },
            {
                "candidate_id":"alt",
                "content_sha256":"2"*64,
                "source_kind":"GENERATED",
                "artifact_type":"docx",
                "generator_trace_sha256":"sha256:"+"3"*64,
            },
        ],
    })
    return state


def auth_pass(step,evidence_sha="e"*64):
    return {
        "pass":True,
        "status":"PASS__PROFESSIONAL_STEP_RESULT_AUTHENTICATED",
        "step_id":step,
        "receipt_path":"canonical/governance/"+step+".json",
        "receipt_git_blob_sha":"c"*40,
        "verification_path":"canonical/verification/"+step+".json",
        "verification_git_blob_sha":"d"*40,
        "evidence_sha256":evidence_sha,
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
        base.return_value={
            "status":"ROUTE__P1_ORDINARY",
            "route":"P1",
            "quality_authority":False,
            "terminal_authority":False,
        }
        state=base_state()
        candidate_evidence=state[r.CANDIDATE_UNIVERSE_KEY]["candidate_universe_sha256"][7:]
        auth.side_effect=lambda binding,**kw: auth_pass(
            kw["step_id"],
            candidate_evidence if kw["step_id"]==r.CANDIDATE_STEP else "e"*64,
        )
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
        state=base_state()
        candidate_evidence=state[r.CANDIDATE_UNIVERSE_KEY]["candidate_universe_sha256"][7:]
        def side(binding,**kw):
            if kw["step_id"]==r.AUTHENTICATED_STEPS[2]:
                return {"pass":False,"status":"FAIL_CLOSED__PROFESSIONAL_STEP_BINDING_INVALID","reason":"bad"}
            return auth_pass(
                kw["step_id"],
                candidate_evidence if kw["step_id"]==r.CANDIDATE_STEP else "e"*64,
            )
        auth.side_effect=side
        out=r.route(state)
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
        base.return_value={"status":"ABSTAIN__P1_INCOMPLETE","route":"ABSTAIN"}
        state=base_state()
        state["decision_payload"]={"context_id":"changed"}
        changed_ctx=r.step_auth.run_context_digest(
            goal=state["goal"],
            decision_payload=state["decision_payload"],
            artifact_paths=state["artifact_paths"],
            hard_defect_profile_id=state["hard_defect_profile_id"],
            detected_triggers=state["detected_triggers"],
        )
        state[r.CANDIDATE_UNIVERSE_KEY]=r.candidate_universe.freeze({
            "behavior_id":r.BEHAVIOR_ID,
            "subject_id":"SUBJECT-V7",
            "subject_sha256":"a"*64,
            "run_context_sha256":changed_ctx,
            "incumbent_candidate_id":"inc",
            "candidates":[
                {"candidate_id":"inc","content_sha256":"1"*64,"source_kind":"INCUMBENT","artifact_type":"docx","generator_trace_sha256":None},
                {"candidate_id":"alt","content_sha256":"2"*64,"source_kind":"GENERATED","artifact_type":"docx","generator_trace_sha256":"sha256:"+"3"*64},
            ],
        })
        candidate_evidence=state[r.CANDIDATE_UNIVERSE_KEY]["candidate_universe_sha256"][7:]
        auth.side_effect=lambda binding,**kw: auth_pass(
            kw["step_id"],
            candidate_evidence if kw["step_id"]==r.CANDIDATE_STEP else "e"*64,
        )
        out=r.route(state)
        contexts={call.kwargs["run_context_sha256"] for call in auth.call_args_list}
        self.assertEqual(len(contexts),1)
        self.assertEqual(out["run_context_sha256"],next(iter(contexts)))

    @patch.object(r.base,"route")
    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_candidate_step_evidence_must_equal_exact_universe_digest(self,load_subject,auth,base):
        load_subject.return_value=({},subject_state())
        auth.side_effect=lambda binding,**kw: auth_pass(kw["step_id"],"f"*64)
        out=r.route(base_state())
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"CANDIDATE_STEP_EVIDENCE_UNIVERSE_MISMATCH")
        base.assert_not_called()

    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_missing_candidate_universe_abstains_before_step_auth(self,load_subject,auth):
        load_subject.return_value=({},subject_state())
        state=base_state(); state.pop(r.CANDIDATE_UNIVERSE_KEY)
        out=r.route(state)
        self.assertEqual(out["status"],"ABSTAIN__P1_VERIFIED_STEP_BINDINGS_REQUIRED")
        self.assertEqual(out["blocking_steps"],[r.CANDIDATE_STEP])
        auth.assert_not_called()

    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_forged_candidate_universe_fails_closed_before_step_auth(self,load_subject,auth):
        load_subject.return_value=({},subject_state())
        state=base_state()
        forged=deepcopy(state[r.CANDIDATE_UNIVERSE_KEY])
        generated=next(row for row in forged["manifest"]["candidates"] if row["source_kind"]=="GENERATED")
        generated["generator_trace_sha256"]=None
        forged["candidate_universe_sha256"]=r.candidate_universe._digest(forged["manifest"])
        state[r.CANDIDATE_UNIVERSE_KEY]=forged
        out=r.route(state)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"CANDIDATE_SELECTION_UNIVERSE_INVALID")
        auth.assert_not_called()

    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_candidate_universe_subject_mismatch_fails_closed(self,load_subject,auth):
        load_subject.return_value=({},subject_state())
        state=base_state()
        manifest=state[r.CANDIDATE_UNIVERSE_KEY]["manifest"]
        rebuilt=r.candidate_universe.freeze({
            "behavior_id":r.BEHAVIOR_ID,
            "subject_id":"OTHER-SUBJECT",
            "subject_sha256":"a"*64,
            "run_context_sha256":manifest["run_context_sha256"],
            "incumbent_candidate_id":manifest["incumbent_candidate_id"],
            "candidates":manifest["candidates"],
        })
        state[r.CANDIDATE_UNIVERSE_KEY]=rebuilt
        out=r.route(state)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"CANDIDATE_SELECTION_UNIVERSE_BINDING_MISMATCH")
        self.assertEqual(out["mismatch_field"],"subject_id")
        auth.assert_not_called()

    @patch.object(r.step_auth,"authenticate_step_binding")
    @patch.object(r,"_load_subject")
    def test_single_incumbent_only_universe_stays_open(self,load_subject,auth):
        load_subject.return_value=({},subject_state())
        state=base_state()
        manifest=state[r.CANDIDATE_UNIVERSE_KEY]["manifest"]
        one=r.candidate_universe.freeze({
            "behavior_id":r.BEHAVIOR_ID,
            "subject_id":manifest["subject_id"],
            "subject_sha256":manifest["subject_sha256"],
            "run_context_sha256":manifest["run_context_sha256"],
            "incumbent_candidate_id":"inc",
            "candidates":[manifest["candidates"][1]],
        })
        state[r.CANDIDATE_UNIVERSE_KEY]=one
        out=r.route(state)
        self.assertEqual(out["status"],"ABSTAIN__P1_VERIFIED_STEP_BINDINGS_REQUIRED")
        self.assertEqual(out["blocking_reason"],"CANDIDATE_BRANCH_SET_NOT_YET_PLURAL")
        auth.assert_not_called()


if __name__=="__main__":
    unittest.main()
