# What a success teaches about *when*

**2026-11-12.** Base `dd67c1f4`. Branch `arena/b2f83018-brain`. Round 3 of the owner's question.

The owner asked, for the third time and in the sharpest form:

> *"Why can't we just give our model the most advanced coding actions and let him experience them
> once and then he will learn them? Can't we do this now? After we do this we have the most advanced
> coding agent on the planet."*

The previous two rounds answered with the identifiability of *rules* — 14 programs survive one
demonstration; the prior does the generalising. Both answers were correct and both were easy to
file under "that's about toy arithmetic". This round does not repeat them. It isolates the property
that computer use needs and arithmetic probes never touched: **applicability** — knowing *when* an
action may be used — and measures how much of it one demonstration supplies.

It also takes the owner's own optima seriously, and adopts one of them outright (§5).

Authority **NONE**. Constructed learner over this tree's declared structure; one machine; no
independent verifier; $0; zero model dependency. `truth.achieved` stays `false`, no capability is
registered, no family flips. It says nothing about GUI computer use.

---

## 1. The sentence, split at the joint that carries the weight

A demonstration of a successful action hands over two things: **the action**, and **the state it
ran in**. This tree already stores both. `macro_v1` remembers a plan keyed by the shape of the goal;
`environment_learning_v1` learns `(state, action) -> state` and plans shortest paths through it.
Those are real mechanisms and the owner is right that they exist.

The word nobody examined is **when**. To *reuse* an action, the machine needs its **applicability
condition**: the facts that must hold for it to work. And here is the whole argument, in one line
that does not require a model, a benchmark, or an opinion:

> A success says the action **can** run here. It cannot say what the action **needs**.
> "Can" is not "must". Necessity is only ever refuted by a failure.

That is not a stylistic complaint. It is the defining asymmetry of learning from positive examples,
and it is why the registry in this repository declares `requires` as a hand-authored conjunction:
somebody had to write down what each capability needs, because a running system cannot read it off
its own successes.

---

## 2. The measurement

`what_a_success_teaches_20261112.py` builds the standard conjunction version space — a hypothesis is
a set of required facts; it is applicable in state `s` iff it is a subset of `s` — over a five-fact
universe, and runs it through this tree's real machinery (`settlement_v1.VersionSpace` for the
hypotheses and update rule; `world_probe_v1` as the only sensor). Nothing is re-implemented.

The domain is exhaustive, not sampled: **every hidden requirement of size 1–3 × every state that
witnesses a success** — 200 exact cases. Error rates are computed against all 32 states, so they are
exact fractions, not estimates.

### A. One success

| measured | value |
|---|---|
| cases where one success identified the requirement | **0 / 200** |
| hypotheses still consistent afterwards | **13.05 of 32** |
| bits left unresolved | **3.40** |
| most **general** survivor ("needs nothing") — says *applicable* where it **fails** | **68% of all states** |
| most **specific** survivor ("needs everything seen") — says *inapplicable* where it **works** | **21% of all states** |
| cases leaving at least one survivor that is wrong somewhere | **200 / 200** |

Both boundaries are wrong, and they are wrong in opposite directions. The general one is the
dangerous one: *"it worked here, so it needs nothing"* is a perfectly consistent reading of a single
success, and it authorises the action in 68% of the states where it breaks. The specific one is
merely useless — it demands the exact accidental configuration of one demonstration and refuses 21%
of the states where the action would have worked.

This is the answer to "why can't we just let it experience them once". It can. It will. What it
learns is a licence to act **everywhere**, because one success never showed it a place to stop.

### B. The same learner, once outcomes include failures

| measured | value |
|---|---|
| cases identified exactly | **25 / 25** |
| mean demonstrations | **2.76** |
| worst case | **4** |
| conclusions that were *wrong* | **0** |

Same space, same learner, same update rule. The only change is that the evidence now contains
**outcomes**, not just successes. Three demonstrations beat one — but not because three examples are
more than one. Because at least one of them **failed**, and a failure on state `s` excludes every
hypothesis satisfied by `s`. Round 1 measured "3 demonstrations do not rescue it" on a *periodic
function* space. Here, three demonstrations with failures identify the rule exactly, every time.
The two results are consistent: what carries information is not the count of demonstrations, it is
whether any of them could have come out the other way.

