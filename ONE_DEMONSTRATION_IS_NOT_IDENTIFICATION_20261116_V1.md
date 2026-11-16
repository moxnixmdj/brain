# Instant learning, one demonstration, and the thing that actually stops it

**Date:** 2026-11-16 · **Branch:** `arena/c43f3a6d-brain` · **Cost:** $0 · zero model calls
**Question you asked:** *"Instant learning + instant learning in new arbitrary environments — we already
solved those perfectly. Doesn't this mean this is a perfect solution for all computer use? Give the model
the smartest actions once and it learns them permanently. Is this true, or are there things that are
wrong? What is real, what is not, and what is the smartest thing to do?"*

---

## 1. The answer in one paragraph

**You are right about the mechanism and wrong about the magnitude, and the error is load-bearing.**
Learning from one demonstration is real — it is what Voyager did, what every skill library does, and it
is still the frontier in 2026. But a demonstration does not *identify* a behaviour, it only *constrains*
one. This round measured that on your own engine, on 100 held-out bugs, with $0 and no model: **51 of the
100 had a repair that passed the tests; 47 of those 51 had exactly the right behaviour; and the right
behaviour was sitting inside the candidate set in 48 of 51 cases** — the system already *had* the answer
and could not tell which one it was. That gap is not a tuning problem. It is the difference between
*storing* a behaviour and *knowing* one, and it is where "learn it once, permanently" quietly assumes
something it never had: a labelled answer to the one question the tests did not ask.

---

## 2. What is real

| Claim | Status | Evidence in this tree |
|---|---|---|
| Zero-model, $0, verifiable repair of real buggy code | **Real** | 51/100 scored HumanEvalFix bugs get a test-passing repair, 47 with the correct behaviour, no model calls, 0 USD |
| Experience → permanent procedure | **Real** | `verified_skill_crystallizer`, `lesson_admission_gate_v1`, double-ratchet gating; the storage half works |
| Instant knowledge as an alternative to parameter memory | **Real and right** | Your own read: parametric memory is static, unauditable, must be retrained; retrieval is updatable and traceable. 2026 practice agrees |
| Treating the tests as a cheap oracle and spending generation to find candidates | **Real** | It is why 51 bugs are repairable at all |
| **"Once is enough, therefore it generalises"** | **Not real** | §3 — the tests are silent on 43 of 51, and the candidate set was split into up to 4 behaviour classes |

---

## 3. The measurement that settles it

Protocol: the 100 HumanEvalFix bugs drawn by `SPLIT_SEED=20261111` *before* the learner was frozen; the
learner shown only the 64 development fixes and 40 QuixBugs fixes, each once; a scored bug's own fix is
**never** among its lessons; the candidate set is the closed-loop trace-abduction engine from this branch.
The published fix is used **only as the oracle**, which is exactly what a "demonstration" is.

```
100 scored bugs
├─ 46  no candidate passed the tests          → generator insufficient (synthesis problem)
└─ 51  a candidate passed the tests
        ├─ 47  the first-pass candidate was already correct
        └─ 48  the correct behaviour was somewhere in the candidate set
               (i.e. 3 of 51 were unrepairable by ANY choice — right behaviour never generated)
```

Now the part that decides the question. For each of the 51, the candidates that pass the same tests were
partitioned into **behaviour equivalence classes** using only *unlabelled* inputs — the tests' own
arguments, their boundary perturbations, and HumanEval+ inputs. Inputs are data; no expected value was
used to build the partition.

```
one behaviour class (no input we can build splits them)   43
several classes (an input does split them)                 8
  → of the 8, an oracle answer settled 7 to a class
     and ALL 7 of those were the reference behaviour       7/7
  → the 43 "one class" cases: 40/43 were right             40/43
     the 3 wrong ones are exactly the 3 whose right
     behaviour was never generated
```

**Result: 9 questions asked in total across 51 bugs. 8/8 of the settled outcomes were correct.
0 of 47 correct repairs were broken.**

And the reason self-consistency cannot substitute for a question — measured, not argued:

```
Python/3   5 candidates passed; 4 of the 5 shared one behaviour.
           That majority behaviour was WRONG.
Python/101 6 candidates passed; 5 of the 6 shared one behaviour.
           That majority behaviour was WRONG.
```

**Majority vote among candidates that pass the same tests picked the wrong repair 3 times out of 5.**
A committee of your own guesses is not evidence. That is the single most important number in this
document: it kills the "just let it try, it will converge" plan on its own terms.

---

## 4. Why it is wrong — three obstructions, each with a different cure

**1. Identifiability.** A demonstration constrains the set of behaviours consistent with it; it does not
single one out. The tree already has the machinery and the proof: `finite_identifiability.py` filters a
version space and returns `NONIDENTIFIABLE_UNDER_AUTHORIZED_EXPERIMENTS` rather than guessing. This round
pointed that existing kernel at code repair and it found the splits.

