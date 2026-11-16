# The verifier is knowledge, not learning — 16 November 2026

Authority: **NONE**. Producer-run sandbox measurement on branch `arena/754f5d1c-brain`, base
`fcd3ec29`. No capability registered, no family flipped, no weight touched, `truth.achieved`
unchanged. Independent verification is open.

This session asked the question for the eighth time, in its sharpest form:

> *"Instant learning and instant learning in new arbitrary environments are already solved
> perfectly. So give the model the most advanced coding actions, let it do a thing once, and it
> knows it permanently — therefore all computer use and the most advanced software engineering
> are solved. Am I right or wrong?"*

**Right about the direction. Wrong about every "therefore".** And this session does not answer
that with an opinion: it builds the one instrument that could have made the "therefore" true, runs
it on this repository's own code, and reports the number — which is small. The small number is the
finding.

---

## 1. The claim is five steps. Four of them are not learning problems.

| # | step | status | where |
|---|---|---|---|
| 1 | an action can be taken at all | **55 of 92** held-out pages, 56 after 2.5× compute | `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md` §2 |
| 2 | one success ⇒ a rule for the next instance | **60.0%** vs 15.0% cache, judged by each page's own reward | `OPEN_BENCHMARK_ONE_SUCCESS_GENERALISATION_20261114_V1.json` |
| 3 | a rule, once stored, is correct | ungated permanence **breaks a correct program**; gated one is rejected | `test_lesson_admission_gate_v1.py` |
| 4 | N verified skills ⇒ a verified sequence | two individually-correct skills compose to a **no-op** | `SKILLS_DONT_COMPOSE_20261112_V1.md` |
| 5 | a learned procedure ⇒ any computer use | best 2026 agent **20.6%** binary on 108 long-horizon tasks | OSWorld 2.0, arXiv:2606.29537 |

Step 2 is real and large: four times a cache, on pages nobody here wrote. It is the part of the
idea that already works. Steps 1, 3, 4 and 5 are not steps learning can take, because each of
them is a question about **evidence**, not about experience.

---

## 2. What was actually missing, said in one sentence

Every loop in this repository ends at the same object: something outside the candidate that says
which outcome was right. Where a test exists, the test is that object. In real work the test is the
expensive part, and the 2026 field reports the same wall from three directions — verification
skipping is the centre of computer-use failure (OSWorld 2.0), test-time self-improvement is
"gated by the same bottleneck: the verifier" (Veritas, arXiv:2611.13336), and **80.2%** of 86,156
agent-authored test patches carried weak or absent oracle signals (*All Smoke, No Alarm*,
arXiv:2606.18168). This tree measured its own version: the shipped test generator's two tests
scored **0.000** on the tree's own mutation engine, because
`assertNotIsInstance(result, BaseException)` is true of every function that returns.

So the question this session asked is not "how do we get more tests". It is:

> **With no specification, no test file and no model, what can be known about whether a piece of
> code is right?**

That is answerable, and it is the only form of the owner's question that has a number attached.

---

## 3. The mechanism: a law proposed by structure, confirmed by execution

New: `canonical/swe_kernel/specification_from_structure_v1.py`.
Measure: `canonical/tools/specification_from_structure_measure_v1.py`.
Receipt: `canonical/verification/SPECIFICATION_FROM_STRUCTURE_20261116_V1.json`.
Tests: `canonical/tests/test_specification_from_structure_v1.py`, **20 passed**.

Two layers, and the second is what makes the first honest:

1. **Proposal is structural and cheap.** A function called `normalize` claims a fixed point. A
   pair called `encode`/`decode` claims a round-trip. A name that says `sort` claims no element is
   lost; a name that says `unique` claims the set survives and the duplicates do not. `isabs` that
   disagrees with `posixpath.isabs` is wrong on the input where they disagree, and the standard
   library is on every machine. Unary functions are proposed for idempotence, involution and
   permutation-invariance; binary ones for associativity and symmetry.
2. **Confirmation is execution on the program as it stands.** A law may judge nothing until it has
   held on the baseline for every input where it is defined. The law is a hypothesis; the baseline
   is its first victim. This is the lesson admission gate's discipline, one level up.

Two refusals matter more than the confirmation, because they are the two ways a verifier lies:

- **REFUTED** — the relation fails on the program as it stands. It is not a law of this program, so
  it judges nothing. (It may be a defect report about the baseline; it is recorded, and not used.)
- **VACUOUS** — the relation holds, but no input in the grid could have broken it. A constant
  function is trivially its own fixed point. A check whose success case is "I didn't look" is the
  exact failure this tree keeps naming, so a vacuous law is counted and never used.