### C. What this machine actually records

`macro_v1.record` stores a plan only when every step verified; a failure is incremented as a counter
and the plan is dropped once failures outnumber successes. That is a defensible policy and it
produces exactly the one-sided evidence class that A measures:

```
macros stored                 2
successes / failures recorded 2 / 0
```

Every replayable demonstration this machine owns is a **success**. There is no store of "this
capability was attempted in this state and refused", so the demonstrations available for reuse are
precisely the ones that cannot decide necessity. That is not a bug in `macro_v1` — the refusals do
exist, they are just spent on a counter instead of being kept as evidence.

### D. The registry's own premises

145 capabilities declare 125 distinct precondition facts. Asking the tree's own perceiver to decide
each one:

| class | count | meaning |
|---|---|---|
| **PROVIDED** | 100 | another registered capability can make it true — a planning step |
| **SENSED** | 14 | this machine can decide it by looking — a perception step |
| **BLIND** | 11 | **neither** — no capability produces it, no sensor reads it |

**135 of 145** capabilities have every premise decidable right now. **10** are held by a premise in
the third column:

```
chart.query.x_value.available            pypi.live_metadata.available
chart.query.y_value.available            pypi.selection.available
chart.question.binary_phase_solvus.available    source.candidate.provenance.verified
chart.question.legend_linear_intersection.available   structured.release_claim.available
chart.series.label.available             git.repository.available
network.http.available
```

This is the sharper finding, and it is about the tree, not about the owner's plan. Those ten
capabilities are registered, verified, and *uninvocable in a way the system cannot notice*: the
premise cannot be satisfied by planning, cannot be established by looking, and therefore cannot be
reported as either true or false. The registry will route to them and then discover the missing
premise at execution time. A premise that no sensor reads is the same object as a premise that was
never learned — and, per A, **no number of demonstrations converts one into the other.**

---

## 3. Where this changes the plan, in the right direction

The owner's engineering intuition — *"give it the smartest actions, let it try, keep what worked"* —
is not refuted by any of this. Two of its parts are correct and are the reason the tree gets as far
as it does:

1. **A stable, typed interface is a pre-loaded hypothesis space.** When `npm test` means the same
   thing in ten thousand repositories, a lesson needs no induction at all: the interface did the
   generalising. This is why the Agent-S4-class results of 2026 are real — *Evolving Agent
   Interfaces* (arXiv 2610.28601) reaches 21.3% on OSWorld V2, 3.8× the same model with fixed
   interfaces, by evolving the **interfaces** and the knowledge of when to use each, selected on
   held-out tasks. Note the second half of that phrase: *when to use each*. The interface layer is
   an applicability layer.
2. **Persistence with expiry, and a refusal that is a first-class answer,** are genuinely ahead of
   most of the field and are what makes the memory worth having.

What must change is the claim that experience alone supplies applicability. Three concrete
consequences, in order of value:

**Adopt the owner's optima first.** The fastest correct move is not a new learner; it is to make
more of computer use *code against a declared interface with a mechanical check*. In that regime
"D. The registry's own premises" is where the leverage is: **11 blind premises are 11 capabilities
that are currently unreachable for a reason the system cannot name.** Making those premises
decidable — a `git` probe, an HTTP reachability probe, a PyPI metadata read — is not a research
bet. It is bounded, verifiable work with a number attached, and it converts "registered but
uninvocable" into "planable". That is the highest expected capability gain per hour available today,
and it is measured, not argued.

**Record failures as demonstrations, not as counters.** `macro_v1.note_failure` throws away the
state in which the plan failed. That state is the only thing that can narrow the applicability
condition — it is literally the `(s, 0)` example that §2B shows converts 25/25 unidentified cases
into identified ones. Retaining `(clause_shape, observed_state, outcome)` on refusal costs bytes and
buys the one evidence class the system currently cannot obtain. This is a small change to an
existing organ, not a new one, and it is the mechanism by which "learn from experience" becomes
true instead of merely fast.

