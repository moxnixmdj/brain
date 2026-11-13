# Learning does not accumulate: 52 lessons write 39 lines nobody wrote

**2026-11-12.** Branch `arena/6bc5654f-brain`, base `b56d981c`. Authority **NONE** — producer-run
sandbox measurement, `$0`, zero model calls, `truth.achieved` stays `false`, no capability
registered, no family flipped, no test weakened.

Owner's thesis this round: *instant learning is solved perfectly, and generalisation with it; so give
the model the most advanced actions, let it do each once, and it learns them permanently; therefore
we solve everything on a computer. Or, if not, the gap is that we are not training weights.*

Both halves of that are half right, and the half that is wrong is measurable. This round measured the
one thing the tree had never measured, and it is the thing the thesis actually assumes.

---

## 1. The assumption nobody tested

Every recorded round measures **one lesson** (precision 1.000, 0.529 coverage), **two lessons**
(0.529 → 0.891), or **which** demonstration to give. These are all sound. They all silently assume
the thing the thesis needs: that a lesson, once learned, keeps working *while other lessons are
present*.

That is a claim about **composition**, and it is not free. It is also the single assumption that
stands between this tree and "learn once, permanently, forever".

I learned 52 lessons — one from each kind of change in the tracked corpus, `seen`, `held_out` and
`fresh`, using the shipped organ exactly as the corpus harness does — and then scored **one fixed set
of 232 target files** under a growing pool of loaded lessons. Two independent readings:

* `same` / `extra` from the corpus's own statement scorer;
* `wrong` from a line diff of three plain texts (original, what the developers wrote, what the engine
  wrote) that touches neither the organ nor the scorer. **They agree at every point of the curve.**

| lessons loaded | rules | files edited | correct | **lines written that no developer wrote** |
|---:|---:|---:|---:|---:|
| 1 | 1 | 1 | 1 | **0** |
| 2 | 2 | 1 | 1 | **0** |
| 3 | 4 | 1 | 1 | **0** |
| 5 | 6 | 1 | 1 | **0** |
| 8 | 9 | 11 | 1 | **20** |
| 13 | 14 | 30 | 24 | **48** |
| 21 | 23 | 64 | 102 | **51** |
| 34 | 43 | 90 | 159 | **49** |
| 52 | 70 | 130 | 270 | **39** |

The own-lesson arm on the same 232 files: **288 correct of 296 questions, 13 wrong lines.**

So: a pool of 52 lessons writes **39** lines on 232 files that no developer wrote, where a pool of
five writes **none**. `extra` and `wrong` are identical at every row — 20/20, 48/48, 51/51, 49/49,
39/39 — by two pieces of code that share no inputs.

## 2. Why this is the answer to the question, and not a footnote

The curve has a shape, and the shape is the finding:

1. **Below ~5 lessons the organ is silent.** It edits one file out of 232. Nothing is wrong, because
   nothing is attempted.
2. **From 8 lessons it starts writing the same lines more than once, or the wrong line, in files it
   was not taught about.** The mechanism is not the matcher being bad — each lesson alone is exact
   on 288 of 296. It is that 232 rules are alive at once, and each question has rules from *other*
   lessons that fit the code and are wrong for it.
3. **The correct count keeps rising with the pool.** Composition is not a disaster; it is a
   **precision-for-reach trade that the system makes silently and without a budget.**

This is the well-known failure mode of a frozen-weight skill library, and 2026 has measured it three
times independently, at three different scales:

* **SkillEvolBench** (arXiv 2605.24117): across 10 model configurations and 3 harnesses, agents "adapt
  locally but rarely form robust reusable skills"; **raw-trajectory reuse frequently outperforms
  distilled skills**; writing *more* skills "improves coverage while introducing episode-specific
  drift and procedural clutter." That is exactly the curve above — coverage up, clutter up.
* **Continual-ARC** (arXiv 2611.14505): "no harness-based method gains on **unseen** tasks, whereas
  weight-based learning shows substantial gains." The persistence half of the thesis is measured and
  **false on held-out tasks** — while memorisation does improve under expert guidance.
* **When Does Continual Learning Require Learning** (arXiv 2607.07847): updates must be matched to the
  *kind* of change. Prompt-shaped updates fit a stage and then forget it; compression "does not help
  learn new tasks." A single update mechanism is the wrong target.

Every one of them says the same thing this corpus now says: **a growing frozen-weight library is not
a learning system. It is a lookup table with an unbounded collision surface.**

## 3. What the owner's four proposed fixes actually do

He proposed four, out of the belief that the gap is that we are not updating weights. Judged against
the evidence above and in the tree, not against taste:

| fix | verdict | why, in one measured line |
|---|---|---|
| **Actual model training** (update weights) | **Real, and the only fix for the held-out half — but not the fastest first move** | Weight-based learning is the *only* arm that gains on unseen tasks in Continual-ARC (S_held 0.29 vs ~0.03 for every harness). But it costs the corpus, the verifier, and the forgetting budget; and it cannot start before the tree can *generate* correct demonstrations at scale, which it cannot yet (62–64% strict). |
| **Conceptual understanding** (semantics, not string matching) | **Already real, in one place** — and it is the proof the thesis works | `file.question.taught_words.v1` is the only capability of 145 whose acceptance predicate is `taught_program_recomputed`. One lesson taught **one word**; 12 unshown requests, **11 right, 0 wrong**, 1 refusal that *names the word*. It composes an unshown sentence correctly. That is the thesis, working, today. |
| **Transfer learning across domains** | **Real, but domain transfer is not the binding constraint** | The three-set corpus (`seen` / `held_out` / `fresh`) *is* cross-project transfer, and `fresh` reaches 79% strict from one showing. What breaks is not a new domain; it is a second lesson. |
| **Reasoning about why a solution works** | **Not measurable yet, and not the limiter** | The tree cannot yet tell a good generalisation from a bad one on a corpus where the developers disagree with each other. The one place it does reason — the operator pack's "is this alias documented?" — is a *closed list lookup*, and it is the thing that makes the rename operator safe. Knowledge, not structure, carried that decision. |

