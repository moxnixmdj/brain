#!/usr/bin/env python3
"""Exact new mandatory-loss rules introduced by the LiveBench union25 delta.

This module does not claim complete union25 closure. It derives only semantic
incompatibilities that follow directly from the pinned checker semantics and
visible recovered contract parameters. Each emitted pair proves that at least
one checker in the pair must fail; no terminal row or hidden metadata is used.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_MANDATORY_LOSS_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"

REPEAT = "combination:repeat_prompt"
NO_COMMA = "punctuation:no_comma"
SECTIONS = "detectable_format:multiple_sections"
ENGLISH_CAPITAL = "change_case:english_capital"
ENGLISH_LOWERCASE = "change_case:english_lowercase"
CAPITAL_FREQUENCY = "change_case:capital_word_frequency"


def _index(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for contract in contracts:
        iid = str(contract.get("instruction_id") or "")
        if iid:
            if iid in out:
                raise ValueError("DUPLICATE_INSTRUCTION_ID:" + iid)
            out[iid] = contract
    return out


def derive(
    contracts: Sequence[Mapping[str, Any]],
    *,
    prompt_to_repeat: str | None = None,
) -> dict[str, Any]:
    by_id = _index(contracts)
    losses: list[dict[str, Any]] = []

    if REPEAT in by_id and NO_COMMA in by_id and prompt_to_repeat is not None and "," in prompt_to_repeat:
        losses.append({
            "rule_id": "REPEAT_PREFIX_COMMA_VS_NO_COMMA",
            "checker_ids": [REPEAT, NO_COMMA],
            "minimum_pair_loss": 1,
            "proof": (
                "RepeatPromptThenAnswer requires the stripped response to start with the "
                "stripped prompt_to_repeat case-insensitively. A comma present in that "
                "required prefix is therefore present in every repeat-satisfying response; "
                "CommaChecker rejects every response containing a comma."
            ),
        })

    section = by_id.get(SECTIONS)
    if section is not None:
        slots = dict(section.get("slots") or {})
        splitter = str(slots.get("section_spliter") or "")
        n = int(slots.get("num_sections") or 0)
        if splitter not in {"Section", "SECTION"}:
            raise ValueError("OUT_OF_FROZEN_GENERATOR_SECTION_SPLITTER:" + splitter)
        if n <= 0:
            raise ValueError("INVALID_FROZEN_SECTION_COUNT")

        if ENGLISH_LOWERCASE in by_id:
            losses.append({
                "rule_id": "LOWERCASE_ENGLISH_VS_SECTION_HEADING_CASE",
                "checker_ids": [ENGLISH_LOWERCASE, SECTIONS],
                "minimum_pair_loss": 1,
                "proof": (
                    "SectionChecker requires at least one literal case-sensitive heading "
                    f"{splitter} <digit>. Both frozen splitters contain uppercase cased "
                    "letters, while LowercaseLettersEnglishChecker requires value.islower()."
                ),
            })

        if ENGLISH_CAPITAL in by_id and splitter == "Section":
            losses.append({
                "rule_id": "UPPERCASE_ENGLISH_VS_MIXED_CASE_SECTION_HEADING",
                "checker_ids": [ENGLISH_CAPITAL, SECTIONS],
                "minimum_pair_loss": 1,
                "proof": (
                    "SectionChecker with splitter Section requires the mixed-case literal "
                    "Section before each section index. Any response containing that literal "
                    "has lowercase cased letters, so value.isupper() is false."
                ),
            })

        cap = by_id.get(CAPITAL_FREQUENCY)
        if cap is not None and splitter == "SECTION":
            cslots = dict(cap.get("slots") or {})
            relation = str(cslots.get("capital_relation") or "")
            threshold = int(cslots.get("capital_frequency") or 0)
            if relation == "less than" and threshold > 0 and n >= threshold:
                losses.append({
                    "rule_id": "CAPITAL_WORD_UPPER_BOUND_VS_UPPERCASE_SECTION_FLOOR",
                    "checker_ids": [CAPITAL_FREQUENCY, SECTIONS],
                    "minimum_pair_loss": 1,
                    "mandatory_capital_word_floor": n,
                    "strict_upper_bound": threshold,
                    "proof": (
                        "Every section delimiter matched by SectionChecker contains the token "
                        "SECTION. Pinned NLTK word_tokenize exposes each SECTION token and "
                        "str.isupper() is true for it, so satisfying n sections forces at "
                        f"least {n} capital words. The paired checker requires strictly fewer "
                        f"than {threshold}."
                    ),
                })

    dedup: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for item in losses:
        key = (item["rule_id"], tuple(sorted(item["checker_ids"])))
        dedup[key] = item

    ordered = [dedup[k] for k in sorted(dedup)]
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_NEW_UNION25_MANDATORY_LOSS_LOWER_BOUND",
        "mandatory_loss_rules": ordered,
        "mandatory_loss_rule_count": len(ordered),
        "new_union25_loss_lower_bound": len(ordered),
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
        "complete_union25_loss_map": False,
        "hard_nonclaims": [
            "RULE_COUNT_IS_NOT_ADDITIVE_WHEN_RULES_SHARE_CHECKERS",
            "THIS_MODULE_IS_A_SOUND_LOWER_BOUND_NOT_A_COMPLETE_POINTWISE_OPTIMUM",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT_FROM_THIS_MODULE_ALONE",
        ],
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = dict(args or {})
    return derive(
        list(args.get("contracts") or []),
        prompt_to_repeat=args.get("prompt_to_repeat"),
    )
