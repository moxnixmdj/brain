# The four-phase plan was refused, and the reason is measurable

**2026-11-13** · branch `arena/bfec7b31-brain` · base `97e38b32` (+ `origin/main` `ca531123`)
**authority: NONE** · `truth.achieved` stays `false` · no capability registered · no weights updated · `$0`

New instrument: `canonical/tools/plan_admission_v1.py`
Recorded plan and its refusal: `canonical/research_sources/PROPOSED_PLAN_20261113_V1.json`
Tests: `canonical/tests/test_plan_admission_v1.py` (13) — total new tests this session: 32

---

## 0. The verdict

The plan (prove on advanced coding → code modification → adjacent domains → any computer use) was
run through a gate that asks one question: **could this plan come back and tell me I was wrong?**

```
$ python3 canonical/tools/plan_admission_v1.py
REJECTED (37 blocking)
  [ACTIVITY_METRIC] Phase 1: counts ['10 causal models', '25 causal models', '40 causal models']
  [NO_RATIO]        Phase 1: no rate/score/coverage unit
  [NO_HELD_OUT]     all four phases: empty
  [NO_CACHE_CONTROL] all four phases: no cache-only arm
  [NO_RANDOM_CONTROL] all four phases: no random arm
  [NO_STOPPING_RULE] all four phases: empty
  [NO_FALSIFIER]     all four phases: empty
  [ACTION_IS_A_TASK_FAMILY] 'multi-step debugging', 'architecture design', 'test generation', ...
  [DOMAIN_SEQUENCING] phases advance by substrate, not by verifier availability
```

Five separate defects. The first one is the fatal one, and it is not an opinion — **this
repository has already measured it.**

---

## 1. The fatal defect: the plan's success criterion is a count of artefacts

Phase 1's proof is: *"Task 1 builds 10 causal models; Task 2 builds 25; Task 3 builds 40. Show: each
task makes the system smarter."*

That is not a capability metric. It is an inventory metric, and **an inventory metric always goes
up**. It went up here, at enormous cost, and was measured not to mean anything:

| what was counted | what it was worth | record |
|---|---|---|
| 12 lessons accumulated | bought **nothing**; one change of part bought thirteen points | `TWELVE_LESSONS_BUY_NOTHING_ONE_PART_BUYS_IT_20261112_V1.md` |
| experience across 5 kinds | **0/5** transfer; **0/10** byte-identical | `ONE_TRY_IS_NOT_A_LEARNING_SIGNAL_20261112_V1.md` §1 |
| learning-to-learn over 10 held-out kinds | **NO_COMPOUNDING** | same |
| 12 programs | **3 explanations** | adjudicator header, defect 9 |
| 233 failures | **226 of them were one gate saying no** | adjudicator header, defect 10 |
| 15/15 "SOLVED_BY_RECALLED_PLAN" | 14 of 15 cost *more* | adjudicator header, defect 2 |

The repository's own ruler was written because of exactly this: *"twelve confident false
positives… almost none were failures of the learner; they were failures of the instrument."*

So the plan is not refused for being ambitious. It is refused because **the number it proposes to
watch cannot distinguish success from accumulation**, and this project has already spent months
learning that the hard way. Building Phase 1 as written would produce 40 causal models and no
information. That is the definition of the waste you asked me to prevent.

## 2. The sequencing defect: phases are ordered by substrate, not by verifiability

The ladder is code → code edits → adjacent → GUI. That reads like increasing difficulty. It is not.
The axis that actually decides whether a phase is tractable is **how cheaply an independent
verifier is available**:

| domain | verifier | cost |
|---|---|---|
| a code change with a test suite | the tests | ~free, runs in seconds |
| a code change with no tests | a human, or nothing | expensive to impossible |
| a GUI task | a human looking at the screen | very expensive |

GUI is not "harder coding". It is a different **observability regime**: no AST, no compiler, no
test suite, an irreversible action space, and state you cannot read. That is why the phases should
be ordered by verifier cost, and why "Phase 4" is not the natural end of the ladder but a different
problem.

The 2026 evidence says the same thing from the other side. OSWorld 2.0's authors name the actual
failure modes of frontier computer-use agents, and not one is a missing action:

> *"they lose track of constraints, miss information that arrives mid-task, guess rather than ask the
> user, and skip verification, struggling most when a task hinges on hidden state they must
> recover."*