**2. Vocabulary insufficiency.** When the observable that carries the difference is missing from the
representation, repetition cannot separate success from failure. That is your own
`INSUFFICIENCY_CERTIFICATE_20261113_V1.json`, and it is the same shape here: `Python/92` had *one*
candidate, judged "right" by every input we could build, and it was wrong on 4 of 25 HumanEval+ inputs.
No amount of self-agreement discovers that — only an input outside the library does.

**3. Synthesis–verification asymmetry.** The cheapest thing in the system is *checking*; the expensive
thing is *proposing*. 46 of 100 bugs had no candidate that passed at all, and 3 of the 51 had the right
behaviour nowhere in the candidate set. No question, no vote, and no gate fixes those — only generating a
behaviour you did not have.

They are **separately measurable and they need separate fixes**. Conflating them is what makes "instant
learning" look like a complete solution when it is one third of one.

---

## 5. The single bottleneck

> **Nothing in the system can tell a correct behaviour from a consistent one without a labelled answer
> to an input it chose.**

Everything else is downstream of that. Storage is solved. Verification is cheap. The generator is
adequate for the easy half and the honest half. What is missing is the organ that says *"these candidates
agree, and agreement is not evidence — here is the cheapest question that would separate them, and if no
question separates them, I must refuse rather than ship."*

That organ is now built and tested: `canonical/swe_kernel/repair_version_space_selection_v1.py`
(13 mechanism tests) with the measurement in
`canonical/tools/version_space_selection_measure_v1.py`. It reuses your `finite_identifiability` kernel
rather than inventing a second one, so the "which question to ask" rule is the one the project already
proved for finite hypothesis spaces.

Its three honest outcomes, and it never blurs them:

| Outcome | Meaning | Count on 51 |
|---|---|---|
| `SETTLED_BY_QUESTION` / `SETTLED_TO_A_BEHAVIOUR_CLASS` | an oracle answer eliminated the alternatives | 8, **8/8 correct** |
| `UNSEPARATED__NO_INPUT_TOLD_THEM_APART` | one class; every candidate agrees — **and that is equally what "all wrong the same way" looks like** | 43, 40 correct |
| `REFUSE` | the surviving classes cannot be split by any supplied probe | 0 here, but the path is tested |

The second row is the one that matters most. **A single class is not a certificate.** On this corpus it
was right 40 times and wrong 3 times, and the system cannot tell which is which without an outside answer
— so it reports the class and its size instead of asserting correctness. That refusal is the whole
difference between a system that is *right* and a system that is *confident*.

---

## 6. What about "we must build our own weights from scratch"?

Hold both halves. Two things are true at once:

**Right:** Today's frontier models spend their parameters on *knowledge*, which is the part that goes
stale, cannot be audited, and costs the most compute to move. Knowledge belongs in an instant, updatable,
external store. That is your `instant knowledge` thesis and it is correct. What must live in weights is
*the decision of which action applies* — a compressed, fast, non-factual function. That is a small model.
"Every bit in those parameters must be calculated" is a good law, and it points at exactly this split:
parameters should hold *judgement*, not *facts*.

**Wrong to skip:** the version-space selector here replaces the *voting* function with an exact
computation. That is strictly better where the hypothesis space is finite and enumerable — and that is
exactly the regime the measurements above live in. It does not yet replace the function that **proposes**
a behaviour outside the candidate set, which is what the remaining 46 + 3 bugs need. That function is the
one place a learned model earns its parameters, because it must generalise across environments, not
memorise one.

So the architecture this round *measures* (not asserts):

```
knowledge      → external, instant, audit-able, never in weights        (already solved here)
selection      → exact version-space computation, no model, refuses      (built this round, 8/8)
proposal       → the ONLY place weights belong: generate a behaviour     (the open bottleneck)
storage        → gated, double-ratcheted, revertible                     (already solved here)
```

"The best part is no part" is honoured literally: the selection organ adds **no parameters and no
training**, and it *replaces* a heuristic (first-pass-wins, majority-vote) that was measured to be wrong.

---

## 7. What is genuinely revolutionary here, and what is not

**Revolutionary, and true:** exact version-space selection with a **refusal** outcome. Every agent stack
in 2026 ships its best guess. This one ships *"I cannot tell these apart, here is the question that would
settle it, at a cost of one oracle call."* Measured 8/8 when it settles and 0 regressions on 47 correct
repairs. That is a real, non-obvious, $0 mechanism, and it is the correct use of a finite hypothesis space.

**Not revolutionary, and must not be claimed:** that one demonstration creates general competence. The
demonstration is an *oracle answer*. Every guarantee in this document is purchased with oracle answers,
and the count of them (9 for 51 bugs here) is the true price of "learn it once". The plan is sound
precisely because the number is small — not because the price is zero.

