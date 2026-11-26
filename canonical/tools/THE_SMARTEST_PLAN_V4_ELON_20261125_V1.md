# The smartest plan v4: delete complexity, win on speed

**Date:** 2026-11-25. **Authority:** NONE (producer-run sandbox).
Supersedes v1, v2 (falsified), v3 (mostly falsified, one survivor). Organized by **Elon's law**:
*best part is no part* (deletion before optimization) and *everything must be insanely fast*
(speed is the metric, not an afterthought). Every number **verified** (measured here or checked
live today), **unverified**, or **failed**.

---

## §0 The Elon's-law diagnosis of this repo

`canonical/runtime/` is **558,398 lines**. That is the problem. The frontier is winning on raw
capability (SWE-bench Verified 95.0%) but losing on the things Elon's law predicts: complexity is
the enemy of scaling, context bloat is the silent killer (134K tokens of tool definitions before
work starts), and multi-agent overhead costs ~3× tokens and time. OSWorld 2.0 best is **20.6%** —
the frontier's complex systems lose track, guess, and skip verification.

Our repo has the same disease (558K lines) **and** the cure (a few simple, insanely fast
mechanisms). The plan is to **delete the disease and keep the cure.**

## §1 Measured speed: the simple mechanisms are orders of magnitude faster

Measured today (fresh venv, this repo):

| mechanism | speed | LLM calls | tokens | lines |
|---|---|---|---|---|
| `transfer_learning.recall` | **0.024 ms** (24 µs) | 0 | 0 | 988 |
| `oe_sygus_synthesizer` | **1.69 ms** | 0 | 0 | 1,118 |
| `stochastic_synthesizer` | 41.62 ms | 0 | 0 | 154 |
| ensemble (OE+stochastic) | 171.47 ms | 0 | 0 | — |
| **frontier LLM call** | **~500-2000 ms** | 1 | thousands | — |

The OE synthesizer is **~300-1000× faster** than a frontier LLM call. Transfer recall is **24
microseconds**. All zero tokens. This is not a marginal advantage — it is a different regime.
The frontier burns tokens and milliseconds; we burn neither.

## §2 What to delete (best part is no part)

| candidate | size | verdict | reason |
|---|---|---|---|
| `causal_angelic_swe_engine_v1` + 5 deps | **~20,300 lines** | **DO NOT PROMOTE** | 14k-line monolith; unproven on corpus; the antithesis of "best part is no part" |
| LiveBench certificate machinery | ~2,000 lines | **fixture; leave or delete** | IF-specific; 0 code-repair concepts; falsified in plan v2 |
| `astra_runtime.py`, `goal_compiler.py`, `live_brain_route_admission_v1.py` | 7,780 / 7,554 / 7,292 | **audit for deletion** | the largest modules; complexity is the enemy of scaling |
| JitRL `use_advantage` code (plan v3) | ~30 lines | **dead code; delete** | falsified (identical 8/15); opt-in but useless |
| weight-space learning path | — | **moot** | 64 verified units << 5000 minimum; no fuel |

**Deletion before optimization.** Do not optimize the angelic engine. Do not promote it. The best
part is no part — the simple synthesizers (~1,270 lines) do the useful work the 20k-line monolith
claims to do, and they do it in milliseconds.

## §3 What to keep (the minimal, fast core)

| mechanism | speed | role |
|---|---|---|
| `transfer_learning_v1` | 0.024 ms recall, 6.333× speedup | instant learning: recall + replay |
| `oe_sygus_synthesizer_v1` | 1.69 ms | exhaustive synthesis (the workhorse) |
| `stochastic_synthesizer_v1` | 41.62 ms | random-search synthesis (diversity) |
| `verified_skill_crystallizer_v1` | fast | crystallize verified fixes into skills |
| `causal_trace_to_skill_compiler_v1` | fast | compile traces into skills |

**Total: ~2,260 lines** for the core. That is the unified runtime's real capability. Everything
else is either a fixture, a monolith, or dead code.

## §4 The unusual ideas (through Elon's lens)

### Idea 1 — The minimal repair loop: recall → synthesize → verify (three steps, zero LLM)

