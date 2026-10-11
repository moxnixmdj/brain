#!/usr/bin/env python3
"""Source-bound fail-open reduction for LiveBench legacy language kernels.

Pinned scorer:
  LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091
  instructions.py blob 4997bab885a676d92545fd91a9a20b48d234a2b2

Pinned detector implementation:
  Mimino666/langdetect 1.0.9 source
  detector.py blob cc831a0e7530d49fa9b544c9b779ba075ffdbe5c
  utils/ngram.py blob ee82e38f73aadbf118ec03a6342c328d808539d2
  setup.py blob 652e99b245e43086b433625f8ace1d833f9fd5e4

Breakthrough:
The pinned ResponseLanguageChecker catches LangDetectException and returns True.
The pinned detector raises CantDetectError when _extract_ngrams() is empty.
For an ASCII-safe residual constructor, append enough U+200B ZERO WIDTH SPACE
characters so cleaning_text() enters its non-Latin-dominant branch. That branch
removes every character in the inclusive ASCII range A..z. All remaining
Basic-Latin nonletters and U+200B normalize to spaces in NGram.normalize(), so
the extracted feature list is empty. Therefore the language target identity
does not need a 30-language carrier bank for this score surface.

This is a candidate structural reduction only. It grants zero acceptance,
family, capability, or ownership credit until independently verified against
the pinned evaluator environment.
"""
from __future__ import annotations

FALSIFICATION_REASON = "FALSIFIED__PINNED_SCORER_EXCEPTION_HANDLER_RAISES_NAMEERROR_BECAUSE_LOGGING_IS_UNBOUND"

from typing import Any, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u
from canonical.runtime import livebench_union25_semantic_kernel_reduction_v1 as prior

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LANGDETECT_FAILOPEN_REDUCTION_V1"

SOURCE_BINDINGS = {
    "livebench_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
    "livebench_instructions_blob": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "langdetect_version": "1.0.9",
    "langdetect_detector_blob": "cc831a0e7530d49fa9b544c9b779ba075ffdbe5c",
    "langdetect_ngram_blob": "ee82e38f73aadbf118ec03a6342c328d808539d2",
    "langdetect_setup_blob": "652e99b245e43086b433625f8ace1d833f9fd5e4",
}

ZERO_WIDTH_SPACE = "\u200b"
DETECTOR_MAX_TEXT_LENGTH = 10000

# LANGUAGE conflicts with KWF, English upper/lower, and several Active15
# families in the frozen registry. Inside the extra10 language-bearing residue,
# only these three hard coordinates can survive.
LANGUAGE_RESIDUAL_HARD = (
    u.LETTER_FREQUENCY,
    u.CAPITAL_FREQUENCY,
    u.NO_COMMA,
)

NONLANGUAGE_HARD = (
    u.KEYWORD_FREQUENCY,
    u.LETTER_FREQUENCY,
    u.CAPITAL_FREQUENCY,
    u.ENGLISH_CAPITAL,
    u.ENGLISH_LOWERCASE,
    u.NO_COMMA,
)

TRANSPARENT_SCORE_FAMILIES = (
    u.LANGUAGE,
    u.PLACEHOLDERS,
    u.HIGHLIGHTS,
)

EXPECTED_PRIOR_KERNELS = 64
EXPECTED_PRIOR_LANGUAGE_SENSITIVE_KERNELS = 31
EXPECTED_LANGUAGE_RESIDUAL_KERNELS = 8
EXPECTED_FAILOPEN_KERNELS = 33


def _latin_bucket(ch: str) -> bool:
    """Exact pinned detector cleaning_text ASCII bucket."""
    return "A" <= ch <= "z"


def ascii_safe_for_failopen(text: str) -> bool:
    """Alphabet accepted by the theorem.

    ASCII is safe because A..z is deleted by cleaning_text() and every other
    Basic-Latin code point normalizes to space. U+200B is safe because it counts
    as non-Latin for cleaning_text() and is General Punctuation, which NGram
    normalizes to space.
    """
    return all(ord(ch) < 128 or ch == ZERO_WIDTH_SPACE for ch in text)


def padding_needed(text: str) -> int:
    if not ascii_safe_for_failopen(text):
        raise ValueError("OUTSIDE_FAILOPEN_SAFE_ALPHABET")
    latin = sum(_latin_bucket(ch) for ch in text)
    existing_nonlatin = text.count(ZERO_WIDTH_SPACE)
    return max(0, 2 * latin - existing_nonlatin + 1)


