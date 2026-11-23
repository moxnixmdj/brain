#!/usr/bin/env python3
"""A docstring leads with its claim; the rarest shared word is the discriminator.

THE BUG THAT HID THIS FOR A WHOLE SESSION
-----------------------------------------
Two defects in my own instruments, both found by measuring them:

1. `_first_paragraph` cut every docstring at 220 characters, so `librosa.resample` -- which states
   3,093 characters across Parameters, Returns, Examples, Raises, See Also and Notes -- reached
   the ranker as one line. Fixed; median docstring went 90 -> 1,206 characters.

2. `doc_overlap` counted DISTINCT SHARED WORDS, so `numpy.prod` ("Return the product of array
   elements over a given axis") tied at 2 with `numpy.bartlett` ("Return the Bartlett window"),
   and the tie broke alphabetically -- putting the answer at rank 38 of 2,256. Ties, not
   vocabulary, were most of the loss.

WHAT THIS FILE DOES ABOUT IT, AND WHY EACH PART IS COMPUTED
-----------------------------------------------------------
  * SUMMARY, not the whole docstring. The first sentence is what the artifact LEADS with; the
    sections after it are parameters, return values and examples, which describe *how* to call
    something while the summary says *what it is for*. Measured: summary 23.5% vs whole-doc 20.6%.
  * IDF over the library's own docstrings. A word that appears in 400 of 2,256 summaries cannot
    tell them apart ("return", "array"); a word in 3 can. The statistic is computed from the
    artifact at query time, so nothing is stored and nothing is fitted. Measured: +3.0 points
    over raw overlap.
  * No name scoring. Measured repeatedly and in both directions: weighting the NAME costs
    2.4 to 5.3 points (`name3+doc` 4.5% vs `doc_only` 15.9% end-to-end). A name is a label the
    library's author chose; a summary is a sentence the same author wrote for a reader. The
    sentence is the better evidence.

THE CORPUS, AND WHY IT HAD TO BE REBUILT TWICE
-----------------------------------------------
GitChameleon ships `name_of_class_or_func`, which reads like the answer and is not: for
`log_ndtr` the shipped solution is `scipy.stats.norm.logcdf`, so 49 of 84 "truths" never appear
in their own solution. The real ground truth is the set of names a solution introduces that its
stub does not already call. Filtered to exactly ONE new name and to goals that share no 6-char
stem with it (`the_goal_must_not_share_a_stem_v1`): **50 rows**, of which 44 have a library whose
inventory can be taken.

MEASURED, on those 34 rows whose answer is actually present:

    idf_summary   9/34 = 26.5%     <- this file
    summary_raw   8/34 = 23.5%
    idf_doc       8/34 = 23.5%
    doc_raw       7/34 = 20.6%
    doc_norm      2/34 =  5.9%     <- normalising by document length is actively wrong

26.5% is progress, not a solution, and the file says so.

Schema BRAIN_THE_FIRST_LINE_IS_THE_CLAIM_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import learned_ranking_store_v1 as L  # noqa: E402

SCHEMA = "BRAIN_THE_FIRST_LINE_IS_THE_CLAIM_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
SUMMARY_CHARS = 300


def summary(doc: str | None) -> str:
    """The artifact's leading claim: the first sentence, capped.

    Not `doc[:200]`. A docstring may open with a version note or a warning, and the first
    sentence boundary is the artifact's own delimiter for "this is what I am".
    """
    text = " ".join((doc or "").split())
    if not text:
        return ""
    end = text.find(". ")
    # keep the terminator: it is the artifact's own end-of-claim, and dropping it made the
    # summary of `numpy.prod` end in "axis" while the same sentence in a comparison string
    # still carried the period -- a difference with no meaning that changes equality tests.
    return (text[: end + 1] if 0 < end else text)[:SUMMARY_CHARS]


def idf_table(docs: Mapping[str, str]) -> dict[str, float]:
    """How much each word distinguishes, computed from the corpus in front of it.

    `log((N + 1) / (df + 1)) + 1`, so a word in no document scores highest, a word in every
    document scores 1, and nothing is ever zero or negative. This is the whole "rare word
    weights more" idea as arithmetic, with no constant to tune.
    """
    df: dict[str, int] = {}
    for text in docs.values():
        for w in L.words(text):
            df[w] = df.get(w, 0) + 1
    n = max(len(docs), 1)
    return {w: math.log((1 + n) / (1 + c)) + 1.0 for w, c in df.items()}


def rank(docs: Mapping[str, str], goal: str) -> list[tuple[str, float]]:
    """Names ordered by how much of the goal their own leading claim carries, rarest first."""
    gw = L.words(goal)
    if not gw:
        return [(n, 0.0) for n in sorted(docs)]
    table = idf_table({n: summary(d) for n, d in docs.items()})
    scored: list[tuple[str, float]] = []
    for name, doc in docs.items():
        shared = gw & L.words(summary(doc))
        scored.append((name, sum(table.get(w, 1.0) for w in shared)))
    scored.sort(key=lambda r: (-r[1], r[0]))
    return scored


def measure(rows: Sequence[Mapping[str, Any]], inventory_of) -> dict[str, Any]:
    """Score rows against inventories the caller supplies, so this stays network-free.

    `inventory_of(library)` returns {name: docstring}. A row counts only when its answer is
    actually present -- otherwise the scorer is being blamed for a supply problem, which is the
    error that produced three wrong headline numbers earlier in this project.
    """
    present = hit = 0
    detail: list[dict[str, Any]] = []
    for r in rows:
        inv = inventory_of(r["library"]) or {}
        truth = r["truth"]
        if truth not in inv:
            continue
        present += 1
        order = [n for n, _ in rank(inv, r["goal"])]
        top = order[0] if order else None
        got = top == truth
        hit += got
        detail.append({"library": r["library"], "truth": truth, "top": top,
                       "rank": order.index(truth) + 1 if truth in order else None,
                       "n": len(order), "hit": got})
    return {"schema": SCHEMA, "authority": AUTHORITY, "rows_scored": present,
            "top1": hit, "rate": round(hit / present, 3) if present else 0.0,
            "detail": detail}


def main(argv: Sequence[str] | None = None) -> int:
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
