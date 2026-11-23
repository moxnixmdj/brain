# The goal-grounding wall: every mechanism in this family lands at 10–25%, and the corpus is the limit

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls

---

## Everything measured on goal → artifact-name, in one table

Two corpora. **Leaky** rows have a goal that shares a stem with the truth (a test file named
after what it tests). **Leak-free** rows do not. Only the second column describes generalisation.

| mechanism | all rows | leak-free |
|---|---|---|
| docstring overlap, normalised by goal | 8.5% | — |
| docstring overlap, raw | 36.1% | — |
| name-only overlap | 43.4% | — |
| **name + docstring (2× name)** | 47.0% | **9.7%** |
| module layout as the index | 43.6% | **11.8%** |
| ask the guide's own prose | 0.0% | 0.0% |
| **morphological strip + 3× name weight** | 47.8% | **25.0%** *(n=16)* |

**The best leak-free number is 25%, on 16 rows.** That is not a result; it is a direction.

---

## Why the sample cannot be grown by adding libraries

Measured across five packages (click, rich, attrs, httpx, tenacity): **83 rows total, 16 leak-free.**
A test file is named after the thing it tests and imports the thing it tests, so test-derived rows
are leaky *by construction*. Adding libraries adds leaky rows, not clean ones. httpx and tenacity
contributed zero rows at all.

**This is the blocker: I do not have a leak-free corpus big enough to distinguish mechanisms, so
every ranking I publish on 16 rows is noise.** Building a fourth scorer would produce a fourth
number and teach nothing.

---

## What the mechanisms do establish

1. **A bag of words is the wrong shape.** The best scorer weights the *name* above the
   *docstring* (3× and 2× variants both win), which says the artifact's own naming is a stronger
   statement than its prose. This matches `the_return_type_selects_the_guide`: *the name is not
   the statement* — but the name is still better evidence than the description.

2. **Asking the guide is strictly worse than ranking everything** (0.0% vs 9.7%). A README is a
   tour, not an index. It names a handful of names in passing and never answers "which of these
   520 names does X". That kills the "ask the environment a question" design for this problem,
   decisively, and it was the design that looked most like the user's own idea.

3. **A real goal carries 3–6 content words, and they are verbs and nouns the library also uses**
   ("retry", "parse", "split", "compress"). The failure is not that the words differ. It is that
   a bag cannot tell which of them is the ACTION and which is the OBJECT — `print a table` has
   two candidate actions and the truth is a noun.

4. **Morphological stripping is the only thing that moved the clean number** (9.7% → 25.0%):
   `retrying` → `retry`, `attaches` → `attach`. That is one regex, not a component.

---

## The verdict on the user's algorithm

| step | status | evidence |
|---|---|---|
| scan the environment | **works** | 216 programs, 48 ms |
| know what you don't know | **works** | 0 probes at rebuild |
| fetch instantly from the guide | **works** | no model call, no quota, ~1 request/library |
| **ground the goal onto a name** | **10–25%, the wall** | this document |

The algorithm is right. Its last step is not solved, and this session established the shape of the
problem rather than a solution to it: **not word matching, not asking the guide, not the layout.**
Something that distinguishes the action from the object in a goal sentence, and that needs a
leak-free corpus to be measured at all.

---

## The next bottleneck, named and honest

**Build a leak-free goal corpus before building another mechanism.** The natural source is goals
written by someone who has never seen the library, against names they do not know. That is the one
thing this session proved it needs and could not synthesise.

`truth.achieved` = **`false`**.
