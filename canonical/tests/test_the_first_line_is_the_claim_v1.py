"""The summary line plus IDF, pinned with fixtures so the suite needs no network."""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import the_first_line_is_the_claim_v1 as F

DOCS = {
    "prod": ("Return the product of array elements over a given axis. Parameters ---------- a : "
             "array_like Input data."),
    "bartlett": ("Return the Bartlett window. The Bartlett window is very similar to a "
                 "triangular window."),
    "sum": "Sum of array elements over a given axis.",
    "mean": "Compute the arithmetic mean along the specified axis.",
}


def test_summary_is_the_first_sentence_not_a_prefix():
    assert F.summary(DOCS["prod"]) == "Return the product of array elements over a given axis."
    assert F.summary("") == ""


def test_idf_makes_a_rare_word_outweigh_a_common_one():
    table = F.idf_table({n: F.summary(d) for n, d in DOCS.items()})
    # "array" appears in three summaries, "product" in one
    assert table["product"] > table["array"]
    assert all(v > 0 for v in table.values())


def test_a_tie_on_distinct_words_is_broken_by_rarity():
    """The bug: `prod` and `bartlett` both share two goal words with the goal, alphabetically
    `bartlett` wins. Rarity must put `prod` first."""
    order = [n for n, _ in F.rank(DOCS, "compute the product of an array")]
    assert order[0] == "prod", order


def test_the_name_is_not_scored():
    """Weighting the name costs points; the summary must be the only evidence."""
    docs = {"zzz_unrelated": "Return the product of array elements over a given axis."}
    order = [n for n, _ in F.rank(docs, "product of an array")]
    assert order[0] == "zzz_unrelated"


def test_measure_counts_only_rows_whose_answer_is_present():
    rows = [{"library": "np", "truth": "prod", "goal": "compute the product of an array"},
            {"library": "np", "truth": "absent_name", "goal": "anything"}]
    res = F.measure(rows, lambda lib: DOCS)
    assert res["rows_scored"] == 1, "an absent answer is a supply problem, not a ranking miss"
    assert res["top1"] == 1