And the two biggest measured wins of the year came from **changing what the agent can observe**, not
from adding actions: `Agent S4` reached **3.8×** on OSWorld V2 by evolving the *interfaces*
(2610.28601); `StateAct` lifted Opus 4.8 from **20.6% to 26.9%** binary at **~9× lower cost** by
grounding action in *program state* instead of pixels (2607.22798).

## 3. The unit defect: five of the "advanced actions" are not actions

"Multi-step debugging", "architecture design", "test generation", "performance profiling",
"complex refactoring" are **task families** — activities a person performs over hours. An action is
`edit_file`, `run_tests`, `apply_patch`: a verb on an object that resolves in one step.

You cannot give a model a task family as an action. What you can give it is an action plus the
*policy* for when to use it — and the policy is the hard part. That is why `SkillsBench` finds
curated skills worth **+16.6 pp** and self-generated skills worth approximately nothing
(2602.12670 v4; 2605.24117), and why `SkillEvolBench` finds *"raw-trajectory reuse frequently
outperforms distilled skills."* The action was never the scarce thing.

---

## 4. The resolution you actually need: memory and weights win in different regimes

The 2026 literature looks contradictory. It is not; it is two regimes, and knowing which one you
are in tells you what your Phase 1 can and cannot buy:

| regime | who wins | measured |
|---|---|---|
| **within** a domain, sequential tasks, verifier present | gated **memory** — and it wins big | KEEL: **+4.2 to +21.7 pp** over no knowledge, against **+2.4 to +9.6** for accumulate-and-hope (2610.34043); FGSE: harmful committed updates **3.6%** (2611.14326) |
| **across** task families, unseen | **weights** only | Continual-ARC: *"No harness-based method gains on unseen tasks, whereas weight-based learning shows substantial gains"* (2611.14505) |

**Memory buys compounding inside a distribution. Weights buy reach outside it.** Everything else
follows:

- Your Phase 1, honestly specified, is a **within-distribution** claim, and it is **achievable at
  $0** — with a gate. KEEL's numbers are token-space numbers.
- Your Phase 4, honestly specified, is a **cross-distribution** claim, and **it is not achievable
  without weight updates.** No amount of Phase 3 leads to it. That is a decision for the owner, not
  a discovery for an agent.
- And in both regimes the gate is load-bearing. Ungated accumulation is measured to be *worse than a
  cache* (2611.14505), and self-generated feedback actively damages the model it trains
  (2610.05076).

---

## 5. What replaces the plan — three moves, each able to fail

Ranked by information per dollar, all $0, each pre-registered before it runs:

**Move 1 — one within-distribution compounding claim, gated, with controls.**
Take one change class the operators already cover. Hold out a *kind* never shown. Arms: gated
learner, cache-only, random/default. Metric: held-out coverage **and** precision, reported
separately, plus the wrong-write count. Stopping rule and falsifier written first. Falsifier: *the
cache arm comes within 5 points of coverage at equal precision.* This is the experiment the repo
keeps deferring and it is the cheapest one that can return NO.

**Move 2 — make the task identifiable instead of making the learner faster.**
For coding: read program state (AST, types, tests) rather than prose reports. For computer use:
typed tool interfaces over screenshots wherever a tool exists. This is where 2026's largest wins
came from, it needs no training, and it raises the bits carried by a single experience — which is
the only honest way to make "learn it once" closer to true.

**Move 3 — inherit FGSE's admission protocol as the named gate** (2611.14326).
The tree already has the parts, scattered across three modules. Consolidating them into one gate
with FGSE's targets (falsification failures ≤5.0%, regression damage ≤1.3%, harmful committed
updates ≤3.6%) turns the strongest published result of the month into a local measurement.

**Explicitly not proposed:** more environments, more action families, longer context, background
runs, or anything whose success is a count. Measured to buy nothing before Move 1 exists.

---

## 6. What this note does not claim

No new learner was run for it. The internal numbers are already-recorded measurements with their
files named; the external numbers are the authors' own, pinned at version and date in
`EXTERNAL_EVIDENCE_LEDGER_V1.json` and **not independently reproduced here**. The gate is a linter
for intentions: a plan can pass it and still be worthless. It has exactly one job — stop the plans
that are guaranteed to be uninformative — and it would have stopped this one.
