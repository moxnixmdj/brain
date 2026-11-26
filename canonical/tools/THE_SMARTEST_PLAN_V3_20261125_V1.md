# The smartest plan v3: be ahead where the frontier is structurally weak

**Date:** 2026-11-25. **Authority:** NONE (producer-run sandbox).
Supersedes `REVISED_PLAN_PROOF_NOT_SCORE_20261124_V1.md` (falsified) and
`THE_SMARTHEST_PLAN_20261124_V1.md`. Every number is **verified** (measured here or checked live
today), **unverified**, or **failed**. Web research maximized per instruction; repo searched under
unfamiliar names.

---

## §0 Measured status (today)

| capability | number | verdict |
|---|---|---|
| Reach (repair corpus) | **0 passes**; 0/51 certified SWE-bench Pro V2 | the binding constraint |
| Transfer (instant learning) | **8/15, 6.333×** mean trial speedup, 0/15 worse-on-trials | fixed; not the bottleneck |
| Isolation | `confinement_v1` leaks (sentinel outside clone, `host_untouched=True`) | **blocked**; do not route around |
| Synthesis | `oe_sygus_synthesizer_v1` **verified working**, now at unified runtime | real component, not a loop |
| Angelic repair loop | `causal_angelic_swe_engine_v1` real, 113 tests, **unproven on corpus** | candidate, not promoted |

## §1 Where the frontier is structurally weak (fresh literature)

- **Computer use is the frontier's open wound.** OSWorld 2.0 (arXiv 2606.29537): 108 long-horizon
  tasks, best **20.6%** (Claude Opus 4.8), 54.8% partial. The authors' own diagnosis: *"progress
  depends less on longer budgets or larger models than on agents that can act on streaming
  interfaces, keep a task-level model in memory across long horizons, and catch and repair their
  own mistakes."* Failures: lose track of constraints, miss mid-task info, **guess rather than ask**,
  skip verification, hidden-state recovery. Completion is **zero above 163 minutes**.
- **The memory-doing gap.** "Learning In-Context Adaptivity through Continual Gameplay" (arXiv
  2611.21710): models **accurately record opponent tendencies in memory yet rarely depart from
  default play**. Memory brings little gain for open-weight models, inconsistent for frontier.
  Having memory ≠ using memory.
- **Continual learning without gradients works.** **JitRL** (arXiv 2601.18510, ICML 2026):
  training-free test-time policy optimization. Stores `<state, action, reward>` triplets, retrieves
  relevant trajectories, estimates advantages, adjusts logits in closed form (`z' = z + βÂ`).
  **Beats fine-tuning at a fraction of the cost.** No gradient updates, no catastrophic forgetting.
- **Skill reuse is the continual-learning signal.** **ContinualSkillBench** (arXiv 2603.12011):
  five ordered 100-task streams, **69.5%** of tasks reuse an earlier core skill. The question is
  whether agents *truly evolve*, not just remember.
- **The harness is the capability.** Terminal-Bench: *"frontier models score 65-73% directly;
  **harness adds 8-15 points**."* The frontier's edge is scaffolding, not the model.
