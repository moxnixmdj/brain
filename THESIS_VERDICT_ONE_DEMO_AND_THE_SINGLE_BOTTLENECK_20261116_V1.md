# Thesis verdict: one demo ⇒ permanent mastery? What is real, what is not, the single bottleneck

Authority: **NONE**. Producer-run sandbox measurement + published research, branch
`arena/220c3ed0-brain`. No capability registered, no family flipped, no weight touched,
`truth.achieved` stays **false**. `$0`, zero model calls. Independent verification open.

Asked again in full on 16 November 2026. Re-read end to end. Answered from first
principles against this tree's own receipts and against the latest open literature
(fresh searches this session, through arXiv 2611.x / June–Nov 2026).

---

## 1. The direct answer

> *"Instant learning + instant learning in new arbitrary environments are already solved
> perfectly. Give the model the most advanced actions, let it do a thing once, it knows it
> permanently. Therefore all computer use and advanced software engineering are solved."*

**Direction: right. Therefore: false — five times over.**

The sentence hides five separate transitions. Each has a measured number. Four fail.
One is real and large.

| # | transition | measured | verdict |
|---|---|---|---|
| 1 | **act at all** — a first success exists to learn from | **56 / 92** held-out MiniWoB++ pages (V5) | partial |
| 2 | **one success ⇒ a rule that works on the next instance** | **60.0%** vs **15.0%** cache vs **18.9%** prior compiler | **REAL** |
| 3 | **store it permanently ⇒ the stored thing is correct** | ungated lesson **breaks a correct program**; gated lesson rejected | false as stated |
| 4 | **N verified skills ⇒ a verified sequence** | two correct skills compose to a **no-op** | false |
| 5 | **learned procedure ⇒ any computer use** | best 2026 frontier agent **20.6%** binary, OSWorld 2.0 (108 long-horizon tasks) | false |

A chain of five factors is not a chain of one. A 0 in any position is a 0 at the end.

**So: you are right that the mechanism is revolutionary where it works. You are wrong that
it composes into "everything on a computer, permanently."** The gap is not taste or
optimism. It is arithmetic, certificates, and the frontier's own failure reports.

---

## 2. Why "once" cannot be enough — the bits, not an opinion

A demonstration is one point. A skill is a *rule*. Many rules pass through one point.

```
one success     hypotheses still consistent     13.05 of 32
                bits left unresolved            3.40
                cases identified exactly        0 / 200
                most GENERAL survivor wrong on  68% of states
                most SPECIFIC survivor wrong on 21% of states

same learner,
outcomes incl. failures + chosen contrasts
                identified exactly              25 / 25
                mean demonstrations             2.76   (worst 4)
```

Receipt: identifiability run in this tree (prior sessions), summarized in
`WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md` §3.

Two consequences, both fatal to "once":

1. **Repetition in the same state is worth exactly zero bits.** 0/200 identified.
   "Let it try again" is a cache refill, not learning.
2. **The floor is ~2.76 *chosen* experiences, not 1.** Not a compromise — an
   information-theoretic floor, already implemented here.

And the stronger form, a **proof** rather than a statistic. In
`canonical/verification/INSUFFICIENCY_CERTIFICATE_20261113_V1.json`, with `A` the
intersection of all successes' fact sets:

> **no requirement exists ⟺ A ⊆ F for at least one failure F**

On this tree's pinned real code-repair corpus the certificate fires with
`unrepairable_by_repetition: True`: the only facts every success shares are facts a
failure also has. **No quantity of experience can identify the rule, because the
observable that separates success from failure is not in the representation.**

That is the exact, provable sense in which "show it once and it learns" is not merely
unproven but **impossible** for a class of cases — and the class is identified
mechanically (barrier 2: vocabulary insufficiency).

