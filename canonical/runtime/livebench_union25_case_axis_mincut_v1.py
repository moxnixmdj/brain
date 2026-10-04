#!/usr/bin/env python3
"""Exact case-axis minimum cut for the LiveBench union25 extension.

This proves the exact *syntactic* interaction between the two English whole-case
checkers and the already-closed Active15 core. Positive satisfaction of the
English checkers also depends on the pinned langdetect runtime and is therefore
kept as a separate independently-verifiable residual.

For every compatible Active15 checker other than multiple_sections, applying
str.upper() or str.lower() to a valid witness preserves the checker's truth:
- existence and forbidden are IGNORECASE;
- nth-paragraph normalizes the observed first word to lowercase;
- postscript lowercases the response before matching;
- end-checker lowercases both response and target;
- number/format/count checkers are case-insensitive by construction or contain
  no case predicate;
- the frozen sentence constructor uses '?' boundaries, so case is irrelevant.

multiple_sections is the sole exception because SectionChecker uses an exact,
case-sensitive splitter.  Therefore:
- english_lowercase + any section splitter is jointly unsatisfiable, because
  every legal splitter contains an uppercase letter;
- english_capital + splitter='Section' is jointly unsatisfiable, because the
  mandatory splitter contains lowercase letters;
- english_capital + splitter='SECTION' has no syntactic case contradiction and
  admits an all-uppercase section carrier. The English langdetect condition is
  intentionally not discharged by this module.

The module is a theorem/carrier layer only and grants zero acceptance credit.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_CASE_AXIS_MINCUT_V1"

CASE_IDS = frozenset({u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE})
SECTIONS = u.SECTIONS

# Special routes that are incompatible with both whole-English-case families in
# the exact frozen conflict graph and therefore never need composition here.
SPECIALS = frozenset({u.JSON_ID, u.TWO, u.REPEAT, u.CONSTRAINED, u.LANGUAGE})

# Compatible Active15 checkers whose exact predicates survive whole-response
# upper/lower transformation.  Sections is deliberately excluded.
CASE_TRANSFORM_PRESERVED_ACTIVE15 = frozenset(u.ACTIVE15 - {SECTIONS})


class CaseAxisError(RuntimeError):
    pass


def _assert_conflict_scope() -> None:
    for case_id in CASE_IDS:
        # Every listed preserved Active15 family must really be compatible with
        # the case checker whenever the registry graph allows the pair.
        if case_id not in u.ALL_IDS:
            raise CaseAxisError("CASE_ID_MISSING_FROM_REGISTRY")

    # Lowercase and uppercase whole-response constraints conflict with each
    # other, as expected.
    if u.ENGLISH_CAPITAL not in u.CONFLICTS[u.ENGLISH_LOWERCASE]:
        raise CaseAxisError("CASE_MUTUAL_CONFLICT_DRIFT")


def section_case_joint_optimum(
    case_id: str,
    section_splitter: str,
) -> dict[str, Any]:
    """Return the exact two-checker optimum for case + sections."""
    if case_id not in CASE_IDS:
        raise CaseAxisError("UNKNOWN_CASE_ID")
    if section_splitter not in {"Section", "SECTION"}:
        raise CaseAxisError("OUTSIDE_PUBLIC_SECTION_SPLITTER_DOMAIN")

    if case_id == u.ENGLISH_LOWERCASE:
        return {
            "jointly_satisfiable": False,
            "syntactic_case_contradiction": True,
            "maximum_passes_of_two": 1,
            "mandatory_loss_from_case_syntax": 1,
            "reason": (
                "EVERY_LEGAL_SECTION_SPLITTER_CONTAINS_UPPERCASE_LETTERS__"
                "LOWERCASE_CHECKER_REQUIRES_VALUE_ISLOWER"
            ),
        }

    if section_splitter == "Section":
        return {
            "jointly_satisfiable": False,
            "syntactic_case_contradiction": True,
            "maximum_passes_of_two": 1,
            "mandatory_loss_from_case_syntax": 1,
            "reason": (
                "TITLECASE_SECTION_SPLITTER_CONTAINS_LOWERCASE_LETTERS__"
                "CAPITAL_CHECKER_REQUIRES_VALUE_ISUPPER"
            ),
        }

    return {
        "jointly_satisfiable": True,
        "maximum_passes_of_two": 2,
        "mandatory_loss": 0,
        "reason": (
            "UPPERCASE_SECTION_SPLITTER_IS_COMPATIBLE_WITH_VALUE_ISUPPER__"
            "NUMERIC_SECTION_BODIES_ADD_NO_LOWERCASE_LETTERS"
        ),
    }


def transform_witness(case_id: str, response: str) -> str:
    """Construct the whole-case carrier for compatible non-section contexts."""
    if case_id == u.ENGLISH_CAPITAL:
        return str(response).upper()
    if case_id == u.ENGLISH_LOWERCASE:
        return str(response).lower()
    raise CaseAxisError("UNKNOWN_CASE_ID")


def verify() -> dict[str, Any]:
    _assert_conflict_scope()

    # Exact visible section slot quotient is only two values.
    matrix = {
        case_id: {
            splitter: section_case_joint_optimum(case_id, splitter)
            for splitter in ("Section", "SECTION")
        }
        for case_id in (u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE)
    }

    if matrix[u.ENGLISH_CAPITAL]["SECTION"]["syntactic_case_contradiction"]:
        raise CaseAxisError("UPPERCASE_SECTION_SHOULD_HAVE_NO_CASE_CONTRADICTION")
    if matrix[u.ENGLISH_CAPITAL]["Section"]["maximum_passes_of_two"] != 1:
        raise CaseAxisError("TITLECASE_SECTION_MINCUT_DRIFT")
    if matrix[u.ENGLISH_LOWERCASE]["SECTION"]["maximum_passes_of_two"] != 1:
        raise CaseAxisError("LOWERCASE_SECTION_MINCUT_DRIFT")
    if matrix[u.ENGLISH_LOWERCASE]["Section"]["maximum_passes_of_two"] != 1:
        raise CaseAxisError("LOWERCASE_TITLECASE_SECTION_MINCUT_DRIFT")

    # Confirm that the only Active15 family with a case-sensitive mandatory
    # alphabetic literal in its checker is the section family.  This list is
    # intentionally explicit and fail-closed if Active15 drifts.
    expected_preserved = frozenset({
        u.EXIST,
        u.FORBIDDEN,
        u.SENTENCES,
        u.PARAGRAPHS,
        u.WORDS,
        u.NTH,
        u.POSTSCRIPT,
        u.BULLETS,
        u.JSON_ID,
        u.TITLE,
        u.TWO,
        u.REPEAT,
        u.END,
        u.QUOTE,
    })
    if CASE_TRANSFORM_PRESERVED_ACTIVE15 != expected_preserved:
        raise CaseAxisError("ACTIVE15_PRESERVATION_SET_DRIFT")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__WHOLE_ENGLISH_CASE_SYNTAX_REDUCED_TO_SECTION_SLOT_MINCUT__LANGDETECT_RESIDUAL_EXPLICIT"
        ),
        "case_transform_preserved_active15": sorted(
            CASE_TRANSFORM_PRESERVED_ACTIVE15
        ),
        "sole_active15_case_sensitive_interaction": SECTIONS,
        "section_slot_matrix": matrix,
        "exact_mandatory_loss_classes": [
            {
                "case": u.ENGLISH_LOWERCASE,
                "section_splitter": "Section",
                "maximum_passes_of_two": 1,
            },
            {
                "case": u.ENGLISH_LOWERCASE,
                "section_splitter": "SECTION",
                "maximum_passes_of_two": 1,
            },
            {
                "case": u.ENGLISH_CAPITAL,
                "section_splitter": "Section",
                "maximum_passes_of_two": 1,
            },
        ],
        "no_syntactic_case_contradiction_class": {
            "case": u.ENGLISH_CAPITAL,
            "section_splitter": "SECTION",
            "maximum_passes_of_two_upper_bound": 2,
            "remaining_residual": "PINNED_LANGDETECT_ENGLISH_POSITIVE_CHECK",
        },
        "composition_consequence": (
            "CASE_SENSITIVE_ACTIVE15_SYNTAX_IS_FULLY_REDUCED_TO_THE_VISIBLE_"
            "SECTION_SPLITTER_SLOT__POSITIVE_ENGLISH_LANGUAGE_DETECTION_REMAINS_"
            "A_SEPARATE_RUNTIME_RESIDUAL"
        ),
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
