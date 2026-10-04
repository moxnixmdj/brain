#!/usr/bin/env python3
"""Second fail-closed slot-feasibility layer for frozen legacy-15 LiveBench.

V2 is additive over V1. It certifies one additional hard-UNSAT class derived
only from the pinned public generator and checker semantics:

  NumberOfSentences(num_sentences=1, relation="less than")
  + EndChecker(one of the two frozen generator end phrases)

The end checker forces a non-empty English question ending. Under the pinned
Punkt English sentence tokenizer each frozen end phrase contributes at least
one sentence, while the sentence checker requires strictly fewer than one.

No terminal row, hidden kwargs, target score, response, or case frequency is
read here. An empty UNSAT-reason set still means UNKNOWN, never SAT.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as v1
from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_SLOT_FEASIBILITY_V2"
PINNED_LIVEBENCH_COMMIT = v1.PINNED_LIVEBENCH_COMMIT
PINNED_INSTRUCTIONS_BLOB = v1.PINNED_INSTRUCTIONS_BLOB
PINNED_REGISTRY_BLOB = v1.PINNED_REGISTRY_BLOB
HISTORICAL_GENERATOR_BLOB = v1.HISTORICAL_GENERATOR_BLOB

SENTENCE = "length_constraints:number_sentences"
END = v1.END

# Exact public generator options in the pinned instructions.py.
PUBLIC_END_PHRASES = frozenset({
    "Any other questions?",
    "Is there anything else I can help with?",
})


def _slots_by_id(contracts: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        iid = str(contract["instruction_id"])
        if iid in out:
            raise ValueError("DUPLICATE_INSTRUCTION_ID")
        out[iid] = dict(contract.get("slots") or {})
    return out


def hard_unsat_reasons(contracts: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return only checker-semantic contradictions that are actually proved."""
    reasons = list(v1.hard_unsat_reasons(contracts))
    by_id = _slots_by_id(contracts)

    if SENTENCE in by_id and END in by_id:
        ss = by_id[SENTENCE]
        relation = str(ss.get("relation") or "")
        try:
            threshold = int(ss.get("num_sentences"))
        except (TypeError, ValueError):
            threshold = None
        end_phrase = str(by_id[END].get("end_phrase") or "").strip()

        # The historical generator draws sentence thresholds from 1..20 and
        # the exact end phrase from PUBLIC_END_PHRASES. At threshold 1,
        # "less than" requires zero Punkt sentences. Either frozen end phrase
        # necessarily yields >=1 under the pinned English Punkt checker.
        if (
            relation == "less than"
            and threshold == 1
            and end_phrase in PUBLIC_END_PHRASES
        ):
            reasons.append("LESS_THAN_ONE_SENTENCE_WITH_MANDATORY_PUBLIC_END_PHRASE")

    # Preserve deterministic ordering and avoid duplicate inherited reasons.
    return tuple(dict.fromkeys(reasons))


def classify_visible_contracts(
    contracts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    ids = tuple(str(c["instruction_id"]) for c in contracts)
    if len(ids) != len(set(ids)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_DUPLICATE_ID",
            "instruction_ids": sorted(ids),
            "hard_unsat_reasons": [],
            "terminal_data_used": False,
            "hidden_kwargs_used": False,
            "acceptance_credit": False,
        }
    if not archetypes.compatible(ids):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_ID_CONFLICT",
            "instruction_ids": sorted(ids),
            "hard_unsat_reasons": [],
            "terminal_data_used": False,
            "hidden_kwargs_used": False,
            "acceptance_credit": False,
        }

    reasons = hard_unsat_reasons(contracts)
    return {
        "schema": SCHEMA,
        "status": (
            "PROVED_UNSAT"
            if reasons
            else "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED"
        ),
        "instruction_ids": sorted(ids),
        "archetype": archetypes.archetype(ids),
        "hard_unsat_reasons": list(reasons),
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
    }


def prove_sentence_end_unsat() -> dict[str, Any]:
    contracts = [
        {
            "instruction_id": SENTENCE,
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": END,
            "slots": {"end_phrase": "Any other questions?"},
        },
    ]
    out = classify_visible_contracts(contracts)
    reason = "LESS_THAN_ONE_SENTENCE_WITH_MANDATORY_PUBLIC_END_PHRASE"
    if out["status"] != "PROVED_UNSAT" or reason not in out["hard_unsat_reasons"]:
        raise RuntimeError("SENTENCE_END_UNSAT_NOT_CERTIFIED")
    return {
        "schema": SCHEMA,
        "status": "PASS__THIRD_PUBLIC_SLOT_UNSAT_CLASS_CERTIFIED",
        "instruction_ids": out["instruction_ids"],
        "hard_unsat_reasons": out["hard_unsat_reasons"],
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    return prove_sentence_end_unsat()


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, sort_keys=True))
