"""Synthetic configured-vs-bare materiality counterfactual for advanced coding.

This does not consume benchmark cases and does not score model intelligence.
It isolates whether the Brain-owned mini-SWE/Superpowers completion contract
materially changes terminal execution when the proposal stream is held fixed.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_CODING_SUBSTRATE_MATERIALITY_COUNTERFACTUAL_V1"
FINISH="echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"

def _auth_errors(auth: Any, *, session_id:str)->list[str]:
    if not isinstance(auth, Mapping):
        return ["TERMINAL_AUTHORIZATION_MISSING"]
    e=[]
    if auth.get("schema")!="BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1":
        e.append("TERMINAL_AUTHORIZATION_SCHEMA_INVALID")
    if auth.get("session_id")!=session_id:
        e.append("TERMINAL_AUTHORIZATION_SESSION_MISMATCH")
    if auth.get("submission_authorized") is not True:
        e.append("TERMINAL_AUTHORIZATION_FALSE")
    if auth.get("known_relevant_failures") not in ([],None):
        e.append("KNOWN_RELEVANT_FAILURES_REMAIN")
    criteria=auth.get("acceptance_criteria")
    checks=auth.get("verification_commands")
    if not isinstance(criteria,list) or not criteria:
        e.append("ACCEPTANCE_CRITERIA_EVIDENCE_MISSING")
    elif any(not isinstance(x,Mapping) or x.get("status")!="PASS" or not x.get("evidence") for x in criteria):
        e.append("ACCEPTANCE_CRITERIA_NOT_ALL_PASS")
    if not isinstance(checks,list) or not checks:
        e.append("VERIFICATION_COMMANDS_MISSING")
    elif any(not isinstance(x,Mapping) or x.get("exit_code")!=0 or not x.get("command") for x in checks):
        e.append("VERIFICATION_COMMANDS_NOT_ALL_PASS")
    return sorted(set(e))

def bare_terminal_decision(command:str)->dict[str,Any]:
    return {
      "accepted": command.strip()==FINISH,
      "status":"TERMINAL_ACCEPTED" if command.strip()==FINISH else "CONTINUE",
      "errors":[],
    }

def configured_terminal_decision(command:str, auth:Any, *, session_id:str)->dict[str,Any]:
    if command.strip()!=FINISH:
        return {"accepted":False,"status":"CONTINUE","errors":[]}
    errors=_auth_errors(auth,session_id=session_id)
    return {
      "accepted":not errors,
      "status":"TERMINAL_ACCEPTED" if not errors else "SUBMISSION_BLOCKED",
      "errors":errors,
    }

def evaluate_counterfactual(*, session_id:str="synthetic-coding-materiality-v1")->dict[str,Any]:
    same_proposal=FINISH
    invalid_auth={
      "schema":"BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1",
      "session_id":session_id,
      "submission_authorized":True,
      "known_relevant_failures":["SYNTHETIC_TEST_FAILURE_REMAINS"],
      "acceptance_criteria":[{"criterion":"tests","status":"FAIL","evidence":"synthetic:test=fail"}],
      "verification_commands":[{"command":"python -m pytest -q","exit_code":1}],
      "authorized_by":"SYNTHETIC_COUNTERFACTUAL",
    }
    valid_auth={
      "schema":"BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1",
      "session_id":session_id,
      "submission_authorized":True,
      "known_relevant_failures":[],
      "acceptance_criteria":[{"criterion":"tests","status":"PASS","evidence":"synthetic:test=pass"}],
      "verification_commands":[{"command":"python -m pytest -q","exit_code":0}],
      "authorized_by":"SYNTHETIC_COUNTERFACTUAL",
    }
    bare=bare_terminal_decision(same_proposal)
    configured_bad=configured_terminal_decision(same_proposal,invalid_auth,session_id=session_id)
    configured_good=configured_terminal_decision(same_proposal,valid_auth,session_id=session_id)
    passed=(
      bare["accepted"] is True and
      configured_bad["accepted"] is False and
      "KNOWN_RELEVANT_FAILURES_REMAIN" in configured_bad["errors"] and
      configured_good["accepted"] is True
    )
    return {
      "schema":SCHEMA,
      "status":"PASS__BRAIN_CONFIGURATION_MATERIALLY_CHANGES_TERMINAL_EXECUTION" if passed else "FAIL_CLOSED",
      "pass":passed,
      "same_proposal_stream":True,
      "proposal":same_proposal,
      "bare_route":bare,
      "configured_route_with_failure":configured_bad,
      "configured_route_after_verified_repair":configured_good,
      "configuration_material_control_proven":passed,
      "model_quality_compared":False,
      "benchmark_case_content_consumed":False,
      "terminal_benchmark_replay":False,
      "interpretation":"HOLDING_THE_PROPOSAL_FIXED__THE_BRAIN_OWNED_COMPLETION_CONTRACT_CHANGES_WHETHER_TERMINAL_EXECUTION_IS_PERMITTED__THIS_IS_CAUSAL_MATERIAL_CONTROL_OF_VERIFIED_COMPLETION_NOT_A_MODEL_INTELLIGENCE_SCORE",
      "scope_limit":"PROVES_MATERIAL_CONTROL_OF_COMPLETION_AND_VERIFICATION_DISCIPLINE__DOES_NOT_BY_ITSELF_ESTABLISH_FULL_CODING_BAR_PERFORMANCE",
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
    }

if __name__=="__main__":
    import json
    print(json.dumps(evaluate_counterfactual(),indent=2,sort_keys=True))
