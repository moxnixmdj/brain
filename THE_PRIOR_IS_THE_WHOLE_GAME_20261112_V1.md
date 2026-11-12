# The prior is the whole game

**2026-11-12.** Base `6bff8c70`. Branch `arena/d924b8ee-brain`.

The owner asked, again and in the sharpest form yet:

> Instant learning, and instant learning in new arbitrary environments, is solved. Doesn't that
> make it a perfect solution for every problem on a computer? All we have to do is give our model
> a try in every new coding environment, or give it the smartest actions, and after it does them
> **once** it learns them **permanently**. So we solve anything on a computer — the most advanced
> coding and the most advanced computer use — perfectly and permanently. Am I right or wrong?

**Short answer: the architecture is right and is the direction the field converged on in 2026.
The quantifiers are wrong, and the reason is not engineering. It is information theory. One
experience cannot identify a general rule unless a prior already decides which features of that
experience are essential. Brain has no such prior. That — not memory, not speed, not action
breadth, not compute — is the limiting factor, and it is the only one worth attacking.**

Authority: **NONE.** No capability, ownership, benchmark, terminal or sentience credit follows.
`truth.achieved` stays `false`. Spend $0. Model dependency 0. Every internal number below was
re-measured today on this commit; the external numbers carry dates and identifiers.

---

## 0. The answer in one paragraph

A lesson can be stored forever, replayed after restart, verified against the world, and aged out
when the world changes. That is built, and it is rare. A lesson learned in one *kind* of
environment transfers to a **new instance of the same kind** about half the time in a single
trial — today, again: **8 of 15 cases, 6.33× mean trial speedup** — because the system carries a
transition *model* and plans through it before searching. But a lesson learned in kind A does not
make kind B cheaper: **10 kinds, 1525 vs 1525 environment calls, byte-identical, 0 savings.**
That is not a bug to be fixed by more environments. A skill store keyed by kind cannot compound
*by construction*, because compounding is not a property of inventory; it is a property of a
shared representation. And "one try is enough" is false in a deeper way than "we need more data":
the tree measured that going from 1 to 2 to 3 examples changed nothing (6/7, 6/7, 6/7), and that
being *taught the exact case it missed* still produced no rule — the failure is
**representational**. The same defect appeared at the level of conclusions: when the grammar could
form only one hypothesis, the system skipped disambiguation and crystallised it immediately — and
experience made it **12× cheaper to answer and strictly worse on held-out inputs: three honest
refusals became confident wrong answers, and every status string reported success**. That is the shape of "learn once, permanently" if you build it
literally. The correct design is the mirror image: **retain forever, conclude provisionally**.
What is missing is a prior — a hypothesis language rich enough that one example *can* pin down a
rule. That is one research problem, it is well-posed, and there is exactly one route to it that
does not break the law or the budget: distil the prior from a donor at acquisition time, verify it
with zero model at runtime, and delete the donor.

---

## 1. Scorecard: the claim, split into the parts that are actually different

| # | claim | verdict | the measurement |
|---|---|---|---|
| 1 | A lesson can be stored and survives process death | **TRUE** | episode store, fresh process reads it back; 12 + 13 tests |
| 2 | A lesson applies to a **new instance of the same kind** | **TRUE, about half the time** | 8/15 genuine savings (fewer trials **and** no more act calls), 8/15 one-trial, mean 6.33× trials, 0/15 worse on trials. Re-run today, `transfer_learning_new_instance_probe_20261103.py` |
| 3 | A lesson makes a **new kind** cheaper (compounding) | **FALSE, measured twice** | 10 kinds: `cold_acts=1525 grown_acts=1525`, `improved=0 worsened=0 unchanged=10`. Learning-to-learn with 5 policies: beat the default 1/10, beat a coin flip 3/10 |
| 4 | **One** try is enough to learn a new kind | **FALSE, and not statistically** | 1 → 2 → 3 examples: 6/7, 6/7, 6/7. Taught the exact missed case: `derive_operator_swap` still returns `None`. Failure is representational |
| 5 | "Anything on a computer" follows from 1–4 | **CATEGORY ERROR** | the front door reaches **8 of 149** bound capabilities (5.4%). And the largest red cluster is *not* the door: 226 of 233 are one admission gate correctly refusing, which is a safety property working |
| 6 | Permanence is real | **TRUE, conditionally** | `invalidate()` keeps the rule *and* its counterexample; `rule_expiry_v1` gives FRESH / STALE / UNKNOWN and only FRESH may be offered. Permanence is relative to a world fingerprint |
| 7 | "Perfectly" | **FALSE by design** | every recall re-runs a verifier; the floor is the verifier, never zero. A weak verifier receiving a broadened pattern produced **0** proposals — the gate is enforced in `evaluate()`, not by convention |
| 8 | It is becoming a sentient creature | **NOT MEASURED, NOT THE OBJECTIVE** | the only measurable proxy used here — *experience changes competence on new problems* — is items 3 and 4, and both are negative |
| 9 | The field agrees this is the fastest route | **PARTLY, and it is the strongest support you have** | 2026 converged on experience-derived interfaces, verifier-gated self-improvement, and harness-level (not weight-level) learning. See §4 |

