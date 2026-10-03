"""Causal-cut admission gate for proposed Brain architecture changes.

V2 tightens terminal-delta V1 by requiring every admissible change to bind to
the current primitive terminal cut and at least one unresolved terminal blocker.
It is meta-governance only and grants no acceptance, capability, family,
execution, or promotion credit.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_CAUSAL_CUT_ADMISSION_GATE_V2"


def _int(m: Mapping[str, Any], key: str) -> int:
    v = m.get(key)
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(key)
    return v


def _set(m: Mapping[str, Any], key: str) -> set[str]:
    v = m.get(key)
    if not isinstance(v, list) or any(not isinstance(x, str) or not x for x in v):
        raise ValueError(key)
    return set(v)


def _links(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("causal_links")
    out: list[Mapping[str, Any]] = []
    for i, link in enumerate(value):
        if not isinstance(link, Mapping):
            raise ValueError(f"causal_links[{i}]")
        blocker = link.get("blocker_id")
        facts = link.get("primitive_fact_ids")
        evidence = link.get("evidence_ids")
        if not isinstance(blocker, str) or not blocker:
            raise ValueError(f"causal_links[{i}].blocker_id")
        if not isinstance(facts, list) or not facts or any(not isinstance(x, str) or not x for x in facts):
            raise ValueError(f"causal_links[{i}].primitive_fact_ids")
        if not isinstance(evidence, list) or not evidence or any(not isinstance(x, str) or not x for x in evidence):
            raise ValueError(f"causal_links[{i}].evidence_ids")
        out.append(link)
    return out


def evaluate(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    blocker_ids: list[str],
    primitive_to_blockers: Mapping[str, list[str]],
    causal_links: list[Mapping[str, Any]],
) -> dict[str, Any]:
    if not blocker_ids or any(not isinstance(x, str) or not x for x in blocker_ids):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["BLOCKER_IDS_REQUIRED"], "admit": False}

    try:
        b_un = _int(before, "unresolved_atomic_predicates")
        a_un = _int(after, "unresolved_atomic_predicates")
        b_fam = _int(before, "accepted_families")
        a_fam = _int(after, "accepted_families")
        b_lb = _int(before, "minimum_remaining_work_lower_bound")
        a_lb = _int(after, "minimum_remaining_work_lower_bound")
        b_prim = _set(before, "unresolved_primitive_facts")
        a_prim = _set(after, "unresolved_primitive_facts")
        b_imp = _set(before, "proved_impossible_branches")
        a_imp = _set(after, "proved_impossible_branches")
        b_edges = _set(before, "verified_implication_edges")
        a_edges = _set(after, "verified_implication_edges")
        b_dom = _set(before, "formally_owned_domain_atoms")
        a_dom = _set(after, "formally_owned_domain_atoms")
        b_protected = _set(before, "protected_terminal_facts")
        a_protected = _set(after, "protected_terminal_facts")
        links = _links(causal_links)
    except ValueError as e:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": [f"INVALID_FIELD:{e.args[0]}"], "admit": False}

    blocker_set = set(blocker_ids)
    mapping: dict[str, set[str]] = {}
    try:
        for fact, blockers in primitive_to_blockers.items():
            if not isinstance(fact, str) or not fact:
                raise ValueError("primitive_to_blockers.key")
            if not isinstance(blockers, list) or not blockers or any(not isinstance(x, str) or not x for x in blockers):
                raise ValueError(f"primitive_to_blockers[{fact}]")
            mapping[fact] = set(blockers)
    except (AttributeError, ValueError) as e:
        key = e.args[0] if e.args else "primitive_to_blockers"
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": [f"INVALID_FIELD:{key}"], "admit": False}

    regressions: list[str] = []
    if a_un > b_un:
        regressions.append("UNRESOLVED_ATOMIC_PREDICATES_INCREASED")
    if a_fam < b_fam:
        regressions.append("ACCEPTED_FAMILIES_DECREASED")
    if a_lb > b_lb:
        regressions.append("MINIMUM_REMAINING_WORK_LOWER_BOUND_INCREASED")
    if not a_prim.issubset(b_prim):
        regressions.append("UNRESOLVED_PRIMITIVE_FACTS_INCREASED")
    if not b_edges.issubset(a_edges):
        regressions.append("VERIFIED_IMPLICATION_EDGE_LOST")
    if not b_dom.issubset(a_dom):
        regressions.append("OWNED_DOMAIN_REGRESSED")
    if not b_protected.issubset(a_protected):
        regressions.append("PROTECTED_TERMINAL_FACT_LOST")

    closed_primitives = b_prim - a_prim
    new_impossibilities = a_imp - b_imp
    new_edges = a_edges - b_edges
    owned_domain_gain = a_dom - b_dom

    valid_linked_facts: set[str] = set()
    linked_edges: set[str] = set()
    linked_impossibilities: set[str] = set()
    linked_owned_atoms: set[str] = set()
    link_errors: list[str] = []

    for i, link in enumerate(links):
        blocker = str(link["blocker_id"])
        if blocker not in blocker_set:
            link_errors.append(f"LINK_{i}_BLOCKER_NOT_DECLARED")
            continue
        facts = set(link["primitive_fact_ids"])
        for fact in facts:
            if fact not in b_prim:
                link_errors.append(f"LINK_{i}_FACT_NOT_IN_CURRENT_CUT:{fact}")
                continue
            if blocker not in mapping.get(fact, set()):
                link_errors.append(f"LINK_{i}_BLOCKER_NOT_BOUND_TO_FACT:{fact}")
                continue
            valid_linked_facts.add(fact)

        edge_ids = link.get("implication_edge_ids", [])
        impossibilities = link.get("impossible_branch_ids", [])
        owned_atoms = link.get("owned_domain_atom_ids", [])
        for key, values in (
            ("implication_edge_ids", edge_ids),
            ("impossible_branch_ids", impossibilities),
            ("owned_domain_atom_ids", owned_atoms),
        ):
            if not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values):
                link_errors.append(f"LINK_{i}_INVALID_{key}")
                values = []
            if key == "implication_edge_ids":
                linked_edges.update(values)
            elif key == "impossible_branch_ids":
                linked_impossibilities.update(values)
            else:
                linked_owned_atoms.update(values)

    unlinked_closed = closed_primitives - valid_linked_facts
    unlinked_edges = new_edges - linked_edges
    unlinked_impossibilities = new_impossibilities - linked_impossibilities
    unlinked_owned = owned_domain_gain - linked_owned_atoms

    if unlinked_closed:
        link_errors.append("UNLINKED_CLOSED_PRIMITIVES:" + ",".join(sorted(unlinked_closed)))
    if unlinked_edges:
        link_errors.append("UNLINKED_NEW_EDGES:" + ",".join(sorted(unlinked_edges)))
    if unlinked_impossibilities:
        link_errors.append("UNLINKED_NEW_IMPOSSIBILITIES:" + ",".join(sorted(unlinked_impossibilities)))
    if owned_domain_gain and unlinked_owned:
        link_errors.append("UNLINKED_OWNED_DOMAIN_GAIN:" + ",".join(sorted(unlinked_owned)))

    lower_bound_reduction = b_lb - a_lb
    aggregate_progress = (b_un - a_un) > 0 or (a_fam - b_fam) > 0
    causal_cut_progress = bool(closed_primitives or new_impossibilities or new_edges)
    if lower_bound_reduction > 0 and not causal_cut_progress:
        link_errors.append("LOWER_BOUND_REDUCTION_WITHOUT_CAUSAL_CUT_EVENT")
    if aggregate_progress and not causal_cut_progress:
        link_errors.append("AGGREGATE_PROGRESS_WITHOUT_CAUSAL_CUT_EVENT")
    if owned_domain_gain and not causal_cut_progress:
        link_errors.append("OWNED_DOMAIN_GAIN_WITHOUT_CAUSAL_CUT_EVENT")

    qualifies = causal_cut_progress and not link_errors
    admit = qualifies and not regressions

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ADMIT_CAUSAL_CUT_DELTA"
            if admit
            else "FAIL_CLOSED__REGRESSION"
            if regressions
            else "PASS__REJECT_UNBOUND_OR_NO_CAUSAL_CUT_DELTA"
        ),
        "admit": admit,
        "blocker_ids": sorted(blocker_set),
        "observed_terminal_delta": {
            "closed_primitive_facts": sorted(closed_primitives),
            "residual_reduction": b_un - a_un,
            "accepted_family_gain": a_fam - b_fam,
            "remaining_work_lower_bound_reduction": lower_bound_reduction,
            "new_verified_implication_edges": sorted(new_edges),
            "new_proved_impossibilities": sorted(new_impossibilities),
            "owned_domain_gain": sorted(owned_domain_gain),
        },
        "regressions": regressions,
        "causal_link_errors": link_errors,
        "rules": [
            "EVERY_ADMITTED_DELTA_MUST_BIND_TO_CURRENT_PRIMITIVE_TERMINAL_CUT_AND_DECLARED_BLOCKER",
            "OWNED_DOMAIN_EXPANSION_ALONE_IS_NEVER_SUFFICIENT",
            "AGGREGATE_COUNTER_MOVEMENT_WITHOUT_A_CAUSAL_CUT_EVENT_IS_NEVER_SUFFICIENT",
            "NO_ACCEPTANCE_FROM_STRUCTURAL_OR_SCHEDULING_PROGRESS_ALONE",
            "PROTECTED_TERMINAL_FACTS_AND_VERIFIED_EDGES_MUST_BE_MONOTONE",
            "ZERO_CREDIT_FROM_THIS_GATE_ITSELF",
        ],
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