The frontier's repair loop is: LLM call (500-2000 ms) → generate patch → LLM call → verify →
repeat. Ours should be: **recall** a similar fix (0.024 ms) → **synthesize** a candidate if none
fits (1.69 ms) → **verify** by running the test (fast, local). Three steps. Zero LLM calls. Zero
tokens. Total latency: **milliseconds**, not seconds. The unusual idea is not a better algorithm —
it is **fewer steps**. Best part is no part: the LLM call is the part to delete.

### Idea 2 — Speed as the only metric (measure everything in ms and tokens)

Every mechanism in the repo should report two numbers: **milliseconds** and **tokens**. The
synthesizers report 1.69 ms / 0 tokens. Transfer reports 0.024 ms / 0 tokens. A mechanism that
cannot beat these numbers should be deleted. This turns Elon's law into a gate: *if it is not
insanely fast, it is not in the runtime.* The frontier cannot copy this because their systems are
built around LLM calls (which are inherently slow and token-hungry).

### Idea 3 — The ensemble is the diversity engine (already proven)

Plan v3's survivor: OE + stochastic ensemble produces **66 candidates vs OE's 38 (+74%)** in
171 ms. The unusual idea: **diversity through cheap parallelism, not through a bigger model.**
Two fast synthesizers (1.69 ms + 41.62 ms) beat one slow LLM call (500-2000 ms) at generating
candidates. Best part is no part — the "part" deleted is the LLM.

### Idea 4 — Delete the harness, keep the loop (the Terminal-Bench insight, inverted)

"Harness adds 8-15 points" — but the frontier's harness is complex (multi-agent, 3× overhead).
The unusual idea: **our harness is three functions.** `recall`, `synthesize`, `verify`. No
orchestration layer, no multi-agent coordination, no 558K lines of runtime. The harness *is* the
loop. Simplicity is the moat.

## §5 Falsifiers

1. **If the minimal loop (recall → synthesize → verify) does not fix any repair-corpus task.**
   Test: wire the three functions into a loop, run on the Part B corpus. If 0 passes stays 0, the
   loop is insufficient (and the corpus data is needed to test this).
2. **If a mechanism cannot beat 1.69 ms / 0 tokens, it should be deleted.** Audit the runtime;
   any module slower than the synthesizers and using tokens is a deletion candidate.
3. **If the ensemble's extra candidates (66 vs 38) do not include any correct patches** the OE
   synthesizer misses, Idea 3's diversity is useless. Test: on repair tasks, check if the
   stochastic-unique candidates contain fixes OE alone misses.
4. **If deleting the 558K lines breaks something load-bearing.** The deletion audit must be
   incremental: delete, test, confirm nothing breaks. If a "complex" module is actually load-bearing,
   it stays (and that is a finding).

## §6 Rejected

| idea | verdict | reason |
|---|---|---|
| Promote the 20k-line angelic engine | **rejected** | complexity is the enemy; best part is no part |
| Compete on proof/certificates | **rejected (falsified)** | IF fixture; 0 code-repair concepts |
| JitRL advantage estimation | **rejected (falsified)** | identical 8/15; optimizes ranking, not reach |
| Weight-space learning | **rejected (moot)** | 64 verified units << 5000 minimum |
| Match frontier on raw coding | **rejected** | 95.0% vs 0/51; speed/simplicity is the winnable axis |
| Bigger model / more parameters | **rejected** | OSWorld: progress depends less on larger models |
| Add more mechanisms | **rejected** | Elon's law: delete first, optimize later |

## §7 Bottom line

The frontier builds complex, slow, token-hungry systems and wins on raw capability while losing
on reliability (OSWorld 20.6%) and efficiency. Elon's law says the winner is the **simplest,
fastest** system. Our repo has both the disease (558K lines) and the cure (three mechanisms,
~2,260 lines, **0.024 ms / 1.69 ms / 41.62 ms**, zero tokens). The plan is to **delete the
disease and keep the cure**: do not promote the 20k-line monolith, delete dead code, measure
everything in ms and tokens, and run the minimal loop — **recall → synthesize → verify** — in
milliseconds with zero LLM calls. The unusual idea is not a new algorithm. It is **fewer parts,
run faster.** §5 is not met.
