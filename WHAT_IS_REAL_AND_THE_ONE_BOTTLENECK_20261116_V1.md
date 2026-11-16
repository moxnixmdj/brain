# What is real, what is not, and the one bottleneck — 16 November 2026

Authority: **NONE**. Producer-run sandbox measurement on branch `arena/51709a27-brain`, base
`a0265cc6`. No capability registered, no family flipped, no weight touched, `truth.achieved` unchanged.
Independent verification is open.

This document answers one question, asked of this project four times now:

> *"Instant learning and instant learning in new arbitrary environments are already solved perfectly.
> So give the agent the most advanced actions, let it do a thing once, and it knows it permanently —
> therefore all computer use and the most advanced software engineering are solved. Am I right?"*

**The direction is right. Every "therefore" is false, and one of them was measured false in this
session — on a public benchmark, with real geometry, no model, $0.**

---

## 1. The claim is five claims, and they do not chain

"Once ⇒ permanent ⇒ any computer" hides five transitions. Each has a number. Four fail.

| # | transition | measured | where |
|---|---|---|---|
| 1 | **act at all** — a first success exists to learn from | **55 of 92** held-out MiniWoB++ pages (this session: **56/92**) | §2, `MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json` |
| 2 | **one success ⇒ a rule for the next instance** | **60.0%** vs **15.0%** cache vs **18.9%** previous compiler | `OPEN_BENCHMARK_ONE_SUCCESS_GENERALISATION_20261114_V1.json` |
| 3 | **permanent storage ⇒ correct knowledge** | ungated lesson **breaks a correct program**; gated one is rejected `ADMISSION_REJECT:BROKE_CORRECT_PROGRAM` | `test_lesson_admission_gate_v1.py`, §5 |
| 4 | **N verified skills ⇒ a verified sequence** | two individually-correct skills compose to a **no-op** | `SKILLS_DONT_COMPOSE_20261112_V1.md` |
| 5 | **learned procedure ⇒ any computer use** | best 2026 frontier agent: **20.6%** binary on 108 long-horizon tasks | OSWorld 2.0, arXiv:2606.29537 |

Step 2 is real and it is large: **four times a cache**, judged by each page's own reward, on tasks
nobody in this repository wrote. That is the part of your idea that is already true and working.

Steps 1, 3, 4 and 5 are why it is not "everything". A chain of five factors is not a chain of one:
a 0 in any position is a 0 at the end, however good the others are.

---

## 2. New measurement: the wall is not the budget, and it is not the hand

This repository last concluded (*"Ranked next work", 14 Nov*) that the largest unrealised pool was
coverage, and that it needed *"a substrate with real geometry (chromium) plus a search that uses the
whole hand."* The first half of that is already done — `..._V5.json` is a full run on headless
Chromium 153 with real mouse and key input, the whole hand, and guided ordering, at 600 actions per
page. I nearly rebuilt it before checking. It exists.

What nobody had separated is the question that decides the roadmap:

> Those 37 pages that yield no first success — are they **unreachable**, or merely **unexplored**?

The explorer answers this per page and its answer is not an opinion. `FAIL_CLOSED__REACHABLE_SPACE_
EXHAUSTED_GOAL_ABSENT` means every action reachable from every state it can distinguish was tried and
no success was among them: for that hand and that state key, a proof of unreachability.
`OPEN__ACTION_BUDGET_EXHAUSTED_GOAL_NOT_OBSERVED` means there were still untried actions.

So I re-ran exactly those 37 held-out pages, same pages (upstream `33c3b4dd`, byte-identical), same
hand, same Chromium, guided order, at **1500 actions — 2.5× the baseline**.

```
pages                                   37
actions spent                           50,154
pages that used the entire budget       32 of 36 measured
first successes found                    1   (use-slider, at 1186 actions)
pages proved unreachable                 0
```

| world | pages | what it means | the repair it asks for |
|---|---|---|---|
| **REACHED** | 1 | the budget *was* the wall | none |
| **STATE** — same look, different behaviour | 3 | the observation merges states that behave differently (`hot-cold`, `hover-shape`, `simon-says`) | add the missing **observable** |
| **SEARCH** — still unexplored | 32 | not reachable *and not proved* out of reach | improve the **prior over actions** |
| **ACTION** — every action tried, no goal | **0** | nothing at all | — |
| instrument error (`BridgeHang`) | 1 | `stock-market` hangs with this hand | repair the instrument |

