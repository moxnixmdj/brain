"""Generic precommit isolation theorem checker.

This module proves only a conditional causal-isolation statement. It does not
establish benchmark comparability and cannot authorize fresh reality.
"""
from __future__ import annotations
import hashlib, json
from collections import deque
from typing import Any, Mapping, Iterable

SCHEMA="PROJECT_BRAIN_GENERIC_PRECOMMIT_ISOLATION_THEOREM_V1"
COMPONENTS=("candidate","harness","scorer","environment","policy")
SOURCES=("case_content","evaluation_output","unrelated_zero_reality_work")

def _sha(x: Any) -> bool:
    s=str(x or "")
    return len(s)==64 and all(c in "0123456789abcdefABCDEF" for c in s)

def commitment_digest(receipt: Mapping[str,Any]) -> str:
    obj={f"{c}_sha256":str(receipt.get(f"{c}_sha256","")).lower() for c in COMPONENTS}
    raw=json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def _reachable(edges: Iterable[tuple[str,str]], src: str, dst: str) -> bool:
    graph: dict[str,list[str]]={}
    for a,b in edges:
        graph.setdefault(a,[]).append(b)
    q=deque([src]); seen={src}
    while q:
        x=q.popleft()
        if x==dst:
            return True
        for y in graph.get(x,[]):
            if y not in seen:
                seen.add(y); q.append(y)
    return False

def verify_generic_isolation(receipt: Mapping[str,Any]) -> dict[str,Any]:
    reasons: list[str]=[]
    for c in COMPONENTS:
        committed=receipt.get(f"{c}_sha256")
        observed=receipt.get(f"observed_{c}_sha256")
        if not _sha(committed):
            reasons.append(f"INVALID_{c.upper()}_SHA256")
        if str(observed or "").lower()!=str(committed or "").lower():
            reasons.append(f"EXECUTED_{c.upper()}_DIFFERS_FROM_COMMITTED")

    if str(receipt.get("commitment_sha256","")).lower()!=commitment_digest(receipt):
        reasons.append("COMMITMENT_DIGEST_MISMATCH")

    commit_seq=receipt.get("commit_event_sequence")
    reveal_seq=receipt.get("case_reveal_event_sequence")
    exec_seq=receipt.get("execution_start_event_sequence")
    if isinstance(commit_seq,bool) or not isinstance(commit_seq,int):
        reasons.append("INVALID_COMMIT_EVENT_SEQUENCE")
    if isinstance(reveal_seq,bool) or not isinstance(reveal_seq,int):
        reasons.append("INVALID_CASE_REVEAL_EVENT_SEQUENCE")
    if isinstance(exec_seq,bool) or not isinstance(exec_seq,int):
        reasons.append("INVALID_EXECUTION_START_EVENT_SEQUENCE")
    if all(isinstance(x,int) and not isinstance(x,bool) for x in (commit_seq,reveal_seq,exec_seq)):
        if not (commit_seq < reveal_seq <= exec_seq):
            reasons.append("PRECOMMIT_ORDER_NOT_PROVED")

    if receipt.get("independent_executor") is not True:
        reasons.append("INDEPENDENT_EXECUTOR_NOT_PROVED")
    if receipt.get("committed_components_immutable") is not True:
        reasons.append("COMMITTED_COMPONENT_IMMUTABILITY_NOT_PROVED")
    if receipt.get("no_case_or_evaluation_feedback_to_committed_components") is not True:
        reasons.append("CASE_OR_EVALUATION_FEEDBACK_NOT_EXCLUDED")
    if receipt.get("unrelated_work_cannot_mutate_committed_components") is not True:
        reasons.append("UNRELATED_WORK_MUTATION_NOT_EXCLUDED")
    if receipt.get("outputs_bound_to_commitment") is not True:
        reasons.append("OUTPUTS_NOT_BOUND_TO_COMMITMENT")

    # A receipt may declare observed causal edges. Any path from a forbidden
    # source to a committed component falsifies generic isolation.
    raw_edges=receipt.get("observed_causal_edges",[])
    edges: list[tuple[str,str]]=[]
    if not isinstance(raw_edges,list):
        reasons.append("CAUSAL_EDGES_NOT_LIST")
    else:
        for i,e in enumerate(raw_edges):
            if not (isinstance(e,(list,tuple)) and len(e)==2 and all(isinstance(z,str) and z for z in e)):
                reasons.append(f"INVALID_CAUSAL_EDGE_{i}")
            else:
                edges.append((e[0],e[1]))
    for src in SOURCES:
        for component in COMPONENTS:
            if _reachable(edges,src,component):
                reasons.append(f"FORBIDDEN_CAUSAL_PATH:{src}->{component}")

    passed=not reasons
    return {
        "schema":SCHEMA,
        "generic_isolation_kernel_pass":passed,
        "conditional_adaptation_independence_proved":passed,
        "reasons":sorted(set(reasons)),
        "benchmark_thin_adapter_required":True,
        "benchmark_comparability_proved":False,
        "fresh_reality_authority":False,
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_authorized":False,
    }

def verify_benchmark_thin_adapter(adapter: Mapping[str,Any]) -> dict[str,Any]:
    required=(
      "population_identity_verified","scorer_or_grader_equivalence_verified",
      "effort_and_context_semantics_verified","tool_and_environment_boundary_verified",
      "exact_comparator_identity_verified","no_proxy_substitution_verified",
      "zero_incremental_spend_or_entitlement_verified","acceptance_rule_bound",
    )
    missing=[k for k in required if adapter.get(k) is not True]
    return {
      "schema":SCHEMA,
      "benchmark_thin_adapter_pass":not missing,
      "missing":missing,
      "generic_isolation_kernel_proved":False,
      "fresh_reality_authority":False,
      "execution_authority":False,
      "promotion_authority":False,
      "acceptance_credit_authorized":False,
    }

def concurrency_admissibility(
    isolation: Mapping[str,Any],
    adapter: Mapping[str,Any],
    *,
    explicit_fresh_reality_authority: bool,
) -> dict[str,Any]:
    iso=verify_generic_isolation(isolation)
    ad=verify_benchmark_thin_adapter(adapter)
    ready=bool(
      iso["generic_isolation_kernel_pass"]
      and ad["benchmark_thin_adapter_pass"]
      and explicit_fresh_reality_authority
    )
    return {
      "schema":SCHEMA,
      "concurrent_collection_ready":ready,
      "generic_isolation_kernel_pass":iso["generic_isolation_kernel_pass"],
      "benchmark_thin_adapter_pass":ad["benchmark_thin_adapter_pass"],
      "explicit_fresh_reality_authority":bool(explicit_fresh_reality_authority),
      "fresh_reality_authority_granted_by_this_module":False,
      "execution_authority":False,
      "promotion_authority":False,
      "acceptance_credit_authorized":False,
    }