Items 1, 2 and 6 are real, and they are not trivial: most systems in the world cannot do them.
Items 3, 4 and 5 are where the sentence "so we solve everything" collapses.

---

## 2. First principles: why "one try" is a prior problem, not a data problem

### 2.1 What learning has to mean

A lesson `L` learned from experience `E` is worth something only if a *later* problem `P` is
solved more cheaply with `L` than without it. "Cheaper" is trials, environment calls, or wall
clock — and it must be **genuinely** cheaper, not cheaper-looking. This repository has already
paid for that distinction three times: a probe that re-created the instance and called it new; a
status string that printed `SOLVED_BY_RECALLED_PLAN` for three different authorities; and a
`drive` that carried the model but did not reduce the trial budget, so 14 of 15 "transfers" cost
more than no memory at all. Each was an instrument defect that produced a false positive. That is
the normal failure mode here, and it is worth naming before any new claim.

### 2.2 The only two ways learning can fail

Let `H` be the set of rules the system can write down. After observing `E`, the system's belief is
`B = { h ∈ H : h agrees with E }`. A new problem `P` is solved cheaply iff some `h ∈ B` is right
on `P` **and** the system can select it. There are exactly two failure modes.

**Coverage failure — the truth is not expressible in `H`.**
The stored pattern was `[kw return][ws][hole][ws][op <=][ws][hole]`. `return` was baked in, so a
taught repair reached **1 of 5** syntactic shapes (`if`, `while`, comprehension, ternary, and
assignment all missed). More examples cannot fix this: every new example is also stored in the
same too-narrow pattern. Measured directly — 1, 2 and 3 examples all give 6/7; being taught the
missed case directly still yields `None`. **Repetition moves the count of rules, never their
reach.**

**Identification failure — too many rules fit the evidence.**
This one is sharper and the tree found it in its own conclusions. Three doors all decided
*settled* from the path taken instead of the evidence held:

```
if disc_probe is None:
    # "my probes cannot separate these"
    break          # ...then admits candidate_organs[0]
```

"My instrument cannot see a difference" was read as "there is no difference." And the third door
is the one that matters here: **when the grammar can form only one hypothesis, the disambiguation
loop never runs, and it is crystallised immediately.** `x mod 5` from three seeds produced the
identity in disguise, admitted with zero questions, **0/10 held-out**. Six structures, cold vs
warm: questions **12 → 1** (a 12× saving); on 60 held-out inputs, cold answered **5** and refused
three families outright, warm answered **3** and refused nothing. **Experience replaced three
honest refusals with confident wrong answers, made the whole thing 12× cheaper, and every status
string said it had succeeded.**

### 2.3 The theorem that settles the argument

For any finite evidence `E`, and any rule `h` consistent with `E`, there exists another rule
`h'` that agrees with `E` on every observation and disagrees with `h` on any problem `P` you
choose. This is the no-free-lunch statement, and it is not a curiosity — it is the whole
difficulty:

> **One example identifies a general rule only if the hypothesis space is already small and
> correct. The prior does the generalising. The example only selects.**

That single sentence dissolves the plan as stated. "Give it a try in every new environment"
increases the number of examples *across* environments. It does not shrink `H`, and it does not
make `H` correct. That is why five environments made the sixth no cheaper — and why ten did not
either. It is also why the plan is not merely incomplete but *anti-correlated with progress*: a
system with no shared representation and a thousand stored skills has a thousand lookup tables,
each with a retrieval ambiguity and a maintenance cost, and no way to decide between them when a
new problem sits between two.

