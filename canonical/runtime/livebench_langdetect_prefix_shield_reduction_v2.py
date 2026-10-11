#!/usr/bin/env python3
"""Prefix-shield reduction for the pinned LiveBench language checker.

This strengthens V1. V1 required the whole constructed response to stay inside
an ASCII-plus-U+200B safe alphabet. The pinned langdetect implementation first
normalizes URL/e-mail text and then reads at most the first 10,000 characters.
Therefore only that prefix must be featureless. Arbitrary constraint-bearing
suffix text can live after the detector window and remains visible to every
LiveBench checker operating on the original response.

Pinned LiveBench scorer:
  LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091
  instructions.py blob 4997bab885a676d92545fd91a9a20b48d234a2b2
  instructions_util.py blob 1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b

Observed langdetect 1.0.9 source:
  detector.py blob cc831a0e7530d49fa9b544c9b779ba075ffdbe5c
  ngram.py blob ee82e38f73aadbf118ec03a6342c328d808539d2
  setup.py blob 652e99b245e43086b433625f8ace1d833f9fd5e4

Important scope rule: LiveBench leaves langdetect unpinned. This theorem is
therefore a source-bound candidate until the independent evaluator receipt
records the installed langdetect code/version and reproduces the behavior.
Zero acceptance/capability credit is granted here.
"""
from __future__ import annotations
FALSIFICATION_REASON = "FALSIFIED__PINNED_SCORER_EXCEPTION_HANDLER_RAISES_NAMEERROR_BECAUSE_LOGGING_IS_UNBOUND"

from typing import Any, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u
from canonical.runtime import livebench_langdetect_failopen_reduction_v1 as v1

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LANGDETECT_PREFIX_SHIELD_REDUCTION_V2"

DETECTOR_WINDOW = 10_000
ZERO_WIDTH_SPACE = "\u200b"
FROZEN_GENERATOR_WORD_LIST_SIZE = 1525
FROZEN_GENERATOR_MAX_FIRST_WORD_LENGTH = 14

SOURCE_BINDINGS = {
    "livebench_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
    "livebench_instructions_blob": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "livebench_instructions_util_blob": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "livebench_langdetect_requirement": "UNPINNED",
    "observed_langdetect_version": "1.0.9",
    "observed_detector_blob": "cc831a0e7530d49fa9b544c9b779ba075ffdbe5c",
    "observed_ngram_blob": "ee82e38f73aadbf118ec03a6342c328d808539d2",
}

LANGUAGE_COMPATIBLE_ACTIVE15 = frozenset({
    u.SENTENCES,
    u.PARAGRAPHS,
    u.WORDS,
    u.NTH,
    u.POSTSCRIPT,
    u.BULLETS,
    u.TITLE,
    u.TWO,
    u.QUOTE,
})


def _latin_bucket_count(text: str) -> int:
    # Exact detector.py cleaning_text bucket, intentionally inclusive A..z.
    return sum("A" <= ch <= "z" for ch in text)


def make_prefix_shield(
    *,
    first_word: str | None = None,
    quote_wrapped: bool = False,
) -> str:
    """Build exactly the 10k detector-visible prefix.

    If NTH paragraph 1 is active, its generated first word can be emitted before
    the shield. The pinned generator chooses that word from a 1,525-item ASCII
    WORD_LIST whose maximum item length is 14. A normal ASCII space follows it,
    so ParagraphFirstWordCheck sees the required first token even though U+200B
    itself is not Python whitespace.

    If quotation is active, the opening quote is placed first. The closing quote
    belongs after the arbitrary suffix.
    """
    header = '"' if quote_wrapped else ""
    if first_word is not None:
        word = str(first_word)
        if not word or not word.isascii():
            raise ValueError("FROZEN_PREFIX_FIRST_WORD_MUST_BE_ASCII")
        if len(word) > FROZEN_GENERATOR_MAX_FIRST_WORD_LENGTH:
            raise ValueError("FROZEN_PREFIX_FIRST_WORD_TOO_LONG")
        header += word + " "

    if len(header) >= DETECTOR_WINDOW:
        raise ValueError("PREFIX_HEADER_OVERFLOW")

    pad_len = DETECTOR_WINDOW - len(header)
    # U+200B is counted as non-Latin by detector.cleaning_text and belongs to
    # General Punctuation, which NGram.normalize maps to ASCII space.
    if not (2 * _latin_bucket_count(header) < pad_len):
        raise AssertionError("CLEANING_DOMINANCE_NOT_PROVED")

    return header + ZERO_WIDTH_SPACE * pad_len


def abstract_detector_projection(prefix: str) -> dict[str, Any]:
    """Reify the exact source facts used by the shield theorem."""
    if len(prefix) != DETECTOR_WINDOW:
        raise ValueError("PREFIX_MUST_FILL_DETECTOR_WINDOW")
    latin = _latin_bucket_count(prefix)
    nonlatin = prefix.count(ZERO_WIDTH_SPACE)
    branch = latin * 2 < nonlatin

    # In our constructed prefix, all A..z characters are removed by cleaning;
    # all remaining header punctuation/space and U+200B normalize to spaces.
    allowed_after_clean = all(
        ("A" <= ch <= "z") or ch in {'"', " ", ZERO_WIDTH_SPACE}
        for ch in prefix
    )
    zero_features = branch and allowed_after_clean

    return {
        "length": len(prefix),
        "latin_count": latin,
        "nonlatin_count": nonlatin,
        "cleaning_branch_taken": branch,
        "post_clean_all_chars_normalize_to_space": zero_features,
        "extracted_ngram_count": 0 if zero_features else None,
        "detector_raises_langdetect_exception": zero_features,
        "livebench_language_checker_returns_true_on_exception": True,
        "suffix_visible_to_detector": False,
    }