- **Self-evolving skills are the OSS frontier.** **Hermes Agent** (NousResearch, **140K stars**):
  auto-generates skill docs after each task, persistent memory, "task → skill → reuse" loop.
  **GenericAgent** (14.4K stars, ~3K lines): self-evolving skill tree, **6× fewer tokens**,
  "don't preload skills, evolve them." **MemSkill** (NeurIPS'26): learnable, evolvable memory
  skills, +8% over baselines. **Memento-Skills**: HLE +116.2% relative, no retraining.
- **Ensembling synthesizers beats one.** Angelix/SyGuS (ICSE'16): combining enumerative, stochastic,
  symbolic, and CVC4 synthesis engines **increases repair success by 50%** over any single engine.
  Different engines fix different bugs. Coding frontier: SWE-bench Verified **95.0%** (Fable 5),
  Terminal-Bench 2.1 **89.5%** — but SWE-bench Verified is **contaminated** (OpenAI declared it so,
  Feb 2026) and still used to rank.

## §2 Our hidden capabilities (searched under unfamiliar names)

| mechanism | where | what it does | status |
|---|---|---|---|
| `transfer_learning_v1` | `canonical/runtime/` | instant learning: 8/15, 6.333× | **verified** |
| `oe_sygus_synthesizer_v1` | `canonical/runtime/` | OE SyGuS + EUSolver synthesis, 3-lang | **verified, promoted this session** |
| `verified_skill_crystallizer_v1` | `canonical/swe_kernel/` | crystallizes verified fixes into skills | present |
| `causal_trace_to_skill_compiler_v1` | `canonical/swe_kernel/` | compiles traces into skills | present |
| `weight_space_fuel_v1` | `canonical/tools/` | counts verified (situation→action) fuel for weight-space learning | present |
| `agent_replay` | `canonical/capabilities/internalized/causal_falsification/` | trajectory recording/replay | present |
| `ignorance_ledger_v1` | `canonical/runtime/` | tracks what the agent does NOT know | present |
| `goal_chase_v1` | `canonical/runtime/execution_guard/` | tracks goals across long horizons | present |
| `computer_env_v1` | `canonical/runtime/` | computer use (unwired from decision layer) | present, **blocked by isolation** |
| `causal_angelic_swe_engine_v1` | branch-only | angelic repair loop, 113 tests | **unproven on corpus** |

**Gaps found by searching under unfamiliar names:**
- **No JitRL-like advantage estimation.** Searched for `advantage`, `value function`, `bellman`,
  `td error`, `reward shaping` — nothing. We store trajectories (`agent_replay`) and do instant
  learning (`transfer_learning`), but we do **not** estimate advantages or do test-time policy
  optimization. This is the JitRL gap.
- **No memory-doing.** Searched for `recall drive`, `memory guided`, `retrieve then act` — nothing.
  We record and recall, but nothing **forces** recalled memory to change behavior. This is the
  memory-doing gap, and we have it too.
- **`jit_knowledge_v1` is a false friend.** "Just-in-time knowledge" = fetching external data
  (github/pypi/npm), not JitRL. Different thing.

## §3 The unusual ideas

### Idea 1 — Implement JitRL on top of what we already have (the highest-leverage gap)

We have trajectory storage (`agent_replay`) and instant learning (`transfer_learning`). We lack
advantage estimation. JitRL proves you can do test-time policy optimization by:
1. Retrieving relevant past trajectories for the current state.
2. Estimating the advantage of candidate actions from historical returns.
3. Adjusting action selection in closed form — **no gradients, no retraining, no forgetting**.

**Why this is unusual and ahead:** the frontier is pursuing weight-space continual learning
(ASCENT, OSFT, RFT) which needs massive verified fuel and risks catastrophic forgetting. JitRL
sidesteps it entirely with a retrieval + estimation layer. We already have the trajectory store.
Adding advantage estimation is a **small, self-contained layer** that turns our existing instant
learning from "recall a similar case" into "optimize the action at test time." It directly attacks
the memory-doing gap: the retrieved trajectory doesn't just inform the prompt, it **changes the
action probabilities**.

### Idea 2 — Close the memory-doing gap by making recall drive action (control flow, not model)

The literature's sharpest finding: models record in memory but don't act on it. We have
`ignorance_ledger_v1` (what we don't know) and `goal_chase_v1` (what we're pursuing). The unusual
idea: **when the agent recalls a relevant skill or experience, force it to consider that recall
before acting** — not as prompt context, but as a control-flow gate. If a recalled skill is
applicable, the agent must either use it or explicitly refuse it with a reason. This turns memory
from "available" into "load-bearing." It is a **scaffolding change**, and the Terminal-Bench
finding says scaffolding is worth 8-15 points.

### Idea 3 — Ensemble the synthesizers (Angelix +50%)

We now have `oe_sygus_synthesizer_v1` at the runtime. Angelix shows ensembling synthesis engines
(enumerative, stochastic, symbolic, CVC4) beats any single one by 50%. The unusual idea: **don't
build a better synthesizer — build a portfolio and forge their results.** Add a stochastic and a
symbolic synthesizer alongside the OE one; when they disagree, that disagreement is information
about the bug. This attacks reach (0 passes) by widening the candidate space, not by deepening one
search.

### Idea 4 — Use weight-space fuel as a continual-learning gate (precondition, not method)

`weight_space_fuel_v1` counts verified (situation→action) events. The unusual idea: **only attempt
weight-space learning when verified fuel is sufficient** — and report the fuel level as the
capability claim. This prevents the standard failure of training on unverified experience. It
turns continual learning from "hope the data is good" into "prove the fuel is sufficient first."
Combined with Idea 1 (JitRL needs no fuel), this gives a two-track continual learning strategy:
JitRL for immediate adaptation, weight-space only when fuel is proven.

### Idea 5 — Compete on harness, not model (the Terminal-Bench insight)

The frontier's coding edge is 8-15 points of scaffolding. Our 4-tier controller + skill
crystallizer + transfer learning + now the SyGuS synthesizer **is** a harness. The unusual idea:
**stop trying to match frontier models on raw capability; win on the harness.** Every point of
harness improvement (Ideas 1-4) is worth more than a point of model improvement, because the
frontier cannot copy our harness without copying our repo. This is the one axis where a small team
with a good harness beats a large team with a good model.

## §4 Falsifiers (what would make this plan wrong)

1. **If JitRL-style advantage estimation doesn't beat plain recall on our transfer benchmark.**
   Test: implement advantage estimation on `agent_replay` trajectories, run
   `transfer_learning_new_instance_probe_20261103.py`. If it doesn't beat 8/15 / 6.333×, Idea 1 is
   falsified.
2. **If forcing recall-to-action doesn't change outcomes.** Test: add the control-flow gate (Idea 2)
   to the controller, measure on the repair corpus. If 0 passes stays 0, the gate is decorative.
3. **If ensembling synthesizers doesn't widen the candidate space usefully.** Test: add a second
   synthesizer, measure candidate diversity on repair tasks. If the ensemble produces the same
   candidates as the OE synthesizer alone, Idea 3 is falsified.
4. **If weight-space fuel is always TOO_THIN.** Run `weight_space_fuel_v1`. If it reports TOO_THIN
   everywhere, Idea 4 is moot (and that itself is a finding: we have no fuel for weight-space
   learning, so JitRL is the only viable continual-learning path).
5. **If the harness improvements don't move any number.** If Ideas 1-4 are implemented and reach
   stays 0, transfer stays 8/15, and no board moves, the plan is falsified.

## §5 Rejected

| idea | verdict | reason |
|---|---|---|
| Compete on proof/certificates | **rejected (falsified)** | certificate machinery is a LiveBench IF fixture; 0 code-repair concepts |
| Wire decision ↔ computer-use now | **rejected** | isolation leaks; "do not route around these blockers" |
| Match frontier models on raw coding | **rejected** | SWE-bench Verified 95.0% vs our 0/51; harness is the winnable axis |
| Promote the 20k-line angelic engine now | **rejected** | unproven on corpus; promoting without a result is adding a fixture |
| Bigger model / more parameters | **rejected** | OSWorld: "progress depends less on larger models" than on memory + self-repair |
| Vision model for GUI | **rejected** | frontier's diagnosis: perception is not the bottleneck |

## §6 Bottom line

The frontier is weak at **long-horizon computer use** (20.6%), at **using the memory it has**
(memory-doing gap), and at **continual learning without forgetting** (JitRL beats fine-tuning).
It is strong at **raw coding** (95.0%) and **harness engineering** (8-15 points). We cannot win
on raw coding. We can win on the harness, on memory-doing, and on training-free continual learning
— because we already have the trajectory store, the instant-learning mechanism, the skill
crystallizer, and now a verified synthesizer. The unusual ideas are not "build a bigger model."
They are: **estimate advantages at test time, force memory to drive action, ensemble synthesizers,
gate weight-space learning on proven fuel, and win on scaffolding.** None requires a frontier
model. All are falsifiable. §4 is not met.