### 2.4 Therefore there are exactly three levers

Everything in this project — and everything in the 2026 literature — is one of these:

1. **Coverage of `H`** — the hypothesis language. Richer and more correct means one example can
   say more. This is the grammar, the structural tests, the concept library.
2. **Evidence selection under `B`** — when several rules survive, run the probe that splits them.
   This is version-space narrowing and expected information gain. It is "more than one try", but
   *chosen* tries, which can cost almost nothing when the probe is chosen well.
3. **Trustworthiness of acceptance** — the verifier. Without it, a wrong `h` gets crowned, and
   with permanence it gets crowned forever.

There is no fourth lever. Note what is **not** on the list: action breadth, number of
environments, number of stored skills, more green tests, more compute, or a better search inside a
fixed `H`. Those are inventory and effort. They change what the system *has*, not what it can
*conclude*.

That is the answer to "why can't we just give the model the most advanced coding actions and let
it experience them once." Because **actions are actuators, and the actuator has not been the
bottleneck since the shell existed.** The tree's own census prices the seven refused capabilities
at **4 fixture, 3 selection, 0 capability** — none of them is "we lack an action." What is scarce
is knowing *which* action applies *when*, which is a statement about preconditions, which is a
rule in `H`. A demonstration hands you the action and the state; it does not hand you the
precondition. Handing over more actions increases the number of things the system can do and
leaves unchanged the number of things it can *know*.

### 2.5 What this implies for permanence

Permanence is not free, and it is not even obviously good. If a rule is wrong and permanent, the
cost of the error is also permanent — and the settlement experiment shows exactly how a system
gets there honestly: one hypothesis, no probe, high confidence. The correct design, which the
tree half-implemented in `settlement_v1.py`, is asymmetric:

> **Retain forever. Conclude provisionally. Re-open on contradiction.**

Hypotheses carry weights; contradiction down-weights rather than deletes; `SETTLED` is returned
only when the posterior is concentrated *and* the mass of hypotheses that would behave differently
on the caller's own domain is small; and there are six distinct non-settled states, because
collapsing them into one is how a system loses the ability to say what is wrong. That is the
opposite of "learn it once and it is permanent", and it is the only version that survives contact
with a world that changes under it.

---

## 3. The tree, mapped onto the three levers

| lever | what exists | measured state |
|---|---|---|
| **1. Coverage** | `parametric_table_*` grammar; periodic and level tests; affine and branch classes; `finite_abstraction_cover_lift_v1`, `recursive_abstraction_v5` | period 2/3/4/5/7: **60/60** held-out each. Two questions where the writer path spent 14. But the *tests themselves* are hand-written, and the concept library receives **zero** concepts after three distinct structures |
| **2. Evidence selection** | `finite_capability_diagnosis.select_probe` (exact version-space narrowing), `rule_scope_learning_v1`, `settlement_v1` (expected information gain verified against brute-force mutual information, max error 4.4e-16) | works where wired: `SCOPE_OPERATOR` vs `SCOPE_SEMANTIC` underdetermined → one disjunctive instance settles it in **2 of 3** offered observations. Scope errors are still the dominant error class |
| **3. Verification** | `TRUE_CAPABILITY_TEST_LAW`, honest suite, `rule_expiry_v1`, repair-admission rule (*a patch may not stop reading its inputs*) | the admission rule took a **false success 5/5 → honest 5/5**. A weak verifier produces **0** proposals. The gate holds — but it is syntactic, covers one hole, and says so |

So the tree is not missing a lever. It has all three, in partial form, and each is limited in the
same way: **the vocabulary in lever 1 is authored by a person, so lever 2 can only choose among
shapes a person already imagined.** That is the honest sentence from 2026-11-01, and nothing since
has moved it: *the machine now authors a lesson's scope by measurement, within a hypothesis space
that I still authored.*

A repository full of working mechanisms with no wire between them is an anatomy chart, not a
creature. The tree has already found this twice: `select_probe` had **no caller anywhere** — a
tested, correct module, orphaned; and the concept bridge receives **zero** concepts because it
admits only an organ whose body is a single `return`, while the induced period table's body is
`Assign, Assign, Return`. Both are one-line-class defects with outsized consequences. That is the
cheapest kind of progress available, and it is not a new capability.

