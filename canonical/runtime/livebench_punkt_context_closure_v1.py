#!/usr/bin/env python3
"""Exact finite Punkt-context closure for frozen LiveBench Active15.

The post-sacrifice parametric reduction proves every non-sentence checker family
symbolically. This module closes the only environment-sensitive remainder:
NLTK Punkt sentence segmentation.

It enumerates every conflict-compatible Active15 ID set containing the sentence
checker, every public sentence threshold/relation that remains after the exact
<1 UNSAT sacrifice, and every slot value that can alter punctuation or the
immediate Punkt boundary context. Slots that can only add alphanumeric tokens or
whitespace are collapsed to extremal representatives, with the collapse stated
explicitly and fail-closed.

No terminal rows, hidden kwargs, row frequencies, model outputs, or target
scores are read.
"""
from __future__ import annotations

from itertools import product
from typing import Any, Callable, Iterable, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feas

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_V1"

PINNED_NLTK_VERSION = "3.10.3"
PINNED_NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
PINNED_EVALUATION_MAIN_BLOB = "4a341984936c4d609644a3b77f8c030ac5aa7269"

_SAFE_REQUIRED = ["western", "signal", "dump", "spot", "opposite"]
_SAFE_FORBIDDEN = ["bottom", "potato", "administration", "working", "welcome"]
_SAFE_NTH = "morning"

_POSTS = ("P.S.", "P.P.S")
_ENDS = ("Any other questions?", "Is there anything else I can help with?")


def _c(iid: str, **slots: Any) -> dict[str, Any]:
    return {"instruction_id": iid, "slots": slots}


def sentence_id_sets() -> tuple[tuple[str, ...], ...]:
    out = tuple(
        ids for ids in arch.enumerate_compatible_sets()
        if comp.SENTENCES in ids
    )
    if not out:
        raise AssertionError("NO_SENTENCE_ID_SETS")
    for ids in out:
        if comp.PARAGRAPHS in ids:
            raise AssertionError("SENTENCE_PARAGRAPH_CONFLICT_DRIFT")
        if any(x in ids for x in (comp.JSON_ID, comp.REPEAT, comp.TWO)):
            raise AssertionError("SENTENCE_SPECIAL_ROUTE_CONFLICT_DRIFT")
    return out


def _variants_for(iid: str) -> tuple[dict[str, Any], ...]:
    """Exact or proof-preserving representatives for non-sentence slots.

    Punctuation-relevant domains are exhausted exactly:
      postscript: 2/2; end: 2/2; quotation/title: structural presence;
      nth paragraph positions: 15/15 because blank-line placement is relevant.

    Punctuation-free dimensions use extremal representatives:
      words: <100 and >=500; bullets: 1 and 5; sections: both splitters at
      counts 1 and 5. Their omitted intermediate values change only counts of
      alphanumeric tokens/newlines and cannot introduce .?! terminators.
    """
    if iid == comp.EXIST:
        return ({"keywords": list(_SAFE_REQUIRED)},)
    if iid == comp.FORBIDDEN:
        return ({"forbidden_words": list(_SAFE_FORBIDDEN)},)
    if iid == comp.WORDS:
        return (
            {"num_words": 100, "relation": "less than"},
            {"num_words": 500, "relation": "at least"},
        )
    if iid == comp.NTH:
        return tuple(
            {
                "num_paragraphs": p,
                "nth_paragraph": k,
                "first_word": _SAFE_NTH,
            }
            for p in range(1, 6)
            for k in range(1, p + 1)
        )
    if iid == comp.POSTSCRIPT:
        return tuple({"postscript_marker": x} for x in _POSTS)
    if iid == comp.BULLETS:
        return ({"num_bullets": 1}, {"num_bullets": 5})
    if iid == comp.TITLE:
        return ({},)
    if iid == comp.SECTIONS:
        return (
            {"section_spliter": "Section", "num_sections": 1},
            {"section_spliter": "SECTION", "num_sections": 5},
        )
    if iid == comp.END:
        return tuple({"end_phrase": x} for x in _ENDS)
    if iid == comp.QUOTE:
        return ({},)
    if iid == comp.SENTENCES:
        raise AssertionError("SENTENCE_VARIANTS_ARE_SUPPLIED_SEPARATELY")
    raise AssertionError("UNEXPECTED_SENTENCE_COMPATIBLE_ID:" + iid)


def _sentence_variants() -> tuple[dict[str, Any], ...]:
    # Exhaust all satisfiable public sentence slots. <1 is globally UNSAT under
    # strict nonempty evaluation and is discharged by the bound feasibility
    # theorem, so it is not a post-sacrifice sentence context.
    out = []
    for n in range(1, 21):
        out.append({"num_sentences": n, "relation": "at least"})
    for n in range(2, 21):
        out.append({"num_sentences": n, "relation": "less than"})
    return tuple(out)


def iter_contexts() -> Iterable[dict[str, Any]]:
    """Yield every dependency-closed exact Punkt context."""
    for ids in sentence_id_sets():
        others = [iid for iid in ids if iid != comp.SENTENCES]
        spaces = [_variants_for(iid) for iid in others]
        for sent in _sentence_variants():
            combos = product(*spaces) if spaces else [()]
            for chosen in combos:
                contracts = [_c(comp.SENTENCES, **sent)]
                contracts.extend(
                    _c(iid, **slots)
                    for iid, slots in zip(others, chosen)
                )
                yield {
                    "ids": ids,
                    "sentence_slots": sent,
                    "contracts": contracts,
                }


