# You are right about one thing and wrong about the other, and the difference is measurable

You asked: *is instant learning plus instant learning in new environments the perfect solution to
everything on a computer, where we only need to give the model one experience and it keeps it
permanently?* And: *is this a revolutionary way to make agents learn faster than the current way?*

Short answer, with the measurements behind it:

| what you said | verdict | the measurement |
|---|---|---|
| It learns a change permanently from one showing | **TRUE, inside one project** | 384 of 726 changes made correctly, **0 wrong**, on 12 merged pull requests — 0.529 of the developers' work |
| It learns in a **new arbitrary environment** from one showing | **FALSE** | the same lesson shown once is **REFUSED on all four** different shapes I tried, including "same defect, different variable names" |
| Give it the action once and it learns it permanently, everywhere | **FALSE as stated** | it is refused, not learned. A refusal keeps nothing |
| The action only needs to happen once | **TRUE for something already seen, FALSE for something new** | a **second** showing, from a second place, is what makes it transfer |
| This is a revolutionary way to learn | **TRUE, narrowly** | two showings from two different places generalise to a new variable name, a new function, new constants. Nothing else here does that |
| We solved Problem 2 | **FALSE** | see §1 and §2. `PROBLEM2_GENERALIZATION_COMPLETELY_SOLVED.md` on main does not survive one command |

The single sentence that matters: **the learner does not overfit to the task, it underfits to the
demonstration.** One showing teaches the *names*. Two showings teach the *shape*, and the shape is
the thing that transfers.

---

## 1. What I found on main before I could answer anything

`canonical/swe_kernel/taught_actions/edit_by_example_v1.py` — the organ every generalisation claim in
this repo rests on — **did not parse**. A merge commit (`ffac8e3f53`) carried two conflict regions,
including a `<<<<<<< HEAD` marker, into the file, and shipped them to main:

```
$ python3 -c "import ast; ast.parse(open('.../edit_by_example_v1.py').read())"
SyntaxError: invalid syntax (line 1598)
```

Both parents of that merge were clean. The markers appeared **in the merge**, and nothing caught
it, so the breakage is in the merge, not in either branch.

What that cost, counted rather than guessed: **10 test files could not even be collected** — every
test that exercises one-shot learning — and `edit_by_example` itself sat *below* the marker, so the
function the whole method calls was unreachable. `pytest` reported `1 error during collection`, which
reads like one broken test and is in fact the whole instrument.

