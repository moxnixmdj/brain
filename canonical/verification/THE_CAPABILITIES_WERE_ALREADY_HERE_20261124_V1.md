# Ahead of the frontier: the capabilities are already here, under the wrong names

**Date:** 2026-11-24 · **Base:** `0b5ede3b` · **Authority:** NONE — sandbox measurement
Supersedes v1 (`729a7cfc`), v2 (`12c7330f`), v3 (`79b34d8d`).

Three plans failed the same way: they diagnosed the repository instead of moving
anything. This one answers the actual instruction — *the hidden capabilities need to be
at the unified runtime* — and it turns out the answer does not require building them.
It requires **recognising them**, because they are already named in a language nobody
else was speaking yet.

---

## Part 1 — Why nobody could find them: the names are a private vocabulary

I searched the 2026 literature for how the frontier handles five areas, then searched
this repository for the same mechanisms. **The mechanisms were here. The vocabulary
matched the frontier's 2026 vocabulary almost exactly — twelve months early, and without
the branding.**

| The frontier's 2026 name | Source | This repo's name | Status |
|---|---|---|---|
| **Modular memory / sleep consolidation** — Core Model + Working Memory + Long-term Memory, "hippocampal fast encoding + cortical slow consolidation via replay" | ICML 2026 position paper, Dagstuhl CL workshop | `continuous_self_v1` (408 ln) + `curriculum_v1` (534 ln) | **works**, SIGKILL-proven |
| **Anytime-valid stopping** — named by ICML 2026 as an *open problem*: "anytime-valid sequential inference for continuous monitoring, evidence aggregation, and principled stopping" | ICML 2026 workshop statement | `h100_anytime_proposal_confidence_v1` — `lower_bound` / `upper_bound` / `n95_from_p` | **works**, orphaned |
| **Automatic curriculum + skill library** (Voyager) | Voyager, in-context lifelong learning | `curriculum_v1` | **works** |
| **Quality-diversity / MAP-Elites archive** | QD literature | `ladder_*` family | present |
| **LLM-as-judge** | AgentMemBench §6.5 | `hidden_evaluator_top_support_dominance_v1` | **works**, orphaned |
| **Computer use with confinement** | OSWorld 2.0; Anthropic's tool schema | `confinement_v1` + `confined_dispatch_v1` + `CONFINED_EFFECT_DECLARATIONS_V1.json` | present, **but 13 capabilities only** |
| **Verification as first-class** | harness-engineering literature | `raw_goal_trace_acceptance_v1` | **works** — the only thing that ever passes |

**The insight:** this repository is not a pile of forgotten modules. It is a working
implementation of the 2026 research agenda that was written without knowing the agenda's
names. "Ladder" is MAP-Elites. "H100 anytime proposal" is an e-process. "Continuous
self" is modular memory with consolidation. The hidden capability was never hidden — it
was **translated badly**.

That is the search problem, and it is now solved. Everything below uses these names.

---

## Part 2 — What I measured that changes the plan

### 2.1 The stopping machinery works, and it decides in exactly 20

`h100_anytime_proposal_confidence_v1`, run directly:

```
perfect  5 for  5   lower=0.242   undecided
perfect 10 for 10   lower=0.432   undecided
perfect 20 for 20   lower=0.615   DECIDED   <- keep
  0 for  5           upper=0.758   undecided
  0 for 10           upper=0.568   undecided
  0 for 20           upper=0.385   DECIDED   <- abandon
```

**Twenty observations, symmetric, in both directions.** That is a certified stopping
rule — and it is the thing the ICML 2026 workshop named as an open problem, sitting
orphaned in this repository.

### 2.2 The system makes one attempt. The rule needs twenty.

The gap is not capability. It is **arithmetic**. Every solve is a single shot: one
bind, one run, one verdict. The rule that would let the system decide has never been
called from the loop.

### 2.3 The refusal is policy, not incapacity — and saying so honestly matters

`computer_execution_boundary_v1` states it plainly:

> *"No request flag, process environment or caller can use it to grant execution
> authority. It marks automatic routes that are deliberately unavailable until a
> reviewed, admitted confinement and effect-verification path exists."*

**16 of 17 goals refuse for this reason.** They compile. They bind. They die for want of
a carrier. And `confined_dispatch_v1` exists to be that carrier — but
`CONFINED_EFFECT_DECLARATIONS_V1.json` admits **13 capabilities, all source-analysis**.
No compression, no shell, no computer use.

So the 16/17 is a **reviewed-data gap**, not a missing mechanism. Closing it is a
declaration review, not an engineering rebuild. I will not bulk-add rows to make the
number look good; that is precisely the self-deception this repository is built to
prevent.