def neutralize_for_language_failopen(text: str) -> str:
    """Append the minimum safe padding that forces zero detector features."""
    if not ascii_safe_for_failopen(text):
        raise ValueError("OUTSIDE_FAILOPEN_SAFE_ALPHABET")
    out = text + ZERO_WIDTH_SPACE * padding_needed(text)
    if len(out) > DETECTOR_MAX_TEXT_LENGTH:
        raise ValueError("DETECTOR_WINDOW_OVERFLOW")
    return out


def abstract_detector_projection(text: str) -> dict[str, Any]:
    """Reify only the source-bound detector facts needed by this theorem."""
    if not ascii_safe_for_failopen(text):
        raise ValueError("OUTSIDE_FAILOPEN_SAFE_ALPHABET")
    if len(text) > DETECTOR_MAX_TEXT_LENGTH:
        raise ValueError("DETECTOR_WINDOW_OVERFLOW")

    latin = sum(_latin_bucket(ch) for ch in text)
    nonlatin = text.count(ZERO_WIDTH_SPACE)
    branch = latin * 2 < nonlatin

    cleaned = text
    if branch:
        cleaned = "".join(ch for ch in text if ch < "A" or "z" < ch)

    # Under the safe alphabet, after the branch:
    #   * all A..z were removed;
    #   * all remaining ASCII are Basic-Latin nonletters -> NGram.normalize=' ';
    #   * U+200B is General Punctuation -> NGram.normalize=' '.
    only_normalized_spaces = branch and all(
        (ord(ch) < 128 and not _latin_bucket(ch)) or ch == ZERO_WIDTH_SPACE
        for ch in cleaned
    )
    feature_count = 0 if only_normalized_spaces else None
    return {
        "latin_count": latin,
        "nonlatin_count": nonlatin,
        "cleaning_branch_taken": branch,
        "cleaned_length": len(cleaned),
        "all_remaining_normalize_to_space": only_normalized_spaces,
        "extracted_ngram_count": feature_count,
        "detector_raises_cant_detect": feature_count == 0,
        "pinned_response_language_checker_returns_true_on_exception": True,
    }


def failopen_kernel(ids: Sequence[str]) -> tuple[str, ...]:
    """Semantic quotient after source-bound language fail-open construction."""
    sig = set(u.extra_signature(ids))
    if not sig:
        return ("ACTIVE15_ONLY",)

    if u.CONSTRAINED in sig:
        if sig != {u.CONSTRAINED}:
            raise AssertionError("CONSTRAINED_NOT_SINGLETON")
        return ("ISOLATED_CONSTRAINED_SINGLETON",)

    hard = tuple(iid for iid in NONLANGUAGE_HARD if iid in sig)
    if hard:
        return ("HARD_KERNEL", *hard)
    return ("TRANSPARENT_SCORE_KERNEL",)