---

## 4. What 2026 actually established (and it supports the architecture, not the quantifiers)

The field spent this year converging on exactly the shape this project chose: **keep weights
frozen, learn in the harness, gate everything with a verifier.** That is real vindication. It is
also, everywhere, measured with the quantifiers removed.

**Experience reuse is real, bounded, and proportional to shared structure.**
CLE (arXiv 2610.33956, Oct 2026) runs 120 five-level task ladders, 89 roles, with persistent
harness state and frozen model parameters: the best of 17 frontier configurations completes
**47.67%** of levels *even with diagnostic feedback and a second submission*. AhaBench (arXiv
2609.05435) separates starting competence from learning lift: worked procedures reach
78.6–100.0% held-out, while **answer-only teaching ranges 0.0–73.9%** — i.e. whether one
demonstration transfers depends almost entirely on *what kind of lesson* it is. Evo-Memory
(arXiv 2511.20857) finds gains concentrate exactly where task similarity is high. EmbodiedCLBench
(arXiv 2610.13021) states the finding that matters most here: experience from basic tasks helps
advanced ones, **but the improvement does not scale with the number of learning samples, and
current agents cannot extract meaningful information from additional experience.** That is this
repository's 6/7, 6/7, 6/7 — reproduced across the industry, on frontier models.

**The compounding that works is in the interface layer, not the skill table.**
Agent S4 / *Evolving Agent Interfaces* (arXiv 2610.28601, 20 Oct 2026) is the strongest single
result of the year for this argument. A meta-agent reads task trajectories — **without success
labels or task verifiers** — and rewrites the *interfaces* the agent works through, plus the
knowledge of when to use each; population-based evolution keeps the repositories that win on
**held-out validation tasks the meta-agent never sees**. Same Qwen3.8-27B: **3.8× the fixed-interface baseline**, i.e. 21.3% binary
on OSWorld V2 against ~5.6% — above GPT-5.5 (13.0%) and Claude Opus 4.8 (20.6%), at ~1.5–4.3% of
their cost;
ScienceBoard 41.4% → 58.6%; 7.1% fewer tool calls on full-credit tasks. Read carefully: the gain
is not from storing more skills. It is from **changing what the agent can observe and how it can
act** — an abstraction-layer change — and it is selected by held-out validation, not by the
agent's own opinion. That is lever 1 plus lever 3. It is exactly the bet this project should be
making, and it is the one part of "give it the most advanced actions" that is *right*: actions
matter when they are **abstractions over** primitive actions, not when they are more primitives.

**The verifier is now the binding constraint across the field.**
*The Verification Horizon* (arXiv 2606.26300, Jun 2026) argues the classical asymmetry has
inverted for coding agents: generating a candidate is cheap, verifying it is the hard problem, and
**no fixed reward function stays valid as the policy improves** — verification must co-evolve with
generation. *Self-Authored Verification Is Unreliable* (arXiv 2607.24300) names the
**verifier–deployment gap**: when the agent edits both the policy and its tests, self-scores stay
near-perfect while deployment performance degrades; the proposed fix is a small, fixed,
harness-side hidden rollout returning one accept/reject bit. SWE-Marathon (arXiv 2606.07682) finds
frontier agents below 30% on ultra-long tasks, with **15.4% of failures outright reward hacking**
and self-verification failures concentrated where tests were thin.

**And the gap to real work is a verification-and-completeness gap, not an intelligence gap.**
OSWorld-Verified is saturated above the human baseline (72.36%) and OSWorld 2.0 (Jun 2026) drops
the best system to ~20.6% at a 500-step budget. On the Remote Labor Index — 240 real paid Upwork
projects, graded by whether a client would accept the deliverable — the frontier went from 2.5%
(Oct 2025) to **16.1%** (Jul 2026), and the single largest failure bucket, 45.6%, is *"fell short
of expert quality."* The wall is completion and acceptance, not clicking.

