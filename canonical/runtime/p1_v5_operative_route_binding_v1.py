"""Fail-closed verifier for the explicit Brain-owned P1 V5 operative route.

This proves only route identity/source ownership/admissibility. It does not clear
P1 scope quarantine, inherit terminal credit, or grant family/capability credit.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.acceptance_capability_source_gate_v2 import evaluate as source_gate

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_V5_OPERATIVE_ROUTE_BINDING_VERDICT_V1"
BINDING="canonical/governance/P1_V5_OPERATIVE_ROUTE_BINDING_V1.json"
EXPECTED_BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
EXPECTED_ENTRY="canonical.runtime.trajectory_failure_typed_ir_candidate_v5:solve"
EXPECTED_PROOF="canonical.runtime.trajectory_failure_typed_ir_proof_v5:score_case"
EXPECTED_ADAPTER="canonical.runtime.trajectory_failure_typed_ir_proof_v5:public_task"

ALLOWED_CANDIDATE_IMPORTS={"__future__","typing"}
FORBIDDEN_TOKENS={
    "openai","anthropic","claude","opus","qwen","transformers","requests","httpx",
    "urllib","socket","aiohttp","subprocess","os.system","popen(","importlib",
    "__import__","ctypes","curl ","wget ","api_key","base_url"
}

def _load(rel:str)->dict[str,Any]:
    v=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(v,dict):
        raise ValueError(rel+":NOT_OBJECT")
    return v

def _blob(rel:str)->str:
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _candidate_import_roots(source:str)->set[str]:
    tree=ast.parse(source)
    out=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for x in node.names:
                out.add(x.name.split(".")[0])
        elif isinstance(node,ast.ImportFrom):
            out.add((node.module or "").split(".")[0])
    return out

def evaluate(binding:Mapping[str,Any]|None=None)->dict[str,Any]:
    b=dict(binding or _load(BINDING))
    errors:list[str]=[]

    if b.get("schema")!="PROJECT_BRAIN_P1_V5_OPERATIVE_ROUTE_BINDING_V1":
        errors.append("BINDING_SCHEMA_DRIFT")
    if b.get("behavior_id")!=EXPECTED_BEHAVIOR:
        errors.append("BEHAVIOR_ID_DRIFT")
    if b.get("entrypoint")!=EXPECTED_ENTRY:
        errors.append("ENTRYPOINT_DRIFT")
    if b.get("proof_evaluator")!=EXPECTED_PROOF:
        errors.append("PROOF_EVALUATOR_DRIFT")
    if b.get("proof_public_task_adapter")!=EXPECTED_ADAPTER:
        errors.append("PUBLIC_TASK_ADAPTER_DRIFT")

    package=b.get("package")
    if not isinstance(package,Mapping):
        errors.append("PACKAGE_MISSING")
        package={}
    for key in ("candidate","proof","governance","activation","independent_verification"):
        row=package.get(key)
        if not isinstance(row,Mapping) or not isinstance(row.get("path"),str) or not isinstance(row.get("git_blob_sha"),str):
            errors.append("PACKAGE_ROW_INVALID:"+key)
            continue
        try:
            if _blob(str(row["path"]))!=row["git_blob_sha"]:
                errors.append("PACKAGE_BLOB_DRIFT:"+key)
        except Exception:
            errors.append("PACKAGE_UNREADABLE:"+key)

    activation=package.get("activation") if isinstance(package.get("activation"),Mapping) else {}
    verification=package.get("independent_verification") if isinstance(package.get("independent_verification"),Mapping) else {}
    try:
        a=_load(str(activation.get("path")))
        if not str(a.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__"):
            errors.append("V5_ACTIVATION_NOT_INDEPENDENT_PASS")
    except Exception:
        errors.append("V5_ACTIVATION_UNREADABLE")
    try:
        v=_load(str(verification.get("path")))
        if not str(v.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"):
            errors.append("V5_VERIFICATION_NOT_INDEPENDENT_PASS")
        exact=v.get("exact_brain_blobs") or {}
        candidate_path=(package.get("candidate") or {}).get("path")
        proof_path=(package.get("proof") or {}).get("path")
        if exact.get(candidate_path)!=(package.get("candidate") or {}).get("git_blob_sha"):
            errors.append("V5_RECEIPT_CANDIDATE_BLOB_MISMATCH")
        if exact.get(proof_path)!=(package.get("proof") or {}).get("git_blob_sha"):
            errors.append("V5_RECEIPT_PROOF_BLOB_MISMATCH")
    except Exception:
        errors.append("V5_VERIFICATION_UNREADABLE")

    candidate_row=package.get("candidate") if isinstance(package.get("candidate"),Mapping) else {}
    try:
        source=(ROOT/str(candidate_row.get("path"))).read_text(encoding="utf-8")
        imports=_candidate_import_roots(source)
        bad_imports=sorted(imports-ALLOWED_CANDIDATE_IMPORTS)
        if bad_imports:
            errors.append("CANDIDATE_UNDECLARED_IMPORTS:"+",".join(bad_imports))
        lowered=source.lower()
        hits=sorted(x for x in FORBIDDEN_TOKENS if x in lowered)
        if hits:
            errors.append("CANDIDATE_EXTERNAL_ROUTE_TOKENS:"+",".join(hits))
        tree=ast.parse(source)
        funcs={x.name for x in ast.walk(tree) if isinstance(x,ast.FunctionDef)}
        if "solve" not in funcs:
            errors.append("CANDIDATE_SOLVE_ENTRYPOINT_MISSING")
    except Exception:
        errors.append("CANDIDATE_SOURCE_UNREADABLE")

    sg=b.get("source_gate")
    if not isinstance(sg,Mapping):
        errors.append("SOURCE_GATE_BINDING_MISSING")
        sg={}
    runtime=sg.get("runtime")
    receipt=sg.get("independent_verification")
    if runtime!="canonical/runtime/acceptance_capability_source_gate_v2.py":
        errors.append("SOURCE_GATE_RUNTIME_DRIFT")
    if isinstance(runtime,str) and isinstance(sg.get("runtime_git_blob_sha"),str):
        try:
            if _blob(runtime)!=sg["runtime_git_blob_sha"]:
                errors.append("SOURCE_GATE_RUNTIME_BLOB_DRIFT")
        except Exception:
            errors.append("SOURCE_GATE_RUNTIME_UNREADABLE")
    if isinstance(receipt,str) and isinstance(sg.get("independent_verification_git_blob_sha"),str):
        try:
            if _blob(receipt)!=sg["independent_verification_git_blob_sha"]:
                errors.append("SOURCE_GATE_RECEIPT_BLOB_DRIFT")
            vr=_load(receipt)
            if not str(vr.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"):
                errors.append("SOURCE_GATE_NOT_INDEPENDENT_PASS")
        except Exception:
            errors.append("SOURCE_GATE_RECEIPT_UNREADABLE")
    route=sg.get("route_input")
    if not isinstance(route,Mapping):
        errors.append("SOURCE_GATE_ROUTE_INPUT_MISSING")
        gate={"pass":False,"errors":["ROUTE_INPUT_MISSING"]}
    else:
        gate=source_gate(route)
        if gate.get("pass") is not True:
            errors.append("SOURCE_GATE_V2_REJECTED:"+",".join(gate.get("errors") or []))

    current=b.get("current_claim") or {}
    if current.get("brain_owned_operative_route_candidate") is not True:
        errors.append("OPERATIVE_ROUTE_CANDIDATE_FLAG_MISSING")
    for k in ("p1_whole_scope_restored","terminal_credit_authorized","family_credit_authorized"):
        if current.get(k) is not False:
            errors.append("PREMATURE_CREDIT_OR_SCOPE_FLAG:"+k)
    if b.get("execution_authority") is not False or b.get("promotion_authority") is not False:
        errors.append("PREMATURE_AUTHORITY")

    ok=not errors
    return {
        "schema":SCHEMA,
        "status":"PASS__P1_V5_BRAIN_OWNED_OPERATIVE_ROUTE_BOUND__SCOPE_AND_RESTORATION_STILL_REQUIRED__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass":ok,
        "errors":sorted(set(errors)),
        "behavior_id":EXPECTED_BEHAVIOR,
        "entrypoint":EXPECTED_ENTRY,
        "source_gate_v2_pass":gate.get("pass") is True,
        "candidate_model_dependency_count":(sg.get("route_input") or {}).get("model_dependency_count"),
        "external_hidden_target_capability_provider":(sg.get("route_input") or {}).get("external_hidden_target_capability_provider"),
        "p1_whole_scope_restored":False,
        "terminal_credit_authorized":False,
        "family_credit_authorized":False,
        "terminal_results_replayed":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "next":"REQUIRE_THIS_OPERATIVE_ROUTE_BINDING_AS_A_PRECONDITION_OF_P1_RESTORATION_AFTER_SCOPE_SUPERSET_INDEPENDENT_PASS"
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
