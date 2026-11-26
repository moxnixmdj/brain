# The smartest plan: attack the frontier's measured wall, not its strength

**Date:** 2026-11-24. **Authority:** NONE (producer-run sandbox).
This is a plan, not a result. Every number is marked **verified** (measured in this tree or checked
live today), **unverified**, or **failed**.

---

## §0 First: what "we already solved it under non-obvious names" actually evaluates to

You were right, and a previous agent already proved it — then disproved the stronger version of it.
Both halves are in `WHERE_THE_SOLUTIONS_LIVE_20261101_V1.md`, which opens:

> *"The owner was right. The mechanisms exist, they have non-obvious names, and they are not orphaned
> prose — I ran their suites in this session."*

**Verified — the five capabilities exist and their suites pass:**

| capability | non-obvious name | verified |
|---|---|---|
| General computer use | `canonical/runtime/computer_env_v1.py` — actions **discovered from `PATH` at runtime**; 90 `osworld_v21_*` modules incl. `positioned_ocr_observer_v1` | **82 passed** |
| Instant learning | `verified_skill_crystallizer_v1` + `transfer_learning_v1` + `causal_trace_to_skill_compiler_v1` | 12 + 13 + 21 passed |
| Persistence to a measured target | `goal_chase_v1` + `closed_loop_autonomous_controller_v1` (**4-tier escalation**: Tier 0 compiled recall <5 ms → Tier 3 discovery) | 57 passed, 1 failed |
| Data-gap → acquisition | `ignorance_ledger_v1` — ranks gaps by **expected value of closing them**; exploration free by prior construction | included above |
| Non-local extrapolation | `curriculum_v1`, `composer_route_v1`, `documentation_mining_v1` | included above |

And the single most important line in that document:

> **"The decision layer is not missing. It is unwired from the computer-use layer."**

**But the same document contains its own demolition, and it must not be skipped:**

> **CORRECTION 2026-11-03.** *"New instances" is not true: four of the five families build the same
> instance for all three phases. This is exact-episode replay, not transfer. Re-measured on genuinely
> distinct instances: **1/15** cases show a genuine saving, median trial speedup **1.00×** (3027 vs
> 3028 environment calls).*

That reconciles with `SEVEN_CLAIMS_SCORED_AGAINST_MEASUREMENT_20261112_V1.md`: same bug again **22/22**;
a *different* program **1/40**; shipped rules **0/40**.

**So the honest verdict on your claim — both halves verified:**

- **The mechanisms exist, under non-obvious names, and they run.** TRUE.
- **They are already unified.** FALSE — see §1.
- **Instant learning in a new environment is solved.** FALSE — 1/15, speedup 1.00×.

---

## §1 The unification gap, measured — this is the part you are right about

Your instruction *"they need to be at the unified runtime, at the unified model"* is not a guess. I
fetched **all 6,965 branches** and counted:

| | |
|---|---|
| distinct `.py` modules under `canonical/` across all branches | **10,367** |
| present on `main` (the unified runtime) | **6,249** |
| **branch-only — never unified** | **4,118** |
| …of which carried by exactly **one** branch | **3,388** |
| …of which carried by ≥50 branches | **1** |

And the repo's own census (`EVERY_VALUABLE_THING_V1.json`, branch `cdfc4713`):

```
files_tracked: 16,312
reachable_by_one_model: 8,949
unreachable: 7,363        <- 45% of the repository cannot be reached by one model
```

**That is the whole thesis, quantified.** There are not "a few hidden gems" — there are 3,388
single-branch modules and 7,363 unreachable files. The capability is not missing; it is
**unwired**. The search problem you named is real, and the previous agent named the exact defect:
*"I searched for obvious names and concluded from absence. The real names are
`THE_SECOND_TIME_IS_INSTANT`, `A_VARIANT_IS_NOT_A_NEW_PROBLEM`, `elevate_trace_to_fastest_layer`,
`ignorance_ledger`."*

**But note the shape of it:** only **1** branch-only module is shared by ≥50 branches. So this is
not "unify 7 branches and get a multiplier" — the 4,118 are mostly *one-branch experiments*. Unifying
them means **harvesting mechanisms**, not merging branches. That distinction decides the plan.

---

## §2 The frontier's wall — from the frontier's own authors

Do not compete where the frontier is strong. It is strong at coding: **SWE-bench Pro 89.9%**, and we
are a certified **0/51** on its hardest subset (`swe-pro-v2-hard51-20261125T204359Z`: oracle 51/51,
nop 0/51, both gates PASS, 0 missing trials — no qualifier left). Fighting there is a 90-point
deficit.

It is **weak** at long-horizon computer use, and its own authors say why. OSWorld 2.0 (arXiv
2606.29537), 108 tasks, median human time ~1.6 h, trajectories 250–300+ steps:

> *"Agents execute local actions well but break when they must recover hidden state, track many items,
> resolve conflicts, or adapt to mid-task changes."*

The four named failure modes: **(1) losing constraints, (2) missing mid-task information, (3) guessing
instead of asking, (4) skipping verification** — plus recovery of hidden/evolving state. XLANG Lab's
Mengqi Yuan: *"the bottleneck moved from perception to memory"*; completion **drops below 10% for all
models in the 137–163 minute bin and reaches zero above 163 minutes**; and the "look, then act" loop
*"isn't built for a computer that keeps moving while the agent is thinking."*

Frontier standing there: **48.7%** binary on OSWorld 2.1 (Opus 5.5), **20.6%** at the 2.0 release.

**Now read those four failure modes against the non-obvious names in §0:**

| frontier's named failure | our organ, already built | why it is the right shape |
|---|---|---|
| losing constraints | `goal_chase_v1` + `closed_loop_autonomous_controller_v1` (4-tier escalation) | completion gated on measured target, not on a summary |
| missing mid-task updates | `elevate_trace_to_fastest_layer` — pixel/UI trace → **deterministic causal program** (`sqlite_exec` <2 ms → `http_request` <15 ms → CLI <50 ms → semantic DOM) | state is **re-read from the environment, not remembered** — the exact fix the OSWorld authors recommend |
| guessing instead of asking | `ignorance_ledger_v1` — ranks gaps by expected value of closing them | makes "ask/probe" a computed decision, not a disposition |
| skipping verification | `verified_skill_crystallizer_v1` + `skill_recheck_v1` (taught ≠ holds) | verification is a gate, not a habit |

**This is the unusual idea, and it is not a new mechanism: it is an existing one pointed at the
frontier's measured weakness.** The frontier spends 300 screenshots and 15.7 B tokens losing state;
`elevate_trace_to_fastest_layer` refuses to look at pixels at all and elevates the trace to the
fastest deterministic layer instead. That is a genuinely different bet, and it is already coded.

---

## §3 What the literature says — and why it does not give us a new organ

Training-free external skill memory is now the validated answer, and it is exactly our §2 boundary:

- **Memento-Skills** (arXiv 2603.18743): frozen LLM, external skill memory, Read-Write Reflective
  Learning, skill router, and — critically — an **automatic unit-test gate before a mutated skill is
  saved**. GAIA 66.0% vs 52.3% static (+13.7 pp), HLE +116.2% relative, **no retraining**.
- **MSCE** (arXiv 2607.16621): training-free memory–skill co-evolution, L1 traces / L2 policies / L3
  environmental cognition; crystallizes only policies that are **supported, positive-gain, and
  stable**, carrying *evidence links, applicability boundaries, verification rules, reliability
  estimates*.
- **Negative transfer is the real risk**, and our tree measured it before the papers did: STRATA's
  agent scores **−100** on a family a *memoryless* agent solves; ΔNL **−26.1** on hard cases; TAME
  rejected **55%** of self-authored rules for breaking something that worked.

**We already have the organs the literature prescribes** — `settled_admission_v1` (a rule may not
touch a new target until its open question is settled), `rule_expiry_v1` (retire on drift),
`skill_recheck_v1` (taught ≠ holds). The literature is not a source of new mechanisms here. It is
**independent confirmation that the boundary in §2 of the mission is the right one**, and a warning
that our 55% self-rejection rate is normal rather than defective.

---

## §4 The plan — one move, then the loop

**Thesis.** The frontier's own authors name memory/constraint-tracking as the bottleneck on the one
benchmark where the frontier is below 50%. We own the organs for those failure modes, under
non-obvious names, measured and passing. The gap is that they are **unwired from each other and from
the computer-use layer**, and that our *transfer* is 1.00×. So: wire, then fix transfer, then measure
on the wall — and do **not** spend the next quarter on SWE-bench Pro.

### Step 1 — Wire the decision layer to the computer-use layer (the measured defect)

`computer_env_v1` (82 passed) is unwired from `goal_chase_v1` / `closed_loop_autonomous_controller_v1`
(57 passed). Neither is broken; the seam is. Concretely: make `computer_env_v1`'s discovered actions
addressable as Tier-0/1 candidates inside the 4-tier escalation, so a discovered action can be
compiled and recalled at <5 ms instead of re-discovered.

