"""Fail-closed prewave guard for CAD T0 terminal binding.

This guard proves only that the CAD terminal route is frozen and information-safe
enough to enter the terminal wave. It does not execute a terminal case or grant
capability/family credit.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_CAD_T0_PREWAVE_BINDING_GUARD_V1"
REQ = {
  "source_pool":"canonical/governance/CAD_T0_GEOMETRY_SOURCE_POOL_V1.json",
  "candidate_freeze":"canonical/governance/CAD_T0_CANDIDATE_FREEZE_V1.json",
  "binding":"canonical/governance/CAD_T0_MULTIPLEX_TERMINAL_BINDING_V1.json",
  "observation_schema":"canonical/governance/CAD_T0_EVALUATOR_OBSERVATION_SCHEMA_V1.json",
}

def _load(root:Path, rel:str)->dict[str,Any]:
    x=json.loads((root/rel).read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(rel+":NOT_OBJECT")
    return x

def evaluate(root:Path)->dict[str,Any]:
    errors=[]
    try:
        src=_load(root,REQ["source_pool"])
        freeze=_load(root,REQ["candidate_freeze"])
        bind=_load(root,REQ["binding"])
        obs=_load(root,REQ["observation_schema"])
    except Exception as e:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":[str(e)],
                "execution_authority":False,"promotion_authority":False}

    if src.get("behavior_id")!="CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001":
        errors.append("SOURCE_BEHAVIOR_ID")
    if freeze.get("behavior_id")!=src.get("behavior_id") or bind.get("behavior_id")!=src.get("behavior_id") or obs.get("behavior_id")!=src.get("behavior_id"):
        errors.append("BEHAVIOR_ID_MISMATCH")

    eligible=src.get("eligible_cases")
    if not isinstance(eligible,list) or not eligible:
        errors.append("ELIGIBLE_CASES_EMPTY")
    else:
        for i,row in enumerate(eligible):
            if not isinstance(row,dict):
                errors.append(f"ELIGIBLE_CASE_INVALID:{i}"); continue
            if row.get("content_opened_before_candidate_freeze") is not False:
                errors.append(f"CASE_CONTENT_EXPOSED_BEFORE_FREEZE:{i}")

    forbidden=src.get("forbidden_before_candidate_freeze")
    expected_forbidden={
      "READ_INSTRUCTION_CONTENT","READ_SOLUTION_CONTENT","READ_GRADER_CONTENT",
      "READ_REFERENCE_MODEL_CONTENT","READ_VISIBLE_ASSET_PIXELS"
    }
    if not isinstance(forbidden,list) or not expected_forbidden.issubset(set(forbidden)):
        errors.append("SOURCE_FORBIDDEN_READ_SET_INCOMPLETE")

    contam=freeze.get("contamination_state")
    if not isinstance(contam,dict):
        errors.append("FREEZE_CONTAMINATION_STATE_MISSING")
    else:
        for k in ("task_instruction_opened","task_solution_opened","task_reference_model_opened","task_grader_content_opened"):
            if contam.get(k) is not False:
                errors.append("PRE_FREEZE_EXPOSURE:"+k)

    rules=freeze.get("post_freeze_rules")
    if not isinstance(rules,list) or not any("HIDDEN_TASK_GRADER_OR_REFERENCE_CONTENT_MAY_BE_READ_ONLY_BY_EVALUATOR_SIDE_AFTER_THIS_FREEZE"==x for x in rules):
        errors.append("EVALUATOR_ONLY_POST_FREEZE_RULE_MISSING")
    if not isinstance(rules,list) or not any("ANY_REQUIRED_CAD_RUNTIME_CHANGE_AFTER_HIDDEN_GRADER_EXPOSURE_INVALIDATES_THIS_CASE_FOR_CLEAN_PROMOTION"==x for x in rules):
        errors.append("POST_EXPOSURE_RUNTIME_INVALIDATION_RULE_MISSING")

    if bind.get("selector")!="GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2_POST_FREEZE_BEACON_RULE":
        errors.append("POST_FREEZE_SELECTOR_NOT_BOUND")
    contam2=bind.get("contamination")
    if not isinstance(contam2,dict) or any(contam2.get(k) is not False for k in (
        "case_specific_tuning_after_freeze","case_replacement","result_to_runtime_feedback_during_wave",
        "evaluator_or_threshold_edit_after_first_terminal_result")):
        errors.append("BINDING_CONTAMINATION_RULES_INVALID")
    ta=bind.get("terminal_acceptance")
    if not isinstance(ta,dict) or ta.get("prewave_binding_is_terminal_result") is not False:
        errors.append("PREWAVE_TERMINAL_RESULT_CONFUSION")

    fields=obs.get("observation_fields")
    if not isinstance(fields,dict) or not fields:
        errors.append("OBSERVATION_FIELDS_MISSING")
    else:
        for name,row in fields.items():
            if not isinstance(row,dict) or row.get("candidate_may_supply") is not False:
                errors.append("CANDIDATE_SUPPLIED_EVALUATOR_FIELD:"+str(name))

    forb=obs.get("forbidden_sources")
    if not isinstance(forb,list) or "CANDIDATE_SELF_REPORT" not in forb or "REFERENCE_DATA_LEAKED_INTO_CANDIDATE_INPUT" not in forb:
        errors.append("FORBIDDEN_OBSERVATION_SOURCES_INCOMPLETE")

    if src.get("terminal_results_observed")!=0 or freeze.get("terminal_results_observed")!=0 or bind.get("terminal_results_observed")!=0:
        errors.append("TERMINAL_RESULT_ALREADY_OBSERVED")
    if src.get("fresh_terminal_evidence_consumed")!=0 or freeze.get("fresh_terminal_evidence_consumed")!=0 or bind.get("fresh_terminal_evidence_consumed")!=0:
        errors.append("FRESH_TERMINAL_EVIDENCE_ALREADY_CONSUMED")

    return {
      "schema":SCHEMA,
      "status":"PASS__PREWAVE_BINDING_INFORMATION_SAFE" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":sorted(set(errors)),
      "execution_authority":False,
      "promotion_authority":False,
      "terminal_results_observed":0,
      "fresh_terminal_evidence_consumed":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "rule":"PREWAVE_BINDING_ONLY__NO_TERMINAL_RESULT_OR_CAPABILITY_CREDIT",
    }

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("repo_root",type=Path); args=ap.parse_args()
    out=evaluate(args.repo_root); print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__": raise SystemExit(main())
