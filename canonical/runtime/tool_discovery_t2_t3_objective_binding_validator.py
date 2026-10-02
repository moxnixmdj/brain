#!/usr/bin/env python3
"""Validate the frozen T2/T3 direct-objective tool-discovery binding.

Prewave only. This validator never consumes a terminal beacon or grants credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from canonical.runtime import tool_discovery_information_safe_proof_v2 as proof
from canonical.runtime import tool_discovery_information_safe_candidate as candidate

BINDING="canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"


def _git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def validate(root: Path) -> dict:
    root=root.resolve()
    binding=json.loads((root/BINDING).read_text(encoding="utf-8"))
    errors=[]

    if binding.get("behavior_id")!="TOOL_ROUTE_DISCOVERY_AND_SELECTION_001":
        errors.append("BEHAVIOR_ID_MISMATCH")
    if binding.get("proof_mode")!="T2_T3_MULTIPLEXED_DIRECT_OBJECTIVE_TOOL_DISCOVERY_GATE":
        errors.append("PROOF_MODE_MISMATCH")

    for label,row in (binding.get("exact_bound_blobs") or {}).items():
        path=row.get("path")
        expected=row.get("blob_sha")
        if not isinstance(path,str) or not isinstance(expected,str):
            errors.append(f"BLOB_BINDING_INVALID:{label}")
            continue
        p=root/path
        if not p.is_file():
            errors.append(f"BLOB_MISSING:{label}:{path}")
            continue
        observed=_git_blob_sha(p)
        if observed!=expected:
            errors.append(f"BLOB_SHA_MISMATCH:{label}:{observed}")

    pool=binding.get("source_pool") or {}
    classes=list(pool.get("class_cycle") or [])
    if classes!=list(proof.CLASSES):
        errors.append("CLASS_CYCLE_MISMATCH")
    count=pool.get("terminal_sample_count")
    if not isinstance(count,int) or count<=0 or count%len(proof.CLASSES)!=0:
        errors.append("TERMINAL_SAMPLE_COUNT_NOT_COMPLETE_CLASS_CYCLES")

    selector=binding.get("selector") or {}
    for key in ("beacon_known_before_freeze","adaptive_case_selection","case_replacement","tuning_replay"):
        if selector.get(key) is not False:
            errors.append(f"SELECTOR_{key.upper()}_NOT_FALSE")

    if selector.get("protocol")!="GLOBAL_TERMINAL_SELECTION_KERNEL_V1":
        errors.append("SELECTOR_PROTOCOL_NOT_IMMUTABLE_KERNEL")
    sel_sem=binding.get("selection_semantics") or {}
    kernel=(binding.get("exact_bound_blobs") or {}).get("selection_kernel") or {}
    if sel_sem.get("kernel")!=kernel.get("path") or sel_sem.get("kernel_blob_sha")!=kernel.get("blob_sha"):
        errors.append("SELECTION_KERNEL_BINDING_MISMATCH")

    info=binding.get("information_boundary") or {}
    hidden=set(info.get("hidden_from_candidate") or [])
    if "ACTUAL_TOOL_CAPABILITY_MATRIX" not in hidden or "LEAST_COST_CAPABLE_ROUTE" not in hidden:
        errors.append("HIDDEN_ORACLE_BOUNDARY_INCOMPLETE")
    if info.get("candidate_receives_hidden_oracle") is not False:
        errors.append("CANDIDATE_RECEIVES_HIDDEN_ORACLE")

    # Fresh deterministic prewave diagnostic. No post-freeze beacon is used.
    case_count=60
    result=proof.run_batch(20261002,case_count,candidate.next_action)
    if result.get("all_pass") is not True:
        errors.append("SIX_CLASS_DIAGNOSTIC_FAILED")
    by_class=result.get("by_class") or {}
    if set(by_class)!=set(proof.CLASSES):
        errors.append("DIAGNOSTIC_CLASS_COVERAGE_INCOMPLETE")
    for cls in proof.CLASSES:
        row=by_class.get(cls) or {}
        if row.get("total")!=case_count//len(proof.CLASSES) or row.get("pass")!=row.get("total"):
            errors.append(f"DIAGNOSTIC_CLASS_FAILED:{cls}")

    # Inspect candidate-visible payloads directly for hidden oracle leakage.
    for ordinal in range(len(proof.CLASSES)):
        case=proof.generate_case(99117,ordinal)
        public=proof.public_stage(case,1,())
        raw=json.dumps(public,sort_keys=True)
        if "_oracle" in public or "epoch0" in raw or "epoch1" in raw:
            errors.append(f"HIDDEN_ORACLE_LEAK:{ordinal}")

    gates=binding.get("route_gates") or {}
    expected_true=(
        "candidate_package_frozen",
        "executable_evaluator_bound",
        "population_or_source_pool_frozen",
        "information_boundary_frozen",
        "post_freeze_selector_frozen",
        "terminal_parent_binding_frozen",
    )
    for key in expected_true:
        if gates.get(key) is not True:
            errors.append(f"ROUTE_GATE_NOT_FROZEN:{key}")
    if gates.get("independent_verification_pass") is not False:
        errors.append("INDEPENDENT_VERIFICATION_MUST_REMAIN_FALSE_BEFORE_EXTERNAL_RECEIPT")

    return {
        "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_T2_T3_OBJECTIVE_BINDING_VALIDATION_V1",
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "diagnostic_case_count":case_count,
        "diagnostic_all_pass":result.get("all_pass") is True,
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path,nargs="?",default=Path("."))
    args=ap.parse_args()
    out=validate(args.root)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1


if __name__=="__main__":
    raise SystemExit(main())
