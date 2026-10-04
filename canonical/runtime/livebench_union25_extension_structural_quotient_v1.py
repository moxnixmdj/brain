#!/usr/bin/env python3
"""Exact structural extension quotient for the public LiveBench union25 target.

The independently verified scope lattice enlarged the load-bearing proof target
from Active15 to the full pinned 25-family registry.  This module compresses the
*identity* part of that delta before any slot-semantic proof is attempted.

It intentionally proves only structure:
- exact 25-family conflict-compatible sets of size 1..5;
- exact projection onto the ten union25-minus-Active15 families;
- exact special-branch isolation;
- a closed-form count for the extension-only conflict graph.

No terminal benchmark row, hidden kwargs, case frequency, response, or score is
read.  Slot semantics remain a separate obligation.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Iterable

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as active15
from canonical.runtime import livebench_public_scope_union_v1 as scope

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_EXTENSION_STRUCTURAL_QUOTIENT_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"

KEYWORD_FREQUENCY = "keywords:frequency"
LETTER_FREQUENCY = "keywords:letter_frequency"
LANGUAGE = "language:response_language"
PLACEHOLDERS = "detectable_content:number_placeholders"
CONSTRAINED = "detectable_format:constrained_response"
HIGHLIGHTS = "detectable_format:number_highlighted_sections"
CAPITAL_FREQUENCY = "change_case:capital_word_frequency"
ENGLISH_CAPITAL = "change_case:english_capital"
ENGLISH_LOWERCASE = "change_case:english_lowercase"
NO_COMMA = "punctuation:no_comma"

JSON_ID = "detectable_format:json_format"
REPEAT = "combination:repeat_prompt"
TWO = "combination:two_responses"

EXTENSION10 = (
    KEYWORD_FREQUENCY,
    LETTER_FREQUENCY,
    LANGUAGE,
    PLACEHOLDERS,
    CONSTRAINED,
    HIGHLIGHTS,
    CAPITAL_FREQUENCY,
    ENGLISH_CAPITAL,
    ENGLISH_LOWERCASE,
    NO_COMMA,
)

UNION25 = tuple(scope.TABLE4_25)
MAX_PUBLIC_INSTRUCTIONS = 5

# Frozen registry semantics, represented as undirected semantic conflict pairs.
# The independent verifier re-derives this graph from the exact pinned registry
# bytes instead of trusting this table.
_DIRECTED_EXTRA: dict[str, set[str]] = {
    LANGUAGE: {
        "detectable_format:multiple_sections",
        "keywords:existence",
        KEYWORD_FREQUENCY,
        "keywords:forbidden_words",
        "startend:end_checker",
        ENGLISH_CAPITAL,
        ENGLISH_LOWERCASE,
    },
    "length_constraints:number_paragraphs": {
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_sentences",
    },
    "length_constraints:nth_paragraph_first_word": {
        "length_constraints:number_paragraphs",
        "detectable_format:number_bullet_lists",
        HIGHLIGHTS,
        "detectable_format:multiple_sections",
    },
    "detectable_format:number_bullet_lists": {
        "length_constraints:nth_paragraph_first_word",
    },
    HIGHLIGHTS: {
        "length_constraints:nth_paragraph_first_word",
    },
    "detectable_format:multiple_sections": {
        LANGUAGE,
        HIGHLIGHTS,
        "length_constraints:nth_paragraph_first_word",
    },
    CAPITAL_FREQUENCY: {
        ENGLISH_LOWERCASE,
        ENGLISH_CAPITAL,
    },
    ENGLISH_LOWERCASE: {
        ENGLISH_CAPITAL,
    },
    "startend:quotation": {
        "detectable_format:title",
    },
}


class Union25QuotientError(ValueError):
    pass


def _conflict_graph() -> dict[str, set[str]]:
    universe = set(UNION25)
    if len(universe) != 25:
        raise Union25QuotientError("UNION25_COUNT_DRIFT")

    graph = {iid: {iid} for iid in UNION25}
    for iid, others in _DIRECTED_EXTRA.items():
        graph[iid].update(others)

    # Exact all-family exclusions from the pinned registry.
    graph[CONSTRAINED].update(universe)
    graph[JSON_ID].update(
        universe - {"keywords:forbidden_words", "keywords:existence"}
    )
    graph[TWO].update(
        universe
        - {
            "keywords:forbidden_words",
            "keywords:existence",
            LANGUAGE,
            "detectable_format:title",
            NO_COMMA,
        }
    )
    graph[REPEAT].update(
        universe
        - {
            "keywords:existence",
            "detectable_format:title",
            NO_COMMA,
        }
    )

    # conflict_make() in the frozen registry makes every edge symmetric and
    # every family self-conflicting.
    for left in tuple(UNION25):
        for right in tuple(graph[left]):
            graph[right].add(left)
        graph[left].add(left)
    return graph


def conflict_pairs() -> tuple[tuple[str, str], ...]:
    graph = _conflict_graph()
    pairs = tuple(
        (a, b)
        for i, a in enumerate(UNION25)
        for b in UNION25[i + 1 :]
        if b in graph[a]
    )
    if len(pairs) != 97:
        raise Union25QuotientError("CONFLICT_PAIR_COUNT_DRIFT:" + str(len(pairs)))
    return pairs


def compatible(ids: Iterable[str]) -> bool:
    rows = tuple(ids)
    if len(rows) != len(set(rows)):
        return False
    graph = _conflict_graph()
    if any(x not in graph for x in rows):
        return False
    return all(
        b not in graph[a]
        for i, a in enumerate(rows)
        for b in rows[i + 1 :]
    )


def enumerate_compatible_sets() -> tuple[tuple[str, ...], ...]:
    out: list[tuple[str, ...]] = []
    for size in range(1, MAX_PUBLIC_INSTRUCTIONS + 1):
        for rows in combinations(UNION25, size):
            if compatible(rows):
                out.append(rows)
    counts = Counter(map(len, out))
    expected = {1: 25, 2: 203, 3: 1055, 4: 3750, 5: 9526}
    if dict(counts) != expected:
        raise Union25QuotientError("STRUCTURAL_COUNTS_DRIFT:" + repr(dict(counts)))
    if len(out) != 14559:
        raise Union25QuotientError("STRUCTURAL_TOTAL_DRIFT:" + str(len(out)))
    return tuple(out)


def extension_signature(ids: Iterable[str]) -> tuple[str, ...]:
    extension = set(EXTENSION10)
    return tuple(sorted(x for x in ids if x in extension))


def extension_signatures() -> tuple[tuple[str, ...], ...]:
    signatures = tuple(
        sorted({extension_signature(rows) for rows in enumerate_compatible_sets()})
    )
    if len(signatures) != 157:
        raise Union25QuotientError(
            "EXTENSION_SIGNATURE_COUNT_DRIFT:" + str(len(signatures))
        )
    return signatures


def _extension_graph_closed_form() -> dict[str, Any]:
    """Prove the 157 count without enumerating the 25-family graph.

    With CONSTRAINED absent:
      - five binary free coordinates are keyword-frequency, letter-frequency,
        placeholders, highlights, and no-comma;
      - the case coordinate has four states: none, capital-frequency,
        english-capital, english-lowercase;
      - when language is present, keyword-frequency is forbidden and the case
        coordinate shrinks to {none, capital-frequency}.

    Hence 4*2^5 + 2*2^4 = 160 graph-compatible non-constrained signatures,
    including the empty signature. Adding singleton CONSTRAINED gives 161.
    Exactly four of those signatures have six members, so the public max-five
    instruction cap leaves 157.
    """
    language_absent = 4 * (2**5)
    language_present = 2 * (2**4)
    before_cap = language_absent + language_present + 1
    excluded_size_six = 4
    after_cap = before_cap - excluded_size_six
    if (language_absent, language_present, before_cap, after_cap) != (
        128,
        32,
        161,
        157,
    ):
        raise Union25QuotientError("CLOSED_FORM_ARITHMETIC_DRIFT")
    return {
        "language_absent_signatures": language_absent,
        "language_present_signatures": language_present,
        "constrained_singleton_signatures": 1,
        "graph_compatible_before_max_instruction_cap": before_cap,
        "excluded_only_by_size_six": excluded_size_six,
        "admitted_extension_signatures": after_cap,
        "formula": "4*2^5 + 2*2^4 + 1 - 4 = 157",
    }


def _branch(rows: tuple[str, ...]) -> str:
    if CONSTRAINED in rows:
        return "CONSTRAINED"
    if JSON_ID in rows:
        return "JSON"
    if REPEAT in rows:
        return "REPEAT"
    if TWO in rows:
        return "TWO"
    return "GENERAL"


def verify() -> dict[str, Any]:
    active = set(active15.ACTIVE_IDS)
    union = set(UNION25)
    extension = set(EXTENSION10)
    if len(active) != 15:
        raise Union25QuotientError("ACTIVE15_COUNT_DRIFT")
    if len(extension) != 10:
        raise Union25QuotientError("EXTENSION10_COUNT_DRIFT")
    if active & extension:
        raise Union25QuotientError("ACTIVE_EXTENSION_OVERLAP")
    if active | extension != union:
        raise Union25QuotientError("ACTIVE_PLUS_EXTENSION_NOT_UNION25")

    rows = enumerate_compatible_sets()
    signatures = extension_signatures()

    by_cardinality = Counter(map(len, rows))
    extension_cardinality = Counter(len(extension_signature(x)) for x in rows)
    branches: dict[str, dict[str, Any]] = {}
    for name in ("GENERAL", "JSON", "REPEAT", "TWO", "CONSTRAINED"):
        selected = tuple(x for x in rows if _branch(x) == name)
        sigs = {extension_signature(x) for x in selected}
        branches[name] = {
            "structural_set_count": len(selected),
            "extension_signature_count": len(sigs),
            "nonempty_extension_signatures": sum(bool(x) for x in sigs),
        }

    expected_branches = {
        "GENERAL": (14526, 156),
        "JSON": (4, 1),
        "REPEAT": (8, 2),
        "TWO": (20, 4),
        "CONSTRAINED": (1, 1),
    }
    for name, (count, sig_count) in expected_branches.items():
        got = branches[name]
        if (got["structural_set_count"], got["extension_signature_count"]) != (
            count,
            sig_count,
        ):
            raise Union25QuotientError("BRANCH_COUNT_DRIFT:" + name)

    if set(
        extension_signature(x)
        for x in rows
        if REPEAT in x
    ) != {(), (NO_COMMA,)}:
        raise Union25QuotientError("REPEAT_EXTENSION_ISOLATION_DRIFT")

    if set(
        extension_signature(x)
        for x in rows
        if TWO in x
    ) != {
        (),
        (LANGUAGE,),
        (NO_COMMA,),
        tuple(sorted((LANGUAGE, NO_COMMA))),
    }:
        raise Union25QuotientError("TWO_EXTENSION_ISOLATION_DRIFT")

    if any(extension_signature(x) for x in rows if JSON_ID in x):
        raise Union25QuotientError("JSON_EXTENSION_ISOLATION_DRIFT")

    constrained_sets = tuple(x for x in rows if CONSTRAINED in x)
    if constrained_sets != ((CONSTRAINED,),):
        raise Union25QuotientError("CONSTRAINED_NOT_SINGLETON")

    closed_form = _extension_graph_closed_form()
    if closed_form["admitted_extension_signatures"] != len(signatures):
        raise Union25QuotientError("CLOSED_FORM_ENUMERATION_MISMATCH")

    return {
        "schema": SCHEMA,
        "status": "PASS__UNION25_EXTENSION_IDENTITY_QUOTIENT_157",
        "scope": {
            "active15": 15,
            "union25": 25,
            "extension10": list(EXTENSION10),
            "extension10_count": 10,
            "conflict_pair_count": len(conflict_pairs()),
            "max_public_instruction_count": MAX_PUBLIC_INSTRUCTIONS,
        },
        "structural_universe": {
            "compatible_set_total": len(rows),
            "by_cardinality": {str(k): by_cardinality[k] for k in sorted(by_cardinality)},
            "active15_only_structural_sets": sum(
                not extension_signature(x) for x in rows
            ),
            "extension_bearing_structural_sets": sum(
                bool(extension_signature(x)) for x in rows
            ),
        },
        "extension_projection": {
            "exact_signature_count": len(signatures),
            "structural_sets_by_extension_cardinality": {
                str(k): extension_cardinality[k]
                for k in sorted(extension_cardinality)
            },
            "closed_form": closed_form,
        },
        "special_branch_isolation": branches,
        "semantic_work_deleted": [
            "DO_NOT_TREAT_ALL_14559_IDENTITY_SETS_AS_DISTINCT_EXTENSION_IDENTITY_PROBLEMS",
            "CONSTRAINED_RESPONSE_IS_A_SINGLETON_BRANCH",
            "JSON_HAS_ZERO_EXTENSION10_INTERACTIONS",
            "REPEAT_HAS_ONLY_OPTIONAL_NO_COMMA_EXTENSION_INTERACTION",
            "TWO_RESPONSES_HAS_ONLY_OPTIONAL_LANGUAGE_AND_NO_COMMA_EXTENSION_INTERACTIONS",
        ],
        "next_load_bearing_proof": (
            "CLOSE_SLOT_SEMANTICS_FOR_THE_156_GENERAL_EXTENSION_SIGNATURES__"
            "REUSING_THE_ALREADY_CLOSED_ACTIVE15_CORE_AND_SPECIAL_BRANCH_ISOLATION"
        ),
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "terminal_frequencies_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "157_IS_AN_EXTENSION_IDENTITY_QUOTIENT_NOT_A_COMPLETE_SLOT_SEMANTIC_QUOTIENT",
            "UNION25_POINTWISE_OPTIMALITY_IS_NOT_YET_PROVED",
            "LIVEBENCH_ACCEPTANCE_CREDIT_REMAINS_ZERO",
            "THE_TERMINAL_GOAL_IS_NOT_YET_PROVED",
        ],
    }


def run(args=None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
