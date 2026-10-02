"""Fail-closed validator for CAD T0 candidate freeze/binding V3.

This is a preterminal validator only. It recomputes Git blob identities and checks
the one-shot population/information-boundary invariants. It must never generate a
terminal case, derive a terminal seed, or grant launch/promotion authority.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CAD_T0_REFREEZE_V3_VALIDATION_V1"
FREEZE=Path("canonical/governance/CAD_T0_CANDIDATE_FREEZE_V3.json")
BINDING=Path("canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V3.json")

def _blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

def validate(root:Path=Path("."))->dict[str,Any]:
    errors=[]
    try:
        freeze=json.loads((root/FREEZE).read_text(encoding="utf-8"))
        binding=json.loads((root/BINDING).read_text(encoding="utf-8"))
    except Exception as exc:
        return _fail("READ:"+type(exc).__name__)
    if freeze.get("schema")!="PROJECT_BRAIN_CAD_T0_CANDIDATE_FREEZE_V3":
        errors.append("FREEZE_SCHEMA")
    if binding.get("schema")!="PROJECT_BRAIN_CAD_T0_POST_REFREEZE_BINDING_V3":
        errors.append("BINDING_SCHEMA")
    cone=freeze.get("exact_cad_dependency_cone")
    if not isinstance(cone,Mapping) or not cone:
        errors.append("CONE_INVALID")
        cone={}
    for rel,expected in cone.items():
        p=root/rel
        if not p.exists():
            errors.append("CONE_PATH_MISSING:"+str(rel)); continue
        if not isinstance(expected,str) or _blob(p)!=expected:
            errors.append("CONE_BLOB_MISMATCH:"+str(rel))
    cf=binding.get("candidate_freeze") or {}
    if cf.get("path")!=str(FREEZE):
        errors.append("FREEZE_PATH_DRIFT")
    elif _blob(root/FREEZE)!=cf.get("blob_sha"):
        errors.append("FREEZE_BLOB_MISMATCH")
    ca=binding.get("candidate_adapter") or {}
    cand_path=ca.get("path")
    if cand_path!="canonical/runtime/cad_t0_route_specific_candidate_v1.py":
        errors.append("CANDIDATE_PATH_DRIFT")
    elif _blob(root/Path(cand_path))!=ca.get("blob_sha"):
        errors.append("CANDIDATE_BLOB_MISMATCH")
    vp=ca.get("independent_verification")
    if vp!="canonical/verification/CAD_T0_ROUTE_SPECIFIC_CANDIDATE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":
        errors.append("CANDIDATE_VERIFICATION_PATH_DRIFT")
    elif _blob(root/Path(vp))!=ca.get("independent_verification_blob_sha"):
        errors.append("CANDIDATE_VERIFICATION_BLOB_MISMATCH")
    if ca.get("hidden_reference_candidate_visible") is not False:
        errors.append("HIDDEN_REFERENCE_VISIBLE")
    allowed=set(ca.get("candidate_visible_input") or [])
    if allowed!={"drawing_svg","declared_output_schema","schema","case_id"}:
        errors.append("CANDIDATE_VISIBLE_INPUT_SET_DRIFT")
    pop=binding.get("population") or {}
    if pop.get("slot_count")!=128: errors.append("SLOT_COUNT")
    if pop.get("post_freeze_beacon_known") is not False: errors.append("BEACON_PREKNOWN")
    if pop.get("case_replacement") is not False: errors.append("CASE_REPLACEMENT")
    if pop.get("adaptive_selection") is not False: errors.append("ADAPTIVE_SELECTION")
    if pop.get("tuning_replay") is not False: errors.append("TUNING_REPLAY")
    ev=binding.get("evaluator") or {}
    if ev.get("hidden_reference_candidate_visible") is not False:
        errors.append("EVALUATOR_HIDDEN_REFERENCE_VISIBLE")
    if ev.get("candidate_self_reported_metrics_authoritative") is not False:
        errors.append("SELF_REPORTED_METRICS_AUTHORITATIVE")
    cont=freeze.get("contamination_state") or {}
    if cont.get("fresh_generated_population_selected") is not False:
        errors.append("FRESH_POPULATION_ALREADY_SELECTED")
    if cont.get("post_freeze_beacon_known") is not False:
        errors.append("FREEZE_BEACON_PREKNOWN")
    for obj,label in ((freeze,"FREEZE"),(binding,"BINDING")):
        if obj.get("terminal_results_observed")!=0: errors.append(label+"_RESULTS_NONZERO")
        if obj.get("fresh_terminal_evidence_consumed")!=0: errors.append(label+"_FRESH_EVIDENCE_NONZERO")
        if obj.get("execution_authority") is not False: errors.append(label+"_EXECUTION_AUTHORITY")
        if obj.get("promotion_authority") is not False: errors.append(label+"_PROMOTION_AUTHORITY")
    return {
        "schema":SCHEMA,
        "status":"PASS__V3_EXACT_BLOBS_AND_ONE_SHOT_INVARIANTS_VERIFIED__ZERO_TERMINAL_CASES_GENERATED" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "terminal_case_generation_performed":False,
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }

def _fail(*errors):
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":list(errors),
            "terminal_case_generation_performed":False,"terminal_results_observed":0,
            "fresh_terminal_evidence_consumed":0,"execution_authority":False,
            "promotion_authority":False,"capability_credit_delta":0,"family_credit_delta":0}