def reduction_lemmas() -> list[dict[str, str]]:
    return [
        {
            "lemma": "STRICT_LT_ONE_REMOVED_BEFORE_PUNKT_CONTEXT_PROOF",
            "proof": (
                "pinned strict evaluator rejects empty/whitespace response; every "
                "strict-eligible nonempty response has >=1 Punkt sentence; planner "
                "therefore sacrifices the sentence checker for relation<1"
            ),
        },
        {
            "lemma": "KEYWORD_IDENTITIES_PUNCTUATION_IRRELEVANT",
            "proof": (
                "public WORD_LIST entries are ASCII alphabetic and composer packs "
                "existence words inside alphanumeric shields; forbidden words emit "
                "no response text; neither can introduce .?!"
            ),
        },
        {
            "lemma": "WORD_THRESHOLD_INTERMEDIATES_PUNCTUATION_IRRELEVANT",
            "proof": (
                "word padding adds only alphanumeric one-word tokens; <100 emits "
                "no padding and >=500 is the maximal pad-length representative; "
                "intermediate thresholds cannot introduce sentence terminators"
            ),
        },
        {
            "lemma": "BULLET_SECTION_INTERMEDIATES_PUNCTUATION_IRRELEVANT",
            "proof": (
                "intermediate bullet/section counts and splitter case alter only "
                "asterisks, alphanumeric tokens, digits, and whitespace/newlines; "
                "the composer emits no .?! in these structures"
            ),
        },
        {
            "lemma": "PUNKT_RELEVANT_PUBLIC_PUNCTUATION_EXHAUSTED",
            "proof": (
                "all 39 satisfiable sentence slot states, both postscript markers, "
                "both fixed end phrases, quotation presence, and all 15 NTH blank-"
                "line positions are represented whenever structurally compatible"
            ),
        },
    ]


def verify_with_counter(count_sentences: Callable[[str], int]) -> dict[str, Any]:
    total = 0
    low = 0
    high = 0
    max_seen_lt = 0
    min_margin_ge = None
    failures: list[dict[str, Any]] = []

    for case in iter_contexts():
        contracts = case["contracts"]
        out = comp.compose_contracts(contracts)
        total += 1
        if out.get("status") != "CANDIDATE_WITNESS":
            failures.append({
                "kind": "COMPOSER_NOT_WITNESS",
                "ids": list(case["ids"]),
                "sentence_slots": case["sentence_slots"],
                "status": out.get("status"),
                "error": out.get("error"),
            })
            if len(failures) >= 20:
                break
            continue

        response = str(out["response"])
        got = int(count_sentences(response))
        slots = case["sentence_slots"]
        n = int(slots["num_sentences"])
        rel = str(slots["relation"])
        ok = got < n if rel == "less than" else got >= n
        if rel == "less than":
            low += 1
            max_seen_lt = max(max_seen_lt, got)
        else:
            high += 1
            margin = got - n
            min_margin_ge = margin if min_margin_ge is None else min(min_margin_ge, margin)

        if not ok:
            failures.append({
                "kind": "PUNKT_BOUNDARY_FAILURE",
                "ids": list(case["ids"]),
                "sentence_slots": slots,
                "got_sentences": got,
                "response": response,
            })
            if len(failures) >= 20:
                break

    if failures:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "context_cases_checked": total,
            "failures": failures,
            "acceptance_credit": False,
        }

    # Reassert the exact independent feasibility premise for the one removed
    # public state. This does not execute terminal data.
    lt1 = feas.hard_unsat_reasons([
        _c(comp.SENTENCES, num_sentences=1, relation="less than")
    ])
    if "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE" not in lt1:
        raise AssertionError("LT1_UNSAT_BINDING_DRIFT")

    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_DEPENDENCY_CLOSED_PINNED_PUNKT_CONTEXTS",
        "sentence_structural_id_sets": len(sentence_id_sets()),
        "context_cases_checked": total,
        "at_least_cases": high,
        "less_than_cases": low,
        "max_observed_sentence_count_in_less_than_contexts": max_seen_lt,
        "minimum_observed_margin_in_at_least_contexts": min_margin_ge,
        "satisfiable_sentence_slot_states_exhausted": 39,
        "strict_lt_one_state": "PROVED_UNSAT_AND_SACRIFICED",
        "reduction_lemmas": reduction_lemmas(),
        "terminal_rows_used": False,
        "terminal_kwargs_used": False,
        "terminal_instruction_ids_used": False,
        "terminal_frequencies_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "next_required": (
            "INDEPENDENT_CONTENT_BOUND_RUN_WITH_NLTK_3_10_3_AND_PINNED_PUNKT_DATA_"
            "THEN_BIND_WITH_POST_SACRIFICE_PARAMETRIC_REDUCTION_AND_POINTWISE_ENVELOPE"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    # Source-only surface. Exact verification requires an explicitly supplied
    # frozen Punkt counter in a controlled verifier.
    contexts = sum(1 for _ in iter_contexts())
    return {
        "schema": SCHEMA,
        "status": "READY_FOR_EXACT_PINNED_PUNKT_VERIFICATION",
        "sentence_structural_id_sets": len(sentence_id_sets()),
        "planned_context_cases": contexts,
        "satisfiable_sentence_slot_states": 39,
        "reduction_lemmas": reduction_lemmas(),
        "acceptance_credit": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, sort_keys=True))