Receipt: `canonical/verification/WHERE_THE_WALL_ACTUALLY_IS_20261116_V1.json`
(tool `canonical/tools/miniwob_where_the_wall_actually_is_v1.py`, 11 tests).

### What this kills

**"The residual is a missing action primitive."** Not one page closed. The whole hand — press,
triple-press, type, hover, grab, drop, nudge, wait — was never *proved* insufficient for any of these
pages: each time the search stopped, there were still untried actions (32 pages) or the state key had
already failed (3 pages). That does **not** prove the hand is sufficient — a page whose required
primitive is genuinely absent would also stay open — but it removes the evidence for the claim that
primitives are what stands in the way, and it makes "add a primitive" a hypothesis to test rather than
a finding to act on.

**"Just try longer."** 2.26× the compute bought **1 page in 37** (+2.7%), for +126% actions. Coverage
moves from 55/92 to 56/92. Coverage is near-inelastic in budget. If the wall were a budget wall, 2.5×
would have moved it far more than one page.

### What it establishes instead, arithmetically

Measured: **8.34 actions per distinguishable state** (50,154 actions over 6,017 states), median 150
states per page. Uniform search costs roughly `b^depth`:

```
b = 8.34        depth 3      580 actions      <- the budget reaches about here
                depth 4    4,838
                depth 5   40,349
                depth 6  336,511   (224x what was spent)

b = 2           depth 6       64 actions
b = 3           depth 6      729
```

The required budget grows **exponentially** in depth; the willingness to spend grows linearly. That
race is lost by construction, and the data shows it lost: 50,154 actions, one page. Reducing the
*effective branching factor* by a factor of four does not buy 4× — it collapses the exponent. **That
is the entire difference between "impossible" and "trivial", and it is not purchasable with
experiences, because an experience requires a first success, which requires reaching the goal.**

Which is the chicken-and-egg at the centre of your plan, stated exactly: *instant learning needs a
demonstration; getting the demonstration needs the thing you were going to learn.*

---

## 3. Why "once" cannot be enough — the bits, not an opinion

A demonstration is one point. A skill is a *rule*. Many rules pass through one point, and the machine
already counts them:

```
one success    hypotheses still consistent      13.05 of 32
               bits left unresolved             3.40
               cases identified exactly         0 / 200
               most GENERAL survivor, wrong on  68% of states
               most SPECIFIC survivor, wrong on 21% of states

same learner,
outcomes incl. failures + chosen contrasts
               identified exactly               25 / 25
               mean demonstrations              2.76   (worst 4)
```

Two consequences, both fatal to "once":

1. **Repetition is worth exactly zero bits.** Showing it the same thing again in the state it already
   worked in eliminates no hypothesis. "Let it try again" is not learning; it is a cache refill.
2. **The floor is ~2.76 chosen experiences, not 1.** Not a compromise — the information-theoretic
   floor, and it is already implemented here.

And the stronger form, which is a **proof** rather than a statistical argument. In
`INSUFFICIENCY_CERTIFICATE_20261113_V1.json`, with `A` the intersection of all successes' fact sets:

> **no requirement exists ⟺ A ⊆ F for at least one failure F**

On this tree's pinned real code-repair corpus the certificate fires with
`unrepairable_by_repetition: True`: the only facts every success shares are facts a failure also has.
More runs of the same kind report the same fact vector forever. **No quantity of experience can
identify the rule, because the observable that separates success from failure is not in the
representation.** Only a new observable helps. That is the exact, provable sense in which "show it
once and it learns" is not merely unproven but impossible for a class of cases — and the class is
identified mechanically.

So the variable was never the *number of experiences*. It is three things, in this order:

**the observable vocabulary → the hypothesis space → which contrast you buy.**

---

## 4. Why "the most advanced actions" is not the lever — and is partly an anti-lever

This is the part of your plan that is not just unproven but backwards.

Every action you add enlarges the *action set*, and therefore the *hypothesis space* — the set of
rules consistent with one demonstration. A hand that can do 8 things has more rules fitting one
example than a hand that can do 2. So unconstrained action richness **makes one-shot learning
strictly harder** while making coverage cheaper. They pull in opposite directions, and the data shows
both sides:

- the whole hand **did** raise first-success from 6 to 15 of 23 pages (real gain, real cost);
- and it multiplied the branching factor that every future search pays, which is precisely the wall
  measured in §2.

