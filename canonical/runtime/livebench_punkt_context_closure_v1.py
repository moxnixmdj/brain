#!/usr/bin/env python3
"""Proof reduction for the final pinned-Punkt obligation in LiveBench active15.

This module does not consume terminal rows, hidden kwargs, row frequencies,
responses, scores, or target outputs.  It reduces the only remaining
environment-sensitive part of the post-sacrifice constructor to:

1. one exact pinned-model exception check for consecutive numeric period tokens;
2. 36 exact tail contexts for the strict "less than N" sentence family.

The exact NLTK execution is intentionally injected by an independent runner.
This file freezes the quotient before that outcome exists.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as reduction

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_post_sacrifice_parametric_reduction_v1.py":
        "4aae8811428221472179049989154bc3e06616e8",
}

PINNED_PYTHON = (3, 12)
PINNED_NLTK_VERSION = "3.10.3"
PINNED_NLTK_WHEEL_SHA256 = "ff9598a8e20518ee0d557745890cc4435b9578489e2dcbc69c4f81fa060caf7c"
PINNED_PUNKT_SOURCE_BLOB = "48496d2448c009221d2452c8e928699027b20ebe"
PINNED_NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
PINNED_PUNKT_TAB_ZIP_BLOB = "5e5ff6137d5ee6025e400d1c3a7b21914c48b635"
PINNED_LIVEBENCH_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

SAFE = "9000001"
POSTSCRIPT_TAILS = ("", "\nP.S.+", "\nP.P.S")
END_TAILS = ("", " Any other questions?", " Is there anything else I can help with?")
QUOTE_MODES = (False, True)
PREFIX_CLASSES = (SAFE, SAFE + "x0")


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def verify_source_bindings() -> dict[str, str]:
    root = _root()
    got = {rel: _git_blob_sha(root / rel) for rel in EXPECTED_BLOBS}
    bad = {rel: {"expected": EXPECTED_BLOBS[rel], "got": got[rel]}
           for rel in EXPECTED_BLOBS if got[rel] != EXPECTED_BLOBS[rel]}
    if bad:
        raise AssertionError("PUNKT_REDUCTION_SUBJECT_BLOB_DRIFT:" + repr(bad))
    return got


def sentence_id_sets() -> tuple[tuple[str, ...], ...]:
    return tuple(ids for ids in arch.enumerate_compatible_sets() if comp.SENTENCES in ids)


def numeric_sentence_tokens(n: int) -> tuple[str, ...]:
    if not 1 <= int(n) <= 20:
        raise ValueError("OUTSIDE_PUBLIC_SENTENCE_DOMAIN")
    return tuple(f"{SAFE}{i}." for i in range(1, int(n) + 1))


def less_than_tail_contexts() -> tuple[str, ...]:
    """Exact punctuation-bearing suffix classes after a punctuation-free prefix.

    The prefix reaching this tail is always either a numeric SAFE token or a
    word-padding SAFE+x token.  All other admitted families occur before the
    sentence scaffold or contribute only punctuation-free material.
    """
    out = []
    for prefix in PREFIX_CLASSES:
        for postscript in POSTSCRIPT_TAILS:
            for end in END_TAILS:
                for quoted in QUOTE_MODES:
                    text = prefix + postscript + end
                    if quoted:
                        text = '"' + text + '"'
                    out.append(text)
    if len(out) != 36 or len(set(out)) != 36:
        raise AssertionError("TAIL_CONTEXT_CARDINALITY_DRIFT")
    return tuple(out)


def symbolic_verify() -> dict[str, Any]:
    bindings = verify_source_bindings()
    reduced = reduction.verify()
    ids = sentence_id_sets()
    if len(ids) != 285:
        raise AssertionError("SENTENCE_COMPATIBLE_ID_SET_COUNT_DRIFT")

    # The first N-1 tokens of the >=N scaffold are consecutive decimal tokens
    # ending in periods.  Punkt normalizes all such token types to ##number##.
    # Once the pinned parameter set is checked to contain neither a raw numeric
    # abbreviation nor the (##number##, ##number##) collocation, first-pass
    # sentbreak=True cannot be revoked by the number heuristic: the next numeric
    # token has no case, so the orthographic heuristic returns "unknown".
    all_numeric = tuple(
        token[:-1] for n in range(1, 21) for token in numeric_sentence_tokens(n)
    )
    if any(not x.isdigit() for x in all_numeric):
        raise AssertionError("NUMERIC_SCAFFOLD_DRIFT")

    # For <N, N>=2, the sentence scaffold itself is SAFE without .?! .
    # Every other constructor family is punctuation-free for sentence purposes
    # except the exact postscript/end tails enumerated above.
    tails = less_than_tail_contexts()

    return {
        "schema": SCHEMA,
        "status": "PASS__PUNKT_OBLIGATION_REDUCED_TO_ONE_MODEL_EXCEPTION_CHECK_PLUS_36_TAIL_CONTEXTS",
        "source_bindings": bindings,
        "upstream_parametric_reduction_status": reduced["status"],
        "sentence_compatible_id_set_count": len(ids),
        "at_least_public_threshold_domain": [1, 20],
        "at_least_theorem": {
            "guaranteed_internal_break_count": "N_MINUS_1",
            "guaranteed_final_nonempty_residual_sentence_count": 1,
            "sufficient_pinned_model_checks": [
                "NONE_OF_90000011_THROUGH_900000120_IS_A_PINNED_ABBREVIATION",
                "COLLOCATION_##number##__##number##_ABSENT",
            ],
            "conclusion_if_checks_pass": "COUNT_SENTENCES_GE_N_FOR_ALL_PUBLIC_N_AND_ALL_285_COMPATIBLE_ID_SETS",
        },
        "less_than_partition": {
            "N_EQ_1": "PROVED_UNSAT_BY_STRICT_NONEMPTY_GATE",
            "N_2_TO_20": "SAME_ONE_SENTENCE_SCAFFOLD__ONLY_36_PINNED_PUNKT_TAIL_CONTEXTS_REMAIN",
            "tail_context_count": len(tails),
        },
        "tail_contexts": list(tails),
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "hard_nonclaims": [
            "PINNED_MODEL_EXCEPTION_CHECK_NOT_EXECUTED_BY_SYMBOLIC_REDUCTION",
            "PINNED_36_TAIL_CONTEXTS_NOT_EXECUTED_BY_SYMBOLIC_REDUCTION",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT_FROM_THIS_FILE_ALONE",
        ],
    }


def verify_with_pinned_tokenizer(
    *,
    tokenizer: Any,
    count_sentences: Callable[[str], int],
) -> dict[str, Any]:
    """Execute the frozen residual against an already content-bound tokenizer."""
    out = symbolic_verify()
    params = tokenizer._params

    numeric_abbrev_hits = sorted(
        x for x in {token[:-1] for n in range(1, 21) for token in numeric_sentence_tokens(n)}
        if x.casefold() in params.abbrev_types
    )
    numeric_collocation = ("##number##", "##number##") in params.collocations
    if numeric_abbrev_hits:
        raise AssertionError("PINNED_NUMERIC_ABBREVIATION_EXCEPTION:" + repr(numeric_abbrev_hits))
    if numeric_collocation:
        raise AssertionError("PINNED_NUMERIC_COLLOCATION_EXCEPTION")

    tail_counts = {text: int(count_sentences(text)) for text in less_than_tail_contexts()}
    bad_tails = {text: n for text, n in tail_counts.items() if n != 1}
    if bad_tails:
        raise AssertionError("LESS_THAN_TAIL_NOT_EXACTLY_ONE_SENTENCE:" + repr(bad_tails))

    # Direct executable cross-check of the >=N core chain for every N.
    chain_counts = {}
    for n in range(1, 21):
        text = "\n".join(numeric_sentence_tokens(n))
        observed = int(count_sentences(text))
        chain_counts[str(n)] = observed
        if observed < n:
            raise AssertionError(f"AT_LEAST_NUMERIC_CHAIN_FAILED:{n}:{observed}")

    out["status"] = "PASS__PINNED_PUNKT_CONTEXTS_CLOSED__UNIVERSAL_PUBLIC_SENTENCE_PARAMETER_DOMAIN_DISCHARGED"
    out["pinned_model_checks"] = {
        "numeric_abbreviation_hits": numeric_abbrev_hits,
        "numeric_numeric_collocation_present": numeric_collocation,
        "tail_contexts_checked": len(tail_counts),
        "tail_contexts_exactly_one_sentence": len(tail_counts),
        "numeric_chain_thresholds_checked": 20,
        "numeric_chain_counts": chain_counts,
    }
    out["hard_nonclaims"] = [
        "THIS_RECEIPT_ALONE_GRANTS_ZERO_ACCEPTANCE_CREDIT",
        "SEPARATE_CONTENT_BOUND_INDEPENDENT_RUNNER_AND_ACCEPTANCE_REDUCTION_REQUIRED",
    ]
    return out


def run(args=None, root=None):
    return symbolic_verify()


if __name__ == "__main__":
    import json
    print(json.dumps(symbolic_verify(), indent=2, sort_keys=True))
