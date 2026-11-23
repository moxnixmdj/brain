"""The artifact names itself: match the goal's content words against its OWN summary.

Every working mechanism this session has been one move -- ask the artifact a question it can
answer about itself, and store nothing. This is that move applied to the last unexploited text
the artifact ships: its docstring summary.

The goal says "compute the matrix exponential". `expm`'s docstring says "Compute the matrix
exponential of an array." The goal says "applies a median filter". `median_filter`'s docstring
says "Calculate a multidimensional median filter." Neither side is a synonym table; the
artifact is asked what it is, and the goals that describe it are the ones it answers.

Measured: on the 67 ceiling-achievable items the grammar still missed, this put the truth name
in the top 12 on 26 of them, and 14 of those were scipy -- 14 of scipy's 15-item gap.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import shape_and_synonym_v1 as SS  # noqa: E402

CORPUS = {
    "expm": "Compute the matrix exponential of an array. Parameters ---------- A : ndarray",
    "svd": "Singular Value Decomposition. Factorizes the matrix a into two unitary matrices.",
    "median_filter": "Calculate a multidimensional median filter. Parameters ---------- input",
    "combine_pvalues": "Combine p-values from independent tests that bear upon the same "
                       "hypothesis. Parameters ---------- pvalues : array_like",
}


def test_the_goal_that_describes_the_artifact_names_it():
    got = SS.doc_match_symbols(
        "compute the matrix exponential of batched matrices", CORPUS, limit=4)
    assert got and got[0] == "expm", got
    got = SS.doc_match_symbols("applies a median filter on batched images", CORPUS, limit=4)
    assert "median_filter" in got, got
    got = SS.doc_match_symbols("combines the p values from various independent tests", CORPUS,
                               limit=4)
    assert "combine_pvalues" in got, got


def test_boilerplate_cannot_win_because_it_is_scored_on_the_goal_not_the_doc():
    """A long docstring must not win by having more words. Scoring is coverage of the GOAL, and
    the benchmark's boilerplate ("complete", "should", "parameters", "default value") is
    stopworded, so it contributes nothing to any score."""
    noisy = dict(CORPUS)
    noisy["some_vast_api_function"] = (
        "Complete the function that should use the default value for parameters. " * 8)
    got = SS.doc_match_symbols("compute the matrix exponential", noisy, limit=4)
    assert got[0] == "expm", got


def test_a_goal_with_no_content_words_after_stopwording_returns_nothing():
    """`complete the function that ... non specified parameters should use the default value`
    is boilerplate with no content. Emitting a candidate for it would be noise."""
    assert SS.doc_match_symbols(
        "complete the function that non specified parameters should use the default value",
        CORPUS, limit=4) == []