**Only then, a prior.** If applicability must be learned where no interface exists, it needs a
hypothesis language rich enough that outcomes can pin it down — the donor-distilled route already
specified in `THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md` §5 Program C. That remains the right
long-horizon bet and this round does not change its priority relative to the two items above, both
of which are cheaper and land sooner.

---

## 4. What is wrong in the original sentence, stated plainly

- **"Give it the actions and let it experience them once."** The actions are not scarce — the
  registry holds 145 of them and the census prices every refusal at zero missing capabilities.
  What is scarce is the precondition, and one success cannot supply it: 200/200 cases leave an
  incorrect survivor standing, and the incorrect survivor is the one that says *always applicable*.
- **"So it learns them permanently."** Permanence is real and built. Permanence applied to the
  general survivor means the machine is wrong **permanently**, and confidently, in every state
  where the action does not apply. Round 2's finding (`permanence_amplifies_check_v1`) is the same
  result from the other side: the demonstration that is kept is the one that can be replayed, and
  replaying a success re-verifies only that it succeeded once.
- **"So we solve everything on a computer."** The measured gap is no longer about clicking or about
  intelligence. 90.19% on OSWorld-Verified (above the human baseline) coexists with 20.6% binary at
  release on OSWorld 2.0's 500-step long-horizon tasks, and the leaderboard best (Opus 5) is 44.3%
  ([Snorkel, Nov 2026](https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/)). The
  named failure modes there are losing track of constraints, missing mid-task information, guessing
  instead of asking, and **skipping verification** — all applicability and completion failures, none
  of them "the agent could not perform an action".
- **"We were making a sentient creature."** Drop the word and keep the measurable half. Experience
  changing competence on new problems is a well-posed target, and §2 is its honest instrument: it
  says the change experience produces is *faster and more confident*, and that the direction of that
  change depends entirely on whether the experience was allowed to contain a "no".

---

## 5. Receipts

```
python3 what_a_success_teaches_20261112.py
    A. 200 exact cases · 0 identified by one success · 13.05/32 survivors · G admits 68% of failing states
    B. 25/25 identified with outcomes · 2.76 demonstrations mean · 0 wrong conclusions
    C. 2 macros stored, 2 successes, 0 failures retained
    D. 145 capabilities · 125 premises · 100 PROVIDED · 14 SENSED · 11 BLIND · 135 fully decidable

/tmp/venv/bin/python -m pytest canonical/tests/test_what_a_success_teaches_v1.py -q
    15 passed
```

The tests pin the numbers and the invariants, not the prose: the space is the entailment lattice of
conjunctions; one success never identifies a requirement of size ≥ 2; the general boundary after a
success is the empty requirement and the specific boundary is the witness itself; a failure is the
only update that can delete the empty requirement; the naive probe's cost is as stated and its
state is unreachable to a success-only learner; the registry totals; and that a BLIND premise is
exactly one that is neither produced nor sensed, and is never reported as established.

**Two errors were made and are recorded rather than hidden**, because they are the reason to trust
the rest. The first version of the learner read `need <= probe` instead of `need <= probe[0]`, which
collapsed the space to one hypothesis and produced a perfect-looking "one success is enough" result.
The second version used the state satisfying the fewest survivors as its probe — a rule that on a
conjunction space picks the empty state and, as the test now pins, cannot be reached at all by a
learner that only ever observes successes. Both were caught by the tests within minutes, and both
would have produced a *more flattering* answer to the owner's question. That is the standing failure
mode of this project, and it is worth naming every time it appears.

---

## 6. Non-claims

The learner is constructed; the domain is this tree's registry and a five-fact toy universe, not a
GUI. A *constructed* demonstration is a clean `(state, outcome)` pair — real demonstrations carry
noisy perception, so the real numbers would be worse, not better. The exact figure 13.05 is a
property of a 5-fact universe with requirements of size ≤3; the invariant is the direction — the
version space after one positive example contains the empty conjunction and 2^|s|−1 others — not the
count. No capability is registered, no family flips, `truth.achieved` stays `false`, spend is $0,
model dependency is 0, and nothing here is independently verified.
