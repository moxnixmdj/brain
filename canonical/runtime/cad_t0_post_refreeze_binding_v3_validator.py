#!/usr/bin/env python3
"""Fail-closed validator for CAD T0 post-refreeze binding V3.

Verification only. Never constructs a terminal beacon or executes terminal cases.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

BINDING=Path("canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V3.json")
BEHAVIOR_ID="CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"


def _blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def validate(root:Path)->dict[str,Any]:
    root=root.resolve()
    errors:list[str]=[]
    try:
        b=json.loads((root/BINDING).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"pass":False,"status":"FAIL_CLOSED","errors":["BINDING_READ:"+type(exc).__name__]}

    if b.get("behavior_id")!=BEHAVIOR_ID:
        errors.append("BEHAVIOR_ID_MISMATCH")
    if b.get("prewave_admissible") is not False:
        errors.append("BINDING_MUST_REMAIN_UNADMITTED_BEFORE_INDEPENDENT_VERIFICATION")
    if b.get("execution_authority") is not False:
        errors.append("PREWAVE_BINDING_MUST_NOT_GRANT_EXECUTION_AUTHORITY")

    freeze=b.get("candidate_freeze") or {}
    freeze_path=root/str(freeze.get("path") or "")
    expected_freeze=freeze.get("blob_sha")
    if not freeze_path.is_file():
        errors.append("CANDIDATE_FREEZE_MISSING")
        freeze_doc={}
    else:
        actual=_blob(freeze_path)
        if actual!=expected_freeze:
            errors.append("CANDIDATE_FREEZE_BLOB_DRIFT")
        try:
            freeze_doc=json.loads(freeze_path.read_text(encoding="utf-8"))
        except Exception:
            freeze_doc={}
            errors.append("CANDIDATE_FREEZE_JSON_INVALID")

    cone=freeze_doc.get("exact_cad_dependency_cone") if isinstance(freeze_doc,dict) else {}
    if not isinstance(cone,dict) or not cone:
        errors.append("CANDIDATE_CONE_MISSING")
        cone={}
    for rel,expected in sorted(cone.items()):
        path=root/rel
        if not path.is_file():
            errors.append("CANDIDATE_CONE_FILE_MISSING:"+rel)
            continue
        if _blob(path)!=expected:
            errors.append("CANDIDATE_CONE_BLOB_DRIFT:"+rel)

    adapter=b.get("candidate_adapter") or {}
    apath=root/str(adapter.get("runtime") or "")
    if not apath.is_file() or _blob(apath)!=adapter.get("runtime_blob_sha"):
        errors.append("CANDIDATE_ADAPTER_BLOB_DRIFT")
    if adapter.get("hidden_oracle_imported") is not False:
        errors.append("CANDIDATE_HIDDEN_ORACLE_BOUNDARY_INVALID")

    population=b.get("population") or {}
    if population.get("slot_count")!=128:
        errors.append("POPULATION_COUNT_MISMATCH")
    for key in ("post_freeze_beacon_known","case_replacement","adaptive_selection","tuning_replay","external_spent_task_used_for_promotion"):
        if population.get(key) is not False:
            errors.append("POPULATION_FLAG_NOT_FALSE:"+key)
    gen=root/str(population.get("generator") or "")
    if not gen.is_file() or _blob(gen)!=population.get("generator_blob_sha"):
        errors.append("POPULATION_GENERATOR_BLOB_DRIFT")

    evaluator=b.get("evaluator") or {}
    for path_key,sha_key,label in (
        ("oracle_adapter","oracle_adapter_blob_sha","ORACLE"),
        ("scorer","scorer_blob_sha","SCORER"),
        ("observation_schema","observation_schema_blob_sha","OBSERVATION_SCHEMA"),
    ):
        path=root/str(evaluator.get(path_key) or "")
        if not path.is_file() or _blob(path)!=evaluator.get(sha_key):
            errors.append(label+"_BLOB_DRIFT")
    if evaluator.get("hidden_reference_candidate_visible") is not False:
        errors.append("HIDDEN_REFERENCE_BOUNDARY_INVALID")
    if evaluator.get("candidate_self_reported_metrics_authoritative") is not False:
        errors.append("CANDIDATE_SELF_METRICS_MUST_NOT_BE_AUTHORITATIVE")

    repair=b.get("antishortcut_repair") or {}
    rpath=root/str(repair.get("repair_verification") or "")
    try:
        receipt=json.loads(rpath.read_text(encoding="utf-8"))
    except Exception as exc:
        receipt={}
        errors.append("REPAIR_RECEIPT_READ:"+type(exc).__name__)
    if not str(receipt.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("REPAIR_RECEIPT_NOT_INDEPENDENT_PASS")
    exact=(receipt.get("exact_repaired_candidate") or {}).get("blob_sha")
    if exact!=adapter.get("runtime_blob_sha"):
        errors.append("REPAIR_RECEIPT_CANDIDATE_BLOB_MISMATCH")
    verified=set(receipt.get("verified") or [])
    for required in (
        "ORIGINAL_TWO_CYCLE_ALL_EIGHT_FROZEN_GEOMETRY_FAMILIES_PASS",
        "ORIGINAL_RENDER_EQUIVALENT_SVG_TEXT_NODE_SPLIT_FALSIFIER_NOW_PASSES",
        "INTRA_NUMERIC_TOKEN_RENDER_EQUIVALENT_SPLIT_PASSES",
        "ZERO_TERMINAL_CASES_CONSUMED",
    ):
        if required not in verified:
            errors.append("REPAIR_RECEIPT_MISSING:"+required)

    return {
        "schema":"PROJECT_BRAIN_CAD_T0_POST_REFREEZE_BINDING_V3_VALIDATION",
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "behavior_id":BEHAVIOR_ID,
        "slot_count":population.get("slot_count"),
        "candidate_blob":adapter.get("runtime_blob_sha"),
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("root",nargs="?",type=Path,default=Path("."))
    out=validate(ap.parse_args().root)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1


if __name__=="__main__":
    raise SystemExit(main())
