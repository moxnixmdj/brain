"""Owned-registry observability closure for Tool Discovery.

This candidate proves a narrow but load-bearing fact for the operative Brain
authority: every currently invocable bound capability has a finite, deterministic
capability-membership decision surface, and every registry entry carries a
verification binding. It does NOT prove whole-protocol identity discovery, V6
policy correctness, or Tool Discovery acceptance.

The only non-local verification binding is the BM25 capability, whose registry
record points to public verifier PR #143 / workflow run 36678278264. The
independent verifier must validate that external binding before this candidate
may be treated as verified.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
REGISTRY_REL="canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
ASTRA_REL="canonical/runtime/astra_runtime.py"
REGISTRY_BLOB="7badee4878700f2cd4176beb8319d2a6a0bdf782"
ASTRA_BLOB="7f5d16b1db69cb620954bc778e0ba6e15e687b75"
LOCAL_EVIDENCE_FIELDS=(
    "receipt_path",
    "verification_result_path",
    "verification_evidence",
    "inherited_supplier_evidence",
    "capability_receipt",
)
BM25_ID="source.objective_relevance.rank.bm25"
BM25_PUBLIC_PR=143
BM25_PUBLIC_RUN=36678278264
BM25_PRODUCER_BLOB="95d2b6bac6f6ffb5db97526407fcd22cbcc6c790"


class ClosureError(RuntimeError):
    pass


def _blob(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def _registry()->dict[str,Mapping[str,Any]]:
    p=ROOT/REGISTRY_REL
    if _blob(p)!=REGISTRY_BLOB:
        raise ClosureError("REGISTRY_BLOB_DRIFT")
    raw=json.loads(p.read_text(encoding="utf-8"))
    if raw.get("schema")!="PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise ClosureError("REGISTRY_SCHEMA_INVALID")
    caps=raw.get("capabilities")
    if not isinstance(caps,dict) or not caps:
        raise ClosureError("REGISTRY_EMPTY")
    return caps


def _local_evidence_refs(verification: Mapping[str,Any])->list[str]:
    return [
        str(verification.get(field))
        for field in LOCAL_EVIDENCE_FIELDS
        if isinstance(verification.get(field),str) and str(verification.get(field))
    ]


def _bm25_external_binding(rec: Mapping[str,Any])->bool:
    v=rec.get("verification")
    return bool(
        isinstance(v,Mapping)
        and v.get("status")=="INDEPENDENT_PUBLIC_CROSS_DOMAIN_QUALIFICATION_PASS"
        and v.get("public_runner_pr")==BM25_PUBLIC_PR
        and v.get("workflow_run_id")==BM25_PUBLIC_RUN
        and v.get("exact_producer_blob")==BM25_PRODUCER_BLOB
        and v.get("model_dependency_count")==0
        and float(v.get("incremental_spend_usd",1))==0
    )


def _astra_chokepoint()->dict[str,Any]:
    p=ROOT/ASTRA_REL
    if _blob(p)!=ASTRA_BLOB:
        raise ClosureError("ASTRA_BLOB_DRIFT")
    text=p.read_text(encoding="utf-8")
    tree=ast.parse(text,filename=ASTRA_REL)
    funcs={
        n.name:n for n in ast.walk(tree)
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
    }
    load=funcs.get("_load_bound_capability_registry")
    invoke=funcs.get("_invoke_bound_capability")
    goal=funcs.get("_goal_action")
    if load is None or invoke is None or goal is None:
        raise ClosureError("ASTRA_CHOKEPOINT_FUNCTION_MISSING")
    load_src=ast.get_source_segment(text,load) or ""
    invoke_src=ast.get_source_segment(text,invoke) or ""
    goal_src=ast.get_source_segment(text,goal) or ""
    lookup="_load_bound_capability_registry().get(cid)"
    return {
        "loads_exact_bound_registry":
            "BOUND_CAPABILITY_REGISTRY_V1.json" in load_src
            and "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1" in load_src,
        "unknown_id_fails_closed":
            lookup in invoke_src and "BOUND_CAPABILITY_UNKNOWN:" in invoke_src,
        "lookup_precedes_adapter":
            lookup in invoke_src
            and "adapter_module" in invoke_src
            and invoke_src.index(lookup)<invoke_src.index("adapter_module"),
        "single_goal_dispatch":
            goal_src.count('if typ=="invoke_capability":')==1
            and "return _invoke_bound_capability(args)" in goal_src,
    }


def safe_probe(tool_id: str, capability: str)->dict[str,Any]:
    caps=_registry()
    tid=str(tool_id or "")
    cap=str(capability or "")
    if tid not in caps:
        raise ClosureError("UNREGISTERED_TOOL_ID")
    if not cap:
        raise ClosureError("CAPABILITY_REQUIRED")
    provides=caps[tid].get("provides")
    if not isinstance(provides,list) or not provides:
        raise ClosureError("PROVIDES_INVALID")
    return {
        "tool_id":tid,
        "capability":cap,
        "supported":cap in {str(x) for x in provides},
        "basis":"CONTENT_ADDRESSED_VERIFIED_BOUND_CAPABILITY_PROVIDES",
        "registry_git_blob":REGISTRY_BLOB,
    }


def evaluate()->dict[str,Any]:
    caps=_registry()
    choke=_astra_chokepoint()
    rows=[]
    errors=[]
    external=[]
    for tid,rec in sorted(caps.items()):
        if not isinstance(rec,Mapping):
            errors.append("RECORD_NOT_OBJECT:"+tid)
            continue
        provides=rec.get("provides")
        if rec.get("status")!="VERIFIED_BOUND_CAPABILITY":
            errors.append("STATUS_NOT_VERIFIED:"+tid)
        if not isinstance(provides,list) or not provides:
            errors.append("PROVIDES_INVALID:"+tid)
        if float(rec.get("incremental_spend_usd",1))!=0:
            errors.append("NONZERO_INCREMENTAL_SPEND:"+tid)
        v=rec.get("verification")
        if not isinstance(v,Mapping):
            errors.append("VERIFICATION_MISSING:"+tid)
            continue
        refs=_local_evidence_refs(v)
        missing=[p for p in refs if not (ROOT/p).is_file()]
        if missing:
            errors.extend("LOCAL_EVIDENCE_MISSING:"+tid+":"+p for p in missing)
        local_bound=bool(refs) and not missing
        external_bound=(tid==BM25_ID and _bm25_external_binding(rec))
        if not local_bound and not external_bound:
            errors.append("NO_VERIFICATION_BINDING:"+tid)
        if external_bound:
            external.append({
                "tool_id":tid,
                "public_repo":"moxnixmdj/verification-capsule-runner",
                "public_pr":BM25_PUBLIC_PR,
                "workflow_run_id":BM25_PUBLIC_RUN,
                "exact_producer_blob":BM25_PRODUCER_BLOB,
                "independent_verifier_must_confirm_success":True,
            })
        rows.append({
            "tool_id":tid,
            "provides_count":len(provides) if isinstance(provides,list) else 0,
            "local_evidence_refs":refs,
            "local_evidence_bound":local_bound,
            "external_public_binding":external_bound,
        })

    for name,value in choke.items():
        if value is not True:
            errors.append("ASTRA_CHOKEPOINT_FAILED:"+name)

    passed=not errors and len(rows)==42
    return {
        "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_OWNED_OBSERVABILITY_CLOSURE_V1",
        "status":(
            "PASS_CANDIDATE__42_OF_42_OWNED_CAPABILITIES_OBSERVABILITY_BOUND__BM25_EXTERNAL_RUN_REQUIRES_INDEPENDENT_RECHECK__ZERO_CREDIT"
            if passed else "FAIL_CLOSED"
        ),
        "registry_git_blob":REGISTRY_BLOB,
        "astra_runtime_git_blob":ASTRA_BLOB,
        "tool_count":len(rows),
        "all_invocable_identities_registry_gated":all(choke.values()),
        "all_registry_entries_have_nonempty_provides":all(r["provides_count"]>0 for r in rows),
        "local_evidence_bound_count":sum(r["local_evidence_bound"] for r in rows),
        "external_public_binding_count":sum(r["external_public_binding"] for r in rows),
        "unbound_count":sum(
            not r["local_evidence_bound"] and not r["external_public_binding"]
            for r in rows
        ),
        "arbitrary_required_capability_membership_is_deterministically_decidable":
            passed,
        "observability_partition_implication":(
            "FOR_THIS_OWNED_42_TOOL_AUTHORITY__NO_REGISTERED_TOOL_HAS_AN_INTRINSICALLY_UNOBSERVABLE_REQUIRED_CAPABILITY_BIT__"
            "ANY_CAPABILITY_STRING_CAN_BE_DECIDED_BY_CONTENT_ADDRESSED_MEMBERSHIP_LOOKUP__"
            "THIS_DOES_NOT_BY_ITSELF_PROVE_IDENTITY_SCOPE_COMPLETENESS_OR_WHOLE_PROTOCOL_ACCEPTANCE"
        ),
        "external_bindings":external,
        "errors":errors,
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


def main()->int:
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["status"].startswith("PASS_CANDIDATE") else 1


if __name__=="__main__":
    raise SystemExit(main())