The correction to the bottom line of his message: **the failure is not that we did not train
weights. It is that we never measured composition, and composition fails before weight training
would help.** Training on top of a pool that writes 39 wrong lines would industrialise the error.

## 4. The limiting factor, from first principles

A lesson is a **quantifier over places**. A pool of lessons is a **partition problem**: for each
place, which lesson owns it. The organ answers "every lesson that fits", and fitting is cheap because
one demonstration is a point. So the pool has no ownership rule, and where two lessons both fit, the
wrong one wins about as often as the right one.

**That is the wall, and it is not a modelling wall. It is an index wall.** Three things follow, and
they are ordered by cost:

1. **Ownership before capacity** (days, no model, no weights). A lesson must carry the *scope* it was
   taught in — module, name, receiver — and a pool must refuse to let a lesson reach a place outside
   its scope. The one measuring attempt in this round (scope by imported module) was killed by its
   own control: it recovered correct changes by *dropping* lessons, and the scope was unique on 1 of
   232 targets. The honest next version scopes by *the changed name*, not by the file's imports.
2. **A verifier is what turns a pool into a system** (already bought, £0, unmeasured at pool size).
   The tree owns `settled_admission_v1` and `one_try_state_probe` — a demonstration plus a check
   settles a place, and a check *refuses* rather than guesses. The pool curve above is the arm with
   **no check**. The 2026 literature is explicit that the difference between a library that helps and
   one that drifts is whether every write is gated (XRepoSkill, arXiv 2609.36807: keep only rules
   "independently verified across repositories" — that is the whole method). **This is the missing
   measurement, and it is the cheapest experiment that can change the answer.**
3. **Weights** (expensive, and only after 1 and 2). Continual-ARC measures weight-based learning as
   the only arm that generalises to unseen tasks. That is true and it is also *downstream*: it needs
   the corpus and the verifier that 1 and 2 produce.

## 5. What is real and what is not, in the owner's words

* **"Instant learning is solved perfectly."** Recall of the shown change: **true**, precision 1.000.
  "Perfectly": **false** — precision is 1.000 only because the organ refuses whatever it was not
  shown, which is why coverage is 0.529 from one showing and 16% on the harder corpus.
* **"Instant learning in new arbitrary environments is solved."** **False as stated.** It works
  across *projects* (that is what `held_out` and `fresh` are). It does not work across *lessons*: this
  round's curve. Those are different environments in the only sense that matters here.
* **"Give it each action once and it learns them permanently."** **False.** It learns them
  **individually and exactly** (288/296), and holding 52 of them at once makes it write 39 lines
  nobody wrote. Permanence without ownership is drift.
* **"So we solve everything on a computer."** **Not yet.** The strongest honest statement is: *the
  tree can repeat one change, across projects, at high precision, and cannot yet hold many changes at
  once without losing precision.*
* **"We were trying to make it a sentient creature."** Nothing here measures sentience and this
  round does not claim it. What it does show is a system that can now be told the difference between
  *more experience* and *better experience* — and that the difference is measurable.
* **"The gap is that we are not training weights."** **Half true, and the wrong half to start on.**
  Weights are the only known fix for the *unseen-task* boundary. They are not the fix for the pool
  writing lines nobody wrote — that is ownership plus a verifier, and it is cheap.

## 6. Reproduce

```
# corpus (needs gh; ~6 min for all three sets)
python3 canonical/tools/edits_repeated_across_projects_v1.py fetch seen
python3 canonical/tools/edits_repeated_across_projects_v1.py fetch held_out
python3 canonical/tools/edits_repeated_across_projects_v1.py fetch fresh

# the pool curve, ~3 min
python3 canonical/tools/lesson_pool_interference_v1.py \
    --json canonical/verification/LESSON_POOL_INTERFERENCE_20261112_V1.json

# pinned by 8 tests, predictions declared before the run
python3 -m pytest canonical/tests/test_lesson_pools_do_not_compose_v1.py
```

## 7. Where this round was wrong

1. **My first two runs of this measurement reported "0" because of my own bug** (`Shown` has no
   `after_text`; the lessons were never learned and every `except` swallowed it). Caught by a control
   that asked a known-good lesson to recover a known-good file — it returned 0. Without that control
   I would have reported "stacking is harmless".
2. **My first scope control was a tautology.** Scoping lesson selection to the target's own imports
   made every target exactly one candidate by construction (unique on 1 of 232). It was killed by its
   own control *before* being quoted as a gain; the honest note is in §4.
3. **`leave_unshown=True` was hiding the refusals.** With it off, 92 of 232 files are refused outright
   with 70 rules loaded. The curve above uses the strict arm, which is the honest one; both arms lose
   the same way, which is why the conclusion does not depend on which one is quoted.