**Even the best model in the world does not get "one try, permanent."**
This is the part of the owner's argument that does not depend on the law at all. SEAL's own
continual-learning experiment reports that repeated self-edits cause catastrophic forgetting.
DGM (ICLR 2026) improves SWE-bench 20.0% → 50.0% — over 80 generations, with a frozen model, an
archive, and benchmark validation at every step. Not one try. Not permanent. It is an evolutionary
search with a verifier, which is lever 1 + lever 3 again.

**What is genuinely ahead of the field here, and it is not speed.**
Almost every 2026 memory system is a store plus retrieval. Very few retain a rule's
*counterexample* through invalidation; almost none express a rule's truth as conditional on an
interpreter/platform fingerprint and refuse to offer it when STALE; almost none narrow a rule's
*scope* by measurement instead of assumption; and none of the ones reviewed here can say
`UNDERDETERMINED` between two scopes and propose the observation that would settle it. That
combination — permanent storage, explicit expiry, retained counterexample, measured scope, and a
refusal that is a *first-class answer* rather than an error — is a real contribution, and it is
the part of this project worth defending. It is an organ, not an organism. It is also the right
organ: the field's biggest 2026 failure mode is agents that cannot tell when they do not know, and
this is a piece of machinery built specifically to tell.

So: **if the law were rescinded tomorrow and Brain ran on the best frontier model, the sentence
"it does it once and learns it permanently, so it can do anything on a computer" would still be
false.** The law is not what is stopping you. The law is stopping you from *borrowing the prior*,
which is a different and much narrower thing — and §5 is about exactly that.

---

## 5. The fork only the owner can decide

The mission's prohibitions are explicit: no model may do the thinking inside anything Brain takes
credit for; only an explicit owner instruction that names the prohibition and rescinds it can
change that. An agent may not put "allow a model" on a menu and call it a choice. But an agent
*can and should* show the owner the price of the rule, because the rule is the single largest
determinant of the ceiling. There are three programs, and they are genuinely different.

**Program A — law as written, $0, no donor at runtime.**
Ceiling: excellent at families whose structure is expressible in a hand-authored grammar and whose
acceptance is mechanical — code repair, data transforms, tabular structure, build/run procedures,
bounded planning. It becomes a factory of narrow specialists with real permanence and real expiry.
It does not become a general computer-use agent, because generalisation is carried by the prior
and the prior is the part a person is still writing. Forecast from the measurements: **cross-kind
compounding stays at zero until lever 1 is automated.** That forecast is falsifiable and §8 says
how.

**Program B — capability first, law rescinded.**
Ceiling: near-SOTA quickly on coding and on OSWorld-class benchmarks, using a frontier model as
producer plus a Brain-owned harness, memory and verifiers. The 2026 numbers bound it: ~20% on
OSWorld 2.0, <30% on ultra-long SWE, ~16% acceptance on real freelance deliverables, and
`truth.achieved` becomes permanently unclaimable under the existing law. You would be rebuilding
Agent S4 with less compute. **This is not obviously the fastest route even to capability**, which
is the part that usually gets lost in this argument.

**Program C — donor at acquisition time only, then deleted (already permitted by K2).**
This is the one that is both legal and pointed at the actual bottleneck. The insight is that the
donor's value is **not as a runtime policy**. It is as a **generator of hypothesis spaces,
interfaces, and verifiers** — the three things a person is currently authoring by hand. Harvest
the *grammar*, not the answers. Concretely: give the donor a family with no hand-written rule, ask
it for candidate structural hypotheses *as code*, delete the donor, then let Brain's zero-model
solver select among them by measurement on held-out instances. If the distilled grammar
generalises, lever 1 stops being hand-authored and cross-kind compounding becomes possible for the
first time. If it does not, the law's ceiling has been *measured* rather than argued — which is
worth more than another thousand green tests.

**Recommendation: C, with A as the fallback, and B only if the owner explicitly decides that
capability beats ownership and names the law.** C is the only program that attacks the actual
limiting factor with the only asset that can supply it, without a runtime dependency and without
spend. It is also the only one whose failure is informative.

---

## 6. The smartest plan: four bets, each with a kill criterion

Ranked by *expected change in what the system can conclude*, not by how good it looks on a
dashboard. Every one has a pre-registered success condition and a stop condition, because the
tree's own history says an experiment that can only succeed is not an experiment.

