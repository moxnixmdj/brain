#!/usr/bin/env python3
"""Sound mandatory-footprint lower bounds for the frozen LiveBench union25 delta.

For frequency-style checkers, every already-required visible literal induces a
minimum observable count. We deliberately take the maximum of per-obligation
floors rather than summing potentially co-satisfiable obligations; this keeps
all certificates sound without solving string-overlap optimization yet.

The result is a lower-bound engine, not a complete satisfiability solver.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_MANDATORY_FOOTPRINT_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

EXIST = "keywords:existence"
KEYWORD_FREQUENCY = "keywords:frequency"
LETTER_FREQUENCY = "keywords:letter_frequency"
NTH = "length_constraints:nth_paragraph_first_word"
POSTSCRIPT = "detectable_content:postscript"
SECTIONS = "detectable_format:multiple_sections"
END = "startend:end_checker"
CAPITAL_FREQUENCY = "change_case:capital_word_frequency"


def _by_id(contracts: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        iid = str(contract.get("instruction_id") or "")
        if not iid:
            continue
        if iid in out:
            raise ValueError("DUPLICATE_INSTRUCTION_ID:" + iid)
        out[iid] = dict(contract.get("slots") or {})
    return out


def _regex_count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _letter_count(letter: str, text: str) -> int:
    return str(text).lower().count(str(letter).lower())


def _literal_obligations(by_id: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return independently mandatory visible literal obligations.

    Counts across records are NOT assumed additive. Each record carries a
    multiplicity only where the checker itself proves repeated disjoint marker
    matches, currently SectionChecker.
    """
    out: list[dict[str, Any]] = []

    if EXIST in by_id:
        for word in by_id[EXIST].get("keywords", ()) or ():
            out.append({"source": EXIST, "text": str(word), "multiplicity": 1})

    if NTH in by_id:
        word = str(by_id[NTH].get("first_word") or "")
        if word:
            out.append({"source": NTH, "text": word, "multiplicity": 1})

    if END in by_id:
        phrase = str(by_id[END].get("end_phrase") or "")
        if phrase:
            out.append({"source": END, "text": phrase, "multiplicity": 1})

    if POSTSCRIPT in by_id:
        marker = str(by_id[POSTSCRIPT].get("postscript_marker") or "")
        if marker:
            # The pinned postscript checker lowercases and requires the marker
            # letters through its regex; case and optional spaces do not remove
            # alphabetic occurrences.
            out.append({"source": POSTSCRIPT, "text": marker, "multiplicity": 1})

    if SECTIONS in by_id:
        splitter = str(by_id[SECTIONS].get("section_spliter") or "")
        count = int(by_id[SECTIONS].get("num_sections") or 0)
        if splitter not in {"Section", "SECTION"}:
            raise ValueError("OUT_OF_FROZEN_GENERATOR_SECTION_SPLITTER:" + splitter)
        if count <= 0:
            raise ValueError("INVALID_FROZEN_SECTION_COUNT")
        out.append({"source": SECTIONS, "text": splitter, "multiplicity": count})

    return out


