#!/usr/bin/env python3
"""Verified skills do not compose just because each one verified.

THE DEFECT THIS CLOSES
----------------------
Each stored rule is verified against the demonstration that taught it. Nothing in the store
relates two rules to each other. Measured 2026-11-12, with two rules that are each accepted:

    teach A:  `x <= 10` -> `x < 10`      crystallized: True
    teach B:  `x < 10`  -> `x <= 10`     crystallized: True

    step 1: 'return x <= 10' -> 'return x < 10'
    step 2: 'return x < 10'  -> 'return x <= 10'
    started: 'return x <= 10'
    ended:   'return x <= 10'      net change: none

Both applications are individually correct and the sequence is a no-op. `recall_and_apply_verified`
cannot catch this: it verifies each candidate at each step, and each step passes. The check is
local, so a local check cannot see a global revert.

WHAT THIS MODULE DOES
---------------------
`verify_sequence(source, rules)` applies the rules in order and records, per step, whether the
step changed anything and whether it changed the text BACK to something an earlier state
already was:

    PASS        every step changed the text, and no step returned to an earlier state
    FAIL        a step reverted to an earlier state (the sequence undoes itself)
    NO_CHANGE   some step was a no-op, so a rule was counted that did nothing
    UNDEFINED   the sequence is empty, or a rule could not be read

A no-op is not a pass. A revert is not a pass. This is a *sequence* property and is separate
from, and weaker than, whole-task correctness -- see `whole_task_correctness_proved`, which
stays false everywhere.

Authority: NONE. No capability is claimed; nothing here is independent verification.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SKILL_SEQUENCE_VERIFY_V1"

PASS = "PASS"
FAIL = "FAIL"
NO_CHANGE = "NO_CHANGE"
UNDEFINED = "UNDEFINED"


def _sha_or_none(text: str | None) -> str | None:
    if text is None:
        return None
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_sequence(
    source: str,
    rules: Sequence[Mapping[str, Any]],
    *,
    apply: Callable[[str, Mapping[str, Any]], str | None] | None = None,
) -> dict[str, Any]:
    """Apply `rules` in order to `source` and say whether the SEQUENCE is meaningful.

    Returns a verdict, the per-step trace, and the text. The trace is the evidence: a PASS on
    one rule says nothing about a PASS on the sequence of two.
    """
    if apply is None:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
            apply_crystallized_code_rule as apply,
        )
    if not rules:
        return {"verdict": UNDEFINED, "reason": "EMPTY_SEQUENCE",
                "steps": [], "source": source, "result": source}

    text = source
    seen: dict[str, int] = {_sha_or_none(source): 0}     # state -> which step produced it
    steps: list[dict[str, Any]] = []

    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, Mapping):
            return {"verdict": UNDEFINED, "reason": f"RULE_NOT_A_MAPPING:step{index}",
                    "steps": steps, "source": source, "result": text}
        try:
            produced = apply(text, rule)
        except Exception as exc:                          # a raising rule is a failed step
            steps.append({"step": index, "outcome": "RAISED",
                          "reason": f"{type(exc).__name__}:{exc}"[:160]})
            return {"verdict": FAIL, "reason": f"STEP_RAISED:step{index}",
                    "steps": steps, "source": source, "result": text}

        if produced is None or produced == text:
            steps.append({"step": index, "outcome": "NO_CHANGE",
                          "skill_id": str(rule.get("skill_id") or "")[:22]})
            return {"verdict": NO_CHANGE, "reason": f"STEP_DID_NOTHING:step{index}",
                    "steps": steps, "source": source, "result": text}

        key = _sha_or_none(produced)
        if key in seen:
            steps.append({"step": index, "outcome": "REVERTED",
                          "skill_id": str(rule.get("skill_id") or "")[:22],
                          "to_state_of_step": seen[key]})
            return {"verdict": FAIL, "reason": f"STEP_REVERTED_EARLIER_STATE:step{index}",
                    "steps": steps, "source": source, "result": produced,
                    "reverted_to_step": seen[key]}

        seen[key] = index
        steps.append({"step": index, "outcome": "CHANGED",
                      "skill_id": str(rule.get("skill_id") or "")[:22]})
        text = produced

    return {"verdict": PASS, "reason": None, "steps": steps,
            "source": source, "result": text, "steps_applied": len(steps)}


def verify_all_pairs(
    source: str,
    rules: Sequence[Mapping[str, Any]],
    *,
    apply: Callable[[str, Mapping[str, Any]], str | None] | None = None,
) -> dict[str, Any]:
    """Every ordered pair. A pair that reverts or does nothing is an interference witness."""
    if apply is None:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
            apply_crystallized_code_rule as apply,
        )
    witnesses: list[dict[str, Any]] = []
    examined = 0
    for i, first in enumerate(rules):
        for j, second in enumerate(rules):
            if i >= j:
                continue
            examined += 1
            for order in ((first, second), (second, first)):
                outcome = verify_sequence(source, order, apply=apply)
                if outcome["verdict"] in (FAIL, NO_CHANGE):
                    witnesses.append({
                        "verdict": outcome["verdict"],
                        "reason": outcome["reason"],
                        "first": str(order[0].get("skill_id") or "")[:22],
                        "second": str(order[1].get("skill_id") or "")[:22],
                        "steps": outcome["steps"],
                    })
    counts = {PASS: 0, FAIL: 0, NO_CHANGE: 0, UNDEFINED: 0}
    for witness in witnesses:
        counts[witness["verdict"]] += 1
    return {"schema": SCHEMA, "authority": "NONE", "pairs_examined": examined,
            "witnesses": witnesses, "witness_counts": counts,
            "interference_found": bool(witnesses)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-json", default=None,
                        help="file holding {source: str, rules: [rule, ...]}")
    parser.add_argument("--pairs", action="store_true", help="check every ordered pair")
    args = parser.parse_args(argv)

    if not args.from_json:
        parser.error("--from-json is required (a {source, rules} document)")

    payload = json.loads(open(args.from_json, encoding="utf-8").read())
    source = str(payload.get("source") or "")
    rules = list(payload.get("rules") or [])

    if args.pairs:
        report = verify_all_pairs(source, rules)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if report["interference_found"] else 0

    outcome = verify_sequence(source, rules)
    print(json.dumps(outcome, indent=2, sort_keys=True))
    return 0 if outcome["verdict"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
