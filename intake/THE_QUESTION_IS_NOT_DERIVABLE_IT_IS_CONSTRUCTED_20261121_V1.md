# The question is not derivable — it is constructed, and the difference is measurable

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls

I had named the last bottleneck as "the question vocabulary is chosen, not derived". Measuring it
splits the claim in two, and one half is a **negative result about my own design**.

---

## Case A — the effect vocabulary is derived, and it is narrow

The effect vocabulary is `PERSIST` / `REMOVE` / `REPLACE` / `APPEND`, read as the diff of the
environment's attested state before and after an action.

Exhaustive test over every small diff (`change` −2..2, `arrived` 0..3, `departed` 0..3):

```
named            5 / 80 small diff shapes
unclassified    75 / 80
```

So the vocabulary names **6.25%** of the shapes a small change can take. It is *derived* — a total
function of three integers, computed from the reading, with nothing chosen — but it is **very far
from complete**. A change that moves two entities in and two out is not described by it at all.

The append case I added today (`(1,2,1)`) raised the count from 4 to 5. That is the shape of this
work: each real environment reveals one more shape, and the vocabulary grows by enumeration of
what actually happened, not by invention.

## Case B — the role vocabulary is chosen, and it reaches 16%

```
103 of 635 help pages (16%) mention any of my five role words
```

Five English words, chosen for a filesystem task family. Nothing in a help page forces the question
to be phrased that way. A host whose documentation uses a different language, or no words at all,
gets nothing.

## The distinction that resolves it

**A question is not derivable from an environment. It is CONSTRUCTED from a goal.**

- The environment can tell you *what actions do* — that is derived, and it is the effect
  vocabulary.
- The environment cannot tell you *what you want*. That comes from the goal.
- What makes a question **general** is not that it is derived from the environment, but that it is
  expressed in a vocabulary the *environment can answer in*: the effect vocabulary.

So the correct architecture is not "derive the question from the environment". It is:

```
goal (from the task)  ->  effect vocabulary  ->  which actions produce those effects
                                              (learned by probing, goal-directed, 3.0x cheaper)
```

The role vocabulary was the wrong layer all along. It is a **shortcut for a documentation-reading
task family** — useful, measured at 253× warm, 16% reach — but it is not the general mechanism,
and presenting it as the general mechanism would have been dishonest.

## What this changes in the plan

| layer | status | evidence |
|---|---|---|
| goal → effect vocabulary | **the general mechanism** | names only 5/80 diff shapes, so it is narrow — but derived, total, and surface-neutral |
| effect → action | **learned, goal-directed** | 12 trials vs 36 (3.0×); abstains when no action produces the effect |
| action → arguments | **asked of the artifact** | 253× warm; 8,240 bytes; sound and complete |
| role vocabulary | **a shortcut, not the mechanism** | 16% reach on an unseen host |

The honest next bottleneck is therefore **not** "derive the role words". It is: **the effect
vocabulary names 6.25% of what a change can be, and the other 75 shapes are unnamed.** Widening it
is enumeration driven by real environments, and that is a finite, measurable programme — unlike
"derive English from a help page", which I now believe is the wrong problem.

`truth.achieved` remains `false`.
