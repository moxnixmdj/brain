# Instant learning: what is measured, what is inferred, and what is false

**2026-11-01.** Written to answer one question honestly: *if instant learning works, is
everything else solved?*

**Answer: no.** Instant learning is real here, and it is measurably good — but it is a
**multiplier on a multiplicand that is still zero in each new environment.** It makes a
solved thing cheap to do again. It does not make an unsolved thing solvable, and it has not
raised the solve rate in any matched measurement taken in this tree.

This document separates four things that are routinely collapsed into one sentence:

1. **instant** (sub-second, inside the current run),
2. **learning** (a verified success is converted into a reusable rule),
3. **permanent** (the rule survives restart, ships with the repo, merges across machines),
4. **general** (the rule fires on a *new* problem, not a renamed copy of the old one).

Only 1–3 are measured as working. 4 is measured as working **within one structural family
and failing outside it**, and no measurement shows it raising the solve rate.

Authority: **NONE**. Zero capability, ownership, benchmark, terminal or sentience credit
follows from this document. It changes no number and moves no row.

---

## 1. The truth ledger

| claim | status | the measurement |
|---|---|---|
| A one-shot structural learner exists and is not a stub | **TRUE** | `canonical/swe_kernel/verified_skill_crystallizer_v1.py` anti-unifies a verified before/after pair into a hole-bearing rule, admits it only after it survives a mutated twin, stores it in SQLite, and re-runs the caller's verifier on recall. |
| Recall replaces search on a structural repeat | **TRUE** | 6/6 structural lessons transfer with `hit=True` and `repair_search_invocations=0` (`canonical/verification/RETAINED_REPAIR_PRODUCTION_QUALIFICATION_20261101_V1.md`). |
| Recall is faster than cold solving | **TRUE, ~45%** | `floor_boundary` 1.473 s → 0.806 s; `iterator_extent` 1.441 s → 0.798 s, medians including external audit. |
| Learning survives a restart | **TRUE now, FALSE before** | The store used to sit in `canonical/astra_runtime/tmp/` (gitignored): 6 rules at the end of one session, **0** at the start of the next. Fixed by moving it out of tmp plus a tracked bundle of 5 rules that a virgin store seeds on first open. |
| Learning merges across machines | **PARTLY** | `export_bundle`/`import_bundle` carry rules by content address, union provenance, and refuse an entry whose id does not match its payload. A fresh store accepted 1 of 1. **What is still asserted, not demonstrated: nothing publishes bundles. Two machines merge only when a human moves a file.** |
| Learning **raises the solve rate** | **FALSE, as measured** | Matched learning-enabled vs learning-disabled arms: **6/9 vs 6/9** solved on historical repairs (`canonical/verification/HISTORICAL_REPAIR_TRANSFER_20261101_V1.md`: "no distinct-issue learning advantage"). Same rate, lower latency. |
| Learning generalizes to a **differently shaped** expression with the same meaning | **FALSE** | One taught `return t - 1` → `return t` repair was offered 5 neighbours: alpha-renamed ✅, different loop form ✅, different literal ✅, **same intent / different structure ❌**, unrelated function ❌. 3 of 5. Holes are `?id`, `?num`, `?str`, `?fresh` — that spans identifiers, literals and operator sequence, and stops there. |
| The learner learns from failures | **FALSE, by construction** | Crystallization consumes a *verified* before/after pair. A task that has never succeeded produces nothing to crystallize. |
| The learner learns from a **selection miss** | **FALSE, by construction** | `sentence → SELECTION → execution → verification → crystallization → store`. Recall sits inside the row that selection already chose. Measured directly: a C++ rule was taught and recalled `MATCHED`, and the door still answered `STATED_SWE_EFFECT_UNSERVED` with `selected: None`, because selection had declined before recall was ever reachable. |
| "Arbitrary environment" learning exists as a general form | **TRUE as code, THIN as evidence** | `canonical/runtime/environment_learning_v1.py` assumes only `reset() / act() / state()`, learns `(state, action) → state`, then BFS's the shortest plan — this is literally "the fastest way with minimal actions". `canonical/runtime/transfer_learning_v1.py` keys a recalled plan on environment shape across runs. **The entire recorded cross-run corpus is one episode**: a `run_gzip` plan on a `str` observation (`canonical/astra_runtime/state/TRANSFER_LEARNING_EPISODES_V1.json`). |
| CLI/GUI recipe abstraction (learning a *workflow*, not a repair) | **NOT IMPLEMENTED** | `HARDCORE_SWE_ALL_PROBLEMS_20261031_V1.md` §7 records it as "documented in the docstring — not implemented". |
| The admission gate is trustworthy | **TRUE, at a price** | 3/3 `.rstrip → .lstrip` lessons were **refused** by mutated-twin verification (`crystallized=False`, store count 0) and had to be solved cold. Refusing a lesson correctly is worth more than accepting it wrongly, but it means "it learned it" is not the default outcome of teaching. |
| Permanent means monotonically better | **FALSE** | Memory must be invalidatable. The audit verified invalidation plus artifact restoration, and the specific assertion identifies the exact original skill so a newly taught skill cannot mask resurrection of an invalidated one. A permanent store of stale rules is a liability, not an asset. |
| This makes the machine sentient | **FALSE — and not the mission** | Every receipt in this tree carries an explicit non-claim (`NOT_TERMINAL_AUTHORITY`, "no … sentience credit"). Sentience was operationalized into five testable behaviours in `canonical/governance/OWNER_ACTIVE_GOAL_20261018_V1.md` §5. Satisfying all five yields a very capable agent — which is the actual objective — and does not measure sentience. |