The resolution is not "more actions" and not "fewer actions". It is that **an action must arrive with
its use condition** — the situation that affords it. That is what "understanding" means operationally
in this system: not a table of what the hand can do, but a mapping from *this instruction and this
page* to *the one action worth trying*. A prior over actions. Everything else is enumeration.

---

## 5. The single bottleneck

If you must fix one thing, it is not storage, not parameters, not the action set, not the number of
demonstrations.

**It is the verifier — the mechanism that decides whether an attempt succeeded.**

Four independent reasons, all measured:

1. **Every number in §1 and §3 above is obtained with the judge handed to the machine.** The 60% is
   measured against each page's own reward. In real use that reward does not exist. So 60% is an
   *upper bound conditional on a perfect oracle* — and a bound is not a capability.
2. **Without it, permanence is actively harmful.** The admission gate reproduced it: an ungated lesson
   breaks a correct program (`inclusive_cap`); the gated one is rejected. A store without a verifier
   does not store knowledge, it stores the 68%-wrong reading — forever, perfectly.
3. **It is the only term that multiplies all the others.** Coverage produces candidates; identification
   needs to know which outcome was success; composition needs to know the sequence did not revert;
   persistence needs to know the row is true. A wrong verifier corrupts all four at once, silently,
   while every local check passes — which is exactly the no-op-composition result: both steps verified,
   the pair does nothing.
4. **The frontier is stuck on the same term, from both sides.** OSWorld 2.0: agents spend **under 7%**
   of their action budget on detecting and repairing their own errors, and their failures are
   verification and state drift, *not* GUI control or coding. Veritas (arXiv:2611.13336): both
   training-time and test-time self-improvement are "gated by the same bottleneck: the verifier", and
   most real tasks arrive **without** one. VerifierBench (arXiv:2610.28679): generated verifiers reject
   valid solutions far more reliably than they accept invalid ones — the asymmetry runs the wrong way.

### The consequence that reorders the whole roadmap

The oracle problem looks opposite in your two target domains and is the same problem:

- **Code** ships an oracle that is *available but unreliable*. 26 of the 500 SWE-bench Verified tasks
  still had tests that **accepted wrong patches** after expert screening. A passing test is a proof of
  a wrong thing, and a learning loop built on it learns the wrong thing with maximal confidence.
- **GUI** ships an oracle that is *reliable but unavailable*. Nothing tells you the spreadsheet is
  right; you have to construct the signal from the state you can read.

So: **the fastest real capability is the domain where the oracle exists and can be made adversarial —
code with execution.** Not because coding is easier, but because it is the only place where a
candidate answer can be *falsified cheaply and independently of the producer*. That is the same
property the mission's own laws require of any credit. GUI is the frontier precisely because it has no
such oracle; it will not be solved by learning faster, because there is nothing to learn from until
something can say "that was right".

---

## 6. The reframe that makes your two mechanisms fit together

You have two solved things: **instant knowledge** (fetch facts at use time; no parameters) and
**instant learning** (a demonstration becomes a scoped, falsifiable skill). Both are real. What this
session's measurement adds is that **they are being used on each other's jobs.**

```
instant learning   identifies a skill   -- needs a demonstration      -- blocked when no success exists
instant knowledge  supplies facts       -- needs no demonstration     -- not blocked
```

Coverage is blocked at *no first success*. Learning cannot break that; it is downstream of it. What
breaks it is **knowledge about the interface** — that a textbox takes text, that a checkbox toggles,
that a slider moves by nudging, that this instruction's quoted span is the value. That is a prior over
actions, and it is *knowledge*, not learning. Injecting it does not reduce the branching factor by a
constant; it changes the exponent (§2), which is why it is the only move that reaches depth 6.

And instant learning is not an alternative to weights. It is **what a strong prior looks like from the
outside**. One example identifies a rule exactly when the hypothesis space is small and the example is
maximally informative. "Small hypothesis space" *is* a built, calculated prior. Which gives your law
its operational meaning:

> **a parameter is justified only by evidence that identifies it.** An unidentified survivor is not
> knowledge; it is one of 13 readings that happen to fit, and the most general of them is wrong on 68%
> of states. Storing that in weights is the "knowledge house" you reject — and it is *worse* than
> storing nothing.

So the division of labour is forced by measurement, not preference: **weights carry procedure and
prior (which is what makes one-shot possible at all); facts stay external; unidentified readings are
stored nowhere.** Today the fuel store stands at 258 units / 64 verified against a 5,000 threshold,
`ready_to_train=False`. Training now would not build the prior; it would bake in the 68%.