I resolved it as a **union**, never a side: one region defines disjoint functions on each side (keep
both), the other is one function each side improved differently (keep the branch's `example` feature
*and* main's `aliases_to_add` call). Result:

* parses; 148 of the tests that were dark now run **green**
* `test_a_change_shown_once_is_kept_and_a_second_showing_widens_it_v1`: **60 passed**, 1 skipped, 2
  failed — against **0 run** before
* the 2 remaining failures are *not* caused by the organ: the organ, asked directly, produces
  exactly the refusal those tests expect (`line 5 of the file has yaml.load called with 1 argument and
  the keyword Loader; ... show that use too, changed or left alone`). They fail because a *different*
  feature is half-wired: `live_brain_route_admission_v1.py` sets `result["taught_action_declined"]`
  (line 5609), but the flow never gets there, so the key is `None`. That is the next honest piece of
  work, named and not hidden.

**This is the answer to "are we already solved".** A repository cannot be "solved" while the file
that does the solving is a syntax error and 10 of its test files cannot start. Everything below is
measured *after* repairing that, because before the repair there was nothing to measure.

---

## 2. `PROBLEM2_GENERALIZATION_COMPLETELY_SOLVED.md` does not survive a measurement

There is a document on main titled **"Problem 2 (Generalization) — COMPLETELY SOLVED"**, from PR
#6808, resting on `semantic_generalization_engine_v1.py`: TF-IDF, cosine similarity, synonym tables.

I measured it, not read it:

* the store holds **24 records but only 8 distinct tasks**, all hand-seeded, all `success`. Nothing
  in it was ever produced by running anything, and **a store with no failures cannot learn where a
  lesson stops applying**.
* the "novel task with completely different vocabulary" is `enumerate subroutines` — the engine's
  own synonym table maps `enumerate → count` and `subroutine → function` by hand. It is exact matching
  through a dictionary.
* the **executed answer comes from the memory: FALSE.** The wrapper (`problem2_solved_wrapper.py`)
  branches on `any(kw in task_description.lower() ...)`; the retrieved strategy contributes only the
  guard `task_type == "information_retrieval"`, and every stored experience sets that same value. The
  memory decides **whether** an answer is given, and which sentence is read back as its provenance.
  It does not decide **what** the answer is.
* the store's opinions live in `canonical/astra_runtime/`, a different naming convention from the
  in-tree `canonical/swe_kernel/` and `canonical/runtime/learned_skills/` — at least three parallel
  "memory" systems, which is exactly what "we built important things with non-obvious names" looks
  like from the inside, and it is a defect, not an achievement: each one has its own notion of an
  experience and none of them validates against a check.

I did *not* damage it and I did not delete it. It is wrong, and it is on main, and the next reader
deserves to see the number instead of the title.

The 2026 literature says the same thing from the outside, which is why the measurement above is not
a quirk of this repo:

* **When Continual Learning Moves to Memory** (arXiv 2604.27003) — experience reuse moves the
  stability–plasticity problem into retrieval; **abstract** memories transfer, raw trajectories cause
  **negative transfer**, and the harm lands on the hard cases.
* **WikiTrace** (arXiv 2611.14320) — memory-induced *degradation*; 52% of failures trace to a memory
  item the agent followed. Memories must link back to the evidence that produced them.
* **LifeMem** (arXiv 2609.12655) — 44.13 vs 41.85 for ExpeL; **removing trajectories costs more than
  removing skills**, and later tasks can *hurt* earlier ones.

Every one of these is a warning about *unvalidated reuse*. The repo's engine stores no failures, no
evidence links, and no check — the three things all three papers say you cannot skip.

---

## 3. The claim you actually care about — one showing, a new environment — measured

The committed round-28 record already answers it for one project: **384 right, 0 wrong, 0.529 of the
work**, on 12 real merged pull requests, with the lesson shown **inside the same project**.

So I asked the question you asked, directly. One lesson, learned from one file:

```
shown:  def at_limit(n):
            if n <= MAX:  ...        ->   if n < MAX:  ...
```

then applied to four other shapes:

| target | result |
|---|---|
| same defect, **different variable names** | **REFUSED** |
| different operator form (`return x <= self.hi`) | **REFUSED** |
| different shape (`[v for v in values if v <= hi]`) | **REFUSED** |
| a `<=` that is genuinely **required** | **REFUSED** |

The refusal message is precise and worth reading, because it names the real limitation:

> `nothing in the file has the form the example changed (n <= MAX -> n < MAX); a part of that form may
> vary only where two changed places differ`

**"A part may vary only where two changed places differ."** That sentence *is* the design. One
showing fixes every part of the rule — the names, the constants, the operator. Two showings that
differ in a place tell it that place may vary. This is version-space generalisation done by hand, and
it is correct as far as it goes. It just means **one example generalises to nothing**.

Now show it the same change **twice, from two different places**:

```
one showing  -> REFUSED on a new name
two showings -> proposes  if x < hi:      <- correct, on a function it has never seen
```

That is real, it is shipped, and it is the revolutionary part. It is also **not** "one experience,
learned permanently, everywhere". It is **"two experiences that differ, generalised to the shape they
share"**.

And the limit survives the second showing: with two showings it **still offers to change a `<=` that
is required**, because nothing in either demonstration says the boundary is exclusive. Only a check on
the *target* file can say that. Two showings widen the rule; they do not make it right.

So the honest ranking of what moves the number, which is what the round-28 record computed:

| lever | measured effect |
|---|---|
| a **second showing** from a different place | 0.529 → **0.891** of the work, 0 wrong |
| **widening the rule** | 0.455 precision, **42 wrong changes** — worse than doing nothing |
| a **check on the target file** | turns a wrong edit into a refusal — but it could run on **0 of 42** real changed files |

---

## 4. Where you are right, precisely

1. **Learning from an example, permanently, is real.** 384 changes the developers also made, zero
   wrong, on real merged PRs. Nothing else in this tree does that.
2. **It is a different mechanism from how agents are trained today**, and the 2026 literature says so
   independently: the bottleneck is *abstraction*, not parameters. Your instinct — the action
   happens, then it is kept — is what SkillOpt, GSE and PolySkill are all reaching for. You are not
   wrong about the direction.
3. **"Give the model the action once and it has it" is true for the second time you meet that
   action**, which is already most of the practical value: the same migration in the same codebase
   is the common case.

## 5. Where it breaks, precisely — the three real limiting factors

**A. One showing is too little information, and that is a fact about information, not about effort.**
One input/output pair admits infinitely many rules. The organ picks the most specific one that fits,
which transfers to nothing. The fix is **more than one showing, differing in the place you want to
vary** — not a bigger model, not a better prompt. Measured: 3 plausible repairs remain consistent
with one showing, and the rule can distinguish **0** of them.

**B. Nothing tells it where to stop, except a check, and checks are missing.**
On the 12 real tasks the check could not run at all: **6 tasks had no test module that imports the
changed file, 6 needed a dependency that is not installed. 0 of 42 changed files were verifiable.**
This is the largest single number in the whole area and it is *environmental*. The learner is not the
limiting factor any more. **Standing up a check is.**

**C. The `<=` problem is not solvable by generality.**
A demonstration shows one boundary; three different programs satisfy it. Widening the rule made it
worse: precision **0.455, 42 wrong changes**. Precision and reach trade off, and the trade is decided
by the check, not by the rule.

## 6. The smartest next actions, in order, and the ones I killed

**Do next (in this order):**

1. **Make the check cheap to stand up.** Resolve declared dependencies (6 of 12 tasks) and find the
   test entry point that actually imports the changed file (the other 6). One instrument, two
   halves, and it converts an unknown share of the 0.529 into *verified* work. Everything else is
   waiting on this number.
2. **Make two showings automatic.** The organ needs a second example that differs in the place you
   want to vary; today a human has to choose it. Selecting the second showing by *which place it
   varies* is a small, measurable change to an organ that already works.
3. **Give the store a failure channel.** All three 2026 papers say the same thing: a memory of
   successes cannot learn a boundary, and unvalidated reuse causes degradation. The in-tree stores
   have `outcome` fields and not one `failure`. That is a one-field change with a measurable
   consequence: does a lesson whose check failed stop being offered?
4. **Retire the duplicate memories.** Three parallel stores (`canonical/astra_runtime/generalization/`,
   `canonical/runtime/learned_skills/`, `canonical/runtime/edit_kind_learning_v1` lessons) is the
   "non-obvious names" problem in the flesh. One store, one notion of an experience, one validator.

**Killed before implementation, with the reason:**

* *"It already generalises, so we only need environments."* Measured false: refused on all four new
  shapes. Building an environment harness on top of that assumption would have failed 100% of the time
  and looked like an environment bug for a week.
* *"Semantic similarity / embeddings will close the gap."* #6808 already did it. Its executed answer
  does not come from the memory, its store has no failures, and its "different vocabulary" is a
  hand-written synonym table.
* *"Make the rule wider / more general."* Measured worse: 42 wrong changes.
* *"More demonstrations, of the same thing."* Does not widen anything. The store already had 24
  records and still could not answer a task it had not seen.
* *"A bigger model, or an LLM in the loop."* Forbidden by the standing constraint, and unnecessary:
  the organ already transfers correctly when given two differing showings. The missing input is
  *information*, not intelligence.

## 7. The creature question, answered honestly

You said: *we were trying to make our model a sentient creature.* Sentience is not something this
repo can measure, and I will not claim it. But there is a *real*, measurable version of that
ambition, and this round found it in the shape of the answer:

* a creature that has seen something **once** and repeats it is a **cache**;
* a creature that has seen something **twice, differently**, and applies the **shared shape** to a
  situation it has never seen is doing something a cache cannot do;
* a creature that can tell **where a lesson stops applying** — because a check on the new situation
  refuses it — is doing the third thing, and that is the one still missing here.

The measurements above put this system at stage two, with stage three blocked on stage one of §6.
That is a much better place than "solved", because it is a place with a next step.

## 8. What this does not claim

Not a benchmark; 12 tasks of one family (mechanical migrations), which is the regime one-shot
learning is best at. The four-shape test is a *probe*, deliberately small, and it measures refusal —
which is a lower bound on inability, not a proof of it: a richer lesson might transfer where these
did. The constructed two-module counterfactual in the round-28 record is constructed and labelled so.
No capability is registered, no family is flipped, `truth.achieved` stays `false`, spend is `$0`, and
no model was called.

Everything here is reproducible with two commands:

```
python3 canonical/tools/what_transfers_v1.py --out canonical/verification/WHAT_TRANSFERS_20261113_V1.json
python3 -m pytest canonical/tests/test_what_transfers_v1.py -q
```