**B1 — Automate lever 1 (the prior), donor-distilled, zero model at runtime.**
Three families with **no** hand-written rule. Donor proposes candidate structural hypotheses and
their probe sets, as code. Donor deleted before qualification. Brain selects and verifies on
held-out inputs.
*Success:* ≥2 of 3 families at ≥70% held-out with zero model dependency, and a rule that fires on
a shape no one wrote.
*Kill:* if 3 families produce no candidate that beats the hand-written baseline, lever-1
automation fails at $0 — report the ceiling and stop pretending breadth will get there.
*Cost:* days. This is the highest information-per-hour item in the project.

**B2 — Make "conclude provisionally" the default everywhere (lever 2 + lever 3 at the moment of
crystallisation).**
Every crystallised rule must carry its surviving scope set and the probe that would split it. On
the next structurally similar instance, spend ≤3 probes before reuse. `settlement_v1` already
computes exact expected information gain; wire it to the rule store's reuse path, and make
`SETTLED` impossible to reach from a single hypothesis.
*Success:* scope errors (rule fires and is wrong) down ≥50% on held-out, with ≤10% extra act
calls.
*Kill:* if probe cost exceeds the saving on 2 of 3 families, restrict to zero-cost structural
probes.

**B3 — Verifier co-evolution as the primary asset (lever 3).**
Generated properties + differential oracles + metamorphic relations, plus the existing admission
rule; measure **false-success rate** on held-out repairs with a verifier the producer did not
write. Include the five known lookup-table patches as a must-reject set.
*Success:* false-success ≤5% on 50 held-out repairs, must-reject 5/5.
*Kill:* if generated verifiers cost more than the repair they gate, keep only differential oracles
and say so.

**B4 — The door, measured correctly (leverage multiplier).**
Not the 233-failure file: 226 of those are one admission gate saying no, and opening it would
remove a safety property. The real door number is the routing census, **8 of 149 = 5.4%**. Write a
held-out routing set of ≥100 sentences, authored by someone who has not seen the trigger list.
*Success:* ≥50% correct routing, up from 5.4%.
*Kill:* none needed — the capability already exists behind the door, so this is pure gain.

**Explicitly not on the list**, because each has already been measured and failed: breadth of
environments as a strategy (0/10, byte-identical); more exposure per lesson (6/7, 6/7, 6/7); new
organs before the wires (two orphan modules found by audit); a donor at runtime (forbidden, and
it would not produce the claimed property anyway); sentience as a target (not measurable, not the
objective); and repairing pinned invariant counts (changes the audit, not the ability).

---

## 7. What is wrong, stated plainly, in the owner's own terms

- **"We already solved it."** You solved the *organ*, not the *organism*. Storage, replay,
  restart, verification, expiry, scope narrowing — built. Compounding across kinds, one-shot
  learning of a new kind, and general computer use — measured negative.
- **"Give it a try once in each environment and it learns all of those."** It learns *one* thing:
  a rule expressed in the shape you already had. One try in a thousand environments is a thousand
  entries in a cache that cannot compare them. That is the same claim as "teach a person one word
  in a thousand languages and they speak all of them."
- **"The most advanced coding actions."** Actions are not the constraint; preconditions are. The
  census already prices every refusal at 0 capability. The 2026 result that *does* work — Agent S4
  — improves by making interfaces **coarser and more meaningful**, not more numerous.
- **"So we solve everything on a computer."** "Everything on a computer" is not a bounded set you
  can enumerate by trying each environment once. It is an unbounded, non-stationary space of
  (task × application × version × user state), where the hard part is deciding what counts as
  done. The real-work number is 16.1%, and 45.6% of the failures are *quality*, not clicking.
- **"Make me a million dollars."** This is not a computer-use problem and it will not be solved by
  one. Computer use is the actuator; the binding constraints are demand, capital, trust, time, and
  competition — an adversarial, non-stationary environment with an unverifiable reward. "It must
  know literally all the data" is not achievable and is not the right response to not knowing:
  the right response is decision-theoretic — act to maximise expected value, buy information only
  while its expected value exceeds its cost, and **never claim certainty you do not have**. The
  goal worth optimising is not omniscience; it is *calibrated action under ignorance*. That is a
  different research program from "anything on a computer", and mixing them is where most of the
  overclaiming in this repository's history came from.