**Real geometry, not invented inputs.** The grid is seeded from the tree itself — its paths, its
source lines, its identifier lists — because every instrument in this project has come out stronger
on real inputs than on invented ones, and the MiniWoB result turned entirely on that difference.

**No part added.** No model, no parameters, no store, no runtime, no registry row. One function and
one bounded child process. Under the law the owner set — *the best part is no part* — a verifier
made of confirmed relations over code that already exists is the cheapest possible verifier.

---

## 4. The measurement, on this repository's own code

Corpus: `canonical/swe_kernel` and `canonical/tools`, 169 files, read as they are. Nothing here was
written for the measurement; the code being judged is the code that runs the project.

```
files scanned                                 169
modules offering a callable function          122
modules where at least one law was confirmed   16
modules judged                                 12

functions offered                             871
functions the grid reached                    384
functions with a non-trivial confirmed law     23      (6.0% of those reached)

laws proposed                                2,791
  confirmed by execution                       407
  refuted by the program as it stands          179
  vacuous (would have been a false check)      177
  not applicable (no defined input)          2,028

behaviourally-altered variants                 89
  rejected by a confirmed law                   8      ( 9.0%)
  rejected only by "it still ran"              23      (25.8%)
  not distinguished at all                     58      (65.2%)
```

The variants are produced by **this tree's own mutation engine**
(`python.tests.mutation_score.v1`), not by anything written for this measurement, and they are
variants of exactly the functions a law was confirmed on — a variant of a function no law talks
about measures the grid, not the specification.

Laws that did the rejecting: `IDEMPOTENCE` 5, `COMMUTATIVITY` 3.

### What the numbers say, without decoration

1. **A decided portion of correctness is recoverable from nothing but structure and execution.**
   407 laws were confirmed and executed 2,791 candidate relations to find them, all of it `$0`,
   no model, no network, no test file. Eight variants that would otherwise have been accepted were
   rejected with a concrete witness: the exact call, the baseline value, the variant value.
2. **The portion is 9%, not 90%.** Sixty-five per cent of behavioural perturbations of real code
   are invisible to this instrument. It is a real oracle and it is a *weak* oracle.
3. **The vacuity filter is doing most of the work.** 177 proposed relations held only because
   nothing could have broken them. An instrument that skipped that filter would have reported 584
   confirmed laws instead of 407, and 177 of them would have been false checks that pass anything.
4. **The wall is not the laws; it is the vocabulary.** Every law that fired here is a *piece of
   knowledge about what a name means* — `normalize`, `encode`, `isabs`, `sort`. Nothing in this
   tree invents that vocabulary; it is read off the same names a human read. Where the name says
   nothing about algebraic structure — an adapter, a planner, a router, which is most of this
   repository — no law can be proposed at all. That is the exact, measured form of the vocabulary
   insufficiency the owner named in
   `INSUFFICIENCY_CERTIFICATE_20261113_V1.json`, and it now has a coefficient: **65%.**

### The two denominator errors this measurement had before it meant anything

Recorded because the session that hides its own corrections cannot be trusted with the next number:

1. **First run: 0 of 144 variants rejected.** The cause was a denominator, not a mechanism: the
   mutation engine mutates *every* function, including variadic adapters no grid can call, and a
   variant of an uncallable function cannot be judged by any law. Corrected by narrowing the
   denominator to functions a law was confirmed on. The blind spot went from a meaningless 100% to
   a meaningful 72.7%.
2. **Second run: 0 of 77 rejected by a law**, with 161 laws "confirmed" — because 154 of them were
   `TOTALITY`, which catches only "it used to return and now it raises". That is a smoke alarm. It
   is why the headline separates *rejected by a law* from *rejected only by "it still ran"*: the
   difference between 9.0% and 34.8% is the difference between an oracle and a smoke detector.

### Four defects in the instrument itself, each now pinned by a test

1. The grid had no absolute path, so `isabs` was a constant `False` and looked idempotent. A law
   that holds because the function is constant is a tautology.
2. Symmetry was proposed on heterogeneous operands, so `a + b` "failed" `COMMUTATIVITY` on
   `"a" + 12` — a law about Python's type rules, not about the function. Preconditions are now
   decided before the call.
3. `MULTISET_PRESERVED` was proposed for a name that says "deduplicate", where dropping duplicates
   is the point. The name now selects the law, and execution still refutes the wrong one.
4. Importing a module to judge it ran the module's top-level code (`sys.path.insert`, `main`
   blocks). Only the selected function definitions and standard-library imports are compiled now,
   so no module-scope statement of real code ever executes. A test proves a module whose top level
   raises `SystemExit` is still judgeable.

---

## 5. The three ceilings the owner named, restated with numbers

