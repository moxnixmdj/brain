# The answer is 5.3% end-to-end, 23.5% conditional — and 22.7% coverage is the wall

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls

---

## The final, complete measurement

84 leak-free rows from GitChameleon. Real prose written by someone who never saw the answer.
Every library installed. Inventory taken in a sandboxed child process. Full docstrings (median
1,206 chars, up from ~90 after I found my own truncation bug).

```
leak-free rows scorable          75
truth present in the corpus      17/75 = 22.7%     <- the ceiling
```

| scorer | end-to-end | **conditional** (truth present) |
|---|---|---|
| name×3 + full docstring | **5.3%** (4/75) | **23.5%** (4/17) |
| name×1 + full docstring | 5.3% | 23.5% |
| full docstring only | 5.3% | 23.5% |
| name×3 + first sentence only | 4.0% | 17.6% |
| **name only** | **0.0%** | **0.0%** |

Three things this settles:

1. **The docstring is the evidence, the name is not.** `name only` scores **zero**. My earlier
   "3× the name weight" result was an artifact of the leaky corpus.
2. **My extraction was throwing away 13× of the evidence.** `_first_paragraph` cut docstrings at
   220 characters. `librosa.resample` states 3,093 characters across Parameters, Returns,
   Examples, Raises, See Also and Notes; the pipeline saw its first line. Fixing it moved
   conditional accuracy 17.6% → 23.5%.
3. **Coverage is the binding constraint, not ranking.** 82.7% of the time the answer is not in the
   corpus, so no scorer can reach it. The ceiling is 22.7%.

---

## Why coverage caps at 22.7% even with everything installed

`sympy` has **17,153** public names, `django` **18**. `torch` and `mitmproxy` yield **0** — their
public surface lives in C extensions and `__all__`-less modules that a non-executing walk cannot
reach. `pandas`, `plotly`, `nltk`, `gradio` each exceed 700 names.

An installed package's inventory is **either too large to rank or too shallow to contain the
answer**, and the artifact never states an index of itself in a form readable without its
documentation site — which is a web page, and blocked here.

---

## What is proven, and what is not

**Proven, measured, repeated:**
- scan a host: 216 programs, 48 ms
- know what you don't know: 0 probes at rebuild
- fetch instantly from the network: no model call, no quota, ~1 request/library
- the store suffices: 125/125 answers on `/usr/bin`, 25,768 B
- goal-directed beats learn-everything: **3.0×**
- the cohort: **37/40** on a 40-item two-library subset

**Not proven, and I will not claim it:**
- instant knowledge for an arbitrary library. **5.3% end-to-end, 23.5% conditional.** The user's
  algorithm is right and its last step is at roughly one in four when the artifact is reachable
  and one in twenty overall.

---

## The real bottleneck, stated once and finally

> A person's goal and an artifact's names live in different vocabularies. The artifact's own
> statement of which name answers which need is **prose**, and no mechanism I have built indexes
> prose. Every scorer in this session lands between 4% and 24% on clean rows because a bag of
> words is the wrong shape for the question "which of these 17,153 names does what I just asked
> for".

That is a real limit, measured from five directions, and it is not a limit of persistence,
fetching, or the store — all three of which work.

**What I got wrong today, five times, in order:** misread `grep` on 189; false root cause on 180;
43.6% → 11.8%; 47.0% → 9.7%; "cannot be measured here" → it could, and gave 5.3%.

`truth.achieved` = **`false`**.