---

## 2. Four specific errors in "so we solved everything"

### 2.1 The multiplicand error
> *"After he does them at least once, he would learn all of those permanently."*

The load-bearing clause is **"after he does them at least once."** That is not a small
precondition; it is the entire problem, restated. Learning amortizes success #2 through #∞.
It cannot pay for #1. In a new environment the first success must come from capability
acquisition — compose, configure, synthesize, search, prove — and that is the expensive part
that the route order `DELETE → BYPASS → REUSE → ADAPT → SUBSTITUTE → COMPOSE → CONFIGURE →
INTEGRATE → SYNTHESIZE_NEW_PRIMITIVE` prices.

Stated as arithmetic: **learning × 0 first successes = 0.** A multiplier cannot rescue a
zero multiplicand, and every "we solved it" argument that starts from "it will do it once"
has quietly assumed the thing it claims to derive.

### 2.2 The routing error
> *"Give our model a try in all those new coding environments."*

Measured on the current tree: **443 registry rows, 566 declared effects, 11 rows ever
reached** by the 49 advanced SWE sentences; **3 rows serve 30 of the 36 served sentences**;
36 served, 13 refused, 0 false. The machine is **not short of capability — it is short of
declaration and routing.** 101 operations exist and 36 effects are declared.

This matters for the learning argument specifically: a taught lesson lives **inside a row**.
If the door does not route a sentence to that row, the lesson is never consulted, no matter
how many times it was taught. Teaching does not fix routing. So "try it in all the
environments" collides first with a declaration table, not with a memory table.

### 2.3 The abstraction error
> *"Just once on a computer, and he learns all of this, permanently."*

`environment_learning_v1` needs `state()` to return something **hashable and comparable**.
On a CLI that is a filename and an exit code. On a GUI it is pixels — a state space where
"learn the transition function by doing it once" is not one observation, it is a
tabulation nobody can afford. The gap between "learned `run_gzip` in one trial" and
"learned to fill a web form in one trial" is **observation abstraction**, and the recipe
layer that would close it is documented in a docstring and **not implemented**.

So the honest status of arbitrary computer use is: the general mechanism exists, the
measured evidence base is **one episode**, and the missing layer is named.

### 2.4 The "all the data" error
From the owner goal: *"It must know literally all the data, and everything must be done in
the fastest way."*

Taken literally this is not achievable by any system, and no amount of engineering changes
that: the unknown space cannot be enumerated, so "fastest" can never be certified globally.
**This clause is the one place the active goal as written cannot be satisfied as written.**

It has a computable version, and the repo already has the machinery for it — report a
**lower bound plus a named coverage residual** and refuse the word "fastest":
*fastest among the searched space, with this explicitly enumerated residual and this
acquisition cost to shrink it.* That is falsifiable, monotone, and it is what
"never conclude from one source" actually means operationally. Recommend adopting that as
the operational reading — by owner decision, not by agent reinterpretation.

---

## 3. What is genuinely strong here

Not everything in the plan is wrong. Five things are real and worth defending:

1. **The learner is not a lookup table.** Anti-unification into holes with a mutated-twin
   admission gate and verifier-re-run-on-recall is the correct architecture. It is why
   memory cannot silently produce a false pass.
2. **The refusal to widen a claim.** 6/9 vs 6/9 was reported as a **negative** result and
   the previous 9/9 headline was not restored by loosening the rename guard. That is the
   behaviour that makes every other number on this page worth reading.
3. **The refusal to let a model be the producer.** 15 of 19 quoted routes were found to
   contain an external model and were given zero credit. If "give the model a try" had been
   allowed into producer cognition, every number here would be unmeasurable.
4. **Minimal-action search is implemented, not promised.** BFS over a self-learned model is
   literally the owner's "fastest way with minimal actions", and it is honest about its three
   limits (no evidence → no model; trial count bounds what is knowable; a plan is a
   hypothesis until executed).
