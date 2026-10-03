"""Fail-closed admission gate for proposed Brain architecture changes.

A proposal is admissible only if observed evidence shows at least one terminally
meaningful delta and no protected terminal regression. This module grants no
acceptance, capability, family, execution, or promotion authority by itself.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TERMINAL_DELTA_ADMISSION_GATE_V1"

def _int(m: Mapping[str,Any], key: str) -> int:
    v=m.get(key,0)
    if isinstance(v,bool) or not isinstance(v,int):
        raise ValueError(key)
    return v

def _set(m: Mapping[str,Any], key: str) -> set[str]:
    v=m.get(key,[])
    if not isinstance(v,list) or any(not isinstance(x,str) for x in v):
        raise ValueError(key)
    return set(v)

def evaluate(before: Mapping[str,Any], after: Mapping[str,Any], *, blocker_ids: list[str]) -> dict[str,Any]:
    if not blocker_ids or any(not isinstance(x,str) or not x for x in blocker_ids):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["BLOCKER_IDS_REQUIRED"],"admit":False}

    try:
        b_un=_int(before,"unresolved_atomic_predicates")
        a_un=_int(after,"unresolved_atomic_predicates")
        b_fam=_int(before,"accepted_families")
        a_fam=_int(after,"accepted_families")
        b_lb=_int(before,"minimum_remaining_work_lower_bound")
        a_lb=_int(after,"minimum_remaining_work_lower_bound")
        b_imp=_set(before,"proved_impossible_branches")
        a_imp=_set(after,"proved_impossible_branches")
        b_dom=_set(before,"formally_owned_domain_atoms")
        a_dom=_set(after,"formally_owned_domain_atoms")
        b_protected=_set(before,"protected_terminal_facts")
        a_protected=_set(after,"protected_terminal_facts")
    except ValueError as e:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":[f"INVALID_FIELD:{e.args[0]}"],"admit":False}

    regressions=[]
    if a_un>b_un: regressions.append("UNRESOLVED_ATOMIC_PREDICATES_INCREASED")
    if a_fam<b_fam: regressions.append("ACCEPTED_FAMILIES_DECREASED")
    if not b_dom.issubset(a_dom): regressions.append("OWNED_DOMAIN_REGRESSED")
    if not b_protected.issubset(a_protected): regressions.append("PROTECTED_TERMINAL_FACT_LOST")

    deltas={
        "residual_reduction": b_un-a_un,
        "accepted_family_gain": a_fam-b_fam,
        "remaining_work_lower_bound_reduction": b_lb-a_lb,
        "new_proved_impossibilities": sorted(a_imp-b_imp),
        "owned_domain_gain": sorted(a_dom-b_dom),
    }
    qualifies=(
        deltas["residual_reduction"]>0
        or deltas["accepted_family_gain"]>0
        or deltas["remaining_work_lower_bound_reduction"]>0
        or bool(deltas["new_proved_impossibilities"])
        or bool(deltas["owned_domain_gain"])
    )
    admit=qualifies and not regressions
    return {
        "schema":SCHEMA,
        "status":"PASS__ADMIT" if admit else ("FAIL_CLOSED__REGRESSION" if regressions else "PASS__REJECT_NO_TERMINAL_DELTA"),
        "admit":admit,
        "blocker_ids":sorted(set(blocker_ids)),
        "observed_terminal_delta":deltas,
        "regressions":regressions,
        "rules":[
            "NO_ARCHITECTURE_ADMISSION_WITHOUT_OBSERVED_TERMINAL_DELTA_OR_PROVED_IMPOSSIBILITY",
            "NO_ACCEPTANCE_FROM_STRUCTURAL_OR_SCHEDULING_PROGRESS_ALONE",
            "PROTECTED_TERMINAL_FACTS_MUST_BE_MONOTONE",
            "OWNED_DOMAIN_MUST_NOT_REGRESS",
            "ZERO_CREDIT_FROM_THIS_GATE_ITSELF",
        ],
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }
