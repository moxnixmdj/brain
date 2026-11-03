# Is it a perfect solution for everything? — answered by re-running the instruments

**2026-11-03.** The owner asked, in substance:

> Instant learning and instant learning in new arbitrary environments are solved. Doesn't that
> make this a perfect solution for every problem Brain has and anything a computer does? All we
> do is give the model a try in each new environment; after it does a thing once it learns it
> permanently. So we solve everything on a computer — plus the most advanced coding — perfectly
> and permanently. We were trying to make our model a sentient creature. Is this true, or is
> something wrong? What is real, what is not, and what is smartest to do?

This is the answer, after **re-running the probes on this checkout (`a70480d`) rather than
quoting the documents**. Every number marked *fresh* was produced in this session, today; every
number marked *documented* is a prior measurement in the tree that I did not re-execute.

Authority: **NONE.** No capability, ownership, benchmark, terminal or sentience credit follows.
`truth.achieved` stays `false`. Model dependency 0. Spend $0.

---

## 1. The verdict, claim by claim

| the claim | verdict | why |
|---|---|---|
| Instant learning works | **TRUE** | Taught one lesson → `crystallized: true`, stored, recalled. *Fresh.* |
| Instant learning in new arbitrary environments works | **TRUE for a defined class of environment** | 5/5 families cold-solved; **10/10 new instances solved by recalled plan**, several at **1 trial**. *Fresh, re-run today.* |
| …therefore it solves everything on a computer | **FALSE** | Three independent breaks: observation (pixels are not a hashable state), verifier precision (broadening is only safe under a real test suite), and routing (a lesson lives *inside* a registry row; teaching does not make the door route to it). |
| "Does it once, learns it permanently" | **TRUE for the part that gets abstracted — FALSE as "all of those"** | 1 example → 6/7, 2 → 6/7, 3 → 6/7. More exposure buys nothing; the limit is representational, not statistical. *(documented)* |
| "Plus the most advanced coding work, perfectly" | **the 5/5 was a false success; it is fixed and re-measured 5/5 honest — but "perfectly" is still false** | The two-file repair was a lookup table fitted to two assertions: 0/5 honest. A *patch may not stop reading its inputs* gate moved it to 5/5 honest. The gate is syntactic, covers one hole, and says so. *(documented)* |
| "So we solve everything on a computer" | **NO — and the refusals are instrument-readable** | *Fresh:* 49 advanced SWE sentences through the live front door → **37 served / 12 refused**, each refusal naming its own cause. |
| "We were making a sentient creature" | **the measurable half exists; sentience is not measured, and is not the objective** | Self-model of ignorance ranked by value (`ignorance_ledger_v1`), a `Creature` that survives restart and an OS kill, and chronicles **0/112 self-authored obligations closed**. No instrument in the tree measures sentience; every receipt carries that non-claim. |

---

## 2. What is real — the strongest true statements, measured today

### 2.1 Cross-run transfer of a solution to a new environment: 5/5, verified by execution

`transfer_learning_new_environment_probe_20261101.py`, re-run on this HEAD:

| family | COLD (learn) | FIRST (unseen instance) | SECOND (unseen instance) |
|---|---|---|---|
| lock, 3 dials | 32 trials — learned | **1 trial** — recalled | **1 trial** — recalled |
| toggles, 4 switches | 8 — learned | 8 — recalled | 8 — recalled |
| word accumulator | 64 — learned | **1** — recalled | **1** — recalled |
| grid, reach a cell | 16 — learned | **1** — recalled | **1** — recalled |
| modulo counter | 8 — learned | **1** — recalled | **1** — recalled |

COLD 5/5, FIRST 5/5 `PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN`, SECOND 5/5. A recalled plan is
executed and the goal is observed; it is a hypothesis, never a fact, and a wrong one is
remembered as wrong. **This is genuine instant learning across runs and it deserves to be called
solved.** Its honest scope: these environments report a compact, hashable `state()`.

### 2.2 The shape barrier is real and has moved — the biggest single gain in the tree

The old probe (`instant_learning_transfer_probe_20261101.py`, re-run today) still reports
**2/9 executed, 1/7 novel shapes, 0/4 cross-language** — because it calls the recall path with the
default `CALLER_PREDICATE` verifier. That is now measuring an old path. The new one
(`canonical/tools/pr_c2_apply_time_broadening_benchmark_v1.py`, re-run today):

| path | bug shapes recalled | misapplications |
|---|---|---|
| stored rule, context-anchored (as taught) | **2/5** | 0 |
| apply-time narrowing, real `ProjectTestOracle` (`TEST_SUITE`) | **5/5** | **0/4** |
| same narrowing, weak verifier (`CALLER_PREDICATE`) | — | **0 broadened proposals reach it** |

