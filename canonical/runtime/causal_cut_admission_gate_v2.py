"""Fail-closed causal-cut admission gate for Brain changes.

V2 strengthens terminal-delta admission by requiring every qualifying change to
carry an independently verified causal binding from a primitive fact on the
current terminal cut to a named terminal blocker. The gate itself grants no
acceptance, capability, family, execution, or promotion authority.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CAUSAL_CUT_ADMISSION_GATE_V2"
_ALLOWED_EFFECTS = {
    "DISCHARGES_PRIMITIVE_FACT",
    "PROVES_ROUTE_IMPOSSIBLE",
    "CREATES_VERIFIED_IMPLICATION",
    "SUPPLIES_IDENTIFIABILITY_INFORMATION",
    "BINDS_ROUTE_OR_SCOPE",
}


def _int(m: Mapping[str, Any], key: str) -> int:
    v = m.get(key, 0)
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(key)
    return v


def _set(m: Mapping[str, Any], key: str) -> set[str]:
    v = m.get(key, [])
    if not isinstance(v, list) or any(not isinstance(x, str) or not x for x in v):
        raise ValueError(key)
    return set(v)


def _links(
    causal_links: Sequence[Mapping[str, Any]],
    *,
    blocker_ids: set[str],
    before_cut: set[str],
    verified_evidence_ids: set[str],
) -> tuple[list[dict[str, str]], list[str]]:
    out: list[dict[str, str]] = []
    errors: list[str] = []
    if not isinstance(causal_links, (list, tuple)) or not causal_links:
        return out, ["CAUSAL_LINKS_REQUIRED"]

    seen: set[tuple[str, str, str, str]] = set()
    for i, link in enumerate(causal_links):
        if not isinstance(link, Mapping):
            errors.append(f"INVALID_CAUSAL_LINK:{i}")
            continue
        edge_id = link.get("edge_id")
        primitive = link.get("primitive_fact_id")
        blocker = link.get("blocker_id")
        evidence = link.get("verified_evidence_id")
        effect = link.get("effect")
        values = (edge_id, primitive, blocker, evidence, effect)
        if any(not isinstance(v, str) or not v for v in values):
            errors.append(f"INVALID_CAUSAL_LINK_FIELDS:{i}")
            continue
        if effect not in _ALLOWED_EFFECTS:
            errors.append(f"INVALID_CAUSAL_EFFECT:{i}:{effect}")
            continue
        if primitive not in before_cut:
            errors.append(f"OFF_CUT_PRIMITIVE_FACT:{i}:{primitive}")
            continue
        if blocker not in blocker_ids:
            errors.append(f"UNDECLARED_BLOCKER:{i}:{blocker}")
            continue
        if evidence not in verified_evidence_ids:
            errors.append(f"UNVERIFIED_CAUSAL_EVIDENCE:{i}:{evidence}")
            continue
        key = (edge_id, primitive, blocker, effect)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "edge_id": edge_id,
                "primitive_fact_id": primitive,
                "blocker_id": blocker,
                "verified_evidence_id": evidence,
                "effect": effect,
            }
        )
    return out, errors


def evaluate(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    blocker_ids: list[str],
    causal_links: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not blocker_ids or any(not isinstance(x, str) or not x for x in blocker_ids):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["BLOCKER_IDS_REQUIRED"],
            "admit": False,
        }

    try:
        b_un = _int(before, "unresolved_atomic_predicates")
        a_un = _int(after, "unresolved_atomic_predicates")
        b_fam = _int(before, "accepted_families")
        a_fam = _int(after, "accepted_families")
        b_lb = _int(before, "minimum_remaining_work_lower_bound")
        a_lb = _int(after, "minimum_remaining_work_lower_bound")
        b_imp = _set(before, "proved_impossible_branches")
        a_imp = _set(after, "proved_impossible_branches")
        b_dom = _set(before, "formally_owned_domain_atoms")
        a_dom = _set(after, "formally_owned_domain_atoms")
        b_protected = _set(before, "protected_terminal_facts")
        a_protected = _set(after, "protected_terminal_facts")
        b_cut = _set(before, "primitive_residual_facts")
        a_cut = _set(after, "primitive_residual_facts")
        verified_evidence = _set(after, "verified_terminal_evidence_ids")
    except ValueError as e:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [f"INVALID_FIELD:{e.args[0]}"],
            "admit": False,
        }

    if not b_cut:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["PRIMITIVE_TERMINAL_CUT_REQUIRED"],
            "admit": False,
        }

    blockers = set(blocker_ids)
    links, link_errors = _links(
        causal_links,
        blocker_ids=blockers,
        before_cut=b_cut,
        verified_evidence_ids=verified_evidence,
    )
    if link_errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__INVALID_CAUSAL_BINDING",
            "errors": link_errors,
            "admit": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    regressions: list[str] = []
    if a_un > b_un:
        regressions.append("UNRESOLVED_ATOMIC_PREDICATES_INCREASED")
    if a_fam < b_fam:
        regressions.append("ACCEPTED_FAMILIES_DECREASED")
    if not b_dom.issubset(a_dom):
        regressions.append("OWNED_DOMAIN_REGRESSED")
    if not b_protected.issubset(a_protected):
        regressions.append("PROTECTED_TERMINAL_FACT_LOST")
    if not a_cut.issubset(b_cut):
        regressions.append("PRIMITIVE_TERMINAL_CUT_EXPANDED")

    reduced_cut = b_cut - a_cut
    linked_facts = {x["primitive_fact_id"] for x in links}
    unbound_reductions = sorted(reduced_cut - linked_facts)
    if unbound_reductions:
        regressions.append("UNBOUND_PRIMITIVE_CUT_REDUCTION")

    deltas = {
        "residual_reduction": b_un - a_un,
        "accepted_family_gain": a_fam - b_fam,
        "remaining_work_lower_bound_reduction": b_lb - a_lb,
        "new_proved_impossibilities": sorted(a_imp - b_imp),
        "owned_domain_gain": sorted(a_dom - b_dom),
        "primitive_cut_reduction": sorted(reduced_cut),
    }

    cut_effects = {x["effect"] for x in links}
    causally_qualified = bool(links) and (
        bool(reduced_cut)
        or bool(deltas["new_proved_impossibilities"])
        or deltas["remaining_work_lower_bound_reduction"] > 0
        or deltas["residual_reduction"] > 0
        or deltas["accepted_family_gain"] > 0
        or (
            bool(deltas["owned_domain_gain"])
            and bool(
                cut_effects
                & {
                    "DISCHARGES_PRIMITIVE_FACT",
                    "CREATES_VERIFIED_IMPLICATION",
                    "SUPPLIES_IDENTIFIABILITY_INFORMATION",
                    "BINDS_ROUTE_OR_SCOPE",
                }
            )
        )
    )

    admit = causally_qualified and not regressions
    if admit:
        status = "PASS__ADMIT_CAUSAL_CUT_DELTA"
    elif regressions:
        status = "FAIL_CLOSED__REGRESSION_OR_UNBOUND_CUT_CHANGE"
    else:
        status = "PASS__REJECT_NO_CAUSALLY_BOUND_TERMINAL_DELTA"

    return {
        "schema": SCHEMA,
        "status": status,
        "admit": admit,
        "blocker_ids": sorted(blockers),
        "causal_links": sorted(
            links,
            key=lambda x: (
                x["primitive_fact_id"],
                x["blocker_id"],
                x["edge_id"],
            ),
        ),
        "observed_terminal_delta": deltas,
        "regressions": regressions,
        "rules": [
            "EVERY_ADMITTED_CHANGE_MUST_BIND_TO_A_PRIMITIVE_FACT_ON_THE_CURRENT_TERMINAL_CUT",
            "EVERY_CAUSAL_BINDING_MUST_REFERENCE_VERIFIED_TERMINAL_EVIDENCE",
            "NO_OWNED_DOMAIN_EXPANSION_CREDIT_WITHOUT_BLOCKER_LINKED_CUT_EFFECT",
            "NO_UNBOUND_PRIMITIVE_CUT_REDUCTION",
            "PROTECTED_TERMINAL_FACTS_AND_OWNED_DOMAIN_MUST_BE_MONOTONE",
            "ZERO_TERMINAL_CREDIT_FROM_THIS_GATE_ITSELF",
        ],
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
