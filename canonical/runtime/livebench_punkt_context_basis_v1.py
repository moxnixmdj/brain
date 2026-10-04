#!/usr/bin/env python3
"""Finite Punkt context basis for frozen LiveBench active15.

After mandatory pointwise sacrifices and the parametric non-sentence reduction,
the only environment-sensitive construction behavior left is NLTK Punkt sentence
segmentation.  This module enumerates every relevant structural/wrapper context
without terminal rows.

The raw word-threshold range does not multiply the basis: for Punkt, WORDS has
only two construction shapes here, no padding (less-than) and positive
punctuation-free padding (at-least).  The public minimum threshold is 100 while
the proven unpadded upper bound is below 100, so the at-least class always adds
one or more punctuation-free pad tokens.  Cardinality of additional pad tokens
cannot introduce sentence punctuation; exact runtime replay still tests the
representative positive-padding context.

Sentence relation classes:
- less-than 1 is removed before construction by the mandatory SENTENCES sacrifice;
- less-than 2..20 has one byte-construction branch, represented by threshold 2;
- at-least 1..20 is exhausted exactly because n controls emitted periods.

No acceptance credit is granted here.  Independent exact-checker replay is
required.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import prod
from typing import Any, Iterable

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lex
from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as param

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_BASIS_V1"
EXPECTED_SENTENCE_ID_SETS = 285
EXPECTED_CONTEXT_COUNT = 147924

EXISTENCE_REP = tuple(lex.EXISTENCE_REPRESENTATIVE)
FORBIDDEN_REP = tuple(lex.GENERIC_FORBIDDEN_FILLERS)
NTH_FIRST_REP = lex.GENERIC_NTH_WORD

POST_VALUES = ("P.S.", "P.P.S")
END_VALUES = (
    "Any other questions?",
    "Is there anything else I can help with?",
)
SECTION_VALUES = tuple(
    (splitter, n)
    for splitter in ("Section", "SECTION")
    for n in range(1, 6)
)
NTH_LOCATIONS = tuple(
    (p, k)
    for p in range(1, 6)
    for k in range(1, p + 1)
)

# The two Punkt-relevant word-construction shapes.
WORD_CONTEXTS = (
    ("NO_PADDING", 100, "less than"),
    ("POSITIVE_PADDING", 100, "at least"),
)

# less-than 1 is intentionally absent because pointwise optimality must drop the
# intrinsically impossible sentence checker before invoking the composer.
SENTENCE_CONTEXTS = (
    (("LT_BOUNDARY", 2, "less than"),)
    + tuple(("GE_" + str(n), n, "at least") for n in range(1, 21))
)

REP_COUNTS = {
    comp.EXIST: 1,
    comp.FORBIDDEN: 1,
    comp.WORDS: len(WORD_CONTEXTS),
    comp.SENTENCES: len(SENTENCE_CONTEXTS),
    comp.NTH: len(NTH_LOCATIONS),
    comp.POSTSCRIPT: len(POST_VALUES),
    comp.BULLETS: 5,
    comp.TITLE: 1,
    comp.SECTIONS: len(SECTION_VALUES),
    comp.END: len(END_VALUES),
    comp.QUOTE: 1,
}


@dataclass(frozen=True)
class Choice:
    iid: str
    label: str
    slots: tuple[tuple[str, Any], ...]

    def contract(self) -> dict[str, Any]:
        return {"instruction_id": self.iid, "slots": dict(self.slots)}


def _choice(iid: str, label: str, **slots: Any) -> Choice:
    return Choice(iid, label, tuple(sorted(slots.items())))


def choices(iid: str) -> tuple[Choice, ...]:
    if iid == comp.EXIST:
        return (_choice(iid, "LEXICAL_NEUTRAL", keywords=list(EXISTENCE_REP)),)
    if iid == comp.FORBIDDEN:
        return (_choice(iid, "LEXICAL_NEUTRAL", forbidden_words=list(FORBIDDEN_REP)),)
    if iid == comp.WORDS:
        return tuple(
            _choice(iid, label, num_words=n, relation=relation)
            for label, n, relation in WORD_CONTEXTS
        )
    if iid == comp.SENTENCES:
        return tuple(
            _choice(iid, label, num_sentences=n, relation=relation)
            for label, n, relation in SENTENCE_CONTEXTS
        )
    if iid == comp.NTH:
        return tuple(
            _choice(
                iid,
                f"P{p}_K{k}",
                num_paragraphs=p,
                nth_paragraph=k,
                first_word=NTH_FIRST_REP,
            )
            for p, k in NTH_LOCATIONS
        )
    if iid == comp.POSTSCRIPT:
        return tuple(_choice(iid, marker, postscript_marker=marker) for marker in POST_VALUES)
    if iid == comp.BULLETS:
        return tuple(_choice(iid, f"B{n}", num_bullets=n) for n in range(1, 6))
    if iid == comp.TITLE:
        return (_choice(iid, "STATIC"),)
    if iid == comp.SECTIONS:
        return tuple(
            _choice(iid, f"{splitter}_{n}", section_spliter=splitter, num_sections=n)
            for splitter, n in SECTION_VALUES
        )
    if iid == comp.END:
        return tuple(_choice(iid, f"END_{i}", end_phrase=p) for i, p in enumerate(END_VALUES))
    if iid == comp.QUOTE:
        return (_choice(iid, "STATIC"),)
    raise ValueError("NON_PUNKT_CONTEXT_ID:" + str(iid))


def sentence_id_sets() -> tuple[tuple[str, ...], ...]:
    rows = tuple(
        ids
        for ids in arch.enumerate_compatible_sets()
        if comp.SENTENCES in ids
    )
    if len(rows) != EXPECTED_SENTENCE_ID_SETS:
        raise RuntimeError("SENTENCE_ID_SET_COUNT_DRIFT:" + str(len(rows)))

    forbidden_special = {comp.PARAGRAPHS, comp.JSON_ID, comp.REPEAT, comp.TWO}
    for ids in rows:
        bad = forbidden_special.intersection(ids)
        if bad:
            raise RuntimeError("PUNKT_ROUTE_CONFLICT_DRIFT:" + repr((ids, sorted(bad))))
        if not set(ids) <= set(REP_COUNTS):
            raise RuntimeError("UNMODELED_PUNKT_ID_SET:" + repr(ids))
    return rows


def context_count() -> int:
    return sum(prod(REP_COUNTS[iid] for iid in ids) for ids in sentence_id_sets())


def iter_contexts() -> Iterable[tuple[dict[str, Any], ...]]:
    """Yield all 147,924 post-sacrifice Punkt context representatives."""
    for ids in sentence_id_sets():
        domains = [choices(iid) for iid in ids]
        for row in product(*domains):
            yield tuple(x.contract() for x in row)


def reduction_proof() -> dict[str, Any]:
    if param.CONSERVATIVE_UNPADDED_WORD_UPPER_BOUND >= 100:
        raise RuntimeError("POSITIVE_PADDING_CLASS_NOT_PROVED")

    # Generated lexical representatives are punctuation-free.  Lexical collision
    # cases remove FORBIDDEN before this stage; the resulting smaller compatible
    # ID set is itself present in sentence_id_sets().
    for word in EXISTENCE_REP + FORBIDDEN_REP + (NTH_FIRST_REP,):
        if not str(word).isascii() or not str(word).isalpha():
            raise RuntimeError("LEXICAL_REP_NOT_ASCII_ALPHA:" + str(word))

    return {
        "sentence_lt1": (
            "REMOVED_BEFORE_CONSTRUCTION_BY_MANDATORY_SENTENCES_SACRIFICE"
        ),
        "sentence_lt2_to_20": (
            "ONE_CONSTRUCTOR_BRANCH__THRESHOLD_DOES_NOT_CHANGE_EMITTED_BYTES__"
            "REPRESENT_BY_LT2_STRONGEST_BOUNDARY"
        ),
        "sentence_ge1_to_20": (
            "EXHAUST_ALL_20_VALUES_BECAUSE_N_CONTROLS_EXPLICIT_PERIOD_CARRIERS"
        ),
        "word_lt100_to_500": (
            "NO_PADDING__ALL_THRESHOLDS_SHARE_IDENTICAL_PUNKT_CONSTRUCTION_SHAPE"
        ),
        "word_ge100_to_500": (
            "ALWAYS_POSITIVE_PUNCTUATION_FREE_PADDING_BECAUSE_UNPADDED_BOUND_LT_100__"
            "REPRESENT_BY_GE100"
        ),
        "lexical_identity": (
            "ASCII_ALPHA_REQUIRED_AND_NTH_WORDS_HAVE_NO_PUNCTUATION__"
            "FORBIDDEN_EMITS_NO_TEXT__LEXICAL_COLLISIONS_DROP_FORBIDDEN"
        ),
        "special_routes": (
            "JSON_REPEAT_TWO_RESPONSE_CANNOT_COEXIST_WITH_SENTENCES_IN_FROZEN_CONFLICT_GRAPH"
        ),
    }


def verify() -> dict[str, Any]:
    a = arch.verify()
    if a["compatible_set_count"] != 928:
        raise RuntimeError("STRUCTURAL_SET_COUNT_DRIFT")

    proof = reduction_proof()
    rows = sentence_id_sets()
    count = context_count()
    if count != EXPECTED_CONTEXT_COUNT:
        raise RuntimeError("PUNKT_CONTEXT_COUNT_DRIFT:" + str(count))

    by_cardinality: dict[int, int] = {}
    weighted_by_cardinality: dict[int, int] = {}
    for ids in rows:
        k = len(ids)
        by_cardinality[k] = by_cardinality.get(k, 0) + 1
        weighted_by_cardinality[k] = (
            weighted_by_cardinality.get(k, 0)
            + prod(REP_COUNTS[iid] for iid in ids)
        )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__147924_EXACT_REDUCED_PUNKT_CONTEXTS_COMPILED__"
            "INDEPENDENT_PINNED_RUNTIME_REPLAY_REQUIRED"
        ),
        "structural_id_sets": 928,
        "sentence_context_id_sets": len(rows),
        "punkt_context_count": count,
        "representative_counts": dict(sorted(REP_COUNTS.items())),
        "sentence_id_sets_by_cardinality": dict(sorted(by_cardinality.items())),
        "contexts_by_cardinality": dict(sorted(weighted_by_cardinality.items())),
        "reduction_proof": proof,
        "independent_replay_contract": {
            "required_nltk_version": "3.10.3",
            "required_checker_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
            "required_evaluation_main_blob": "4a341984936c4d609644a3b77f8c030ac5aa7269",
            "required_punkt_source_blob": "48496d2448c009221d2452c8e928699027b20ebe",
            "for_every_context": [
                "COMPOSER_RETURNS_CANDIDATE_WITNESS",
                "EXACT_PINNED_SENTENCE_CHECKER_PASSES",
                "EVERY_OTHER_ACTIVE_CHECKER_PASSES",
            ],
        },
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "terminal_frequencies_used": False,
        "target_scores_used": False,
        "fresh_reality_used": False,
        "acceptance_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "THIS_BASIS_HAS_NOT_YET_BEEN_INDEPENDENTLY_REPLAYED",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT_UNTIL_EXACT_PINNED_RUNTIME_REPLAY_PASSES",
            "NO_TERMINAL_GOAL_COMPLETION_CREDIT_FROM_THIS_MODULE_ALONE",
        ],
    }


def run(args=None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
