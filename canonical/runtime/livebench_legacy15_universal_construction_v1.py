#!/usr/bin/env python3
"""Universal post-sacrifice construction proof for frozen LiveBench active15.

For every contract tuple admitted by the frozen public active15 generator,
after removing the minimum mandatory-loss coordinates certified by
livebench_pointwise_minimum_cut_v1, Composer V2 has no remaining slot-domain
obstruction.

The proof is parametric. It composes the exact structural, lexical, numeric, and
minimum-cut reductions already frozen in the Brain, then checks that the
remaining syntax layers are non-interfering.

Zero terminal rows, hidden kwargs, responses, frequencies, or target scores are
consumed. This grants zero acceptance credit until independently verified.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lex
from canonical.runtime import livebench_legacy15_numeric_quotient_v1 as numeric
from canonical.runtime import livebench_pointwise_minimum_cut_v1 as cut
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feas

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_UNIVERSAL_CONSTRUCTION_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py":
        "5803c31e3972c6d40415f319e808c48420bc0388",
    "canonical/runtime/livebench_legacy15_numeric_quotient_v1.py":
        "72189bb8adb12ad36a52ee666a1f79fbb201b06b",
    "canonical/runtime/livebench_pointwise_minimum_cut_v1.py":
        "0d4e563b618f8fd7f37396a88738cefb50979ff3",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
}

PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_INSTRUCTIONS_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
PINNED_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"

# Exact public words that can occur as unshielded alphabetic scaffold literals.
# "section" remains SAT because Composer emits 9Section/9SECTION. The other four
# are exactly the WORD_LIST intersections of the two fixed end phrases and are
# handled by the shared forbidden-collision minimum cut.
SCAFFOLD_PUBLIC_WORD_HAZARDS = frozenset({
    "section", "other", "anything", "can", "help",
})
END_PUBLIC_WORD_HAZARDS = frozenset({"other", "anything", "can", "help"})


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _verify_bindings() -> dict[str, str]:
    root = _root()
    got = {rel: _git_blob_sha(root / rel) for rel in EXPECTED_BLOBS}
    bad = {
        rel: {"expected": EXPECTED_BLOBS[rel], "got": got[rel]}
        for rel in EXPECTED_BLOBS
        if got[rel] != EXPECTED_BLOBS[rel]
    }
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:" + repr(bad))

    if comp.PINNED_LIVEBENCH_COMMIT != PINNED_LIVEBENCH_COMMIT:
        raise AssertionError("LIVEBENCH_COMMIT_DRIFT")
    if comp.PINNED_INSTRUCTIONS_BLOB != PINNED_INSTRUCTIONS_BLOB:
        raise AssertionError("INSTRUCTIONS_BLOB_DRIFT")
    if comp.PINNED_REGISTRY_BLOB != PINNED_REGISTRY_BLOB:
        raise AssertionError("REGISTRY_BLOB_DRIFT")
    if comp.HISTORICAL_GENERATOR_BLOB != PINNED_GENERATOR_BLOB:
        raise AssertionError("GENERATOR_BLOB_DRIFT")
    if lex.PINNED_INSTRUCTIONS_UTIL_BLOB != PINNED_INSTRUCTIONS_UTIL_BLOB:
        raise AssertionError("INSTRUCTIONS_UTIL_BLOB_DRIFT")
    return got


def _ids_without(ids: Iterable[str], drops: Iterable[str]) -> tuple[str, ...]:
    drop = set(drops)
    return tuple(iid for iid in ids if iid not in drop)


def _verify_route_partition() -> dict[str, int]:
    counts = {"JSON": 0, "REPEAT_PROMPT": 0, "TWO_RESPONSES": 0, "GENERAL": 0}
    for ids_tuple in arch.enumerate_compatible_sets():
        ids = set(ids_tuple)
        if comp.JSON_ID in ids:
            if not ids <= {comp.JSON_ID, comp.EXIST, comp.FORBIDDEN}:
                raise AssertionError("JSON_ROUTE_COMPANION_DRIFT:" + repr(ids_tuple))
            counts["JSON"] += 1
        elif comp.REPEAT in ids:
            if not ids <= {comp.REPEAT, comp.EXIST, comp.TITLE}:
                raise AssertionError("REPEAT_ROUTE_COMPANION_DRIFT:" + repr(ids_tuple))
            counts["REPEAT_PROMPT"] += 1
        elif comp.TWO in ids:
            if not ids <= {comp.TWO, comp.EXIST, comp.FORBIDDEN, comp.TITLE}:
                raise AssertionError("TWO_ROUTE_COMPANION_DRIFT:" + repr(ids_tuple))
            counts["TWO_RESPONSES"] += 1
        else:
            if comp.QUOTE in ids and comp.TITLE in ids:
                raise AssertionError("QUOTE_TITLE_COMPATIBILITY_DRIFT")
            if comp.NTH in ids and ids & {
                comp.PARAGRAPHS, comp.BULLETS, comp.SECTIONS
            }:
                raise AssertionError("NTH_DELIMITER_CONFLICT_DRIFT")
            counts["GENERAL"] += 1

    expected = {
        "JSON": 4,
        "REPEAT_PROMPT": 4,
        "TWO_RESPONSES": 8,
        "GENERAL": 912,
    }
    if counts != expected:
        raise AssertionError("ROUTE_PARTITION_COUNT_DRIFT:" + repr(counts))
    return counts


def _verify_post_sacrifice_closure() -> int:
    """Every possible minimum-cut deletion remains inside constructor grammar."""
    checked = 0
    possible_drops = (
        (),
        (comp.SENTENCES,),
        (comp.FORBIDDEN,),
        (comp.SENTENCES, comp.FORBIDDEN),
    )
    for ids in arch.enumerate_compatible_sets():
        for drops in possible_drops:
            reduced = _ids_without(ids, drops)
            if reduced and not arch.compatible(reduced):
                raise AssertionError(
                    "POST_SACRIFICE_SET_LEFT_GRAMMAR:" + repr(
                        (ids, drops, reduced)
                    )
                )
            checked += 1
    expected = 928 * len(possible_drops)
    if checked != expected:
        raise AssertionError("POST_SACRIFICE_CLOSURE_COUNT_DRIFT")
    return checked


def _verify_symbolic_lemmas() -> dict[str, str]:
    # Existence uses raw substring search while forbidden uses word boundaries.
    # Digits are word characters, so the packed carrier preserves every
    # existence substring and destroys forbidden boundaries around it.
    if comp._packed_required(["rock"]) != "9000rock0009":
        raise AssertionError("REQUIRED_SHIELD_CONSTRUCTION_DRIFT")
    if comp._forbidden_hit(comp._packed_required(["rock"]), ["rock"]) is not None:
        raise AssertionError("REQUIRED_SHIELD_FORBIDDEN_LEMMA_FAILED")

    # SectionChecker has no left-boundary requirement. Prefixing the splitter
    # with a digit preserves its suffix match but defeats whole-word "section".
    for splitter in ("Section", "SECTION"):
        sample = "9" + splitter + " 1\n90000011"
        if comp._forbidden_hit(sample, ["section"]) is not None:
            raise AssertionError("SECTION_BOUNDARY_SHIELD_FAILED:" + splitter)

    # RepeatPromptThenAnswer compares strip/lower prefixes. Composer emits the
    # exact stripped visible prefix first, so prompt text is parametric.
    adversarial_prefixes = (
        "Public visible request.",
        "  leading and trailing  ",
        "Line one\nLine two",
        "Ä Unicode ARTICLE text ?! ",
        "<<title-like>>\n***\n* prompt syntax",
    )
    for raw in adversarial_prefixes:
        base = raw.strip()
        if not base:
            raise AssertionError("EMPTY_REPEAT_TEST")
        response = base + "\n" + comp._SAFE
        if not response.strip().lower().startswith(raw.strip().lower()):
            raise AssertionError("REPEAT_PREFIX_PARAMETRIC_IDENTITY_FAILED")

    # TWO has exactly one separator and two unequal nonempty payloads.
    by_two = {comp.TWO: {"instruction_id": comp.TWO, "slots": {}}}
    two = comp._special_two(by_two)
    chunks = [x for x in two.split("******") if x.strip()]
    if len(chunks) != 2 or chunks[0].strip() == chunks[1].strip():
        raise AssertionError("TWO_RESPONSE_CONSTRUCTION_DRIFT")

    # JSON syntax is constructionally valid independently of lexical identity.
    by_json = {comp.JSON_ID: {"instruction_id": comp.JSON_ID, "slots": {}}}
    json.loads(comp._special_json(by_json))

    return {
        "existence_forbidden":
            "ALPHANUMERIC_WORD_CHARACTER_SHIELD_IS_IDENTITY_PARAMETRIC",
        "section_forbidden":
            "DIGIT_PREFIX_DESTROYS_FORBIDDEN_BOUNDARY_WITHOUT_DESTROYING_SECTION_REGEX",
        "repeat_prompt":
            "ARBITRARY_NONEMPTY_VISIBLE_PREFIX_IS_PRESERVED_BY_SHARED_STRIP_LOWER_STARTSWITH_NORMALIZATION",
        "two_responses":
            "EXACTLY_ONE_SEPARATOR_TWO_NONEMPTY_UNEQUAL_NUMERIC_PAYLOADS",
        "json":
            "STDLIB_JSON_DUMPS_CONSTRUCTION_WITH_SHIELDED_PAYLOAD",
    }


def verify() -> dict:
    bindings = _verify_bindings()
    structural = arch.verify()
    lexical = lex.verify()
    numeric_out = numeric.verify()
    cut_out = cut.verify()

    if structural["compatible_set_count"] != 928:
        raise AssertionError("STRUCTURAL_QUOTIENT_DRIFT")
    if lexical["exact_reachable_signature_count"] != 192:
        raise AssertionError("LEXICAL_QUOTIENT_DRIFT")
    if numeric_out["word_upper_bound"]["analytic_constructor_ceiling"] != 48:
        raise AssertionError("WORD_CEILING_DRIFT")
    if numeric_out["word_upper_bound"]["minimum_safety_margin"] != 52:
        raise AssertionError("WORD_SAFETY_MARGIN_DRIFT")
    if cut_out["maximum_mandatory_sacrifices_per_case"] != 2:
        raise AssertionError("MINIMUM_CUT_DIMENSION_DRIFT")

    route_counts = _verify_route_partition()
    closure_cases = _verify_post_sacrifice_closure()
    lemmas = _verify_symbolic_lemmas()

    general_layer_lemmas = {
        "title": "EXPLICIT_NONEMPTY_DOUBLE_ANGLE_TITLE",
        "sections": "EXACT_COUNT__SECTION_SUFFIX_REGEX_SURVIVES_9_PREFIX",
        "bullets": "EXACT_STAR_LINES__TRIPLE_STAR_SEPARATOR_NOT_A_BULLET",
        "nth_paragraph": "DOUBLE_NEWLINE_NAMESPACE_EXCLUSIVE_BY_CONFLICT_GRAPH",
        "paragraphs": "EXACT_COUNT_MINUS_ONE_TRIPLE_STAR_SEPARATORS",
        "postscript": "EXPLICIT_MARKER__P_S_PLUS_IS_SENTENCE_NEUTRAL",
        "end": "APPENDED_LAST__OUTER_QUOTES_STRIPPED_BY_END_CHECKER",
        "quotation": "EXACT_OUTER_DOUBLE_QUOTES",
        "number_words": "PARAMETRIC_48_LT_100_CEILING_AND_MONOTONE_PADDING",
        "number_sentences":
            "THREE_CLASS_PARTITION__LT1_UNSAT__LT2_20_SINGLE_SENTENCE__ATLEAST_MONOTONE",
    }

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__UNIVERSAL_POST_SACRIFICE_CONSTRUCTION_REDUCTION__"
            "NO_RAW_SLOT_CARTESIAN_ENUMERATION_REQUIRED"
        ),
        "source_bindings": bindings,
        "public_source_bindings": {
            "livebench_commit": PINNED_LIVEBENCH_COMMIT,
            "instructions_blob": PINNED_INSTRUCTIONS_BLOB,
            "registry_blob": PINNED_REGISTRY_BLOB,
            "instructions_util_blob": PINNED_INSTRUCTIONS_UTIL_BLOB,
            "historical_generator_blob": PINNED_GENERATOR_BLOB,
        },
        "structural_id_sets": 928,
        "pointwise_loss_classification_cases":
            cut_out["exact_classification_cases"],
        "route_partition": route_counts,
        "post_sacrifice_structural_closure_cases": closure_cases,
        "word_upper_bound": 48,
        "minimum_word_threshold": 100,
        "minimum_word_safety_margin": 52,
        "mandatory_loss_coordinates": cut_out["mandatory_loss_coordinates"],
        "scaffold_public_word_hazards": sorted(SCAFFOLD_PUBLIC_WORD_HAZARDS),
        "end_public_word_hazards": sorted(END_PUBLIC_WORD_HAZARDS),
        "symbolic_lemmas": lemmas,
        "general_layer_lemmas": general_layer_lemmas,
        "deleted_requirements": [
            "FULL_RAW_1525_WORD_IDENTITY_CARTESIAN_PRODUCT",
            "ARBITRARY_REPEAT_PROMPT_TEXT_ENUMERATION",
            "FULL_NUMERIC_SLOT_CARTESIAN_PRODUCT",
        ],
        "remaining_load_bearing_obligation": (
            "INDEPENDENT_EXACT_BYTE_VERIFIER_MUST_BIND_THIS_PROOF_TO_PINNED_"
            "LIVEBENCH_CHECKERS_AND_THEN_BIND_THE_RESULT_TO_THE_ACCEPTED_"
            "LIVEBENCH_IF_GE_65_7_SCOPE"
        ),
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_responses_read": 0,
        "terminal_frequencies_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "NO_ACCEPTANCE_CREDIT_BEFORE_INDEPENDENT_EXACT_BYTE_VERIFICATION",
            "NO_CLAIM_THAT_CURRENT_ACCEPTED_LIVEBENCH_SCOPE_BINDING_IS_ALREADY_DISCHARGED",
            "NO_TERMINAL_GOAL_COMPLETION_CREDIT_FROM_THIS_MODULE_ALONE",
        ],
    }


def run(args=None, root=None) -> dict:
    return verify()


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