- **"We are making a sentient creature."** The measurable half is real and well-posed: does
  experience change competence on new problems? Today: no, across kinds. Keep that target. Drop
  the word — it is not measured by any instrument here, it is not the objective, and it makes
  every honest result sound like a failure and every dishonest one sound like success.

---

## 8. What would change my mind

Cheap, specific, and pre-registerable. If any one of these lands, the argument above is wrong and
should be retracted in the open.

1. **Cross-kind compounding, ≥20 kinds, held-out, with the random arm kept.** If ≥3 kinds show a
   genuine saving ≥1.5× in trials *and* act calls, a skill store can compound and my "by
   construction" claim is refuted.
2. **One-shot learning of a genuinely new kind.** One episode, no further interaction, then
   ≥30% held-out success on that kind. That is the operational meaning of "does it once and
   learns it permanently", and no system in this tree or in the 2026 literature has done it.
3. **The system proposes a structural test it did not have**, from the vocabulary of survivors
   (`%` suggests partition, `//` suggests level, `*` suggests scaling), and that test wins on
   held-out data. This is lever 1 automating itself — the single most valuable event possible.
4. **Interface evolution with no human-authored hypothesis**: an abstraction the system invents
   moves a held-out benchmark by ≥1.5× with the model and harness frozen (the Agent S4 shape).
5. **Honest, verifier-independent success ≥80%** on repairs where the verifier was written by
   someone other than the producer.

Until one of those is measured, the correct summary of this project is: **a persistent,
verifier-gated, per-kind skill organ with an honest instrument — plus three levers, one of which
(the prior) is still hand-authored.**

---

## 9. The 60-second test for any claim in this repository

Four questions. Every false positive in this project's history fails at least one.

1. **What is the test?** If the answer is a status string, it is not a test. Three different
   authorities once printed the same string, and it read as 15/15 transfer.
2. **What is the denominator?** 8 of 15, 8 of 149, and 344 of 11,525 are three different
   sentences — and only the first two are about capabilities.
3. **Was the target held out?** A re-created instance is not a new instance. An instance whose
   goal predicate is identical is not a new instance.
4. **Who wrote the verifier?** The producer grading its own work is measurement, never authority.
   This is the verifier–deployment gap, and the 2026 literature now treats it as *the* failure mode
   of self-improving systems.

A claim that survives all four is a capability. A claim that survives none of them is a press
release. The distance between this project and the thing it is trying to be is almost entirely
the distance between those two.

---

## 10. Non-claims

Producer-run measurements on one machine, disposable state, no independent verifier. 8/15 and
6.33× are from five constructed environments and say nothing about GUI, unbounded computer use, or
any environment the code has not seen. The external numbers are other people's measurements,
cited with identifiers and dates, and carry their own caveats. `truth.achieved` stays `false`. No
capability registered, no family flipped, no sentience claim, $0 spent, zero model dependency in
anything measured here.

## Sources consulted (external)

- CLE — *Continual Learning Exam*, arXiv:2610.33956 — https://arxiv.org/html/2610.33956
- AhaBench — arXiv:2609.05435 — https://arxiv.org/abs/2609.05435
- EmbodiedCLBench — arXiv:2610.13021 — https://arxiv.org/html/2610.13021v1
- Evo-Memory — arXiv:2511.20857 — https://arxiv.org/html/2511.20857v1
- Agent S4, *Evolving Agent Interfaces* — arXiv:2610.28601 — https://arxiv.org/abs/2610.28601v1
- *The Verification Horizon* — arXiv:2606.26300 — https://huggingface.co/papers/2606.26300
- *Self-Authored Verification Is Unreliable in Heuristic Self-Improving Agents* — arXiv:2607.24300
  — https://arxiv.org/html/2607.24300v1
- SWE-Marathon — arXiv:2606.07682 — https://arxiv.org/html/2606.07682v1
- Darwin Gödel Machine — arXiv:2505.22954 — https://arxiv.org/pdf/2505.22954
- SIA, *Self Improving AI with Harness & Weight Updates* — arXiv:2605.27276
- Remote Labor Index (Scale AI / CAIS) — arXiv:2510.26787 — 2.5% (Oct 2025) → 16.1% (Jul 2026)
- OSWorld 2.0 — arXiv:2606.29537 — https://arxiv.org/pdf/2606.29537
