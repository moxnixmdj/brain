#!/usr/bin/env python3
"""Strengthened mandatory-footprint lower bounds for frozen LiveBench union25.

V1 intentionally aggregated all mandatory literals by MAX because arbitrary
obligations may share the same response span.  That is sound but unnecessarily
weak for three structural checker families whose required witnesses are
provably position-separated under the pinned checker semantics:

* multiple_sections: re.split consumes num_sections non-overlapping splitter
  matches, each containing the case-sensitive splitter token;
* postscript: the checker requires one P.S. or P.P.S marker occurrence;
* end_checker: the checker requires one of two exact fixed suffix phrases.

The fixed postscript markers and fixed ending phrases contain no section marker
with a digit, the ending phrases contain no postscript marker, and the
postscript markers contain no ending phrase.  Therefore these mandatory spans
cannot be the same character span.  Their keyword/letter contributions may be
summed safely.  Unlocated existence and nth-first-word obligations remain
MAX-combined with the separated structural floor so no overlap is invented.

This module strengthens only lower bounds. It does not claim complete union25
satisfiability or acceptance credit.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_union25_mandatory_footprint_v1 as v1

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_MANDATORY_FOOTPRINT_V2"
SUPERSEDES = "PROJECT_BRAIN_LIVEBENCH_UNION25_MANDATORY_FOOTPRINT_V1"
PINNED_LIVEBENCH_COMMIT = v1.PINNED_LIVEBENCH_COMMIT
PINNED_INSTRUCTIONS_BLOB = v1.PINNED_INSTRUCTIONS_BLOB

EXIST = v1.EXIST
KEYWORD_FREQUENCY = v1.KEYWORD_FREQUENCY
LETTER_FREQUENCY = v1.LETTER_FREQUENCY
NTH = v1.NTH
POSTSCRIPT = v1.POSTSCRIPT
SECTIONS = v1.SECTIONS
END = v1.END
CAPITAL_FREQUENCY = v1.CAPITAL_FREQUENCY

END_PHRASES = {
    "Any other questions?",
    "Is there anything else I can help with?",
}
POSTSCRIPT_MARKERS = {"P.S.", "P.P.S"}


def _structural_obligations(
    by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Return mandatory literals whose character spans are pairwise distinct."""
    out: list[dict[str, Any]] = []

    if SECTIONS in by_id:
        splitter = str(by_id[SECTIONS].get("section_spliter") or "")
        count = int(by_id[SECTIONS].get("num_sections") or 0)
        if splitter not in {"Section", "SECTION"}:
            raise ValueError("OUT_OF_FROZEN_GENERATOR_SECTION_SPLITTER:" + splitter)
        if not 1 <= count <= 5:
            raise ValueError("OUT_OF_FROZEN_GENERATOR_SECTION_COUNT")
        out.append({
            "source": SECTIONS,
            "text": splitter,
            "multiplicity": count,
            "separation_basis": "NONOVERLAPPING_RE_SPLIT_MATCHES",
        })

    if POSTSCRIPT in by_id:
        marker = str(by_id[POSTSCRIPT].get("postscript_marker") or "")
        if marker not in POSTSCRIPT_MARKERS:
            raise ValueError("OUT_OF_FROZEN_GENERATOR_POSTSCRIPT_MARKER:" + marker)
        out.append({
            "source": POSTSCRIPT,
            "text": marker,
            "multiplicity": 1,
            "separation_basis": "FIXED_POSTSCRIPT_MARKER",
        })

    if END in by_id:
        phrase = str(by_id[END].get("end_phrase") or "")
        if phrase not in END_PHRASES:
            raise ValueError("OUT_OF_FROZEN_GENERATOR_END_PHRASE:" + phrase)
        out.append({
            "source": END,
            "text": phrase,
            "multiplicity": 1,
            "separation_basis": "EXACT_SUFFIX_PHRASE",
        })

    # Source-level non-aliasing checks. They are deliberately stronger than a
    # prose claim: none of the fixed literals can satisfy another structural
    # family's mandatory witness.
    for phrase in END_PHRASES:
        low = phrase.casefold()
        if "p.s." in low or "p.p.s" in low:
            raise AssertionError("END_PHRASE_ALIASES_POSTSCRIPT")
        if "section" in low:
            raise AssertionError("END_PHRASE_ALIASES_SECTION")
    for marker in POSTSCRIPT_MARKERS:
        low = marker.casefold()
        if "section" in low:
            raise AssertionError("POSTSCRIPT_ALIASES_SECTION")
        if any(phrase.casefold() in low for phrase in END_PHRASES):
            raise AssertionError("POSTSCRIPT_ALIASES_END_PHRASE")

    return tuple(out)