def mandatory_footprint(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_id = _by_id(contracts)
    obligations = _literal_obligations(by_id)

    keyword_floor = None
    keyword_target = None
    if KEYWORD_FREQUENCY in by_id:
        slots = by_id[KEYWORD_FREQUENCY]
        keyword_target = str(slots.get("keyword") or "")
        if keyword_target:
            candidates = [
                {
                    "source": o["source"],
                    "count": _regex_count(keyword_target, o["text"]) * int(o["multiplicity"]),
                }
                for o in obligations
            ]
            best = max(candidates, key=lambda x: x["count"], default={"source": None, "count": 0})
            keyword_floor = int(best["count"])
            keyword_floor_source = best["source"]
        else:
            keyword_floor = 0
            keyword_floor_source = None
    else:
        keyword_floor_source = None

    letter_floor = None
    letter_target = None
    if LETTER_FREQUENCY in by_id:
        slots = by_id[LETTER_FREQUENCY]
        letter_target = str(slots.get("letter") or "")
        if letter_target:
            candidates = [
                {
                    "source": o["source"],
                    "count": _letter_count(letter_target, o["text"]) * int(o["multiplicity"]),
                }
                for o in obligations
            ]
            best = max(candidates, key=lambda x: x["count"], default={"source": None, "count": 0})
            letter_floor = int(best["count"])
            letter_floor_source = best["source"]
        else:
            letter_floor = 0
            letter_floor_source = None
    else:
        letter_floor_source = None

    capital_floor = None
    capital_floor_source = None
    if CAPITAL_FREQUENCY in by_id:
        # Other frozen public literals can be rendered lowercase when their
        # checker is case-insensitive. SectionChecker is the one admitted
        # active literal with a case-sensitive all-uppercase mandatory token.
        section = by_id.get(SECTIONS)
        if section and str(section.get("section_spliter") or "") == "SECTION":
            capital_floor = int(section.get("num_sections") or 0)
            capital_floor_source = SECTIONS
        else:
            capital_floor = 0

    return {
        "schema": SCHEMA,
        "status": "PASS__SOUND_MANDATORY_FOOTPRINT_LOWER_BOUND",
        "obligations": obligations,
        "keyword_frequency": {
            "target": keyword_target,
            "mandatory_floor": keyword_floor,
            "floor_source": keyword_floor_source,
        },
        "letter_frequency": {
            "target": letter_target,
            "mandatory_floor": letter_floor,
            "floor_source": letter_floor_source,
        },
        "capital_word_frequency": {
            "mandatory_floor": capital_floor,
            "floor_source": capital_floor_source,
        },
        "aggregation_rule": "MAX_OF_PER_OBLIGATION_FLOORS__NO_UNPROVED_ADDITIVITY",
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
    }


def proved_upper_bound_losses(contracts: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    by_id = _by_id(contracts)
    fp = mandatory_footprint(contracts)
    losses: list[dict[str, Any]] = []

    if KEYWORD_FREQUENCY in by_id:
        s = by_id[KEYWORD_FREQUENCY]
        if str(s.get("relation") or "").casefold() == "less than":
            threshold = int(s.get("frequency") or 0)
            floor = int(fp["keyword_frequency"]["mandatory_floor"] or 0)
            if threshold > 0 and floor >= threshold:
                losses.append({
                    "rule_id": "KEYWORD_FREQUENCY_STRICT_UPPER_BOUND_BELOW_MANDATORY_LITERAL_FLOOR",
                    "checker_id": KEYWORD_FREQUENCY,
                    "forcing_source": fp["keyword_frequency"]["floor_source"],
                    "mandatory_floor": floor,
                    "strict_upper_bound": threshold,
                })

    if LETTER_FREQUENCY in by_id:
        s = by_id[LETTER_FREQUENCY]
        if str(s.get("let_relation") or "").casefold() == "less than":
            threshold = int(s.get("let_frequency") or 0)
            floor = int(fp["letter_frequency"]["mandatory_floor"] or 0)
            if threshold > 0 and floor >= threshold:
                losses.append({
                    "rule_id": "LETTER_FREQUENCY_STRICT_UPPER_BOUND_BELOW_MANDATORY_LITERAL_FLOOR",
                    "checker_id": LETTER_FREQUENCY,
                    "forcing_source": fp["letter_frequency"]["floor_source"],
                    "mandatory_floor": floor,
                    "strict_upper_bound": threshold,
                })

    if CAPITAL_FREQUENCY in by_id:
        s = by_id[CAPITAL_FREQUENCY]
        if str(s.get("capital_relation") or "").casefold() == "less than":
            threshold = int(s.get("capital_frequency") or 0)
            floor = int(fp["capital_word_frequency"]["mandatory_floor"] or 0)
            if threshold > 0 and floor >= threshold:
                losses.append({
                    "rule_id": "CAPITAL_WORD_STRICT_UPPER_BOUND_BELOW_MANDATORY_SECTION_FLOOR",
                    "checker_id": CAPITAL_FREQUENCY,
                    "forcing_source": fp["capital_word_frequency"]["floor_source"],
                    "mandatory_floor": floor,
                    "strict_upper_bound": threshold,
                })

    return tuple(losses)


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    contracts = list((args or {}).get("contracts") or [])
    return {
        "footprint": mandatory_footprint(contracts),
        "proved_upper_bound_losses": list(proved_upper_bound_losses(contracts)),
        "complete_union25_loss_map": False,
        "acceptance_credit": False,
    }
