# Being ahead of the frontier: the plan, second pass

**Date:** 2026-11-24 · **Base:** `0b5ede3b` (+ Track 0, `687011e1`) · **Authority:** NONE — sandbox measurement

Second pass. The first plan said three frontier surfaces were weak and this repo had
orphaned machinery for them. That was right but anecdotal. This pass measures the pool,
opens four mechanisms I had not tested, and finds one seam in the literature I had been
looking past.

---

## Part 1 — The hidden pool, measured

### 1.1 It is working code, not rubble

I sampled **44 orphan test files at random** (seed `20261124`) from the **998** test files
that correspond to ORPHAN modules:

```
318 passed, 1 failed, 2 subtests passed  in 13.19s
```

**99.7% pass.** The orphan pool is not dead code. It is tested, working, unreachable code.

That converts the premise from a hunch into a number, and it sharpens the problem:
the defect is not *"the capabilities are missing"*, it is *"998 tested modules have no
caller."*

### 1.2 Still, they are unreachable

| | |
|---|---|
| `continuous_self_v1.py` | ORPHAN, fan-in 0 |
| `hidden_evaluator_top_support_dominance_v1.py` | ORPHAN, fan-in 0 |
| `h100_anytime_proposal_confidence_v1.py` | ORPHAN, fan-in 0 |
| `live_brain_runtime_v1.py` (1,990 lines) | ORPHAN, fan-in 0 |
| `associative_memory_v1.py` | ORPHAN, fan-in 0 |

Grep for any of the first three inside `brain_unified_model_v1.py`: **0 hits.** The front
door cannot reach them.

---

## Part 2 — Four mechanisms, tested this pass

### 2.1 `continuous_self_v1` — a process that survives being killed

408 lines. A durable self with an identity that outlives the process, a journal written
before every transition, and three claims it says are "each falsifiable by killing the
process."

I killed it. `SIGKILL`, mid-task, then resumed in a fresh interpreter:

```
resumed      : True
epoch        : 2
was_absent   : True   absence_s: 7.006637
identity kept: 2e65975f1d6a      <- same subject, new epoch
INTERRUPTED  : [('a task that will be killed mid-flight', 'INTERRUPTED')]
```

**All three claims hold.** The identity persists, the absence is *measured* (7.0 s), and
the in-flight work is reported `INTERRUPTED` — not lost, not claimed done.

Nothing in the frontier's agent frameworks does this. Every one of them (Claude Code,
Codex, Devin, OpenClaw) loses in-flight state on a crash and reports nothing about it.
Orchestration papers treat restarts as a scheduling problem, not an *honesty* problem.
This module treats "I was doing X when I died" as a first-class record.

### 2.2 `hidden_evaluator_top_support_dominance_v1` — claims that never touch the target

125 lines. It certifies that **every certified support class dominates every admissible
outcome class**, over a finite partial order, with no target distribution and no
target-case outputs.

Tested:

| Case | Result |
|---|---|
| A ≻ B ≻ C, support {A} | `PASS`, `UNIVERSAL_TOP_SUPPORT_IMPLIES_TARGET_FREE_MONOTONE_DOMINANCE` |
| support {B} (B does not dominate A) | `FAIL_CLOSED` — `TOP_SUPPORT_DOES_NOT_DOMINATE_ALL:B:A` |
| cycle A≻B≻A | `FAIL_CLOSED` — `DOMINANCE_NOT_ANTISYMMETRIC:A:B` |

It returns `target_distribution_required: False` and `acceptance_credit_delta: 0`.

**This is the structurally unusual one.** The entire field fights benchmark contamination
with held-out splits, flags, and post-hoc audits — all of which are *empirical* defences
against a *structural* problem. A claim that never touches the target cannot be
contaminated by it. That is a different category of answer, and it fails closed.

### 2.3 `h100_anytime_proposal_confidence_v1` — a statistical stopping rule

