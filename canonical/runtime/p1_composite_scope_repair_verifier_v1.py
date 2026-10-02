"""Fail-closed verifier for the predeclared P1 composite proof repair.

This verifier does not reinterpret the narrow terminal scorer as whole-scope P1
coverage. It proves only that the exact frozen P1 check/mutation obligations were
predeclared as a composite of:
  (a) independently verified Typed-V4 cross-domain mechanism/pattern evidence; and
  (b) immutable T0/T2 terminal causal-localization/repair/rescue evidence.

No terminal replay, acceptance credit, family credit, execution authority or
promotion authority is created here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
P1="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
BINDING_PATH="canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
RECON_PATH="canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json"
V4_VER_PATH="canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
TERMINAL_PATH="canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
PARENT_BINDING_PATH="canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json"
SUITE_PATH="canonical/runtime/contract_native_proof_suites.py"
AUDIT_PATH="canonical/runtime/p1_terminal_execution_scope_audit_v1.py"
QUARANTINE_PATH="canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json"

V4_REQUIRED_PATHS={
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py",
    "canonical/runtime/trajectory_failure_typed_ir_proof_v4.py",
    "canonical/tests/test_trajectory_failure_typed_ir_v4.py",
    V4_VER_PATH,
}
EXPECTED_V4_DOMAINS={"BROWSER","FILESYSTEM","TOOL_API","ARTIFACT","RESEARCH","CODE"}
EXPECTED_V4_KINDS={"AUTHORITY","SCHEMA","PROVENANCE","INVARIANT","STATE_TRANSITION","TOOL_CONTRACT","DEPENDENCY"}
EXPECTED_V4_PATTERNS={"SINGLE","DELAYED","INTERACTION","AMBIGUOUS"}

def load(path:str)->dict[str,Any]:
    value=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError(path+":NOT_OBJECT")
    return value

def blob(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load_live()->dict[str,Any]:
    return {
        "binding":load(BINDING_PATH),
        "reconciliation":load(RECON_PATH),
        "v4_verification":load(V4_VER_PATH),
        "terminal":load(TERMINAL_PATH),
        "parent_binding":load(PARENT_BINDING_PATH),
        "quarantine":load(QUARANTINE_PATH),
        "actual_blobs":{
            BINDING_PATH:blob(BINDING_PATH),
            V4_VER_PATH:blob(V4_VER_PATH),
            "canonical/runtime/trajectory_failure_typed_ir_proof_v4.py":blob("canonical/runtime/trajectory_failure_typed_ir_proof_v4.py"),
            "canonical/tests/test_trajectory_failure_typed_ir_v4.py":blob("canonical/tests/test_trajectory_failure_typed_ir_v4.py"),
            "canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py":blob("canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py"),
            PARENT_BINDING_PATH:blob(PARENT_BINDING_PATH),
            SUITE_PATH:blob(SUITE_PATH),
            AUDIT_PATH:blob(AUDIT_PATH),
            QUARANTINE_PATH:blob(QUARANTINE_PATH),
        },
    }

def _fail(errors:list[str])->dict[str,Any]:
    return {
        "schema":"PROJECT_BRAIN_P1_COMPOSITE_SCOPE_REPAIR_VERDICT_V1",
        "status":"FAIL_CLOSED",
        "pass":False,
        "scope_repair_proved":False,
        "errors":sorted(set(errors)),
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def _partition(role_map:Any)->tuple[set[str],bool]:
    if not isinstance(role_map,Mapping) or not role_map:
        return set(),False
    union:set[str]=set()
    disjoint=True
    for values in role_map.values():
        if not isinstance(values,list) or any(not isinstance(x,str) or not x for x in values):
            return set(),False
        s=set(values)
        if len(s)!=len(values) or union & s:
            disjoint=False
        union |= s
    return union,disjoint

def _terminal_receipt(terminal:Mapping[str,Any],portfolio:str)->Mapping[str,Any]|None:
    rows=(((terminal.get("reduction_input") or {}).get("wave") or {}).get("parent_portfolio_receipts") or {}).get(portfolio)
    if not isinstance(rows,list):
        return None
    found=[x for x in rows if isinstance(x,Mapping) and x.get("behavior_id")==P1]
    return found[0] if len(found)==1 else None

def evaluate(
    *,
    binding:Mapping[str,Any],
    reconciliation:Mapping[str,Any],
    v4_verification:Mapping[str,Any],
    terminal:Mapping[str,Any],
    parent_binding:Mapping[str,Any],
    quarantine:Mapping[str,Any],
    actual_blobs:Mapping[str,str],
)->dict[str,Any]:
    e:list[str]=[]

    if binding.get("behavior_id")!=P1:
        e.append("P1_BINDING_BEHAVIOR_DRIFT")

    deps=binding.get("dependencies")
    if not isinstance(deps,list) or not V4_REQUIRED_PATHS.issubset(set(deps)):
        e.append("V4_NOT_PREDECLARED_IN_FROZEN_BINDING")

    checks=((binding.get("evaluator") or {}).get("required_checks"))
    muts=((binding.get("evaluator") or {}).get("required_mutations"))
    if not isinstance(checks,list) or len(checks)!=len(set(checks)):
        e.append("FROZEN_REQUIRED_CHECKS_INVALID")
        checks=[]
    if not isinstance(muts,list) or len(muts)!=len(set(muts)):
        e.append("FROZEN_REQUIRED_MUTATIONS_INVALID")
        muts=[]

    check_union,check_disjoint=_partition(reconciliation.get("proof_roles"))
    if check_union!=set(checks):
        e.append("REQUIRED_CHECK_PARTITION_MISMATCH")
    if not check_disjoint:
        e.append("REQUIRED_CHECK_PARTITION_NOT_DISJOINT")

    mut_union,mut_disjoint=_partition(reconciliation.get("mutation_roles"))
    if mut_union!=set(muts):
        e.append("REQUIRED_MUTATION_PARTITION_MISMATCH")
    if not mut_disjoint:
        e.append("REQUIRED_MUTATION_PARTITION_NOT_DISJOINT")

    authority=reconciliation.get("authority")
    if not isinstance(authority,Mapping):
        e.append("RECONCILIATION_AUTHORITY_MISSING")
        authority={}
    authority_checks={
        "p1_binding":BINDING_PATH,
        "v4_independent_preflight":V4_VER_PATH,
        "v4_proof":"canonical/runtime/trajectory_failure_typed_ir_proof_v4.py",
        "v4_tests":"canonical/tests/test_trajectory_failure_typed_ir_v4.py",
        "parent_binding":PARENT_BINDING_PATH,
        "executed_suite":SUITE_PATH,
        "scope_audit":AUDIT_PATH,
        "quarantine":QUARANTINE_PATH,
    }
    for key,path in authority_checks.items():
        row=authority.get(key)
        if not isinstance(row,Mapping) or row.get("path")!=path or row.get("git_blob_sha")!=actual_blobs.get(path):
            e.append("AUTHORITY_BLOB_MISMATCH:"+key)

    status=str(v4_verification.get("status") or "")
    if "INDEPENDENT_PASS" not in status:
        e.append("V4_INDEPENDENT_VERIFICATION_NOT_PASS")
    pub=v4_verification.get("public_verifier")
    if not isinstance(pub,Mapping) or pub.get("conclusion")!="success":
        e.append("V4_PUBLIC_RUNNER_NOT_SUCCESS")
    verified=v4_verification.get("verified")
    if not isinstance(verified,Mapping):
        e.append("V4_VERIFIED_PAYLOAD_MISSING")
        verified={}
    if set(verified.get("normalized_domains") or [])!=EXPECTED_V4_DOMAINS:
        e.append("V4_DOMAIN_COVERAGE_DRIFT")
    if set(verified.get("mechanism_classes") or [])!=EXPECTED_V4_KINDS:
        e.append("V4_MECHANISM_COVERAGE_DRIFT")
    if set(verified.get("causal_patterns") or [])!=EXPECTED_V4_PATTERNS:
        e.append("V4_PATTERN_COVERAGE_DRIFT")
    if verified.get("cross_product_case_count")!=168:
        e.append("V4_CASE_COUNT_DRIFT")
    if verified.get("hidden_oracle_not_candidate_visible") is not True:
        e.append("V4_HIDDEN_ORACLE_BOUNDARY_NOT_PROVED")
    if verified.get("falsifiable_repair_targets_scored_against_hidden_oracle") is not True:
        e.append("V4_REPAIR_TARGET_SCORING_NOT_PROVED")
    exact=v4_verification.get("exact_brain_blobs")
    expected_v4={
        "candidate":actual_blobs.get("canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py"),
        "proof":actual_blobs.get("canonical/runtime/trajectory_failure_typed_ir_proof_v4.py"),
        "tests":actual_blobs.get("canonical/tests/test_trajectory_failure_typed_ir_v4.py"),
    }
    if not isinstance(exact,Mapping) or any(exact.get(k)!=v for k,v in expected_v4.items()):
        e.append("V4_EXACT_BLOB_BINDING_DRIFT")

    if parent_binding.get("exact_brain_blobs",{}).get(SUITE_PATH)!=actual_blobs.get(SUITE_PATH):
        e.append("EXECUTED_SUITE_NOT_EXACTLY_BOUND")

    terminal_cases=0
    binding_sha=actual_blobs.get(BINDING_PATH)
    for portfolio in ("T0","T2"):
        row=_terminal_receipt(terminal,portfolio)
        if row is None:
            e.append("TERMINAL_RECEIPT_MISSING:"+portfolio)
            continue
        if row.get("binding_blob")!=binding_sha:
            e.append("TERMINAL_BINDING_BLOB_MISMATCH:"+portfolio)
        if any(row.get(k) is not True for k in ("load_bearing","direct_instrumentation_pass","parent_terminal_acceptance_pass")):
            e.append("TERMINAL_RECEIPT_NOT_PASS:"+portfolio)
        if any(row.get(k) is not False for k in ("case_replaced","tuning_replay","result_to_runtime_feedback")):
            e.append("TERMINAL_RECEIPT_CONTAMINATED:"+portfolio)
        cid=str(row.get("case_id") or "")
        try:
            n=int(cid.rsplit("::",1)[-1])
        except Exception:
            n=-1
        if n!=30:
            e.append("TERMINAL_CASE_COUNT_DRIFT:"+portfolio)
        else:
            terminal_cases+=n

    guards=terminal.get("result_guards")
    if not isinstance(guards,Mapping) or guards.get("no_case_replacement") is not True or guards.get("no_tuning_replay") is not True or guards.get("result_to_runtime_feedback_during_wave") is not False:
        e.append("TERMINAL_CONTAMINATION_GUARDS_FAIL")

    qstatus=str(quarantine.get("status") or "")
    if "FAIL_CLOSED_QUARANTINE" not in qstatus:
        e.append("P1_SCOPE_QUARANTINE_NOT_PRESERVED")
    repair_law=str(quarantine.get("repair_law") or "")
    if "SEARCH_EXISTING_TYPED_V4" not in repair_law or "ONLY_IRREDUCIBLE_MISSING_REALITY_MAY_AUTHORIZE_NEW_OBSERVATION" not in repair_law:
        e.append("QUARANTINE_REPAIR_LAW_DRIFT")

    if reconciliation.get("verification_state",{}).get("independent_verification") is not False:
        e.append("CANDIDATE_VERIFICATION_STATE_OVERCLAIM")
    if reconciliation.get("verification_state",{}).get("quarantine_resolved") is not False:
        e.append("CANDIDATE_QUARANTINE_STATE_OVERCLAIM")

    if e:
        return _fail(e)

    return {
        "schema":"PROJECT_BRAIN_P1_COMPOSITE_SCOPE_REPAIR_VERDICT_V1",
        "status":"PASS__PREDECLARED_COMPOSITE_P1_SCOPE_REPAIR_CANDIDATE__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT",
        "pass":True,
        "scope_repair_proved":True,
        "behavior_id":P1,
        "required_check_count":len(checks),
        "required_mutation_count":len(muts),
        "v4_case_count":168,
        "terminal_case_count":terminal_cases,
        "proof_roles":{
            "V4_TYPED_CROSS_DOMAIN_PREFLIGHT":len(reconciliation["proof_roles"]["V4_TYPED_CROSS_DOMAIN_PREFLIGHT"]),
            "T0_T2_TERMINAL_INTERVENTION_RESCUE":len(reconciliation["proof_roles"]["T0_T2_TERMINAL_INTERVENTION_RESCUE"]),
        },
        "rule":"COMPOSITE_SCOPE_IS_PROVED_ONLY_AS_A_CANDIDATE_PARTITION__THE_NARROW_TERMINAL_SCORER_REMAINS_NARROW__INDEPENDENT_PUBLIC_RUNNER_VERIFICATION_MUST_PRECEDE_QUARANTINE_RESOLUTION",
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }
