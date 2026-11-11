#!/usr/bin/env python3
"""Fail-closed population congruence guard for comparator-derived benchmark bars.

A score threshold inherited from comparator C on population P_C is admissible
for subject S only when S is evaluated on that same population, or a separately
proved transfer/worst-case theorem makes the population substitution valid.

Matching counts, task labels, release labels, or scorer code are not population
identity proofs.
"""
from __future__ import annotations
from typing import Any

SCHEMA="PROJECT_BRAIN_LIVEBENCH_BAR_POPULATION_CONGRUENCE_GUARD_V1"

def adjudicate(args: dict[str,Any] | None=None) -> dict[str,Any]:
    a=args or {}
    comparator_population=str(a.get("comparator_population_id") or "").strip()
    subject_population=str(a.get("subject_population_id") or "").strip()
    exact_identity_proved=bool(a.get("exact_population_identity_proved",False))
    transfer_theorem_proved=bool(a.get("score_transfer_theorem_proved",False))
    worst_case_theorem_proved=bool(a.get("official_population_worst_case_bound_proved",False))
    same_counts=bool(a.get("same_counts",False))
    same_task_labels=bool(a.get("same_task_labels",False))

    if exact_identity_proved:
        if not comparator_population or not subject_population:
            return {
                "schema":SCHEMA,"status":"FAIL_CLOSED",
                "reason":"IDENTITY_CLAIM_REQUIRES_CONTENT_ADDRESSED_POPULATION_IDS",
                "threshold_transfer_authorized":False,
            }
        if comparator_population != subject_population:
            return {
                "schema":SCHEMA,"status":"FAIL_CLOSED",
                "reason":"IDENTITY_CLAIM_CONTRADICTS_POPULATION_IDS",
                "threshold_transfer_authorized":False,
            }
        return {
            "schema":SCHEMA,"status":"PASS_SAME_POPULATION",
            "reason":"SUBJECT_AND_COMPARATOR_SCORE_THE_SAME_CONTENT_ADDRESSED_POPULATION",
            "threshold_transfer_authorized":True,
            "authority_basis":"EXACT_POPULATION_IDENTITY",
        }

    if transfer_theorem_proved:
        return {
            "schema":SCHEMA,"status":"PASS_PROVED_SCORE_TRANSFER",
            "reason":"A_SEPARATE_SCORE_TRANSFER_THEOREM_AUTHORIZES_POPULATION_SUBSTITUTION",
            "threshold_transfer_authorized":True,
            "authority_basis":"SCORE_TRANSFER_THEOREM",
        }

    if worst_case_theorem_proved:
        return {
            "schema":SCHEMA,"status":"PASS_OFFICIAL_POPULATION_WORST_CASE_BOUND",
            "reason":"SUBJECT_LOWER_BOUND_WAS_PROVED_OVER_THE_UNRESOLVED_OFFICIAL_POPULATION_CLASS",
            "threshold_transfer_authorized":True,
            "authority_basis":"WORST_CASE_OFFICIAL_POPULATION_THEOREM",
        }

    return {
        "schema":SCHEMA,
        "status":"BLOCKED_POPULATION_CONGRUENCE_UNPROVED",
        "reason":"COMPARATOR_BAR_AND_SUBJECT_SCORE_ARE_NOT_PROVED_TO_SHARE_A_POPULATION",
        "threshold_transfer_authorized":False,
        "same_counts_not_sufficient":same_counts,
        "same_task_labels_not_sufficient":same_task_labels,
        "required_one_of":[
            "EXACT_CONTENT_ADDRESSED_POPULATION_IDENTITY",
            "PROVED_SCORE_TRANSFER_THEOREM",
            "PROVED_WORST_CASE_BOUND_OVER_THE_OFFICIAL_POPULATION_CLASS",
        ],
    }

def run(args:dict[str,Any],root=None)->dict[str,Any]:
    return adjudicate(args)
