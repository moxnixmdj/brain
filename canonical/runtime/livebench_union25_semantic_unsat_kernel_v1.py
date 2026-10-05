#!/usr/bin/env python3
"""Sound semantic UNSAT kernel for the frozen LiveBench public union25 surface.

This composes three independently motivated proof layers:
1. the repaired Active15 slot contradictions;
2. exact new union25 pair/slot contradictions;
3. strengthened mandatory frequency floors from structurally separated literals.

Every emitted record proves that the supplied contract subset cannot be jointly
satisfied. Returning no records means UNKNOWN, never SAT.

No terminal row, hidden kwarg, comparator response, case frequency, or target
score is consumed.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as active15
from canonical.runtime import livebench_union25_mandatory_loss_v1 as mandatory_loss
from canonical.runtime import livebench_union25_mandatory_footprint_v2 as footprint

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_SEMANTIC_UNSAT_KERNEL_V1"
REPEAT = "combination:repeat_prompt"


def _ids(contracts: Sequence[Mapping[str, Any]]) -> list[str]:
    ids = [str(c.get("instruction_id") or "") for c in contracts]
    if any(not x for x in ids):
        raise ValueError("INSTRUCTION_ID_REQUIRED")
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_INSTRUCTION_ID")
    return ids


def _repeat_prefix(contracts: Sequence[Mapping[str, Any]]) -> str | None:
    for c in contracts:
        if str(c.get("instruction_id") or "") == REPEAT:
            return str((c.get("slots") or {}).get("prompt_to_repeat") or "")
    return None


def _active15_core_ids(reason: str, present: set[str]) -> list[str]:
    if reason == "NTH_FIRST_WORD_IS_FORBIDDEN_WORD":
        candidates = {
            "length_constraints:nth_paragraph_first_word",
            "keywords:forbidden_words",
        }
    elif reason.startswith("MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:"):
        candidates = {
            "startend:end_checker",
            "keywords:forbidden_words",
        }
    elif reason == "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE":
        candidates = {"length_constraints:number_sentences"}
    else:
        # Fail closed on provenance granularity: the reason remains sound for
        # the supplied subset, but we do not invent a smaller minimal core.
        candidates = set(present)
    return sorted(candidates & present)


def prove_unsat(
    contracts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [dict(c) for c in contracts]
    ids = _ids(rows)
    present = set(ids)
    evidence: list[dict[str, Any]] = []

    for reason in active15.hard_unsat_reasons(rows):
        evidence.append({
            "source": active15.SCHEMA,
            "rule_id": reason,
            "core_instruction_ids": _active15_core_ids(reason, present),
        })

    ml = mandatory_loss.derive(
        rows,
        prompt_to_repeat=_repeat_prefix(rows),
    )
    for rule in ml.get("mandatory_loss_rules") or []:
        evidence.append({
            "source": mandatory_loss.SCHEMA,
            "rule_id": str(rule["rule_id"]),
            "core_instruction_ids": sorted(
                str(x) for x in rule.get("checker_ids") or []
            ),
            "details": {
                k: v
                for k, v in rule.items()
                if k not in {"proof"}
            },
        })

    for rule in footprint.proved_upper_bound_losses(rows):
        # The strengthened floor is derived only from obligations present in
        # this exact subset. Use the whole subset as the sound core rather than
        # pretending a smaller minimal core that was not proved.
        evidence.append({
            "source": footprint.SCHEMA,
            "rule_id": str(rule["rule_id"]),
            "core_instruction_ids": sorted(ids),
            "details": dict(rule),
        })

    # Stable deduplication by proof identity and declared core.
    dedup: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    for item in evidence:
        key = (
            str(item["source"]),
            str(item["rule_id"]),
            tuple(item["core_instruction_ids"]),
        )
        dedup[key] = item
    ordered = [dedup[k] for k in sorted(dedup)]

    return {
        "schema": SCHEMA,
        "status": "PROVED_UNSAT" if ordered else "UNKNOWN__NO_SOUND_UNSAT_CERTIFICATE",
        "instruction_ids": sorted(ids),
        "hard_unsat_evidence": ordered,
        "hard_unsat_evidence_count": len(ordered),
        "jointly_unsatisfiable": bool(ordered),
        "complete_unsat_kernel": False,
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "terminal_case_ids_read": 0,
        "case_frequencies_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return prove_unsat(list((args or {}).get("contracts") or []))


if __name__ == "__main__":
    import json
    import sys
    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