5. **Cost is separated.** `B_exec / B_verify / B_proof / B_JIT` are reported apart, so a
   memory win cannot hide as a reasoning win.

---

## 4. What is smartest to do next, ranked

Ranked by the repo's own criterion: capability gain × reuse breadth × reliability ÷
(wall-clock × compute × evidence risk). Items 1–2 are cheap and blocked by nothing.

**1. Move learning upstream of selection — a refusal/routing memory.**
Today a selection miss is never learned, so the machine can repeat the same miss forever.
Learn `sentence-shape → row`, admit a mapping only when it is re-verified on held-out
instances, invalidate on a miss. This is the only place where "learn once, never again" is
literally true of the *agent's own behaviour* rather than of a code fix — and it is the one
form of instant learning that directly attacks the refusal count. Already identified as an
open item; still open. **Highest leverage per hour on this page.**

**2. Generate the declarations (D1).** 101 operations, 36 declared effects, 11/443 rows
reached. This is a generator, not research: the capability is already written and unreachable.
Converts existing code into reachable capability, which is progress class
`VERIFIED_INTEGRATION_OF_OWNED_CAPABILITY`.

**3. Deepen the abstraction, not the trial budget.** `?id/?num/?str/?fresh` is macro
recording with holes. The 2-of-5 failures are all "same meaning, different shape", which
needs a **typed AST-subtree hole** (match any expression of the right type at the right
position). This is the exact boundary between the current learner and the "learn it once,
permanently" the plan wants — and it is synthesis work, not tuning.

**4. Build an instrument for the admission gate itself.** Nothing here measures the gate's
precision and recall. Today it is conservative to the point of discarding 3 of 3 real
lessons. A gate that refuses everything is safe and worthless; you cannot rank lesson
sources without knowing its error rates. Missing instrument, cheap to add.

**5. Use the model where the law permits it — as a donor, not a runtime.** K2 acquisition
is legal through the transfer gate as long as the donor is deleted before qualification.
That is what "give our model a try" should mean: harvest candidate rules from a donor,
prove them on fresh instances with Brain-owned mechanisms, then delete the donor. Anything
else re-creates the audit that zeroed 15 of 19 routes.

**6. Fix the instrument floor before optimising.** 2,248 test modules with no sitting that
finishes inside budget; a 54-case matrix with world oracles and no gate. Every gain from
items 1–5 regresses silently within a week without this. The 2026-11-01 inventory says this
in its own words: "every improvement in §9 without item 10 will regress silently within a
week."

**7. For computer use, attack observation abstraction first.** Do not start with arbitrary
GUIs. Start with a small typed predicate set — what changed, what is visible, what is
enabled — so state is comparable across apps. That is the difference between the one
recorded gzip episode and a workflow learner.

**8. Add rule expiry and re-verification over time.** There is no mechanism today for a
stored rule whose language, library or OS version moved underneath it. "Permanent" without
expiry is how a skill store becomes a source of confident wrong answers.

---

## 5. What the smartest move is *not*

- Not letting a model into producer cognition, in any wrapper, at any price, on hard cases
  only. `NO_MODEL_PRODUCER_COGNITION` / `HOSTING_DOES_NOT_LAUNDER` / `K3_FORBIDDEN`.
- Not reading 6/9 vs 6/9 as a learning win. It is a latency win and a null rate result.
- Not chasing a benchmark number. `RED_ROW_IS_NOT_AUTHORITY`.
- Not claiming sentience, and not asking the owner to soften the objective. It is
  open-ended by design; a missing mechanism is a finding, not a reason to edit the target.
- Not repeating "it generalizes, so everything is solved". The tree already falsified it
  with its own measurements; repeating it is the failure mode
  `MEMORY_IS_NOT_AUTHORITY` exists to prevent.

---

## 6. The one experiment that would settle it

Teach exactly one lesson, then offer **20 structurally novel instances from a different
repository and a different language**, none of them alpha-renames.

Prediction from the measurements above: **near 0 hits** outside the trained structural
family, high hits inside it. If that prediction holds, instant learning is a **speed and
consistency multiplier for a family you already solve**, and the plan's remaining work is
capability acquisition plus routing — not more memory. If it fails and hits are high, this
document is wrong and should be replaced by the measurement that replaced it.

That is the difference between a story and a result, and this repo's only real asset is that
it keeps choosing the second.

---

## 7. Non-claims

No capability, ownership, benchmark, acceptance, promotion, terminal, permanence, optimality
or sentience credit is claimed or implied. Zero incremental spend. Zero model dependency in
any producer path. Every number attributed here is quoted from a measurement already in this
tree, with its source named; none was produced by this document.