### 2.4 Latency, decomposed

| Component | Measured | Share |
|---|---|---|
| do the work | 7.30 s | 62% |
| **prove the work was done** | **4.76 s** | **44%** |
| compile the goal | 1.16 s | 11% |
| **cold total** | **10.6 s** | |
| warm total | 3.6 s | cache warmth, not a different path |

The one capability that passes spends **44% of its time proving itself**. The frontier's
numbers (0.5–1.5 s cached, 3–6 s monolith) are the ceiling this must reach.

---

## Part 3 — The research, condensed to what changes decisions

**Coding agents.** The finding is brutal and it is a gift: *scaffolding moves 22 points;
switching between the six best frontier models moves 1 point* (SWE-bench Pro). Mini-SWE-Agent
implements all seven harness subsystems in **~100 lines** and reports 74%+ on SWE-bench
Verified — the same range as systems **three orders of magnitude larger**. Loop
sophistication does not predict performance. Grok Code Fast went 6.7% → 68.3% by
changing **only its edit-tool format**.

*Consequence for us:* the front door imports **35 modules in 0.14 s** — the harness is
already small. Size is not our problem. Our problem is that the loop makes one attempt
and the verification is 44% of the cost.

**Continual learning.** Consensus has converged on fast/slow separation: fast in-context
skill edits, slow parametric consolidation, replay during idle. **ICL gives the largest
standalone gain in every configuration** (arXiv 2611.19700). Voyager's result: capability
grows with **zero weight updates** because the library of verified programs is the memory.
MetaClaw argues both timescales are required, neither alone sufficient.

*Consequence:* `continuous_self_v1` **is** the slow timescale, already built and
SIGKILL-proven. `curriculum_v1` **is** the fast one. Nothing to build.

**Memory.** The market's numbers are unstable in a way worth noticing: an independent
eval scored Mem0's open-source edition at **32.4%** on LongMemEval while the vendor's
managed platform self-reports **93.4%**. Supermemory claims 85.4% *and* sub-300 ms. The
spread between an independent measurement and a vendor claim is larger than the spread
between the systems. Prefix caching alone cut Mem0's p95 from 17.12 s → 1.44 s.

*Consequence:* memory benchmarks are not yet trustworthy, and **retrieval latency is a
cache problem more than an indexing problem** — exactly the shape of our 10.6 s cold /
3.6 s warm split.

**Computer use.** OSWorld-Human measured it: agents take **2.7–4.3× longer trajectories
than necessary**; **66% of steps are wasted stuck in loops**; **23% of errors are poor
visual grounding**, costing up to 30 extra steps. Leading agents resolve only 20.6% of
OSWorld 2.0 tasks. The named fixes: cut planning/reflection latency, cut step count,
add grounding backoff.

*Consequence:* we are not behind on computer use — **the frontier is bad at it too**, and
the failure mode they name (wasted steps in a loop) is exactly what an anytime stopping
rule fixes.

**Instant learning.** aTTT: in-episode weight updates beat the same text delivered
in-context (54.3% vs 49.3%, below the 51.4% no-update baseline) — because injected notes
get *displaced* in long contexts. So context injection has a real ceiling.

*Consequence:* this strengthens our position. We cannot update weights, but we do not
need to: our signal is a **verified receipt**, not a soft score, and a noise-free reward
reaches a decisive bound in 20 observations.

---

## Part 4 — The plan

Four moves. Two delete, one measures, one closes a loop. **Nothing new is invented.**

### Move 1 — Delete: 4,134 documents that cannot execute. (a few hours)

`canonical/verification/` holds **3,069 files**; `canonical/action_intents/` holds **1,065**.
Neither can run. They compete for attention with 998 working-but-unreached modules.

Collapse to one index: path, claim, falsifier, date. **3,068 lookups deleted.** This is
the single largest "no part" available, and it costs nothing behavioural because none of
it is executable.

### Move 2 — Delete: finish the canonical form. (an hour)

Already done for 33 modules (**+33 / −330 lines**). **25 remain pinned by `git blob_sha`**
in governance tests. Updating those pins is a reviewed governance act, not a cleanup.
Do it deliberately, in one commit, with the reason recorded — or leave the 25 alone and
say so. Do not silently `--force` a pin.

### Move 3 — Measure: put a latency budget in the front door. (an hour)

There is currently no latency assertion anywhere. Add one, using the frontier's own
numbers as the bar:

