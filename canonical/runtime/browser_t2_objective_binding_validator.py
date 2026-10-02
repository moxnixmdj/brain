#!/usr/bin/env python3
"""Validate the frozen T2 direct-objective browser terminal binding.

Prewave only. No terminal beacon, case, promotion, capability or family credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from canonical.runtime import browser_state_information_safe_proof as proof
from canonical.runtime import browser_state_information_safe_candidate as candidate
from canonical.runtime.objective_route_promotion_transition import validate_promotion_transition

BINDING="canonical/governance/BROWSER_T2_OBJECTIVE_TERMINAL_BINDING_V1.json"


def _git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def validate(root: Path) -> dict:
    root=root.resolve()
    b=json.loads((root/BINDING).read_text(encoding="utf-8"))
    errors=[]

    if b.get("behavior_id")!="BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001":
        errors.append("BEHAVIOR_ID_MISMATCH")
    if b.get("proof_mode")!="T2_MULTIPLEXED_PUBLIC_BAR_PLUS_DIRECT_OBJECTIVE_BROWSER_GATE":
        errors.append("PROOF_MODE_MISMATCH")

    for label,row in (b.get("exact_bound_blobs") or {}).items():
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

    pool=b.get("direct_objective_source_pool") or {}
    classes=list(pool.get("class_cycle") or [])
    if classes!=list(proof.CLASSES):
        errors.append("CLASS_CYCLE_MISMATCH")
    count=pool.get("terminal_sample_count")
    if not isinstance(count,int) or count<=0 or count%len(proof.CLASSES)!=0:
        errors.append("TERMINAL_SAMPLE_COUNT_NOT_COMPLETE_CLASS_CYCLES")

    selector=b.get("selector") or {}
    for key in ("beacon_known_before_freeze","adaptive_case_selection","case_replacement","tuning_replay"):
        if selector.get(key) is not False:
            errors.append(f"SELECTOR_{key.upper()}_NOT_FALSE")

    if selector.get("protocol")!="GLOBAL_TERMINAL_SELECTION_KERNEL_V1":
        errors.append("SELECTOR_PROTOCOL_NOT_IMMUTABLE_KERNEL")
    sel_sem=b.get("selection_semantics") or {}
    kernel=(b.get("exact_bound_blobs") or {}).get("selection_kernel") or {}
    if sel_sem.get("kernel")!=kernel.get("path") or sel_sem.get("kernel_blob_sha")!=kernel.get("blob_sha"):
        errors.append("SELECTION_KERNEL_BINDING_MISMATCH")

    info=b.get("information_boundary") or {}
    if info.get("candidate_receives_hidden_oracle") is not False:
        errors.append("CANDIDATE_RECEIVES_HIDDEN_ORACLE")
    hidden=set(info.get("hidden_from_candidate") or [])
    for req in ("TARGET_ELEMENT_IDENTITY","TERMINAL_GOAL_STATE_PREDICATE","UNDECLARED_SIDE_EFFECT_TRUTH"):
        if req not in hidden:
            errors.append(f"HIDDEN_BOUNDARY_MISSING:{req}")

    result=proof.run_batch(20261002,50,candidate.next_action)
    if result.get("all_pass") is not True:
        errors.append("FIVE_CLASS_BROWSER_DIAGNOSTIC_FAILED")
    by_class=result.get("by_class") or {}
    if set(by_class)!=set(proof.CLASSES):
        errors.append("DIAGNOSTIC_CLASS_COVERAGE_INCOMPLETE")
    for cls in proof.CLASSES:
        row=by_class.get(cls) or {}
        if row.get("total")!=10 or row.get("pass")!=10:
            errors.append(f"DIAGNOSTIC_CLASS_FAILED:{cls}")

    for ordinal in range(len(proof.CLASSES)):
        case=proof.generate_case(99117,ordinal)
        state=case["_initial_state"]
        public=proof.public_state(case,state,[])
        raw=json.dumps(public,sort_keys=True)
        if "_oracle" in public or "_oracle" in raw or "_initial_state" in public:
            errors.append(f"HIDDEN_ORACLE_LEAK:{ordinal}")

    parent=b.get("public_bar_parent") or {}
    if parent.get("frozen_public_scored_task_count")!=600:
        errors.append("AUTOMATIONBENCH_PUBLIC_TASK_COUNT_MISMATCH")
    if parent.get("acceptance")!="PASS_RATE_GE_0_40_ON_ALL_FROZEN_600_PUBLIC_SCORED_TASKS":
        errors.append("AUTOMATIONBENCH_ACCEPTANCE_MISMATCH")

    gates=b.get("route_gates") or {}
    for key in (
        "candidate_package_frozen","executable_evaluator_bound",
        "population_or_source_pool_frozen","information_boundary_frozen",
        "post_freeze_selector_frozen","terminal_parent_binding_frozen",
    ):
        if gates.get(key) is not True:
            errors.append(f"ROUTE_GATE_NOT_FROZEN:{key}")
    errors.extend(
        validate_promotion_transition(
            root,
            b,
            binding_path=BINDING,
            behavior_id="BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
            prepromotion_status="FROZEN_PREWAVE_BINDING__SELECTION_KERNEL_REBOUND__INDEPENDENT_VERIFICATION_PENDING__ZERO_TERMINAL_RESULTS",
            promoted_status="FROZEN_PREWAVE_BINDING__INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_TERMINAL_RESULTS",
        )
    )

    return {
        "schema":"PROJECT_BRAIN_BROWSER_T2_OBJECTIVE_BINDING_VALIDATION_V1",
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "diagnostic_case_count":50,
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
