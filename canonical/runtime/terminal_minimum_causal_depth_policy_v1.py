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

COUNT_KEYS = (
    "accepted_families", "open_families", "proved_atomic", "unresolved_atomic",
    "total_families", "total_atomic", "root1_positive_gaps", "root2_only",
    "root3_only", "root2_and_root3",
)


def _count(state: Mapping[str, Any], key: str) -> int:
    value = state.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"INVALID_LIVE_STATE_COUNT:{key}:{value!r}")
    return value


def validate_live_state(state: Mapping[str, Any]) -> None:
    """Validate current-state invariants instead of pinning one historical snapshot.

    The capability envelope remains 19 families / 38 atomic predicates. Within
    that envelope, verified deltas are allowed to move acceptance and root
    partitions without requiring a code edit. Any internally inconsistent
    projection fails closed.
    """
    counts = {key: _count(state, key) for key in COUNT_KEYS}
    if counts["total_families"] != 19:
        raise ValueError(f"UNEXPECTED_FAMILY_ENVELOPE:{counts['total_families']}")
    if counts["total_atomic"] != 38:
        raise ValueError(f"UNEXPECTED_ATOMIC_ENVELOPE:{counts['total_atomic']}")
    if counts["accepted_families"] + counts["open_families"] != counts["total_families"]:
        raise ValueError("INCONSISTENT_FAMILY_PARTITION")
    if counts["proved_atomic"] + counts["unresolved_atomic"] != counts["total_atomic"]:
        raise ValueError("INCONSISTENT_ATOMIC_PARTITION")
    root_total = (
        counts["root1_positive_gaps"]
        + counts["root2_only"]
        + counts["root3_only"]
        + counts["root2_and_root3"]
    )
    if root_total != counts["unresolved_atomic"]:
        raise ValueError(
            f"INCONSISTENT_ROOT_PARTITION:{root_total}!={counts['unresolved_atomic']}"
        )
    terminal = state.get("terminal")
    if not isinstance(terminal, bool):
        raise ValueError(f"INVALID_TERMINAL_FLAG:{terminal!r}")
    derived_terminal = counts["open_families"] == 0 and counts["unresolved_atomic"] == 0
    if terminal != derived_terminal:
        raise ValueError(f"INCONSISTENT_TERMINAL_FLAG:{terminal}!={derived_terminal}")


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
