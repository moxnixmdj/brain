#!/usr/bin/env python3
"""Fail-closed validator for the current CAD T0 post-refreeze binding V4.

Verification only. Never constructs a terminal beacon or executes terminal cases.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

BINDING=Path("canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V4.json")
BEHAVIOR_ID="CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"
CURRENT_CANDIDATE="aa32750b220a023617938b7be9476f6b3aac6704"

def _blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def validate(root:Path)->dict[str,Any]:
    root=root.resolve(); errors=[]
    try:
        b=json.loads((root/BINDING).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"pass":False,"status":"FAIL_CLOSED","errors":["BINDING_READ:"+type(exc).__name__]}
    if b.get("behavior_id")!=BEHAVIOR_ID: errors.append("BEHAVIOR_ID_MISMATCH")
    if b.get("prewave_admissible") is not False: errors.append("BINDING_MUST_REMAIN_UNADMITTED_BEFORE_INDEPENDENT_VERIFICATION")
    if b.get("execution_authority") is not False: errors.append("PREWAVE_BINDING_MUST_NOT_GRANT_EXECUTION_AUTHORITY")

    freeze=b.get("candidate_freeze") or {}
    fp=root/str(freeze.get("path") or "")
    if not fp.is_file():
        errors.append("CANDIDATE_FREEZE_MISSING"); fdoc={}
    else:
        if _blob(fp)!=freeze.get("blob_sha"): errors.append("CANDIDATE_FREEZE_BLOB_DRIFT")
        try: fdoc=json.loads(fp.read_text(encoding="utf-8"))
        except Exception: fdoc={}; errors.append("CANDIDATE_FREEZE_JSON_INVALID")
    cone=fdoc.get("exact_cad_dependency_cone") if isinstance(fdoc,dict) else {}
    if not isinstance(cone,dict) or not cone:
        errors.append("CANDIDATE_CONE_MISSING"); cone={}
    for rel,expected in sorted(cone.items()):
        p=root/rel
        if not p.is_file(): errors.append("CANDIDATE_CONE_FILE_MISSING:"+rel)
        elif _blob(p)!=expected: errors.append("CANDIDATE_CONE_BLOB_DRIFT:"+rel)

    adapter=b.get("candidate_adapter") or {}
    ap=root/str(adapter.get("runtime") or "")
    if adapter.get("runtime_blob_sha")!=CURRENT_CANDIDATE: errors.append("CANDIDATE_NOT_CURRENT_PIN")
    if not ap.is_file() or _blob(ap)!=adapter.get("runtime_blob_sha"): errors.append("CANDIDATE_ADAPTER_BLOB_DRIFT")
    if adapter.get("hidden_oracle_imported") is not False: errors.append("CANDIDATE_HIDDEN_ORACLE_BOUNDARY_INVALID")

    pop=b.get("population") or {}
    if pop.get("slot_count")!=128: errors.append("POPULATION_COUNT_MISMATCH")
    for key in ("post_freeze_beacon_known","case_replacement","adaptive_selection","tuning_replay","external_spent_task_used_for_promotion"):
        if pop.get(key) is not False: errors.append("POPULATION_FLAG_NOT_FALSE:"+key)
    gp=root/str(pop.get("generator") or "")
    if not gp.is_file() or _blob(gp)!=pop.get("generator_blob_sha"): errors.append("POPULATION_GENERATOR_BLOB_DRIFT")

    ev=b.get("evaluator") or {}
    for pk,sk,label in (
        ("oracle_adapter","oracle_adapter_blob_sha","ORACLE"),
        ("scorer","scorer_blob_sha","SCORER"),
        ("observation_schema","observation_schema_blob_sha","OBSERVATION_SCHEMA"),
    ):
        p=root/str(ev.get(pk) or "")
        if not p.is_file() or _blob(p)!=ev.get(sk): errors.append(label+"_BLOB_DRIFT")
    if ev.get("hidden_reference_candidate_visible") is not False: errors.append("HIDDEN_REFERENCE_BOUNDARY_INVALID")
    if ev.get("candidate_self_reported_metrics_authoritative") is not False: errors.append("CANDIDATE_SELF_METRICS_MUST_NOT_BE_AUTHORITATIVE")

    repair=b.get("antishortcut_repair") or {}
    rp=root/str(repair.get("current_verification") or "")
    try: receipt=json.loads(rp.read_text(encoding="utf-8"))
    except Exception as exc:
        receipt={}; errors.append("REPAIR_RECEIPT_READ:"+type(exc).__name__)
    if not str(receipt.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("REPAIR_RECEIPT_NOT_INDEPENDENT_PASS")
    exact=(receipt.get("exact_brain_blobs") or {}).get("canonical/runtime/cad_t0_route_specific_candidate_v1.py")
    if exact!=CURRENT_CANDIDATE: errors.append("REPAIR_RECEIPT_CANDIDATE_BLOB_MISMATCH")
    verified=set(receipt.get("verified") or [])
    for required in (
        "CAD_ALL_EIGHT_FROZEN_GEOMETRY_FAMILIES_PASS",
        "CAD_RENDER_EQUIVALENT_NODE_SPLIT_PASS",
        "CAD_INTRA_NUMERIC_TOKEN_SPLIT_PASS",
        "CAD_RENDER_ORDER_INDEPENDENT_OF_DOM_SOURCE_ORDER",
        "ZERO_TERMINAL_CASES_CONSUMED",
    ):
        if required not in verified: errors.append("REPAIR_RECEIPT_MISSING:"+required)

    return {
      "schema":"PROJECT_BRAIN_CAD_T0_POST_REFREEZE_BINDING_V4_VALIDATION",
      "status":"PASS" if not errors else "FAIL_CLOSED","pass":not errors,
      "errors":sorted(set(errors)),"behavior_id":BEHAVIOR_ID,
      "slot_count":pop.get("slot_count"),"candidate_blob":adapter.get("runtime_blob_sha"),
      "terminal_results_observed":0,"fresh_terminal_evidence_consumed":0,
      "execution_authority":False,"promotion_authority":False
    }

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("root",nargs="?",type=Path,default=Path("."))
    out=validate(ap.parse_args().root); print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__": raise SystemExit(main())