Fresh: `taught_crystallized: true`, `stored_context_anchored: true`, `direct_recall_count: 2`,
`scoped_test_suite_recall_count: 5`, `negative_control_misapplications: 0`,
`weak_verifier_broadened_proposals: 0`.

**And this is the whole lesson of the whole project in one table:** the same broadening that is
sound under a test suite corrupts 3 of 4 correct sources under a weak verifier. **Precision is a
property of the verifier, not of the pattern.** So "it learns it permanently and correctly"
reduces, every time, to "you had a real oracle" — which is exactly the condition you do *not*
have in the general case.

### 2.3 Cross-language: the lesson does travel, but only on the permissive path

Fresh probe, teaching `<= hi → < hi` in Python, then recalling on a Go source:

- scoped `TEST_SUITE`: **refused** (my probe's verifier returned a bool, which is auto-demoted and
  then legitimately refused — the gate working, not a defect).
- unscoped `CALLER_PREDICATE`: **hit**, `recall_strategy: cross_language_lexical`, patched to
  `return x < hi` in Go.

So the *unverified* route is the one that carries a lesson across languages. That is not a bug to
celebrate; it is a precise statement of where the safety boundary sits today.

### 2.4 A false absence I produced myself, in ten minutes — and it matters

Two tests in `canonical/tests/test_optimal_unified_creature_and_prc2_v1.py` failed
(`compile_rule_to_cst_skeleton` → `unexpectedly None`, `assertIsNotNone` on a cross-language
recall) **only because the pinned substrate (`tree_sitter==0.20.4`,
`tree_sitter_languages==1.10.2`) was not installed in the sandbox.** After installing the
declared versions: **27 passed**. The capability was always there; the substrate was missing and
the failure was silent.

This is the fifth recorded species of instrument defect on this project and the same family as
the other four: *the machine looks worse than it is when an instrument is broken, and looks
better than it is when an instrument is permissive.* Anyone reading a capability number here
must know which of those happened.

---

## 3. What is not real — the four breaks in the argument

### Break 1: "anything on a computer" is an observation problem, not a learning problem

`environment_learning_v1` needs `state()` to return something **hashable and comparable**. A CLI
reports a filename and an exit code. A GUI reports pixels. "Learn the transition function by
doing it once" is one observation on a 3-dial lock and an unaffordable tabulation on a desktop.
The recipe layer that would turn a screen into a comparable state is **documented in a docstring
and not implemented**. That is the honest boundary of "any computer", and it is a boundary of
*observation*, not of *learning*. What remains is one sentence: *pyautogui drives a real OS.*

### Break 2: "at least once and it learns all of those" is measurably false

1 example → 6/7, 2 → 6/7, 3 → 6/7. Taught the one missed case *directly*, the operator-swap
deriver still returns `None`: it cannot solve the lesson it was just shown. Repetition increases
the **count** of rules, never their **reach**. The multiplicand is not ~1 per success; it is ~1
on structural repeats and ~0 on a different shape. *(documented, three independent ways)*

### Break 3: the door is contract-filling, not paraphrase matching — teaching does not fix routing

A learned lesson lives **inside a registry row**. If the sentence never selects that row, the
lesson is never consulted, however many times it was taught. Measured fresh today: **37/49
served, 12 refused**, and the refusals are dominated by
`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADM…` (confinement admission) and
`POLYGLOT/PYTHON_SWE_REFUSED:*` (the stated effect was not present to act on). Several of the
refusals are **fixture** and **selection** defects, not capability defects — the tree's own
`defect_owner` classifier prices them that way. "Give it a try in all those environments"
collides first with a declaration table, not with a memory table.

### Break 4: the hypothesis space is still authored by a person

The machine now authors a lesson's **scope** by measurement (`rule_scope_learning_v1` calls
`select_probe`; a rule the tree once declared too narrow now reaches 7/7). But building a third
hypothesis required a human to see that `a < b or a == b` means `a <= b`. The frontier did not
disappear; it **moved from "a human decides the scope" to "a human decides which shapes are
representable"**, which is strictly harder, and it is not a learning-rate or memory-capacity
problem.

### And one live wire I can name exactly

`rule_expiry_v1` (FRESH / STALE / UNKNOWN, only `reverify()` may restore FRESH) exists and is
tested, and is consumed by the awake loop, the CoW repair engine and the polynomial CI engine —
but **`live_brain_route_admission_v1` never mentions `rule_expiry`.** The front door can recall a
rule whose truth depends on an interpreter the world has since changed. "Permanent" without expiry
is a liability. This is a one-wire integration, not research.

---

## 4. Sentience, plainly

