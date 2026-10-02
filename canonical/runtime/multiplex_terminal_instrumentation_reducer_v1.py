"""Terminal reducer for same-parent-case multiplex instrumentation contracts.

This module DOES NOT generate terminal cases. Parent T0/T1/T2/T3 carriers must
emit behavior-specific instrumentation receipts on the exact parent case. The
reducer enforces that every load-bearing receipt passes its direct instrument
and its parent terminal acceptance, with no duplicate/cross-portfolio credit.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_MULTIPLEX_TERMINAL_INSTRUMENTATION_REDUCER_V1"

M0="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"
STRUCTURED="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
P1="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
P2="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
NATIVE="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001"
P3="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"

PARENTS={
    M0:("T0","T1","T2","T3"),
    STRUCTURED:("T0","T1"),
    P1:("T0","T2"),
    P2:("T1",),
    NATIVE:("T1",),
    P3:("T1","T3"),
}

INSTRUMENTATION_SCHEMA={
    M0:"M0_DIRECT_INSTRUMENTATION_V1",
    STRUCTURED:"STRUCTURED_METHOD_DIRECT_INSTRUMENTATION_V1",
    P1:"P1_CAUSAL_INTERVENTION_RESCUE_INSTRUMENTATION_V1",
    P2:"P2_PROFESSIONAL_QUALITY_INSTRUMENTATION_V1",
    NATIVE:"NATIVE_ARTIFACT_MECHANICAL_INSTRUMENTATION_V1",
    P3:"P3_GROUNDED_SYNTHESIS_INSTRUMENTATION_V1",
}


def bound_behavior_ids()->tuple[str,...]:
    return tuple(sorted(PARENTS))


def reduce_behavior(behavior_id:str, receipts:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if behavior_id not in PARENTS:
        raise ValueError("UNBOUND_MULTIPLEX_BEHAVIOR:"+str(behavior_id))
    if not isinstance(receipts,Sequence) or isinstance(receipts,(str,bytes)):
        raise ValueError("RECEIPTS_SEQUENCE_REQUIRED")

    allowed=set(PARENTS[behavior_id])
    expected_schema=INSTRUMENTATION_SCHEMA[behavior_id]
    errors:list[str]=[]
    seen:set[tuple[str,str]]=set()
    parent_counts=Counter()
    load_counts=Counter()
    total=0
    load_bearing=0

    for i,row in enumerate(receipts):
        total+=1
        if not isinstance(row,Mapping):
            errors.append(f"RECEIPT_NOT_OBJECT:{i}")
            continue
        if row.get("behavior_id")!=behavior_id:
            errors.append(f"BEHAVIOR_ID_MISMATCH:{i}")
        portfolio=row.get("portfolio")
        case_id=row.get("parent_case_id")
        if portfolio not in allowed:
            errors.append(f"PARENT_PORTFOLIO_INVALID:{i}:{portfolio}")
            continue
        if not isinstance(case_id,str) or not case_id:
            errors.append(f"PARENT_CASE_ID_INVALID:{i}")
            continue
        key=(str(portfolio),case_id)
        if key in seen:
            errors.append(f"DUPLICATE_PARENT_CASE:{portfolio}:{case_id}")
            continue
        seen.add(key)
        parent_counts[str(portfolio)]+=1

        applicable=row.get("load_bearing")
        if applicable is not True and applicable is not False:
            errors.append(f"LOAD_BEARING_FLAG_INVALID:{i}")
            continue
        if applicable is False:
            if row.get("instrumentation_pass") not in (None,False):
                errors.append(f"NON_LOAD_BEARING_CASE_CANNOT_SUPPLY_POSITIVE_INSTRUMENTATION_CREDIT:{i}")
            continue

        load_bearing+=1
        load_counts[str(portfolio)]+=1
        if row.get("instrumentation_schema")!=expected_schema:
            errors.append(f"INSTRUMENTATION_SCHEMA_MISMATCH:{i}")
        if row.get("instrumentation_pass") is not True:
            errors.append(f"DIRECT_INSTRUMENTATION_FAIL:{i}")
        if row.get("parent_terminal_pass") is not True:
            errors.append(f"PARENT_TERMINAL_ACCEPTANCE_FAIL:{i}")
        if row.get("cross_behavior_score_inheritance") is not False:
            errors.append(f"CROSS_BEHAVIOR_SCORE_INHERITANCE_NOT_FALSE:{i}")
        if row.get("case_replayed_for_tuning") is not False:
            errors.append(f"TUNING_REPLAY_NOT_FALSE:{i}")

    # Fail closed against vacuous "proof": every declared parent portfolio must
    # contribute at least one load-bearing same-case observation.
    missing=[p for p in PARENTS[behavior_id] if load_counts[p]==0]
    if missing:
        errors.append("MISSING_LOAD_BEARING_PARENT_COVERAGE:"+",".join(missing))

    passed=not errors and load_bearing>0
    return {
        "schema":SCHEMA,
        "behavior_id":behavior_id,
        "status":"PASS" if passed else "FAIL_CLOSED",
        "pass":passed,
        "receipt_count":total,
        "load_bearing_receipt_count":load_bearing,
        "parent_receipt_counts":dict(sorted(parent_counts.items())),
        "load_bearing_parent_counts":dict(sorted(load_counts.items())),
        "required_parent_portfolios":list(PARENTS[behavior_id]),
        "expected_instrumentation_schema":expected_schema,
        "no_standalone_terminal_population_generated":True,
        "terminal_result":True,
        "capability_credit_delta":"DEFER_TO_TERMINAL_REDUCER",
        "family_credit_delta":"DEFER_TO_TERMINAL_REDUCER",
        "errors":sorted(set(errors)),
    }


def make_receipt(
    *,
    behavior_id:str,
    portfolio:str,
    parent_case_id:str,
    load_bearing:bool,
    instrumentation_pass:bool|None,
    parent_terminal_pass:bool,
)->dict[str,Any]:
    if behavior_id not in PARENTS:
        raise ValueError("UNBOUND_MULTIPLEX_BEHAVIOR:"+str(behavior_id))
    if portfolio not in PARENTS[behavior_id]:
        raise ValueError("PARENT_PORTFOLIO_INVALID")
    if not isinstance(parent_case_id,str) or not parent_case_id:
        raise ValueError("PARENT_CASE_ID_REQUIRED")
    if load_bearing is False and instrumentation_pass is True:
        raise ValueError("NON_LOAD_BEARING_POSITIVE_CREDIT_FORBIDDEN")
    return {
        "behavior_id":behavior_id,
        "portfolio":portfolio,
        "parent_case_id":parent_case_id,
        "load_bearing":bool(load_bearing),
        "instrumentation_schema":INSTRUMENTATION_SCHEMA[behavior_id] if load_bearing else None,
        "instrumentation_pass":instrumentation_pass if load_bearing else None,
        "parent_terminal_pass":bool(parent_terminal_pass),
        "cross_behavior_score_inheritance":False,
        "case_replayed_for_tuning":False,
    }