182 lines. Exact Clopper–Pearson bounds with summable α-spending (each side gets
α/2, time *t* gets α_side/(t(t+1))), so a union bound gives simultaneous coverage at
**every stopping time** without optional-stopping leakage.

Tested on a stream that starts bad and turns good: correctly returns `CONTINUE`, with
`p_lower_anytime 0.468 / p_upper_anytime 0.949` straddling the 0.5 viability threshold.
Bounds compute correctly (`7/10` → lower 0.5184, upper 0.8802 at 95%).

### 2.4 What Track 0 already proved

`program_synthesis_v1.synthesize()` — orphaned, now wired — closes
`"compress notes.txt into notes.txt.gz with gzip"` on the first try with
`PASS__PROGRAM_SYNTHESISED_AND_VERIFIED`. Curriculum tests 13 failing → 1.

---

## Part 3 — The seam I had been missing

I searched under "stopping rules", "anytime-valid", "conformal prediction", "confidence
sequences". The first pass missed the venue that names the whole problem.

**ICML 2026 Workshop: *Statistical Frameworks for Uncertainty in Agentic Systems*** —
"distribution-free validity layers", "anytime-valid sequential inference for continuous
monitoring, evidence aggregation, and **principled stopping**", and, in the call itself:

> "Long-horizon agentic workloads mark a shift into a regime where declarative systems
> adaptively build larger declarative systems. In this setting, uncertainty quantification
> must address not only output-level error, but also **adaptive resource allocation:
> routing to tools and subagents, safeguards against unnecessary spend, principled
> stopping under continuous monitoring**, and compositional guarantees across modular
> systems."

The frontier has **named this as an open problem in 2026**. The literature attacking it:

| Work | What it does | Where it applies the guarantee |
|---|---|---|
| **Anytime-FC-RAG** | truncated betting e-process, supermartingale, time-uniform alarm + controller safety | *retrieval calibration* |
| **ORCA** (COLM 2026) | conformal calibration of the **stopping decision rule** + test-time training | *token-level reasoning* |
| **Sequential-EDFL** | self-normalised empirical-Bernstein e-process on information lift | *generation stopping* |
| **CC-SMCS** | simultaneous confidence sequences for model selection | *model choice* |
| **MiCP** | conformal stopping for research agents | *turn count* |

**Every one applies the guarantee inside a single model's output stream.** Not one applies
it to the agent's *decision about its own work* — should I keep trying this route, or
abandon it and buy a different one, given a fixed budget and a stream of failures that
are not i.i.d.?

That is the gap. And `h100_anytime_proposal_confidence_v1` is built for exactly that
decision, sitting orphaned.

---

## Part 4 — The plan

### The bet, stated once

> The frontier is converging on bigger windows, more tools, and trained fast weights,
> and it has publicly named *principled stopping under continuous monitoring* as unsolved.
> This repository's unusual assets are: a process that survives death honestly, a
> statistical rule for when to abandon a route, memory that earns importance from
> outcome, and claims that never touch the target.
>
> **The bet is an agent that knows when to stop, remembers what helped, survives being
> killed, and whose successes cannot be contaminated — because they were never about the
> target.**

That is one sentence, and every clause is backed by tested, orphaned code.

### Track A — Continuity as a product (2 days)

1. Relocate `continuous_self_v1` into `canonical/runtime/` index with `capability: true`.
2. Give it a real worker: it runs `study()` lessons in a loop, `begin()` before each,
   `commit_world_and_signature` after.
3. **The measurable:** kill it at a random point 20 times; require 20/20 resumes with the
   correct `INTERRUPTED` record and a measured absence. That is a test, not a demo.
4. Publish the journal as an artifact. *No frontier agent publishes "what it was doing
   when it died."*

**Stop condition:** 20/20 kill tests, or the continuity claim is false.

### Track B — Stopping as a capability (3 days)

Wire `h100_anytime_proposal_confidence_v1` to the thing it was written for: the
**decision to keep trying a route**. Feed it the per-attempt outcomes `study()` already
produces.