def _unlocated_obligations(
    by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Obligations that may share a span with a structural witness."""
    out: list[dict[str, Any]] = []
    if EXIST in by_id:
        for word in by_id[EXIST].get("keywords", ()) or ():
            out.append({"source": EXIST, "text": str(word), "multiplicity": 1})
    if NTH in by_id:
        word = str(by_id[NTH].get("first_word") or "")
        if word:
            out.append({"source": NTH, "text": word, "multiplicity": 1})
    return tuple(out)


def strengthened_mandatory_footprint(
    contracts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_id = v1._by_id(contracts)
    baseline = v1.mandatory_footprint(contracts)
    structural = _structural_obligations(by_id)
    unlocated = _unlocated_obligations(by_id)

    keyword = dict(baseline["keyword_frequency"])
    if KEYWORD_FREQUENCY in by_id:
        target = str(by_id[KEYWORD_FREQUENCY].get("keyword") or "")
        structural_floor = sum(
            v1._regex_count(target, o["text"]) * int(o["multiplicity"])
            for o in structural
        ) if target else 0
        unlocated_floor = max(
            (
                v1._regex_count(target, o["text"]) * int(o["multiplicity"])
                for o in unlocated
            ),
            default=0,
        ) if target else 0
        floor = max(
            int(keyword.get("mandatory_floor") or 0),
            structural_floor,
            unlocated_floor,
        )
        keyword.update({
            "mandatory_floor": floor,
            "separated_structural_floor": structural_floor,
            "unlocated_max_floor": unlocated_floor,
            "aggregation_rule": "MAX(SEPARATED_STRUCTURAL_SUM,UNLOCATED_MAX,V1_FLOOR)",
        })

    letter = dict(baseline["letter_frequency"])
    if LETTER_FREQUENCY in by_id:
        target = str(by_id[LETTER_FREQUENCY].get("letter") or "")
        structural_floor = sum(
            v1._letter_count(target, o["text"]) * int(o["multiplicity"])
            for o in structural
        ) if target else 0
        unlocated_floor = max(
            (
                v1._letter_count(target, o["text"]) * int(o["multiplicity"])
                for o in unlocated
            ),
            default=0,
        ) if target else 0
        floor = max(
            int(letter.get("mandatory_floor") or 0),
            structural_floor,
            unlocated_floor,
        )
        letter.update({
            "mandatory_floor": floor,
            "separated_structural_floor": structural_floor,
            "unlocated_max_floor": unlocated_floor,
            "aggregation_rule": "MAX(SEPARATED_STRUCTURAL_SUM,UNLOCATED_MAX,V1_FLOOR)",
        })

    capital = dict(baseline["capital_word_frequency"])

    return {
        "schema": SCHEMA,
        "supersedes": SUPERSEDES,
        "status": "PASS__SEPARATED_STRUCTURAL_LITERAL_FLOORS_ADD_SOUNDLY",
        "structural_obligations": list(structural),
        "unlocated_obligations": list(unlocated),
        "keyword_frequency": keyword,
        "letter_frequency": letter,
        "capital_word_frequency": capital,
        "proof": {
            "section_matches": "PYTHON_RE_SPLIT_MATCHES_ARE_NONOVERLAPPING",
            "postscript_marker": "ONE_FIXED_P_S_OR_P_P_S_MARKER_REQUIRED",
            "end_phrase": "ONE_EXACT_FIXED_SUFFIX_REQUIRED",
            "cross_family_aliases": "ZERO_FOR_PINNED_FIXED_LITERALS",
            "safe_sum_scope": [SECTIONS, POSTSCRIPT, END],
            "nonadditive_scope": [EXIST, NTH],
        },
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def proved_upper_bound_losses(
    contracts: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    by_id = v1._by_id(contracts)
    fp = strengthened_mandatory_footprint(contracts)
    losses: list[dict[str, Any]] = []

    if KEYWORD_FREQUENCY in by_id:
        s = by_id[KEYWORD_FREQUENCY]
        if str(s.get("relation") or "").casefold() == "less than":
            threshold = int(s.get("frequency") or 0)
            floor = int(fp["keyword_frequency"].get("mandatory_floor") or 0)
            if threshold > 0 and floor >= threshold:
                losses.append({
                    "rule_id": "KEYWORD_FREQUENCY_STRICT_UPPER_BOUND_BELOW_STRENGTHENED_MANDATORY_FLOOR",
                    "checker_id": KEYWORD_FREQUENCY,
                    "mandatory_floor": floor,
                    "strict_upper_bound": threshold,
                })

    if LETTER_FREQUENCY in by_id:
        s = by_id[LETTER_FREQUENCY]
        if str(s.get("let_relation") or "").casefold() == "less than":
            threshold = int(s.get("let_frequency") or 0)
            floor = int(fp["letter_frequency"].get("mandatory_floor") or 0)
            if threshold > 0 and floor >= threshold:
                losses.append({
                    "rule_id": "LETTER_FREQUENCY_STRICT_UPPER_BOUND_BELOW_STRENGTHENED_MANDATORY_FLOOR",
                    "checker_id": LETTER_FREQUENCY,
                    "mandatory_floor": floor,
                    "strict_upper_bound": threshold,
                })

    if CAPITAL_FREQUENCY in by_id:
        s = by_id[CAPITAL_FREQUENCY]
        if str(s.get("capital_relation") or "").casefold() == "less than":
            threshold = int(s.get("capital_frequency") or 0)
            floor = int(fp["capital_word_frequency"].get("mandatory_floor") or 0)
            if threshold > 0 and floor >= threshold:
                losses.append({
                    "rule_id": "CAPITAL_WORD_STRICT_UPPER_BOUND_BELOW_MANDATORY_SECTION_FLOOR",
                    "checker_id": CAPITAL_FREQUENCY,
                    "mandatory_floor": floor,
                    "strict_upper_bound": threshold,
                })

    return tuple(losses)


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    contracts = list((args or {}).get("contracts") or [])
    return {
        "footprint": strengthened_mandatory_footprint(contracts),
        "proved_upper_bound_losses": list(proved_upper_bound_losses(contracts)),
        "complete_union25_loss_map": False,
        "acceptance_credit": False,
    }