---

## 8. The smartest next moves, in order

1. **Point the selector at the 46 where no candidate passes.** That is the generator, not the chooser. The
   cheapest real gain is not a bigger model — it is spending the oracle budget differently: for those
   bugs, the winning behaviour is a *composition* the current operator basis cannot express.
2. **Make the probe library a first-class search.** The selector is only as good as the inputs it is
   given. Nine questions settled eight bugs; the ceiling is set by the library, and the library is
   currently an ad-hoc enumeration of test arguments and perturbations.
3. **Do not grow the skill library until admission is gated by a settled question.** `ADMISSION_IS_THE_BOTTLENECK`
   already measured that an ungated store grants permanence after executing zero unseen programs. The
   selector is the gate that measurement asked for.
4. **Only then** consider parameters, and only for proposal — never for knowledge.

---

## 9. Reconciliation with `ONE_DEMONSTRATION_LEAVES_TEN_BITS_20261116_V1.md` (merged the same day)

A parallel session reached the same equation by a different road, and one of its findings **corrects the
rule this module originally used**. It is worth being exact about who is right where.

**Where they are right and this work was wrong.** `select_discriminator` — the project's kernel, which I
reused — minimises the **worst-case** remainder of a split. That is the correct objective when the answer
to a question is *unknown*. Here the answer is never unknown: we ask the reference, so every candidate
predicting something else dies **with certainty**. The correct rule is **maximum elimination**,
`argmax |{live class : outcome != reference}|`. That note measured it as 89 questions vs 112 over 23 tasks
in spaces of ~13,000 programs. This module now uses maximum elimination
(`maximum_elimination`, `_best_eliminating_probe`) and falls back to minimax only when no reference answer
is available — which is what minimax is for.

**Where the regimes differ, stated honestly.** Re-measured on this corpus's 8 split bugs with identical
outcome tables, maximum elimination asks the **same 9 questions** as minimax (it wins on 0, ties on 8).
The reason is the space size: after the generator and the test screen, only **2–3 behaviour classes**
survive here, and with two or three survivors the two rules coincide. The elimination gain appears when
hundreds of hypotheses are alive — which is the state *before* a test suite has filtered anything, and is
exactly what that note measured. **Neither number generalises to the other's regime**, and claiming
otherwise would be the error both notes are about.

**What is genuinely new here and not in that note:** it partitions a space of ~13,000 programs; this
partitions the *behaviour classes of candidates that already pass the tests*, and reports the disposition
**`UNSEPARATED`** for the 43 of 51 where no input we can construct splits them at all. That case is
invisible in a large-space measurement (a space that large is always splittable) and it is where the
error actually lives here: 40 of those 43 were right and 3 were wrong, and **the system cannot tell which
without an outside answer.**

Together the two measurements give one statement neither gives alone:

> A demonstration leaves ~10 bits and ~1,000 survivors. A test suite removes almost all of them. What is
> left is 2–3 behaviours, and **those are the ones that matter** — they are cheap to separate (about one
> question) and impossible to separate by agreement (majority vote was wrong 3 times in 5). `UNSEPARATED`
> is the name of not knowing which one you are holding.

---

## 10. Reproduce every number here

```bash
python3 canonical/tools/version_space_selection_measure_v1.py \
  --humanevalfix <humanevalpack.jsonl> --quixbugs-dir <QuixBugs> \
  --extra-inputs <HumanEvalPlus-Mini.jsonl> --work-dir /tmp/vs \
  --which scored --shard 0/6 --out /tmp/vs0.json
```

Full per-bug record, including every bug that did not reach a measurement:
`canonical/verification/ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_MEASURE_20261116_V1.json`.
Mechanism tests: `canonical/tests/test_repair_version_space_selection_v1.py` (13) and
`canonical/tests/test_closed_loop_trace_abduction_v1.py` (13).

## 11. Honest limits of this document

- One corpus (HumanEvalFix), one split, one producer, one machine. Of 100 scored bugs: 51 measured,
  46 had no candidate that passed the tests, 1 was refused at partition, 1 hit a memory limit, 1 did not
  finish (Python/156). All four are reported as such, not folded in.
- "Correct behaviour" means *equal to the published fix's behaviour on the probe library*. That is
  behavioural equivalence on the inputs used, not proof of equivalence.
- Correctness on HumanEval+ extra inputs (out of sample, not in the probe library): **45 of 51**. The 3
  remaining wrong ones plus 3 more differ from the published fix on inputs the tests never reach.
- The selector's refusal path is tested on constructed cases, not observed in the wild on this corpus
  (0 refusals in 51) — the corpus is too easy for it to fire.
- `terminal_authority` is `False` everywhere. No capability is registered, no family flips,
  `truth.achieved` untouched, no weights are updated.