**Identifiability.** One trace is consistent with many hypotheses; without a counterfactual the
learner picks surface accidents. This tree already counted it: after one success, **13.05 of 32**
hypotheses survive, 3.40 bits unresolved, **0 of 200** cases identified exactly; the most general
survivor is wrong on **68%** of states. The mechanism added this session is a *counterfactual
generator* in the only place counterfactuals are cheap: it invents the intervention (apply the
function twice; encode then decode; swap the operands; permute the sequence; compare with the
standard library) and keeps only interventions the program itself confirms. That is why it is a
learning instrument and not a test-writing instrument.

**Vocabulary insufficiency.** A rule cannot be learned if the observable that separates success
from failure is absent from the representation, and repetition cannot add it. Measured here in
code: **65%** of perturbations are separated by no relation this vocabulary can express, and the
laws that do fire are all read off names. The wall is a *vocabulary* wall, and a vocabulary is
knowledge.

**Synthesis–verification asymmetry.** Retrieving or replaying a seen edit covers repeated syntax —
**~2.2%** of SWE-bench Verified. Composing a new edit is the other 97.8%, and the reason it is hard
is not that the edit is hard to produce; it is that nothing cheap says whether the edit is right.
This session measured how much of that gap a spec-free verifier closes on real code: **9%**.

---

## 6. The answer to the owner's question

> *"Why can't we just give our model the most advanced coding actions and let it experience them
> once and then it will learn them?"*

Because the experience is not the missing half. **The verdict is.** A demonstration without a
verdict teaches the machine what happened, not what was correct — and the two differ on exactly the
cases that matter. Three measured consequences, in order of how much they cost:

1. **A richer hand makes one-shot learning strictly harder while making coverage cheaper.** Every
   action added enlarges the hypothesis space of rules consistent with one demonstration, and it
   multiplies the branching factor every later search pays: this tree measured **8.34 actions per
   distinguishable state**, so uniform search at depth 6 costs `8.34^6 = 336,511` actions against
   1,500 spent, and 2.26× the budget bought **1 page in 37**. Action richness is not free and it is
   not the lever.
2. **One experience cannot identify a rule.** The floor is **~2.76 chosen contrasts**, not one, and
   in a mechanically identifiable class no number of repeats can work at all, because the
   separating observable is absent. Repeating the same demonstration is worth **exactly zero bits**.
3. **Permanence without a verdict is worse than no memory.** The admission gate reproaches this
   directly: an ungated lesson breaks a correct program; a gated one is rejected. A store fed by
   unverified experience does not hold knowledge, it holds the 68%-wrong reading, forever, at full
   confidence.

So the honest ranking of what to build next is unchanged from the last two sessions, and this
session moved the first item from "argued" to "measured":

```
coverage prior (K1)  ->  state key  ->  verifier  ->  admission  ->  weights
                                          ^
                          this session: 9% of the gap, measured
```

**And the direction the numbers point is not "learn faster".** A verifier is *knowledge about what
correct means*. It arrives from four places: a test someone wrote, a type someone declared, a
specification someone stated, or a law a name implies. This instrument reads the fourth. It is the
cheapest of the four, and it is also the smallest — which is why the fastest real path to capability
is **acquiring the oracle**, not searching for it. That is a workload for the instant-knowledge
channel the owner already built, not for the learning loop.

---

## 7. On "the most advanced coding actions"

The advanced action this repository was about to build was a test generator, and its output was
measured at mutation score **0.000**. The advanced actions that exist (145 bound capabilities,
1,594 committed execution receipts) have **0** verified (situation → action → verdict) events usable
for weight-space learning, and this session adds none of that shape. So "give it the most advanced
actions" is currently an exchange of bytes for the *appearance* of capability: more code that runs,
no more code that can be told right from wrong.

The one action genuinely worth adding is the one this instrument supplies: **a counterfactual
generator that is confirmed by the program itself**. That is not a bigger hand. It is a better
question to ask the hand.

---

## 8. What this session does and does not establish

Establishes, on this tree's own real code, `$0`, zero model calls, zero network:

- A specification can be derived from structure and confirmed by execution with no test, no model
  and no human, and it rejects behaviourally wrong variants with a concrete witness.
- The size of that effect on this corpus: **8 of 89** variants rejected by a confirmed law,
  **23** more only by "it still ran", **58** not distinguished.
- The vacuity filter is load-bearing: 177 of 656 holding relations were vacuous and would have been
  false checks.
- A module's import side effects are never executed to judge its functions.

Does **not** establish:

- Any capability, family flip, benchmark movement, terminal credit, or sentience result.
- That a kill is a proof: it is one law, confirmed on this program over a bounded grid, separating
  one variant. The grid is bounded on purpose and the blind spot is printed beside the gain.
