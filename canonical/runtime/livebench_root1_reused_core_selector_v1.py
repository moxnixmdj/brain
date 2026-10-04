#!/usr/bin/env python3
"""Fail-closed minimum-byte semantic-core scheduler for LiveBench Root1.

This module grants no capability credit.  It only prevents the scheduler from
jumping to a much larger external acquisition while a smaller, already-executed
zero-spend carrier remains unfalsified for the narrower Root1 semantic-seed role.
"""
from __future__ import annotations

from typing import Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_ROOT1_REUSED_CORE_SELECTOR_V1"

_CARRIERS = (
    {
        "id": "QWEN3_5_4B_Q4_K_M_EXISTING_CARRIER",
        "model": "Qwen/Qwen3.5-4B",
        "bytes": 3013027808,
        "already_executed_zero_spend": True,
        "root1_status": "UNTESTED",
        "evidence": "canonical/capabilities/obsolescence/LOCAL_QWEN3_5_4B_TASK_B_FALSIFICATION_20260929_V1.json",
    },
    {
        "id": "QWEN3_5_9B_Q4_K_M_EXISTING_CARRIER",
        "model": "Qwen/Qwen3.5-9B",
        "bytes": 5060174144,
        "already_executed_zero_spend": True,
        "root1_status": "UNTESTED",
        "evidence": "canonical/capabilities/obsolescence/LOCAL_QWEN3_5_9B_BIOPHYSICS_TASK_B_FALSIFICATION_20260929_V1.json",
    },
    {
        "id": "SMAUG_MINI_BF16_EXTERNAL_ACQUISITION",
        "model": "abacusai/Smaug-Mini",
        "bytes": 55600000000,
        "already_executed_zero_spend": False,
        "root1_status": "PUBLIC_PRIOR_ONLY",
        "evidence": "canonical/governance/LIVEBENCH_ROOT1_OPEN_WEIGHT_DOMINANCE_UPDATE_V1.json",
    },
)


def ranked_root1_core_actions(
    root1_falsified_ids: Iterable[str] = (),
) -> list[dict]:
    """Return the byte-minimal admissible Root1 qualification ladder.

    Historical failures from other capability targets do not count as Root1
    falsifications.  Only exact carrier IDs supplied in root1_falsified_ids are
    removed from the ladder.
    """
    failed = frozenset(str(x) for x in root1_falsified_ids)
    actions: list[dict] = []
    for carrier in sorted(_CARRIERS, key=lambda item: int(item["bytes"])):
        if carrier["id"] in failed:
            continue
        action = (
            "REUSE_AND_QUALIFY_ROOT1"
            if carrier["already_executed_zero_spend"]
            else "ACQUIRE_AND_QUALIFY_ROOT1"
        )
        actions.append(
            {
                **carrier,
                "action": action,
                "acceptance_credit": 0,
                "capability_credit": 0,
                "ownership_credit": 0,
            }
        )
    return actions


def select_minimum_root1_core(
    root1_falsified_ids: Iterable[str] = (),
) -> dict:
    ladder = ranked_root1_core_actions(root1_falsified_ids)
    if not ladder:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "reason": "NO_UNFALSIFIED_CORE_ROUTE",
            "acceptance_credit": 0,
            "capability_credit": 0,
            "ownership_credit": 0,
        }
    selected = ladder[0]
    return {
        "schema": SCHEMA,
        "status": "QUALIFICATION_REQUIRED",
        "selected": selected,
        "remaining_ladder": [item["id"] for item in ladder[1:]],
        "semantic_seed_role_only": True,
        "fresh_terminal_reality_authorized": False,
        "promotion_authorized": False,
        "acceptance_credit": 0,
        "capability_credit": 0,
        "ownership_credit": 0,
    }


def run(args: dict | None = None, root=None) -> dict:
    values = (args or {}).get("root1_falsified_ids") or []
    return select_minimum_root1_core(values)