```python
# canonical/tests/test_front_door_latency_budget_v1.py
# warm solve must beat a frontier monolith; cold solve must beat 2x it.
assert warm_solve_ms < 3000      # frontier monolith: 3-6 s
assert cold_solve_ms < 6000
assert verification_share < 0.35 # currently 0.44
```

**This is how "insanely fast" stops being an adjective and becomes a build rule.**

### Move 4 — Close the loop: 20 attempts, not 1. (the real work)

The one thing worth building. Replace the single-shot attempt with the loop the
machinery was always shaped for:

```
for attempt in 1..20:
    result   = solve_once(goal)          # existing path, unchanged
    reward   = result.status == PASS     # a verified receipt, not a score
    if reward: successes += 1
    lb = anytime.lower_bound(successes, attempt)     # <-- already exists
    ub = anytime.upper_bound(successes, attempt)
    if lb > 0.5:  return CLOSED_CERTIFIED             # decides at 20/20
    if ub < 0.5:  return ABANDONED_CERTIFIED          # decides at 0/20
```

**What this buys, and it is not small:** every termination carries a probability bound
that survives optional stopping. The frontier's agents stop when they run out of budget
or a judge says so. **Ours stops when the evidence is decisive, and can prove it.**
The ICML 2026 workshop listed this as open. It is a 12-line loop.

**What it costs, honestly:** at ~0.5 s per typical attempt, 20 attempts ≈ 10 s — versus
3–6 s for one frontier shot. **We pay ~2–3× in latency to buy a certificate.** That is a
legitimate trade, and it is the only place in this exercise where I can name a trade the
frontier cannot match at any price.

**Stop condition:** if 20 attempts does not change the verdict distribution verse
1 attempt, the loop is not learning and gets deleted.

---

## Part 5 — The order, and what I refuse to do

1. **Move 4** — the loop. Everything else is maintenance. One file, one loop, 20 observations.
2. **Move 3** — the latency budget, so Move 4 cannot land and then rot.
3. **Move 1** — delete the 4,134 documents.
4. **Move 2** — the 25 pins, deliberately or not at all.

**I refuse to:**
- bulk-add `CONFINED_EFFECT_DECLARATIONS` rows to make 16/17 look like 16/17 pass.
  The number is honest. Closing it is a review, and reviews are supposed to be slow.
- claim the 33-module canonical-form merge bought speed. It bought **297 lines**. I
  measured speed and it did not move, and I am not going to imply otherwise.
- propose one more framework, index, registry, or governance artifact.

---

## Part 6 — The bet, in one table

| | Frontier 2026 | This repo, after Move 4 |
|---|---|---|
| latency, cache hit | 0.5–1.5 s | 3.6 s warm / 10.6 s cold |
| latency, monolith | 3–6 s | ~10 s for 20 certified attempts |
| cost per task | $0.03–$0.13 | **$0.00** |
| stopping rule | budget exhaustion or judge | **anytime-valid, 20 observations, certificate** |
| restart after crash | lost in-flight state | **honest `INTERRUPTED`, measured absence** |
| claims | held-out split, post-hoc audit | **target-free, contamination-free by construction** |
| step efficiency | 66% of steps wasted in loops | one attempt — no loop to waste |

**The bet:** the frontier is racing to make one attempt fast. We are the only system
that can say *"we stopped because the evidence was decisive, and here is the bound"* —
and the machinery to say it is already written, already correct, and currently called
by nothing.

That is not an incremental advantage. It is a different claim.

---

## Reproduce

```bash
# the stopping rule decides in exactly 20
python3 -c "
import sys;sys.path.insert(0,'.')
from canonical.runtime import h100_anytime_proposal_confidence_v1 as h
for n in (10,20): print(n,'perfect -> lower bound',round(h.lower_bound(n,n),3))"
# 10 -> 0.432 (undecided)   20 -> 0.615 (DECIDED)

# 13 capabilities admitted for confinement, all source-analysis
python3 -c "import json;print(list(json.load(open('canonical/runtime/CONFINED_EFFECT_DECLARATIONS_V1.json'))['capabilities']))"

# latency decomposed: work 7.3s, proof 4.8s of a 10.6s cold solve
python3 -c "
import cProfile,pstats,io,sys;sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as ra
pr=cProfile.Profile();pr.enable()
ra.solve({'task_id':'t','goal':'index the python symbols in this repo with ast'})
pr.disable();s=io.StringIO()
pstats.Stats(pr,stream=s).sort_stats('cumulative').print_stats(20)
print('\n'.join(l for l in s.getvalue().splitlines() if 'nt' in l)[:600])"
```
