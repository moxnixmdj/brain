"""Fail-closed terminal causal-depth policy.

Scheduling only. It cannot grant execution, promotion, fresh-reality, family,
capability, ownership, or acceptance credit.
"""
from __future__ import annotations
from typing import Iterable, Mapping, Any

SCHEMA = "PROJECT_BRAIN_TERMINAL_CAUSAL_DEPTH_COLLAPSE_V1"

UNRESOLVED = {
"CODING_TB4_GE_66_4","CODING_FRONTIERCODE_GE_54_4","CODING_CURSORBENCH_GE_57_8",
"PROWORK_GDPVAL_GE_1846","PROWORK_AA_BRIEFCASE_GE_1822","AUTOMATIONBENCH_GE_40",
"HLE_TOOLS_GE_67_7","TB_SCIENCE_GE_58_7","CHARTOGRAPHY_TOOLS_GE_89",
"OSWORLD_2_1_PARTIAL_GE_81_8","FINANCE_ACCOUNTING_INDEX_GE_61",
"FINANCE_AGENT_V2_GE_58_59","LIVEBENCH_IF_GE_65_7","ARTIFACT_AA_BRIEFCASE_GE_1822",
"MYSTERYMECHANISM_GE_49_55","SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
"AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION","VISION_DENSE_NONCHART_SCOPE",
"FINANCE_UNCOVERED_SCOPE_AUDIT","IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT","COMPOSITION_COMPONENT_SCOPED_PROOFS",
"COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES","AGENCY_MATCHED_SUCCESS_NONINFERIOR",
"IF_SCOPE_BOUNDARY_NONINFERIOR","COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}

RELATIVE_ELO = {
"PROWORK_GDPVAL_GE_1846",
"PROWORK_AA_BRIEFCASE_GE_1822",
"ARTIFACT_AA_BRIEFCASE_GE_1822",
}

PURE_ABSOLUTE = {
"FORMAL_ENTAILMENT",
"OBJECTIVE_CEILING_OR_FLOOR",
"EXHAUSTIVE_FINITE_UNIVERSE",
"SCOPE_SAFE_STRONGER_PROOF",
}
RELATIVE_SAFE = {
"RELATIVE_SCORE_BRIDGE",
"EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE",
"OWNER_RESULT",
"MATCHED_EMPIRICAL_COMPARISON",
}
FRESH_REALITY = {
"MATCHED_EMPIRICAL_COMPARISON",
"FIXED_BAR_SCORE",
"DIRECT_ORACLE",
}
ZERO_REALITY = {
"FORMAL_ENTAILMENT","OBJECTIVE_CEILING_OR_FLOOR","EXHAUSTIVE_FINITE_UNIVERSE",
"SCOPE_SAFE_STRONGER_PROOF","RELATIVE_SCORE_BRIDGE",
"EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE","OWNER_RESULT",
"ACCOUNT_OR_PROTOCOL_FACT","SCOPE_CERTIFICATE","UPSTREAM_SCOPE_RECEIPT",
}

def validate_live_state(state: Mapping[str, Any]) -> None:
    expected = {
        "accepted_families":5,"open_families":14,"proved_atomic":12,
        "unresolved_atomic":26,"total_families":19,"total_atomic":38,
        "root1_positive_gaps":0,"root2_only":16,"root3_only":7,
        "root2_and_root3":3,"terminal":False,
    }
    for k,v in expected.items():
        if state.get(k) != v:
            raise ValueError(f"STALE_LIVE_STATE:{k}:{state.get(k)!r}!={v!r}")

def route_admissible(predicate_id: str, route_kind: str, *, explicit_relative_bridge: bool=False) -> bool:
    if predicate_id not in UNRESOLVED:
        raise ValueError("UNKNOWN_PREDICATE")
    if predicate_id in RELATIVE_ELO and route_kind in PURE_ABSOLUTE and not explicit_relative_bridge:
        return False
    if route_kind not in ZERO_REALITY | FRESH_REALITY:
        raise ValueError("UNKNOWN_ROUTE_KIND")
    return True

def filter_routes(routes: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out=[]
    for raw in routes:
        r=dict(raw)
        p=r.get("predicate_id"); k=r.get("route_kind")
        if route_admissible(p,k,explicit_relative_bridge=bool(r.get("explicit_relative_bridge"))):
            out.append(r)
    return out

def compile_waves(
    state: Mapping[str, Any],
    routes: Iterable[Mapping[str, Any]],
    *,
    generic_isolation_proved: bool,
    fresh_reality_authorized: bool,
) -> dict[str, Any]:
    validate_live_state(state)
    admitted=filter_routes(routes)
    zero=[r for r in admitted if r["route_kind"] in ZERO_REALITY]
    fresh=[r for r in admitted if r["route_kind"] in FRESH_REALITY]
    fresh_runnable = bool(generic_isolation_proved and fresh_reality_authorized)
    return {
        "schema":SCHEMA,
        "wave0":{
            "parallel":True,
            "typed_evidence_collapse":zero,
            "generic_precommit_isolation_kernel":{
                "required":not generic_isolation_proved,
                "credit":0,
            },
        },
        "wave1":{
            "barrier":"EXACT_FIXED_POINT_RECOMPUTE",
            "rule":"DELETE_PROVED_ZERO_PROBABILITY_AND_STRICTLY_DOMINATED_ACTIONS",
        },
        "wave2":{
            "parallel":True,
            "fresh_reality_authorized":fresh_runnable,
            "actions":fresh if fresh_runnable else [],
            "blocked_actions":[] if fresh_runnable else fresh,
            "result_escrow":True,
        },
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_authorized":False,
    }

def dominance_prune(actions: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Delete only mechanically proven dominance: same phase, known costs,
    superset coverage, no weaker information class.
    Unknown costs/probabilities are never guessed.
    """
    rows=[dict(a) for a in actions]
    keep=[True]*len(rows)
    for i,a in enumerate(rows):
        ca=a.get("critical_path_seconds")
        if not isinstance(ca,(int,float)) or ca < 0:
            continue
        cover_a=set(a.get("covers",[]))
        phase_a=a.get("phase")
        for j,b in enumerate(rows):
            if i==j or not keep[i]:
                continue
            cb=b.get("critical_path_seconds")
            if not isinstance(cb,(int,float)) or cb < 0:
                continue
            if phase_a != b.get("phase"):
                continue
            cover_b=set(b.get("covers",[]))
            if cb <= ca and cover_b.issuperset(cover_a) and b.get("information_class",0) >= a.get("information_class",0):
                if cb < ca or cover_b != cover_a or b.get("information_class",0) > a.get("information_class",0):
                    keep[i]=False
    return [r for r,k in zip(rows,keep) if k]