The measurable half is real and I will not under-credit it: a **self-model of ignorance ranked by
what closing each gap is worth** (13 tests), a creature whose history survives an OS kill and
changes what it *chooses*, and which reports **0/112** closed rather than inventing a number.

Sentience is a different claim. There is no instrument for it here, and asserting it would put
every real number above at risk — because a claim that cannot be measured is precisely what the
laws in this tree exist to prevent. The objective does not require it:

```
BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE
```

Finishing the five testable behaviours in `OWNER_ACTIVE_GOAL_20261018_V1.md` §5 is worth more
than any sentence about a creature.

### On "give our model a try in all those environments"

Under current law (`MISSION_LOCK_V10`, `CAPABILITY_TRANSFER_VS_COGNITION_OUTSOURCING_LAW_V1`) a
donor model may not be the producer of anything credited: not remote, not local, not open-weight,
not wrapped, not "only on hard cases". Renaming it distillation or retrieval does not change its
class.

There *is* a lawful version of the instinct, and it is the route nobody here has been using:
**route (c), the acquisition-time donor.** A donor may help *create* a Brain-owned mechanism —
distil a procedure, recover a workflow, reimplement it mechanistically — and then must be
**deleted before qualification**, with twelve conditions including donor-deletion proof,
independent qualification on frozen held-out evidence not used for teaching, and causal ownership
by ablation. That is what "give the model a try" should mean. Anything else re-creates the audit
that zeroed 15 of 19 routes.

---

## 5. What is smartest to do, ranked by measured value per hour

**1. Make the substrate a precondition, not a surprise.** I turned 2 failures into 2 passes by
installing two pinned packages; the capability had been invisible and the failure was silent. A
declared-substrate check at test start (fail with `SUBSTRATE_MISSING`, never with
`assertIsNotNone`) is the cheapest fix in the tree and it protects every other number. It is also
the only item here that costs minutes.

**2. Instrument the verifier, because the verifier is where the correctness lives.** §2.2 shows
the identical transformation is 0/4 misapplications under a real suite and 3/4 corruptions under
a weak callback. Today **no caller is required to declare its verifier strength** beyond the
existing kind check. Make every recall site report `verification_kind` and count how many live
call sites run at `CALLER_PREDICATE`. That number *is* the size of the "learned but unsafe"
region, and nobody knows it.

**3. Close the rule lifecycle: wire `rule_expiry` into the front door.** §3's last item. Cheap,
integration-only, and it is the difference between "permanent" and "permanent and still true".

**4. Feed recall misses back as scope evidence.** A rule that fires on A and misses structurally
similar B is an observation about where its scope ends. `finite_capability_diagnosis` +
`rule_scope_learning_v1` already implement the mathematics; the miss signal is not wired to it.
This is the only path to the machine widening its own hypothesis space, which §3 Break 4 names as
the real frontier.

**5. Build the observation abstraction — the one genuinely hard item.** A symbolic projection
from a screen (accessibility tree / DOM / widget tree) into a hashable state, i.e. the
documented-but-unimplemented recipe layer. This is where "any computer" is won or lost. Nothing
below it matters for GUI, and it is synthesis, not tuning.

**6. Do not connect the learner to the front door by bypassing verification.** Freshly measured
today, the coding front door stops at
`BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:python.software.repair.apply.verified.v1`
and refuses to execute at all. That is *correct behaviour on an unmet precondition*, not a bug:
either a distinct verifier runs and records a real run reference, or the claim narrows. The one
thing that must not happen is making it green.

**7. Do not run unattended.** A thing that closes 0/112 accumulates honest failure faster on a
cron.

**And the discipline that makes all of the above worth anything:** *every* claim carries a
negative control that fails when the mechanism is deleted. Three of the five instrument defects
recorded this session were gates or oracles that would have passed with the mechanism removed.
A number without a control that could have contradicted it is not evidence.

---

## 6. The short answer

- **Real:** instant learning; transfer of a solution to a new instance of a known environment
  (10/10 by recall, several at 1 trial); apply-time abstraction lifting cross-shape recall 2/5 →
  5/5 with 0 misapplications *under a real test suite*; a working self-model of ignorance; a
  creature that persists and reports honestly, including 0/112.
- **Not real:** "perfectly", in any clause. "Everything on a computer" — pixels are not a state.
  "Once → all of those" — reach does not grow with repetition. "Plus the most advanced coding
  perfectly" — the perfect 5/5 was a false success, and the honest replacement has a gate that
  covers one hole and says so. Sentience — no instrument, and not the objective.
- **Smartest next move:** not a new mechanism. Make the substrate a precondition, then instrument
  verifier strength, then close the rule lifecycle, then feed misses back as scope. The system is
  not short of mechanisms — it is short of knowing, per call site, **which of them is running
  unverified.**
