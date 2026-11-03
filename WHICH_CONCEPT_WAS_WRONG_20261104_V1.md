# Which Concept Was Wrong?

**2026-11-04 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0 spent**

This closes the gap left open by the last document, and it does so by first discovering that the
mechanism I had pre-registered for it was **empty**. Both parts matter; the empty part more.

---

## 1. What I said the problem was, and what it actually is

Last document: *"the top-ranked move is to wire `helped=False` to a real outcome instead of a
caller's opinion."* Having read the call sites, that framing was wrong:

- Callers receive a string body and use it immediately — `python_feature_implement_function_spec.py`
  raises if it is empty and proceeds. There is no validation at emission.
- So at the moment a body is produced, **nobody knows whether it is right.** The synthesizer cannot
  decide this; it is a fact about when knowledge exists, not a missing wire.

The gap is narrower and more honest: **the notice must come from outside the library. What belongs
inside is attribution** — deciding which concept, of possibly several used in one failed program, is
responsible. That is a real problem with content, and it is where I went.

---

## 2. The mechanism I got wrong

I pre-registered this counterfactual:

> for each concept used by the failed program: substitute its body textually; if the program now
> passes, the concept is refuted.

It is vacuous, and the reason is embarrassingly simple:

> **Inlining a definition preserves semantics exactly.** So "does the program pass without concept
> X", implemented by substitution, is the same question as "does the program pass with X".

Measured: a two-concept failed program reported **both concepts innocent**, including the guilty one,
because the substituted program still failed — as it necessarily had to. A counterfactual that
provably cannot change the outcome is not a counterfactual.

This is the sixth instrument error in the project and the **first that was wrong at the level of the
idea rather than the implementation**. The previous five were bugs in code or data. This one would
have shipped as a working-looking module that could never report a culprit — and because it always
said "innocent", it would have looked *cautious* rather than broken.

I recorded the nullification in the pre-registration file before replacing it, and the benchmark now
contains a `vacuity_control` finding that demonstrates the flaw, so it cannot return disguised.

---

## 3. The mechanism that has content

The question is not about arithmetic, it is about the **search**:

> A failure is evidence about a concept when **re-synthesizing the same problem with that concept
> withheld succeeds.** A correct program over those examples existed, and the concept we were
> offering steered the search away from it.

If the re-synthesis also fails, the problem is out of reach either way and the concept is **not**
charged. That second arm is what stops the mechanism manufacturing a culprit.

## 4. Result: 5/5

| finding | measured |
|---|---|
| guilty charged, innocent spared | failed body `concept_bad0001(v, 1, h) * 2`, suspects `[bad]`, good **not** retired |
| charging repairs the next answer | OVERFIT → re-synthesize → **SOLVED** `concept_good0001(v, l, h) + 0.5` |
| no culprit for an unsolvable problem | adversarial target, nothing emitted, **0 retired** |
| vacuity control | inlined body is behaviourally identical — the flaw is on record |
| revision is reversible | `revive` → disconfirmations 0, retired False |

The first two rows are the loop closing. The library contained two plausible-looking concepts. The
search reached for the wrong one and produced a confident wrong answer. Nothing outside told it
which was at fault. Attribution re-ran the search without one suspect, found that a correct program
existed without it, charged that one, spared the other — and the very next attempt produced
`concept_good0001(v, l, h) + 0.5`, which generalises to four withheld points it never saw.

Four days ago the same situation produced `c or 0.5` and called it a day.

---

## 5. The honest bound

**The notice is still external.** Nothing here detects that a failure occurred. My benchmark calls
`attribute_failure` when it already knows the answer was wrong. A creature that must be told it
failed has gained judgement about *which part* failed, not the ability to notice failure.

That distinction is worth stating precisely, because it is where the whole project is currently
bounded:

| capability | status |
|---|---|
| invent a concept from examples | measured, works |
| notice two differently-written programs mean the same thing | measured, works |
| revise or retire a concept when told it failed | measured, works |
| attribute a failure to a specific concept | **measured, works** |
| **notice that it failed** | **absent** |

**Attribution is only possible when ablating the concept makes the problem solvable.** For a problem
nobody can solve, there is no evidence to distinguish concepts, and the mechanism correctly does
nothing — which means it is silent exactly when things are hardest.

**Thresholds are heuristics.** Three disconfirmations per refutation is chosen for a clean
trajectory, not derived, and the same criticism applies as last time.

**Non-claims.** No sentience. Pure Python over small numeric tuples; no I/O, no host execution, no
GUI; nothing here bears on reaching a shell or browser, which remain gated. `truth.achieved` stays
false. $0 spent.

---

## 6. What is now different, structurally

Three days of this project's work now compose into a loop that did not previously exist anywhere:

```
invent a concept from examples            ->  library grows
use it as a building block                ->  answers reach further
produce a wrong answer with it            ->  (noticed outside)
attribute which concept misled the search ->  library revises
retry the same problem                    ->  different, correct answer
```

Every stage is measured. The first four are internal to the creature's own state; only the initial
notice crosses the boundary. And the loop is **reversible** — `revive` undoes a bad retirement — so
the creature cannot ratchet itself into confident wrongness, which was the failure mode I fixed
yesterday at the level of individual priors.

That is the smallest honest thing that deserves the word "learning": not a model that improves, but
a history that constrains the next search and can itself be corrected.

**The single missing piece is now one component:** something that observes an outcome and *initiates*
the audit. Everything downstream of that is built and measured.

---

## 7. Ranked next moves

1. **The initiator.** A component that watches outcomes the creature already receives and decides
   "this failed, and I should audit". The audit machinery is complete; what is missing is the trigger
   and the judgement of *when* to spend it. This is the last piece of the loop.
2. **Repair rather than discard.** A refuted concept's body could be anti-unified against the
   programs that refuted it — reuse the semantic machinery in the opposite direction: from failure
   back to a corrected concept, instead of from failure to a deleted one.
3. Relative retirement (compare against the concept that displaced it) instead of the 3-and-0 rule.
4. Composition of invented concepts; concept invention on the primary path; backlog.
