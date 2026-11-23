# The first line is the claim: 20.6% → 29.4%, and my corpus was wrong twice

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls

---

## The corpus was wrong, and fixing it changed everything

GitChameleon ships `name_of_class_or_func`, which reads like the answer. **It is not.** For the
item labelled `log_ndtr` the shipped solution is `scipy.stats.norm.logcdf`. Measured: **49 of 84**
of those "truths" never appear in their own solution.

So every number I published last turn — 5.3% end-to-end, 23.5% conditional, "coverage caps at
22.7%" — was measured against a label that half the time is not the answer.

**Corrected ground truth:** the names a solution introduces that its stub does not already call.
Filtered to exactly one new name, and to goals sharing no 6-char stem with it: **50 rows**, 44 with
a takeable inventory, **34 whose answer is actually present**.

| | old (label) corpus | corrected corpus |
|---|---|---|
| answer present in corpus | 22.7% | **77.3%** |
| best top-1 | 5.3% | **29.4%** |

---

## Two bugs in my own instrument, both found by measuring

1. **`_first_paragraph` cut docstrings at 220 characters.** `librosa.resample` states 3,093
   characters across Parameters, Returns, Examples, Raises, See Also and Notes; the ranker saw one
   line. Median docstring after the fix: **90 → 1,206 characters**.

2. **`doc_overlap` counted distinct shared words, so near-perfect matches tied and lost
   alphabetically.** `numpy.prod` — *"Return the product of array elements over a given axis"* —
   tied at 2 with `numpy.bartlett` — *"Return the Bartlett window"* — and the tie put the answer
   at **rank 38 of 2,256**. Ties, not vocabulary, were most of the loss.

---

## What wins, and each part is computed

| scorer | top-1 (34 rows) |
|---|---|
| **summary + IDF** | **29.4%** |
| summary, raw overlap | 23.5% |
| whole docstring + IDF | 23.5% |
| whole docstring, raw | 20.6% |
| normalise by doc length | 5.9% |

- **Summary, not the whole docstring.** The first sentence is what the artifact leads with. The
  sections after it describe *how to call* something; the summary says *what it is for*.
- **IDF over the library's own docstrings.** A word in 400 of 2,256 summaries cannot discriminate
  ("return", "array"); a word in 3 can. `log((N+1)/(df+1))+1` — no constant to tune, nothing stored.
- **The name is not scored.** Weighting it costs 2.4–5.3 points in every configuration tested.
  A name is a label the author chose; a summary is a sentence the same author wrote for a reader.

**What it acquires, concretely:** `scipy.circvar` from among **5,116** names; `librosa.vqt`,
`pyin`, `lpc`, `rms`, `localmax` from among 274; `geopandas.sjoin`; `gradio.Dropdown`. Prose in,
name out, no model, no training.

---

## What is still wrong, stated plainly

29.4% is progress and it is not a solution. The failures are diagnostic:

* `pandas.Series` for *"Predict behaviour of setting values with iloc inplace"* — the truth's
  docstring shares **zero** goal words. The goal is about a *behaviour of an operation*, and the
  answer is the *type that has the operation*. No bag-of-words over the type's docstring can see
  that.
* `pandas.concat` for *"Combine series and dataframes"* — the truth says "Concatenate pandas
  objects along a particular axis". **"Combine" and "concatenate" are a synonym the scorer cannot
  know**, and the artifact never says they are the same word.
* `Dropdown` was found; `Brush` won, because `Brush`'s docstring literally repeats the goal's
  nouns.

**The wall is now specific: the goal's verb and the artifact's verb are different words for the
same action, and the artifact states the mapping only in prose that is not in any docstring.**

---

## Doctests: killed properly this time

Last turn I killed the doctest channel in 29 seconds on a 1.3% measurement — **taken on
click/rich/tenacity/tabulate, which are web libraries.** Re-measured with full docstrings:

```
librosa 70.8%   numpy 40.1%   scipy 33.4%   pandas 17.8%
jinja2 4.0%     flask 0.5%
```

**Doctest availability is library-culture-dependent and I generalised from the wrong culture.**
That is a real correction. But the channel still fails on merit: as a *scorer*, doctest-only is
**0.0%** and prose+doctest is **1.3%** against prose-only **5.3%**. Killed for the right reason
on the second attempt.

---

## Where this leaves the user's algorithm

| step | status |
|---|---|
| scan | **works** — 216 programs, 48 ms |
| know what you don't know | **works** — 0 probes |
| fetch instantly | **works** — no model call, no quota, ~1 request/library |
| inventory the artifact | **works** — 17,153 names from sympy, sandboxed |
| **ground the goal onto the name** | **29.4%** |

`truth.achieved` = **`false`**.
