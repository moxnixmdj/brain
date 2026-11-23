# I installed every library and it did not help: 4.0% → 4.0%

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls

---

## What I set out to prove, and what happened

My previous receipt said the wall was **supply, not search** — the sdist doesn't contain 84.5% of
the answer names, and the fix would be `pydoc`/`inspect` on the *installed* library, "which cannot
be measured here". Then I noticed I was wrong about that: `pypi.org` is open, so I can install
anything. **So I did.**

All 16 libraries in the leak-free set, installed and inventoried:

```
sympy 17153   scipy 5116   pandas 2897   numpy 2256   nltk 1988
gradio 1323   plotly 742   falcon 653   jinja2 447   librosa 274
geopandas 212  flask 202    tqdm 74      lightgbm 57   matplotlib 27
django 18     mitmproxy 0   torch 0
```

```
                              sdist      installed
truth present in corpus       15.5%   ->   22.7%
TOP-1 correct                  4.0%   ->    4.0%
```

**Coverage improved by 7 points. Top-1 did not move at all.** Installing everything and reading its
complete public inventory recovered 4 more truths out of 84, and the system still found 3.

---

## Why the inventory does not rescue it

The inventory is a **flat list of thousands of names with one-line docstrings**, which is exactly
the corpus that already scored 9.7–25%. The supply was never the binding constraint on *ranking* —
it was the binding constraint on *having any chance*. Fixing it moved the chance from 15% to 23%
and left the ranking untouched at its true level.

Look at the two extremes in that table and the shape of the problem is obvious:

* `sympy` — **17,153 public names.** No index, no grouping, no guide. A flat list.
* `django` — **18 names** at top level, because its API lives in `django.db.models` and friends,
  which `__all__`-based walking does not flatten into a namespace a user would search.

An installed package's inventory is either too large to rank or too shallow to contain the answer.
The artifact does not state an index of itself anywhere I can read without its documentation site.

---

## The honest verdict, corrected three times and now stable

| claim | status |
|---|---|
| scan the environment | **works** — 216 programs, 48 ms |
| know what you don't know | **works** — 0 probes |
| fetch instantly, no model call, no quota | **works** — 1 request/library |
| the fetched supply contains the answer | **22.7%** |
| **ground the goal onto the name** | **4.0% end-to-end, 9.7–25% conditional** |

**Instant knowledge is demonstrated for what an artifact says in its own source and its own
help page. It is not demonstrated for a large library, because a large library's self-description
is a documentation site, and a documentation site is a web page this sandbox cannot reach.**

---

## What I got wrong, in order, so the record is complete

1. Claimed 189 regressed — a misread `grep`. It solved.
2. Claimed `stub_imports` was the root cause of item 180 — measurement refuted it.
3. Reported 43.6% for module layout — actually 11.8% leak-free.
4. Reported 47.0% for name+doc overlap — actually 9.7% leak-free.
5. Claimed the `inspect` fix "cannot be measured here" — **it could, and it did not work.**

Number 5 is the one that matters most, because it is the one where I assumed a limitation instead
of testing it. The measurement took twenty minutes.

---

## The one thing that is now certain

**The bottleneck is not persistence, not fetching, not the store, and not parameter efficiency.**
It is that a user's goal and an artifact's names live in different vocabularies, and the artifact's
own statement of which name answers which need is its **documentation**, which is prose written to
be read by a human, and which no mechanism I have built can index.

Every number in this session either measures that gap or fails to measure it honestly.
`truth.achieved` = **`false`**.