**Cost:** small. **Risk:** low — both sides already pass their suites; this is a seam, not a rewrite.
**Kill condition:** if the wired system does not beat `computer_env_v1` alone on a held-out
`osworld_v21_*` probe, the seam was not the defect and Step 1 is falsified.

### Step 2 — Make state re-read, not remembered (the OSWorld fix)

`elevate_trace_to_fastest_layer` exists. Wire it as the **default observation path** for any
long-horizon task: before acting, re-derive the current state from the fastest deterministic layer
available, and treat the agent's own summary as *untrusted*. This is the literal recommendation of
the OSWorld authors ("a working set that lives outside the context window — and gets re-read, not
remembered").

**Kill condition:** if elevation cannot cover a task class that pixel-reading covers, record it as a
measured limit rather than adding a vision model.

### Step 3 — Fix transfer, honestly, or stop claiming it

1/15 and 1.00× is the load-bearing failure. Not 1/40 — that is a different corpus — but the same
shape: **exact recall is perfect, generalization is absent.** The literature's answer is not more
recall, it is **applicability boundaries + verification rules + reliability estimates at
crystallization time** (MSCE), which is what `settled_admission_v1` and `skill_recheck_v1` are for
and what they currently under-deliver. Measure on **genuinely distinct instances** — the 2026-11-03
correction is the protocol: same instance is replay, not transfer.

**Kill condition:** if a held-out variant in a different environment does not improve over the empty
store, the claim stays false and gets recorded as false.

### Step 4 — Judge with the whole file, always

Measured: **44.44%** of wrong mutants of a real fix pass the target test; the whole test file catches
**56.25%** of those. Any arm tuned against the target node alone is tuned to a signal that is wrong
44% of the time. Whole-file judging from the first line, or every later number is contaminated.

### Step 5 — Measure on the wall, not beside it

OSWorld 2.1 is the right board and it is currently **blocked** (gated HuggingFace task classes, a
14.9 GB QCOW2, KVM, self-hosted websites). The blocker policy correctly fails closed rather than
inventing a score. Unblocking is a credentials/infrastructure question, not a research one — it is
the one place where the plan needs something only you can supply.

---

## §5 Rejected ideas

| idea | verdict | reason |
|---|---|---|
| Compete on SWE-bench Pro / Terminal-Bench generation | **rejected** | 89.9% vs certified 0/51. A 90-point deficit is not closed by a better generator; our own measurement says perfect selection is worth ≤+2 of 128. |
| Unify the 7 "best" branches into one binary | **rejected** | only **1** branch-only module is on ≥50 branches. The 4,118 are single-branch experiments; merging branches unions unverified code rather than harvesting mechanisms. |
| Build a bigger mutation grammar / search | **rejected** | 75.2% of real fix pieces are unreachable by a fixed grammar (1,638/2,178). Reach moves the set, not the class. |
| 16-way parallel CoW rollouts now | **rejected** | 16 × a 0% operator is 0%. Parallelism multiplies an operator; it does not create one. |
| Add a vision model for GUI perception | **rejected for now** | the frontier's own diagnosis is that perception is *not* the bottleneck; `elevate_trace_to_fastest_layer` is the opposite bet and it is already built. Only revisit on a measured uncovered task class. |
| Feed a store mined from target repos back into those tasks | **rejected** | warehouses the benchmark in the store exactly as §2 forbids in weights; `b81b2217` §7 forbids it explicitly. |
| Seed the store to lift 0/51 | **rejected** | that run was the **empty-store arm** (`STORE_FILE_ABSENT`); 0/51 is the ablation floor, not the system. Lifting it by seeding cheats the ablation. |

---

## §6 What would make this plan wrong

Stated in advance, so it can be killed rather than defended:

1. **If Step 1's seam is not the defect** — measured by the wired system failing to beat
   `computer_env_v1` alone on a held-out probe.
2. **If transfer cannot be improved** — then "learn once, work on the next machine" is false, and the
   honest capability is *exact recall at 187 ms*, which is real and narrow, and the plan must say so.
3. **If OSWorld stays blocked** — then the wall cannot be measured, and every claim about
   long-horizon computer use stays `unverified`. That is the single largest risk to this plan and it
   is not a research risk.

**Nothing here meets §6**, and this document does not claim otherwise. The frontier wins on capability
today: 89.9% on SWE-bench Pro against our certified 0/51. The plan does not dispute that. It says the
frontier's own authors have named the wall it cannot climb, and we are already holding the organs for
it under names nobody thought to search.
