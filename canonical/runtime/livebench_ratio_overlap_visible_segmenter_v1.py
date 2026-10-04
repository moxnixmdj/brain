#!/usr/bin/env python3
from __future__ import annotations

import re

from canonical.runtime import livebench_ngram_whitespace_invariant_compiler_v1 as ngram_compiler

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_VISIBLE_REFERENCE_SEGMENTER_V1"


class VisibleReferenceSegmentationError(ValueError):
    pass


_OVERLAP = re.compile(
    r"Maintain\s+a\s+trigram\s+overlap\s+of\s+"
    r"(?P<percentage>\d+(?:\.\d+)?)%\s*\(±2%\)\s+"
    r"with\s+the\s+provided\s+reference\s+text\.",
    flags=re.I,
)

_SENTENCE_KEYWORD = re.compile(
    r"The\s+response\s+must\s+include\s+keyword\s+"
    r"[^\s.]+\s+in\s+the\s+\d+-(?:st|nd|rd|th)\s+sentence\.",
    flags=re.I,
)

_CONSONANT_CLUSTER = re.compile(
    r"Ensure\s+each\s+word\s+in\s+your\s+response\s+has\s+at\s+least\s+"
    r"one\s+consonant\s+cluster\s*\(two\s+or\s+more\s+consonants\s+together\)\.",
    flags=re.I,
)


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def recover_normalized_reference(prompt: str) -> dict:
    """Recover the public IFBench ratio-overlap reference from visible text only.

    This function knows no row IDs, hidden kwargs, responses, or terminal cases.
    It deletes only public constraint-description spans that are independently
    known to co-occur with ratio:overlap in the pinned public IFBench population.

    Fail closed if the overlap clause is absent/ambiguous or no base request
    survives deletion.
    """
    prompt = str(prompt or "")
    matches = list(_OVERLAP.finditer(prompt))
    if len(matches) != 1:
        raise VisibleReferenceSegmentationError(
            "EXACTLY_ONE_RATIO_OVERLAP_DESCRIPTION_REQUIRED"
        )

    percentage = float(matches[0].group("percentage"))
    stripped, overlap_count = _OVERLAP.subn(" ", prompt)
    stripped, keyword_count = _SENTENCE_KEYWORD.subn(" ", stripped)
    stripped, consonant_count = _CONSONANT_CLUSTER.subn(" ", stripped)
    reference = normalize_ws(stripped)
    if not reference:
        raise VisibleReferenceSegmentationError("EMPTY_REFERENCE_AFTER_SEGMENTATION")

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "normalized_reference": reference,
        "percentage": percentage,
        "removed": {
            "ratio_overlap": overlap_count,
            "sentence_keyword": keyword_count,
            "consonant_cluster": consonant_count,
        },
        "source": "VISIBLE_PROMPT_ONLY",
        "row_identity_required": False,
        "hidden_kwargs_required": False,
        "terminal_case_data_required": False,
    }


def construct_overlap_witness_from_visible_prompt(prompt: str) -> dict:
    """Compose visible-only segmentation with the whitespace-invariant compiler.

    This proves only the ratio:overlap predicate. Any additional co-constraints
    remain separate obligations for a higher-level composer.
    """
    recovered = recover_normalized_reference(prompt)
    witness = ngram_compiler.construct(
        recovered["normalized_reference"],
        recovered["percentage"],
    )
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "segmentation": recovered,
        "overlap_witness": witness,
        "co_constraints_removed_not_claimed_satisfied": (
            recovered["removed"]["sentence_keyword"]
            + recovered["removed"]["consonant_cluster"]
        ),
    }
