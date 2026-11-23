# The probe fired 5 times out of 34 and got it right once

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls

---

## What I thought I had, and what I actually had

I ran `np.prod` and `np.nancumprod` on `[1,2,3,4]`. One returned a scalar, one an array, and the
goal said *"computes the product of an array"*. I wrote:

> **The probe works and it's decisive.**

Measured across the corpus:

```
rows where the goal named a shape : 11/34
probe fired (some survivor)       :  5/34
picked the truth when it fired    :  1/5
end-to-end                        :  8/34 = 23.5%   vs baseline 29.4%
```

**The probe makes it worse.** It fired on 5 rows and was right once. I had generalised from a single
case I had already looked at, which is the same error as the doctest-culture call and the leaky
corpus: a true observation about one example, promoted to a mechanism.

---

## Why it fails, mechanically

My shape vocabulary is a bag of output nouns, and goals name inputs with the same nouns they name
outputs with. `array` had to be removed from both lists because it made `scalar` and `sequence`
tie on "the product of an array" — the product is a scalar and the array is what goes in. Even
after removing it, the vocabulary fires on 11 of 34 and the two it fires on wrongly cost more than
the one it gets right.

And a real limit underneath: **the sample the probe runs on is mine, not the artifact's.** A
candidate that raises on my array is eliminated, which is not evidence against the goal — the file
says so, and the file is right, but it means a wrong sample silently deletes the answer.

---

## What survives, and it is small

`the_shape_of_the_answer_is_the_probe_v1` keeps **6 passing tests** and two things that are true:

1. A tie between `prod` and `nancumprod` **is** resolvable by behaviour, and by nothing else —
   their summaries are word-for-word the same claim.
2. **A candidate that raises must be eliminated, never blamed.** Turning a probe against the wrong
   data into a verdict about the goal is how a probe manufactures false negatives.

What does **not** survive is the claim that this raises the number. It does not. The honest status
is: a correct idea with an incompetent vocabulary, measured, and rejected on the measurement.

---

## The one number that did improve, and it is the important one

```
top-1   10/34 = 29.4%
top-2   15/34 = 44.1%
top-3   16/34 = 47.1%
top-10  18/34 = 52.9%
top-20  22/34 = 64.7%
```

The system puts the answer at **rank 2 of 17,153** (`sympy.primepi`) and **rank 3 of 2,256**
(`numpy.prod`). It does not fail to *find* the answer; it fails to *choose* among near-synonyms of
the answer. That is the real shape of the remaining problem, and it is a different problem from the
one I have been solving all session.

**These two are both true: the neighbourhood is found reliably, and the member is chosen 29% of the
time.** A plan that only quotes the first is a lie, and a plan that only quotes the second throws
away the part that works.

---

## Six correction classes in one session, and the pattern

| # | error | how it was caught |
|---|---|---|
| 1 | "189 regressed" | re-read the raw log |
| 2 | `stub_imports` root cause | measurement refuted it |
| 3 | 43.6% → 11.8% | leakage split |
| 4 | 47.0% → 9.7% | leakage split |
| 5 | "cannot be measured here" → 5.3% | installed the libraries |
| 6 | doctest 1.3% → 18–71% | full docstrings; wrong library culture |
| 7 | "probe is decisive" → 1/5 | ran it on the corpus |

Every one is the same failure: **a true statement about the sample I happened to hold, reported as
a statement about the world.** The guard `the_goal_must_not_share_a_stem_v1` catches one class
(leakage). Nothing catches this one except measuring the claim on the whole corpus before writing
it down, which is what I should do first and keep doing last.

`truth.achieved` = **`false`**.