1. After each failed channel, the sequence answers: is the lower anytime-valid bound on
   this route's viability still above threshold? If not, abandon the route.
2. Replace the current fixed `cost` ordering with the confidence sequence over
   *measured* per-channel outcomes.
3. **The measurable:** on the existing curriculum gaps, total attempts-to-close must fall
   with **no increase in false abandonment** (a route abandoned that would have closed).

This is the frontier's named open problem, applied one level up from where anyone is
applying it.

**Stop condition:** if the sequence never fires (bounds too conservative and the loop
behaves exactly as before), the mechanism is decoration and must be said to be.

### Track C — Target-free claims (1 day)

1. Register `hidden_evaluator_top_support_dominance_v1` as the certificate path for
   capability claims.
2. **The measurable:** take the 45-commit corpus. For each solve, emit the dominance
   certificate. Count how many claims are target-free vs. how many still need the target.
3. Publish that split. It is the honest answer to "is this capability real or fitted?"

**Stop condition:** if fewer than a handful of claims can be certified target-free, say
so — the theorem is real but the tree does not yet instantiate it.

### Track D — Composition, measured (ongoing, smallest step)

Do not wire 20 modules. First **measure novelty**: cluster the 1,519 orphans by symbol
overlap and see how many distinct mechanisms there are. If 1,519 collapse to 80, the
plan changes entirely and we should say so early.

**Stop condition:** the dedupe number. Everything downstream depends on it.

### What I would NOT do

- Not build another capability. There are 1,519 unreached ones.
- Not chase SWE-bench. The six-pass audit put us 20–30× behind and nothing here changes that.
- Not touch the composed/raw status label. 259 of 636 tests asserting it already fail;
  fixing it is a 25-file coordinated change.

---

## Part 5 — Honest risk register

| Risk | How I would know | What it would mean |
|---|---|---|
| `continuous_self` is a journal, not a self | its only consumer is a test | the continuity claim is a file format |
| the confidence sequence never fires | Track B stop condition | decoration, not capability |
| target-free certification covers almost nothing | Track C count | a beautiful theorem with no instances |
| the 1,519 orphans are 80 mechanisms | Track D | "hidden capabilities" is overcounted by ~19× |
| composition ≠ capability | already known | wiring does not move the 20–30× gap |

The last one is settled and should be said plainly: **none of this closes the frontier
gap on task completion.** It is an argument about being *ahead* on a narrow, defensible
axis — stopping, continuity, and uncontaminated claims — where the frontier's own 2026
workshop says it does not yet know how.

---

## Reproduce

```bash
# the pool is working code
python3 -m pytest $(python3 - <<'PY'
import json,pathlib,random
m=json.load(open('canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json'))
orph={r['path'] for r in m['source_index'] if r['classification']=='ORPHAN'}
t=[p for p in pathlib.Path('canonical/tests').glob('test_*.py')
   if any(pathlib.Path(o).stem==p.stem.replace('test_','') for o in orph)]
random.seed(20261124); print(' '.join(map(str,random.sample(t,44))))
PY
) -q --tb=no

# kill-proof continuity
python3 -c "
import sys;sys.path.insert(0,'.')
from canonical.runtime import continuous_self_v1 as C
s=C.ContinuousSelf(state_path='/tmp/s.json',journal_path='/tmp/j.jsonl',beat_seconds=1.0)
print(s.resume()['epoch'])"

# target-free certificate
python3 -c "
import sys;sys.path.insert(0,'.')
from canonical.runtime import hidden_evaluator_top_support_dominance_v1 as D
r={'path':'x','git_blob_sha':'0'*40,'scope_complete':True,'independent_or_objective':True}
print(D.verify_top_support_certificate({'outcomes':['A','B'],'dominance_edges':[['A','B']],
  'brain_top_support':['A'],'brain_support_receipt':r})['status'])"
```