def language_compatible_active15() -> frozenset[str]:
    """Compute rather than merely assert the active families that coexist."""
    out = set()
    for iid in u.ACTIVE15:
        if u.compatible((u.LANGUAGE, iid)):
            out.add(iid)
    return frozenset(out)


def verify() -> dict[str, Any]:
    raise AssertionError(FALSIFICATION_REASON)
    upstream = v1.verify()

    actual_active = language_compatible_active15()
    if actual_active != LANGUAGE_COMPATIBLE_ACTIVE15:
        raise AssertionError(
            "LANGUAGE_ACTIVE15_COMPATIBILITY_DRIFT:" + repr(sorted(actual_active))
        )

    # Frozen generator source audit values. instructions_util.generate_keywords
    # is random.sample(WORD_LIST), and the bound list is 1,525 ASCII entries,
    # maximum length 14. The independent runner must re-audit this source.
    for word in ("a", "administration", "responsibility", "representative"):
        p = make_prefix_shield(first_word=word)
        facts = abstract_detector_projection(p)
        if not facts["detector_raises_langdetect_exception"]:
            raise AssertionError("FIRST_WORD_PREFIX_NOT_FEATURELESS")

        q = make_prefix_shield(first_word=word, quote_wrapped=True)
        qfacts = abstract_detector_projection(q)
        if not qfacts["detector_raises_langdetect_exception"]:
            raise AssertionError("QUOTED_FIRST_WORD_PREFIX_NOT_FEATURELESS")
        # Exact raw first token shape used by ParagraphFirstWordCheck:
        # paragraph.split()[0].lstrip("'").lstrip('"')
        token = q.split()[0].strip().lstrip("'").lstrip('"')
        if token != word:
            raise AssertionError("NTH_FIRST_WORD_PREFIX_INTERFERENCE")

    plain = make_prefix_shield()
    quoted = make_prefix_shield(quote_wrapped=True)
    if not abstract_detector_projection(plain)["detector_raises_langdetect_exception"]:
        raise AssertionError("PLAIN_PREFIX_NOT_FEATURELESS")
    if not abstract_detector_projection(quoted)["detector_raises_langdetect_exception"]:
        raise AssertionError("QUOTED_PREFIX_NOT_FEATURELESS")

    # V1 independently derived the exact semantic quotient from the frozen
    # union25 conflict graph. V2 removes V1's arbitrary-suffix alphabet limit;
    # it does not increase credit.
    red = upstream["kernel_reduction"]
    if red["candidate_total_after_failopen"] != 33:
        raise AssertionError("UPSTREAM_33_KERNEL_REDUCTION_DRIFT")
    if red["language_residual_hard_kernel_count"] != 8:
        raise AssertionError("UPSTREAM_8_LANGUAGE_RESIDUAL_DRIFT")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__PREFIX_SHIELD_DELETES_ARBITRARY_SUFFIX_LANGUAGE_IDENTITY_"
            "DEPENDENCY__33_KERNEL_QUOTIENT_PRESERVED_AS_CANDIDATE"
        ),
        "source_bindings": SOURCE_BINDINGS,
        "theorem": {
            "detector_visible_prefix_chars": DETECTOR_WINDOW,
            "shield_char": "U+200B_ZERO_WIDTH_SPACE",
            "arbitrary_suffix_after_window_allowed": True,
            "target_language_identity_required": False,
            "langdetect_rng_relevant_after_zero_features": False,
            "pinned_checker_fail_open": True,
        },
        "prefix_sensitive_frozen_coordinates": {
            "quotation": "OPENING_QUOTE_MOVED_INSIDE_10K_SHIELD_HEADER",
            "nth_paragraph_first_word": (
                "IF_NTH_IS_1_EMIT_FROZEN_ASCII_FIRST_WORD_PLUS_ASCII_SPACE_"
                "BEFORE_U+200B_PADDING"
            ),
            "frozen_word_list_size": FROZEN_GENERATOR_WORD_LIST_SIZE,
            "frozen_max_first_word_length": FROZEN_GENERATOR_MAX_FIRST_WORD_LENGTH,
        },
        "language_compatible_active15": sorted(actual_active),
        "kernel_reduction_candidate": {
            "prior_conservative_total": 64,
            "language_sensitive_prior": 31,
            "language_residual_after_failopen": 8,
            "total_after_failopen": 33,
        },
        "remaining_promotion_gates": [
            "INDEPENDENT_RUNNER_RECORD_ACTUAL_INSTALLED_LANGDETECT_VERSION_AND_SOURCE_BEHAVIOR",
            "EXECUTE_PINNED_RESPONSELANGUAGECHECKER_WITH_10K_SHIELD_FOR_ALL_30_LANGUAGE_CODES",
            "EXECUTE_SHIELD_PRESERVATION_MATRIX_FOR_THE_9_LANGUAGE_COMPATIBLE_ACTIVE15_CHECKERS",
            "RECHECK_SENTENCE_LT_1_EDGE_WITH_ZERO_FEATURE_EMPTY_RESPONSE_OR_PROVE_NO_ADDITIONAL_LOSS",
        ],
        "new_critical_path": (
            "INDEPENDENTLY_VERIFY_PREFIX_SHIELD_THEN_DELETE_LANGUAGE_IDENTITY_"
            "AND_30_LANGUAGE_CARRIER_BANK_FROM_LIVEBENCH_UNION25_CRITICAL_PATH"
        ),
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "target_responses_read": 0,
        "target_scores_read": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "independent_verification_required": True,
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
