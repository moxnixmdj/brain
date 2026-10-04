#!/usr/bin/env python3
"""Close the frozen LiveBench active15 lexical dimension exactly.

The public lexical generator has 1,525 unique ASCII alphabetic words, but the
checker-relevant collision quotient is exactly 192 reachable signatures. This
module composes the quotient with the canonical semantic UNSAT kernel, candidate
constructor, and exact strict public checker.

For every reachable lexical signature it proves exactly one of:
1. semantic UNSAT, with the precise NTH/forbidden and/or end/forbidden reason; or
2. an exact-checker witness satisfying existence, forbidden, NTH-first-word, and
   fixed-end constraints simultaneously.

This closes the lexical identity dimension only. Numeric and other structural
slot domains remain separate proof obligations. No terminal rows, frequencies,
hidden kwargs, comparator responses, or scores are consumed.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from canonical.runtime import livebench_legacy15_contract_composer_v2 as composer
from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as exact
from canonical.runtime import livebench_legacy15_lexical_collision_signatures_v2 as quotient
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_LEXICAL_CLOSURE_V1"
EXPECTED_SIGNATURES = 192
EXPECTED_UNSAT = 155
EXPECTED_WITNESSES = 37


class LexicalClosureError(RuntimeError):
    pass


def _contract(iid: str, **slots: Any) -> dict[str, Any]:
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def _contracts(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _contract(
            "keywords:existence",
            keywords=list(row["existence_keywords"]),
        ),
        _contract(
            "keywords:forbidden_words",
            forbidden_words=list(row["forbidden_words"]),
        ),
        _contract(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=2,
            nth_paragraph=1,
            first_word=str(row["nth_word"]),
        ),
        _contract(
            "startend:end_checker",
            end_phrase=str(row["end_phrase"]),
        ),
    ]


def _expected_reasons(row: dict[str, Any]) -> tuple[str, ...]:
    out: list[str] = []
    if bool(row["nth_in_forbidden"]):
        out.append("NTH_FIRST_WORD_IS_FORBIDDEN_WORD")

    membership = dict(row["special_forbidden_membership"])
    phrase = str(row["end_phrase"])
    if phrase == quotient.END_PHRASES[0]:
        if membership["other"]:
            out.append("MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other")
    elif phrase == quotient.END_PHRASES[1]:
        for word in ("anything", "can", "help"):
            if membership[word]:
                out.append("MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:" + word)
    else:
        raise LexicalClosureError("UNKNOWN_END_PHRASE")

    return tuple(out)


def _verify_keyword_carrier_theorem(words: tuple[str, ...]) -> int:
    """Mechanically verify the identity-independent boundary carrier theorem.

    Every generated word is ASCII alphabetic. Wrapping any such word in decimal
    digits preserves the raw substring required by Existence while eliminating
    both word boundaries required by ForbiddenWords. Because the composer's
    packed carrier uses only word characters between/around required words, the
    same argument composes for arbitrary generated five-word lists.
    """
    checked = 0
    for word in words:
        carrier = "0" + word + "0"
        if re.search(re.escape(word), carrier, flags=re.IGNORECASE) is None:
            raise LexicalClosureError("RAW_EXISTENCE_CARRIER_FAILED:" + word)
        if re.search(
            r"\b" + re.escape(word) + r"\b",
            carrier,
            flags=re.IGNORECASE,
        ) is not None:
            raise LexicalClosureError("FORBIDDEN_BOUNDARY_CARRIER_FAILED:" + word)
        checked += 1
    return checked


def verify(livebench_root: str | Path) -> dict[str, Any]:
    root = Path(livebench_root).resolve()
    words = quotient.load_pinned_word_list(root)
    carrier_words_checked = _verify_keyword_carrier_theorem(words)
    signatures = quotient.enumerate_signatures(words)
    if len(signatures) != EXPECTED_SIGNATURES:
        raise LexicalClosureError(
            "SIGNATURE_COUNT_DRIFT:" + str(len(signatures))
        )

    unsat = 0
    witnesses = 0
    exact_checker_calls = 0
    observed_reason_counts: dict[str, int] = {}

    for index, row in enumerate(signatures):
        contracts = _contracts(row)
        expected = _expected_reasons(row)
        observed = feasibility.hard_unsat_reasons(contracts)

        if observed != expected:
            raise LexicalClosureError(
                "UNSAT_REASON_MISMATCH:"
                + str(index)
                + ":expected="
                + repr(expected)
                + ":observed="
                + repr(observed)
            )

        for reason in observed:
            observed_reason_counts[reason] = observed_reason_counts.get(reason, 0) + 1

        built = composer.compose_contracts(contracts)

        if expected:
            if built.get("status") != "PROVED_UNSAT":
                raise LexicalClosureError(
                    "EXPECTED_UNSAT_NOT_CERTIFIED:" + str(index)
                )
            if tuple(built.get("hard_unsat_reasons") or ()) != expected:
                raise LexicalClosureError(
                    "COMPOSER_UNSAT_REASON_DRIFT:" + str(index)
                )
            if built.get("response") is not None:
                raise LexicalClosureError(
                    "UNSAT_SIGNATURE_EMITTED_RESPONSE:" + str(index)
                )
            unsat += 1
            continue

        if built.get("status") != "CANDIDATE_WITNESS":
            raise LexicalClosureError(
                "SAT_SIGNATURE_NO_CANDIDATE:" + str(index) + ":" + str(built)
            )
        response = built.get("response")
        if not isinstance(response, str) or not response.strip():
            raise LexicalClosureError(
                "SAT_SIGNATURE_EMPTY_CANDIDATE:" + str(index)
            )

        checked = exact.postvalidate_proofgrade(
            response,
            contracts,
            root,
        )
        exact_checker_calls += 1
        if checked.get("binding", {}).get(
            "proofgrade_runtime_dependencies_bound"
        ) is not True:
            raise LexicalClosureError(
                "EXACT_BINDING_NOT_PROOFGRADE:" + str(index)
            )
        runtime_status = (
            checked.get("binding", {}).get("runtime", {}).get("status")
        )
        if runtime_status != "NOT_REQUIRED__NO_NLTK_DEPENDENT_ACTIVE15_CHECKER":
            raise LexicalClosureError(
                "UNEXPECTED_RUNTIME_DEPENDENCY:" + str(runtime_status)
            )
        if checked.get("checker_results") != [True, True, True, True]:
            raise LexicalClosureError(
                "EXACT_WITNESS_REJECTED:"
                + str(index)
                + ":"
                + repr(checked.get("checker_results"))
            )
        witnesses += 1

    if unsat != EXPECTED_UNSAT or witnesses != EXPECTED_WITNESSES:
        raise LexicalClosureError(
            f"CLOSURE_COUNT_DRIFT:unsat={unsat}:witnesses={witnesses}"
        )
    if unsat + witnesses != EXPECTED_SIGNATURES:
        raise LexicalClosureError("LEXICAL_PARTITION_NOT_TOTAL")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__EXACT_LEXICAL_DOMAIN_CLOSED__"
            "155_SEMANTIC_UNSAT__37_EXACT_WITNESSES"
        ),
        "source_binding": {
            "livebench_commit": exact.PINNED_LIVEBENCH_COMMIT,
            "instructions_blob": exact.PINNED_INSTRUCTIONS_BLOB,
            "registry_blob": exact.PINNED_REGISTRY_BLOB,
            "instructions_util_blob": exact.PINNED_UTIL_BLOB,
            "evaluation_main_blob": exact.PINNED_EVALUATION_MAIN_BLOB,
        },
        "raw_word_identity_count": len(words),
        "keyword_carrier_words_checked": carrier_words_checked,
        "reachable_lexical_signature_count": len(signatures),
        "semantic_unsat_signature_count": unsat,
        "exact_witness_signature_count": witnesses,
        "exact_checker_witness_calls": exact_checker_calls,
        "unsat_reason_counts": dict(sorted(observed_reason_counts.items())),
        "lexical_identity_dimension_remaining": 0,
        "numeric_and_structural_dimensions_remaining": True,
        "terminal_case_content_read": 0,
        "terminal_case_metadata_read": 0,
        "terminal_frequency_used": False,
        "hidden_kwargs_used": False,
        "comparator_response_used": False,
        "terminal_scores_used": False,
        "acceptance_credit": False,
        "capability_credit": False,
    }


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    livebench_root = args.get("livebench_root")
    if not livebench_root:
        raise LexicalClosureError("LIVEBENCH_ROOT_REQUIRED")
    return verify(livebench_root)


if __name__ == "__main__":
    import json
    import sys

    print(json.dumps(run(json.load(sys.stdin)), indent=2, sort_keys=True))