---

## 7. On "sentient creature"

Nothing in this repository measures sentience, and modules named `sentient_*` are names. But the word
can be replaced with three properties that *are* measurable, and the frontier's own failure report
names them:

1. **state continuity** — it carries the task state across hundreds of steps instead of losing
   constraints (OSWorld 2.0: "loss of task-level state");
2. **self-verification** — it checks the result against the requirement rather than against "an action
   completed" (under 7% of budget spent on error detection);
3. **recovery** — noticing it is wrong and repairing before submission.

Those are buildable and testable. "Sentient" is not a target; it is a word that hides three targets.
The system that has all three will look like the thing you mean. The system that has them will also,
incidentally, be the one that stops learning the wrong things permanently.

---

## 8. Kill list — measured dead, do not rebuild

- **More demonstrations in the same state.** Exactly zero bits (0/200 identified).
- **Choosing which instances to learn from.** Built, measured, tied: 0.6987 vs 0.7038 for 360 extra
  page reads. The theory-recommended active learner lost to arrival order. Kept only as a control.
- **A bigger skill library.** In-context maintenance ≈ no library at all (ContinualSkillBench,
  arXiv:2608.03874: 0.605 vs 0.602). Library-level debt becomes load-bearing at scale.
- **More action primitives, as the coverage fix.** Measured this session: **0 of 37** pages are
  proved unreachable, so no page is evidence for a missing primitive.
- **More search budget, as the coverage fix.** 2.26× compute → 1 page. Near-inelastic.
- **Training weights now.** `ready_to_train=False`; the data that exists is unidentified success.
- **Breadth of environments as a substitute for admission.** More places to be wrong, unverified.
- **Any claim built on the 60% while the judge is an oracle.** That number is conditional on a
  verifier the deployment does not have.

## 9. Build list — ranked by what it unlocks

1. **A prior over actions, from interface knowledge (K1), to cut the branching factor.** This is the
   only measured lever on the 32 SEARCH pages, and the arithmetic says it changes the exponent. Pass
   condition, pre-registered: on the same 37 pages, first-success coverage rises by ≥8 pages while the
   55 already-covered pages lose none. Fail condition: any regression on the covered 55, or a gain that
   is explained by more actions rather than by fewer *tried* actions.
2. **A state key that can see what the page's behaviour depends on.** 3 pages stop because the same
   look behaves differently. That is a missing observable, and the certificate in §3 is the instrument
   that says whether a given observable can ever separate the cases.
3. **Verifier construction for the domain that has an oracle — code — made adversarial.** Execution
   evidence, plus a check that the check cannot be satisfied by a no-op. This is the term with the
   largest multiplier and the lowest cost of being wrong.
4. **Wire the existing admission gate into one autonomous caller**, so nothing becomes permanent
   without a held-out verdict.
5. **Weights last**, from identified, contrastive, admitted traces only — after 1–4 exist, not before.

## 10. Honest limits of this document

- **One substrate, one session, producer-run.** Chromium 153.0.8010.0 via `@sparticuz/chromium`, 480×360,
  one page, real layout and hit-testing; not a person's desktop. Not independent verification.
- **Not a leaderboard entry.** The first success is found by exploring against the page's own reward,
  which a leaderboard agent is not given. MiniWoB++ is also a small, relatively easy suite by 2026
  standards — frontier agents reach high scores on held-in subsets. That cuts both ways: our 60% is
  far below frontier, so it is *not* evidence of frontier capability, and the mechanism result stands
  on its own terms.
- **The depth arithmetic is an order-of-magnitude argument**, not a per-page theorem: the explorer
  merges states, so `b^depth` overstates the true cost. It does not overstate it by the two orders of
  magnitude that separate 1500 from 336,511.
- **One page (`stock-market`) could not be measured** — the bridge hung. It is recorded as an
  instrument error, not as a wall.
- **Not claimed:** any capability, any family flip, any weight change, any terminal credit, any
  sentience result.

## 11. Test ledger

```
canonical/tests/test_where_the_wall_actually_is_v1.py            11 passed
  incl. a stale stored label that says "budget" while the statuses say "exhausted"
        -> the statuses decide, so an older build cannot redirect the roadmap
```

The two load-bearing tests fail if the classification regresses: an exhausted space reported as a
budget problem would buy compute forever, and a state-blind stop reported as a budget problem would
buy compute for a defect that compute cannot reach.