- That 65% is a property of code in general. It is a property of *this corpus* under *this
  vocabulary*; a larger vocabulary would lower it, and that is exactly the finding — the number
  moves with knowledge, not with compute.
- Independence: producer-run, one machine, one session.

---

## 9. Kill list — measured dead, do not rebuild

- **More demonstrations in the same state.** Exactly zero bits (0/200 identified).
- **A bigger hand, as the coverage fix.** 0 of 37 pages proved unreachable; branching factor is the
  cost and action richness raises the hypothesis space.
- **More search budget.** 2.26× compute → 1 page in 37.
- **A bigger skill library.** In-context maintenance ≈ no library (0.605 vs 0.602).
- **Training weights now.** `ready_to_train=False`; 258 units against a 5,000 threshold, and the
  data that exists is unidentified success.
- **A verifier built from a model's judgement.** Forbidden by law, and it would import the same
  unverifiability it was meant to remove.
- **Mutation score as a correctness proof.** It is a lower bound on detection over the mutants
  generated, and the two survivors on this tree's own fixture are equivalent mutants. The docstring
  of the engine says so; repeating it here keeps the next session from quoting 0.833 as a guarantee.
- **"A law that fires on nothing is safe."** `NOT_APPLICABLE` is not evidence of safety; that is why
  a law with no already-correct victim yields `REFINE`, never `ADMIT`.

---

## 10. Ranked next work, pre-registered

1. **Grow the law vocabulary, and count it as knowledge, not as capability.** Each new law shape is
   one more thing the machine knows about what a name means. Pass condition: on the same corpus and
   the same variants, *rejected by a confirmed law* rises above 8 of 89 with **no** rise in the
   vacuous count above 177 (a rise in vacuity means the new law is a tautology, not a law).
   Fail condition: any claim of the gain made while the vacuity count rises.
2. **Move the residual to the domain that has an oracle.** The 65% blind spot is a specification
   problem; the fastest place to buy specification is where one already exists — a failing test, a
   declared type, a stated requirement. Wire this instrument as an *amplifier* on top of a real
   test suite: of the mutants the suite already kills, none matter; of the survivors, how many does
   a law kill? That is the number that predicts whether an agent with weak tests can trust a pass.
3. **A state key that can see what behaviour depends on.** 3 MiniWoB pages stop because the same
   look behaves differently; the insufficiency certificate is the instrument that says whether a
   given observable can ever separate the cases.
4. **Wire the admission gate into one autonomous caller**, so no law or lesson becomes permanent
   without a held-out verdict.
5. **Weights last**, from identified, contrastive, admitted traces only.

---

## 11. Test ledger (producer-run, this tree)

```
python3 -m unittest canonical.tests.test_specification_from_structure_v1
  -> 20 tests, OK   (29.5 s)

python3 canonical/tools/specification_from_structure_measure_v1.py --max-modules 40 \
    --json canonical/verification/SPECIFICATION_FROM_STRUCTURE_20261116_V1.json
  -> the table in §4, reproducible, deterministic input grid, no network
```

The tests fail if: a law that the program breaks is used instead of refuted; a vacuous law judges
anything; a variant is judged by a law about another function; a module's top-level code executes;
a call that never returns hangs the instrument; a variant no law covers is counted as a pass; or a
number in the receipt exceeds what was executed.

---

## 12. External context used for ranking, not for authority

These informed the framing. They are not Brain capability evidence and they do not verify anything
here.

- OSWorld 2.0, arXiv:2606.29537 — long-horizon computer use remains weak; verification skipping and
  state drift are the central failure modes, under 7% of the action budget spent on error repair.
- Veritas, arXiv:2611.13336 — training-time and test-time self-improvement are "gated by the same
  bottleneck: the verifier"; most real tasks arrive without one.
- VerifierBench, arXiv:2610.28679 — generated verifiers reject valid solutions far more reliably
  than they accept invalid ones; the asymmetry runs the wrong way.
- All Smoke, No Alarm, arXiv:2606.18168 — weak or absent oracle signals in 80.2% of 86,156
  agent-authored test-file patches.
- GRASP, arXiv:2605.29668 — the gain localizes to the acceptance gate, not to skill writing.
- FGSE, arXiv:2611.14326 — falsification-gated self-evolution; harmful committed updates still 3.6%.
- Continual-ARC, arXiv:2611.14505 — "No harness-based method gains on unseen tasks, whereas
  weight-based learning shows substantial gains"; most harness methods fall below a
  demonstration-cache floor.
- Mutation testing, Offutt et al. 1996 (ROR/AOR/LCR/SVR operators), is the engine reused for the
  variants and is not claimed as a correctness criterion.