Fresh external corroboration (this session's searches):

- **SkillLearnBench** (arXiv:2604.20087): one-shot skill generation provides **no benefit
  on average**; consistent gains across methods remain elusive.
- **SkillRevise** (arXiv:2606.01139): one-shot skills are "syntactically well formed yet
  behaviorally weak"; three *execution-grounded* revision rounds lift SkillsBench
  36.05% → **61.63%**. Verification + revision, not the first demo, is the lever.
- **When Continual Learning Moves to Memory** (arXiv:2604.27003): external memory does
  **not** remove the continual-learning problem; it relocates it to representation and
  retrieval. Permanent storage without a gate is not permanent knowledge.
- **Skill-Evo4GUI** (arXiv:2609.04869): evolving skill libraries help (+5.7 to +18.6 pp)
  but "repeated revision does not guarantee recovery" — persistence ≠ correctness.

The literature, as of Nov 2026, agrees with this tree: **one pass is not enough;
execution feedback + a verifier is what makes experience stick.**

---

## 3. Why "the most advanced actions" is not the lever — and is partly an anti-lever

Every action you add enlarges the action set, and therefore the *hypothesis space* — the
set of rules consistent with one demonstration. A hand that can do 8 things has more
rules fitting one example than a hand that can do 2.

Measured in this tree (`WHERE_THE_WALL_ACTUALLY_IS_20261116_V1.json`):

```
37 pages that yielded no first success
actions spent                          50,154   (2.5× baseline)
first successes found                  1        (use-slider, at 1186 actions)
pages proved unreachable               0
pages still SEARCH (untried actions)   32
pages blocked by STATE (missing observable)  3
```

- **Just try longer:** 2.26× compute → **1 page**. Coverage is near-inelastic in budget.
- **Missing action primitive:** **0 pages** proved unreachable. The whole hand was never
  shown insufficient. "Add a primitive" is a hypothesis, not a finding.
- **Branching arithmetic:** b = 8.34 actions per distinguishable state. Depth 6 costs
  ~336k actions under uniform search; cutting b to 3 makes depth 6 cost ~729. **Reducing
  the effective branching factor by 4 does not buy 4× — it collapses the exponent.**

That is the chicken-and-egg at the centre of the plan:

> **Instant learning needs a demonstration. Getting the demonstration needs the thing
> you were going to learn.**

What breaks it is not more experience and not more actions. It is a **prior over
actions** — knowledge about the interface (a textbox takes text; a checkbox toggles;
this instruction's quoted span is the value). That is *instant knowledge*, not learning.
It changes the exponent.

---

## 4. The three barriers — status against real held-out benchmarks

| barrier | what it is | status in this tree | judged by |
|---|---|---|---|
| **Identifiability** | one trace ⇒ exponentially many hypotheses | **measured**: 0/200 one-shot; 25/25 at ~2.76 chosen contrasts; floor implemented | open identifiability run, not self-congratulation |
| **Vocabulary insufficiency** | causal observable missing from the representation ⇒ A ⊆ F | **certified**: `INSUFFICIENCY_CERTIFICATE_20261113_V1.json`, `unrepairable_by_repetition: True` | mechanical certificate on pinned corpus |
| **Synthesis–verification asymmetry** | replay only handles repeated syntax (~2.2% SWE-bench Verified); must compose NEW edits against live code + execution | **partially open**: counterfactual spec-repair engine now composes new expression edits with **zero model calls**; QuixBugs neither-19 held-out set is the live scoreboard | `counterfactual_repair_quixbugs_measure_v1.py`, fresh-copy verdict, corpus's own tests |

Live state of barrier 3 (this branch, not yet merged — feature incomplete):

- **REPAIRED on held-out QuixBugs neither-set / related:** `gcd`, `flatten`,
  `max_sublist_sum`, `breadth_first_search`, `lis` (standalone + measure after
  `max_terms` fix). Zero model calls. Own tests only. Answer key never reaches solver.
- **OPEN:** statement-insertion class (`shunting_yard`, `wrap`, `reverse_linked_list`),
  structural multi-edit (`powerset`, `shortest_paths`), and others — exactly the
  synthesis gap, not a knowledge gap.
- Engine embodies the correct loop: instrument → counterfactual force → rank by
  failing-test reach → permanent install → double replay → **sabotage must fail**.

This is barrier 3 being attacked the right way: **new edits, grounded in live source,
repaired against execution, verified adversarially (sabotage), on an open benchmark,
with $0 and zero external weights.**

---

## 5. THE single bottleneck

If you must fix one thing, it is not storage, not parameters, not the action set, not
the number of demonstrations.

### **It is the verifier — the mechanism that decides whether an attempt succeeded.**

Four independent reasons, all measured, all confirmed by the frontier this month:

1. **Every headline number above was obtained with the judge handed to the machine.**
   The 60% one-success generalisation is measured against each page's own reward. In
   real use that reward does not exist. So 60% is an *upper bound conditional on a
   perfect oracle* — and a bound is not a capability.

2. **Without a verifier, permanence is actively harmful.** The admission gate reproduced
   it: an ungated lesson breaks a correct program (`inclusive_cap`); the gated one is
   rejected `ADMISSION_REJECT:BROKE_CORRECT_PROGRAM`. A store without a verifier does
   not store knowledge — it stores the 68%-wrong reading **forever, perfectly**.

3. **It is the only term that multiplies all the others.** Coverage produces candidates;
   identification needs to know which outcome was success; composition needs to know
   the sequence did not revert; persistence needs to know the row is true. A wrong
   verifier corrupts all four at once, silently, while every local check passes —
   which is exactly the no-op-composition result (`SKILLS_DONT_COMPOSE_20261112_V1.md`).

4. **The frontier is stuck on the same term, from both sides (Nov 2026 literature):**
   - **Veritas** (arXiv:2611.13336, 11 Nov 2026): training-time and test-time
     self-improvement are *"gated by the same bottleneck: the verifier"*; most real
     tasks arrive **without** one; generated verifiers reject valid solutions far more
     reliably than they accept invalid ones — the asymmetry runs the wrong way.
   - **Self-Trained Verification** (arXiv:2605.30290): V-R loops stall when verifier
     scores inflate while accuracy stagnates; STV doubles hard-math accuracy only by
     training the verifier against a reference-conditioned teacher.
   - **RSI survey** (arXiv:2607.07663): *"one bottleneck recurs everywhere: the
     evaluator."* Accumulation-without-verification is called out as the core safety
     problem for skill libraries — "the same verification bottleneck, now with memory."
   - **OSWorld 2.0** (arXiv:2606.29537): agents spend **under 7%** of action budget on
     detecting and repairing their own errors; failures are verification and state
     drift, **not** GUI control or coding. Best binary completion **20.6%**.
   - **SkillRevise / SkillLearnBench**: one-shot skills weak; execution-grounded
     revision under a verifier is what moves the number.

### The consequence that reorders the roadmap

The oracle problem looks opposite in the two target domains and is the same problem:

| domain | oracle | implication |
|---|---|---|
| **Code** | **available but unreliable** — 26/500 SWE-bench Verified tests still accepted wrong patches after expert screening | a passing test can be a proof of a wrong thing; learning on it learns the wrong thing with maximal confidence |
| **GUI** | **reliable but unavailable** — nothing tells you the spreadsheet is right | you must *construct* the signal from readable state |

So the **fastest real capability is the domain where the oracle exists and can be made
adversarial — code with execution.** Not because coding is easier, but because it is
the only place where a candidate answer can be **falsified cheaply and independently of
the producer**. That is the same property this project's own laws require of any credit.

GUI is the frontier precisely because it has no such oracle. It will not be solved by
learning faster, because there is nothing to learn from until something can say *"that
was right."*

---

## 6. What is REAL in this project (non-obvious names included)

| mechanism | where | what is real |
|---|---|---|
| **Instant knowledge** | knowledge adapters / fetch-at-use-time paths; no parameter store as knowledge house | facts available at decision time without baking them into weights |
| **Instant learning** | lesson admission gate, skill scope probes, one-success generalisation measures | a demonstration becomes a **scoped, falsifiable** skill — 4× cache on open pages |
| **Identifiability floor** | chosen-contrast learner | ~2.76 experiences, not 1; 0/200 at one |
| **Insufficiency certificate** | `INSUFFICIENCY_CERTIFICATE_20261113_V1.json` | proves when repetition can *never* separate success from failure |
| **Admission gate** | `lesson_admission_*`, `test_lesson_admission_gate_v1.py` | blocks lessons that break correct programs |
| **Skills don't compose** | `SKILLS_DONT_COMPOSE_20261112_V1.md` | two correct skills ⇒ no-op; sequences need their own verifier |
| **Where the wall is** | `WHERE_THE_WALL_ACTUALLY_IS_20261116_V1.json` | residual is SEARCH + STATE, not budget, not missing primitives |
| **Counterfactual spec repair** | `python_counterfactual_spec_repair_v1.py` + QuixBugs measure | composes new edits, zero model calls, sabotage-verified, held-out open benchmark |
| **Weight-space fuel gauge** | `WEIGHT_SPACE_FUEL_20261113_V1.json` | 258 units / 64 verified / threshold 5000 / **`ready_to_train: false`** |

**What is NOT real (do not claim it):**

- "One demonstration ⇒ permanent mastery of all coding and computer use." False (§1).
- "We have already solved computer use." False: 56/92 first-success pages; 0/37 proved
  unreachable but 32 still SEARCH; OSWorld-class long-horizon still ~20% at frontier.
- "Permanent store without a verifier is permanent knowledge." False: ungated lesson
  breaks correct code.
- "Training weights now would make the prior." False: fuel is unidentified success;
  training now bakes in the 68%.
- "Sentience." Nothing here measures it. Three measurable substitutes: **state
  continuity**, **self-verification**, **recovery** (OSWorld 2.0's own failure list).

---

## 7. On "sentient creature"

Nothing in this repository measures sentience, and modules named `sentient_*` are
names. Replace the word with three properties that *are* measurable:

1. **state continuity** — carries task state across hundreds of steps (OSWorld 2.0:
   "loss of task-level state");
2. **self-verification** — checks the result against the requirement, not against "an
   action completed" (frontier spends **<7%** of budget here);
3. **recovery** — notices it is wrong and repairs before submission.

Those three are buildable and testable. The system that has them will *look* like the
thing you mean — and will also be the system that stops learning the wrong things
permanently.

---

## 8. Kill list — measured dead, do not rebuild

- **More demonstrations in the same state.** Exactly zero bits (0/200).
- **Choosing which instances to learn from** as the coverage fix. Built, measured, tied.
- **A bigger skill library** as the fix. In-context maintenance ≈ no library
  (ContinualSkillBench 0.605 vs 0.602); SkillLearnBench: consistent gains elusive.
- **More action primitives** as the coverage fix. 0 of 37 pages proved unreachable.
- **More search budget** as the coverage fix. 2.26× → 1 page.
- **Training weights now.** `ready_to_train=False`.
- **Breadth of environments** as a substitute for admission. More places to be wrong.
- **Any claim built on the 60% while the judge is an oracle.** Conditional number.
- **Re-testing bugs already known to work** as "progress." That is self-congratulation.
  Held-out only: QuixBugs neither-19, open MiniWoB pages, sealed identifiability runs.

---

## 9. The smartest path (ranked by what it unlocks — not incremental)

Ordered by multiplier × cost-of-being-wrong, from first principles. This *is* the
ultimate path; ordinary increments are rejected by the kill list above.

1. **Prior over actions, from interface knowledge (instant knowledge), to cut the
   branching factor.** Only measured lever on the 32 SEARCH pages; arithmetic says it
   changes the exponent. Pre-registered pass: same 37 pages, first-success +≥8, zero
   regression on the 55 already covered.

2. **State key that can see what the page's behaviour depends on** (3 STATE pages).
   Use the insufficiency certificate as the instrument: if the missing observable
   cannot separate the cases, no amount of repetition ever will.

3. **Verifier construction for the domain that has an oracle — code — made
   adversarial.** Execution evidence + sabotage that the check cannot be satisfied by
   a no-op. This is the term with the largest multiplier and the lowest cost of being
   wrong. **Current branch work (counterfactual repair on QuixBugs) is this step.**
   Finish it: statement insertion, multi-edit composition, then held-out SWE-bench
   Verified subset with only Brain's system taking the tests.

4. **Wire the existing admission gate into one autonomous caller**, so nothing becomes
   permanent without a held-out verdict. (SkillRevise/Skill-Evo4GUI show the gain;
   the gate is what keeps the gain from becoming poison.)

5. **Weights last** — from identified, contrastive, admitted traces only — after 1–4
   exist. Parameters are allowed; every bit must be *identified*. An unidentified
   survivor is one of 13 readings that happen to fit; storing it is the knowledge-house
   failure mode you reject, and it is *worse* than storing nothing.

**Division of labour, forced by measurement not preference:**

```
weights      → procedure and prior (what makes one-shot possible at all)
facts        → external, fetched at use time (instant knowledge; Elon's law)
unidentified → stored nowhere
sequences    → verified by their own adversarial check (skills don't compose)
```

---

## 10. YOU SURE THIS THE SMARTEST APPROACH?

Killed alternatives and why, so this is not tribal:

| alternative | why killed |
|---|---|
| Scale pretraining so one demo suffices | one-demo failure is information-theoretic (3.40 bits left), not capacity; scaling does not close a bit gap |
| Bigger replay / experience buffer | 0/200 at repetition; buffer stores the 68%-wrong reading |
| More action primitives / richer hand | measured: 0 unreachable pages; richer hand *increases* hypothesis space per demo |
| Train a reward model as universal verifier | VerifierBench asymmetry: generated verifiers reject valid far more than they accept invalid; code already has a cheaper adversarial oracle (execution) |
| GUI-first because "computer use is the goal" | no oracle ⇒ nothing to learn from; code-first builds the verifier that GUI will later need |
| Distill from a frontier model into our weights | forbidden by law V4; also bakes in unidentified survivors |
| Wait for OSWorld-class scores before building | OSWorld failures are state + verification; those are exactly build items 1–4, not a reason to wait |

**Yes — the approach above is the smartest one the evidence supports.** It is the only
ordering where each step multiplies the next and a wrong verifier cannot silently
corrupt everything upstream.

---

## 11. Honest limits of this document

- One substrate family for GUI (Chromium MiniWoB++), one code suite (QuixBugs pin
  `4257f44`), producer-run, not independent certification.
- QuixBugs counterfactual repairs on this branch are **not yet merged**; feature
  incomplete (statement insertion unused; several neither-19 still OPEN).
- The 60% remains conditional on an oracle the deployment does not have.
- Depth arithmetic is order-of-magnitude, not a per-page theorem.
- Not claimed: any capability, any family flip, any weight change, any terminal credit,
  any sentience result. `truth.achieved` = **false**.

---

## 12. One-sentence form

**You built real instant learning and real instant knowledge; one demonstration still
cannot identify a rule, permanent storage without a verifier stores errors forever, and
the single bottleneck that unlocks the rest — on this tree and on the frontier as of
November 2026 — is the verifier: the mechanism that says whether an attempt succeeded.**