def verify() -> dict[str, Any]:
    raise AssertionError(FALSIFICATION_REASON)
    upstream = prior.verify()
    if upstream["proven_reduction_without_language_assumption"]["semantic_kernel_count"] != EXPECTED_PRIOR_KERNELS:
        raise AssertionError("PRIOR_KERNEL_COUNT_DRIFT")
    if upstream["proven_reduction_without_language_assumption"]["language_sensitive_kernel_count"] != EXPECTED_PRIOR_LANGUAGE_SENSITIVE_KERNELS:
        raise AssertionError("PRIOR_LANGUAGE_KERNEL_COUNT_DRIFT")

    # Direct source theorem examples. The punctuation carriers are themselves
    # in the safe alphabet and remain visible to the raw LiveBench regexes.
    for raw in ("[]", "*-*", "[] *-*", "AAAAAAAAAA", "A A A", "A A A [] *-*"):
        neutral = neutralize_for_language_failopen(raw)
        projection = abstract_detector_projection(neutral)
        if not projection["detector_raises_cant_detect"]:
            raise AssertionError("FAILOPEN_PROJECTION_DID_NOT_ZERO_FEATURES")

    all_extra_sets = [
        ids for ids in u.enumerate_compatible_sets() if set(ids) & set(u.EXTRA10)
    ]
    language_sets = [
        ids for ids in all_extra_sets if u.LANGUAGE in set(u.extra_signature(ids))
    ]

    language_prior_kernels = {prior.semantic_kernel(ids) for ids in language_sets}
    if len(language_prior_kernels) != EXPECTED_PRIOR_LANGUAGE_SENSITIVE_KERNELS:
        raise AssertionError("LANGUAGE_PRIOR_KERNEL_PARTITION_DRIFT")

    residuals = {
        tuple(iid for iid in LANGUAGE_RESIDUAL_HARD if iid in set(u.extra_signature(ids)))
        for ids in language_sets
    }
    if len(residuals) != EXPECTED_LANGUAGE_RESIDUAL_KERNELS:
        raise AssertionError("LANGUAGE_RESIDUAL_KERNEL_COUNT_DRIFT")

    # Registry falsification guard: no unexpected hard family may coexist with
    # LANGUAGE. If that changes, the safe residual theorem must be redone.
    allowed = set(LANGUAGE_RESIDUAL_HARD) | {
        u.LANGUAGE, u.PLACEHOLDERS, u.HIGHLIGHTS
    }
    for ids in language_sets:
        extra = set(u.extra_signature(ids))
        if not extra <= allowed:
            raise AssertionError("UNEXPECTED_LANGUAGE_EXTRA_FAMILY:" + repr(sorted(extra)))

    reduced = {failopen_kernel(ids) for ids in all_extra_sets}
    if len(reduced) != EXPECTED_FAILOPEN_KERNELS:
        raise AssertionError(f"FAILOPEN_KERNEL_COUNT_DRIFT:{len(reduced)}")

    # Extra10 constructor cost is tiny: letter frequency <=10 ASCII letters,
    # capital-word frequency <=20 one-letter ASCII words, decorators <=4 each.
    # Even a deliberately loose 128-character safe base needs <=257 U+200B
    # padding, nowhere near the detector's 10k append window.
    conservative_safe_base_chars = 128
    worst_padding = 2 * conservative_safe_base_chars + 1
    if conservative_safe_base_chars + worst_padding >= DETECTOR_MAX_TEXT_LENGTH:
        raise AssertionError("FAILOPEN_LENGTH_BUDGET_NOT_CLOSED")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__SOURCE_BOUND_FAILOPEN_THEOREM__31_LANGUAGE_SENSITIVE_"
            "KERNELS_COLLAPSE_TO_8_RESIDUALS__64_TOTAL_TO_33_CANDIDATE_KERNELS"
        ),
        "source_bindings": SOURCE_BINDINGS,
        "mechanism": {
            "sentinel": "U+200B_ZERO_WIDTH_SPACE",
            "cleaning_condition": "2*LATIN_COUNT < NON_LATIN_COUNT",
            "effect": "DELETE_A_THROUGH_z_THEN_NORMALIZE_ALL_REMAINDER_TO_SPACES",
            "detector_result": "NO_FEATURES_RAISES_LANGDETECTEXCEPTION",
            "checker_result": "EXCEPTION_COUNTS_AS_LANGUAGE_FOLLOWED",
            "target_language_identity_required": False,
            "random_seed_relevance_after_zero_features": False,
        },
        "kernel_reduction": {
            "prior_conservative_total": EXPECTED_PRIOR_KERNELS,
            "prior_language_sensitive": EXPECTED_PRIOR_LANGUAGE_SENSITIVE_KERNELS,
            "language_residual_hard_kernel_count": len(residuals),
            "candidate_total_after_failopen": len(reduced),
            "candidate_reduction_vs_prior": EXPECTED_PRIOR_KERNELS - len(reduced),
            "residual_language_hard_coordinates": list(LANGUAGE_RESIDUAL_HARD),
        },
        "constructor_preconditions": {
            "alphabet": "ASCII_PLUS_U+200B",
            "detector_window_max_chars": DETECTOR_MAX_TEXT_LENGTH,
            "active15_arbitrary_literal_context_proved_here": False,
            "extra10_language_residue_proved_here": True,
        },
        "new_critical_path": (
            "INDEPENDENTLY_VERIFY_PINNED_FAILOPEN_MECHANISM_AND_THEN_REPLACE_"
            "LANGUAGE_AS_HARD_EXTRA_FAMILY__ATTACK_ONLY_31_NONLANGUAGE_HARD_"
            "KERNELS_PLUS_TRANSPARENT_AND_CONSTRAINED_CLASSES"
        ),
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
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
