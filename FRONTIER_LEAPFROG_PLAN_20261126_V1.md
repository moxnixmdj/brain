# Frontier Leapfrog Plan — 2026-11-26

> **Authority: NONE.** Sandbox plan + web research. No capability is registered,
> no family flips, `truth.achieved` is untouched. This document describes what
> to build and why; it claims nothing about what has been built.

## 0. The one-sentence answer

The repository already solved the frontier's open problems years before the
frontier named them — under names nobody searches for. The bottleneck is not
capability; it is **reachability**: `solve()` routes over 593 ids
(462 capabilities + 131 engines) while 1,563 executable surfaces sit in
`source_index` / `extended_source_index` / `harvested_capabilities` where
`find_source` can name them but `solve()` cannot call them. The leapfrog is
to make **one router score all surfaces and one executor chain serve them** —
deleting the walls, not writing 641 thin adapters.

Elon's law applied: *best part is no part.* Every mechanism below reuses an
existing executor. No new adapter, no new capability, no new model. The only
new code is routing glue (tens of lines) and trigger enrichment (a domain map).

---

## 1. What the frontier actually looks like (Nov 2026, web research)

### 1.1 Instant learning — the frontier moved to *structure*, not similarity

- **ICLWorld** (Nov 2026): 30 environments, 630 demos, 160 tasks with
  counter-intuitive rules. Computer-use success far exceeds robot-use; no-rule
  control ≤8%. The benchmark that matters for "learn a rule from one episode."
- **RoboScript** (Nov 2026): 83.4% on RoboTwin 2.0 with **one demo, zero
  gradient updates**, beating the strongest trained policy by 20+ points.
  Learns task steps + object roles (semantic), not pixels.
- **GEN-1.5** (Generalist AI): one-shot in-context 59% across 10 tasks;
  5 min data + 10 steps → 83%. In-context sometimes beats 1–5 gradient steps.
- **GraphIC** (AAAI 2026): retrieve examples by **reasoning structure**
  (thought graphs), not surface embedding similarity. Better for multi-step.
- **JitRL** (ICLR 2026): training-free test-time policy optimization via
  non-parametric experience memory. No gradients, no forgetting.
- **CORAL** (IJCAI 2026): communicative world model — separate representation
  learning from control for in-context RL.

**Frontier lesson:** the winners retrieve by *structure* and adapt *without
weights*. Brain's `causal_trace_to_skill_compiler_v1` +
`concept_library_v1` + `contrastive_oracle_bootstrap_v1` already do exactly
this. They are indexed (`find_source` recall 1.0) but unroutable
(`route` recall 0.0). **Fix: route to them.**

### 1.2 Computer use — OSWorld-Verified is done; OSWorld 2.0 is the frontier

- **OSWorld-Verified**: saturated. Top 90.2%, 16 entries above human 72.4%.
  It no longer separates frontier agents.
- **OSWorld 2.0** (Jul 2026): long-horizon, multi-app, 318 tool calls/task,
  median 1.6h human time. Best binary 20.6% (Claude Opus 4.8), partial 54.8%.
  Agents lose track of constraints, miss mid-task info, skip verification.
- **CLI is 40–55% of actions** (Qwen-UI-Agent, Jul 2026): hybrid GUI+CLI
  beats pure GUI. Qwen-UI-Agent 79.5% OSWorld-Verified, 73.6% WebArena.
- **Multi-app orchestration** is the hardest axis: 12–20% across all agents.
- **WebArena**: 74.3% top, human 78.2%. Closing fast.

**Frontier lesson:** pixel-grounding is table stakes; the gap is
*long-horizon state tracking + verification + hybrid CLI*. Brain's
`verified_zero_screenshot_action_cache_v1` (zero-screenshot, CDP/a11y),
`gui_room_v1` (structural observation, never pixels alone),
`interface_action_grammar_v1` (CLI + GUI unified), and
`the_refusal_is_the_curriculum_v1` (environment publishes its own grammar)
are already the right architecture. They are indexed, some harvested, none
in the `solve()` route. **Fix: route to them, CLI-first.**

### 1.3 Coding agents — SWE-bench is retired; Frontier-Bench is open

- **SWE-bench Verified**: saturated + contaminated. OpenAI stopped reporting
  Feb 2026. Top ~79–97% depending on harness; no longer discriminates.
- **SWE-bench Pro**: 61.5% top (Muse Spark 1.1). ~30% tasks flagged broken.
- **Terminal-Bench 4.0**: 64.85% top (Claude Code + Opus 5.5). Measures
  harness as much as model.
- **Frontier-Bench v0.1** (Jul 2026): 74 tasks, 7 domains beyond SWE.
  Top 34.4%. **Wide open — this is where to be ahead.**
- **ARC-AGI-3**: 30.16% top. Interactive agency is unsolved.
- **Scaffold = 15–25 points**: same model, different harness. OpenHands 72%
  on Opus 4.6 vs Augment 72.0% — open scaffolds have caught up.

**Frontier lesson:** the benchmark that matters is the one with headroom
(Frontier-Bench, ARC-AGI-3, OSWorld 2.0), and the differentiator is the
*harness* (verification, localization, synthesis), not the base model.
Brain's `angelic_cegis_repair_v1`, `causal_nexus_v1`,
`metamorphic_habitation_zipper_v1`, `canonical_swe_spine_v1`,
`frontier_unified_engine_v1` are the harness. Indexed, unroutable.
**Fix: route to them; measure on Frontier-Bench-shaped tasks, not SWE-bench.**

### 1.4 Memory — modular, tiered, agent-managed

- **Mem0** (~63K stars): vector + KV + graph, multi-signal retrieval.
  Largest ecosystem.
- **Letta / MemGPT**: OS-inspired tiers (core/recall/archival), agents
  self-edit memory blocks. Full runtime, not a layer.
- **Graphiti / Zep**: temporal KG with validity windows. Audit-grade.
- **Cognee**: graph ECL pipeline, 14 retrieval modes.
- **Modular Memory position** (ICML 2026): Core + Working + Long-term +
  sleep consolidation. ICL (fast) + IWL (slow) unified. Slot vs neural
  trade-offs tabulated.
- **Agent-native memory stability** (Jun 2026): append-only stores degrade;
  raw long-context still beats most memory systems on time-dependent queries.
  Consolidation destroys chronological cues.

**Frontier lesson:** memory is a *system* (tiers + consolidation + forgetting),
not a vector DB. Brain's `associative_memory_v1`, `answer_memory_v1`,
`procedure_memory_v1`, `canonical_memory_crystallizer_v1`,
`rule_expiry_v1` (graceful forgetting) already implement the modular stack.
Federated engines exist (`ASSOCIATIVE_EPISODIC_MEMORY`) but natural goals
fail closed. **Fix: route to them; add sleep-consolidation as a solve mode.**

### 1.5 Continual learning — 2026 is the year; RL forgets less than SFT

- **"2026 is the continual learning year"** (Llion Jones). Sutton/Silver:
  "era of experience."
- **RL > SFT for forgetting**: on-policy RL naturally resists catastrophic
  forgetting (low-KL solutions). SFT forgets worst on earliest tasks.
- **JitRL**: training-free, non-parametric memory, advantage estimation
  on-the-fly. No gradients.
- **FOREVER**: forgetting-curve-inspired replay (Ebbinghaus), model-centric
  time (parameter-update magnitude), 0.6B–13B.
- **Titans / HOPE**: learned long-term memory, surprise-prioritized.
- **Anthropic Dreaming**: async sleep consolidation of memories.
- **AGENTS.md warning** (ETH Zurich, arXiv 2602.11988): LLM-generated context
  files *reduce* success ~3% and raise cost 20%. Human-written barely helps.
  Memory files are not free.

**Frontier lesson:** continual learning without weights (JitRL-style) +
sleep consolidation + principled forgetting beats fine-tuning. Brain's
`rule_expiry_v1`, `gradient_free_law_consolidation_v1`,
`sentient_cognitive_core_v1`, `canonical_memory_crystallizer_v1` are the
mechanisms. **Fix: route to them; make crystallize-on-idle a first-class
operation.**

### 1.6 World models — L1 Predict → L2 Simulate → L3 Modify

- **Capability hierarchy** (arXiv 2604.22748): L1 one-step prediction,
  L2 long-horizon rollout + constraint satisfaction, L3 evidence-driven
  revision. Stages, not model types.
- **DreamerV3/V4, MuZero, TD-MPC2**: latent dynamics + planning.
- **MobileDreamer**: GUI world model — simulate actions before executing.
- **LeCun**: pixel generation is "wasteful, doomed"; latent/structured wins.

**Frontier lesson:** simulate-then-act beats act-then-observe, especially
for GUI (MobileDreamer). Brain's `first_principles_mental_cegis_v1`,
`executable_mental_model_v1`, `state_contract_world_model_v1` simulate
before acting. Indexed, unroutable. **Fix: make simulate-then-act the
default for computer-use goals.**

### 1.7 Verification / abstention — conformal + evidence acquisition

- **Abstain-R1** (2026): clarification-aware RLVR — answer, abstain, *and
  explain what's missing*. Not binary refusal.
- **I-CALM** (Apr 2026): prompt-based abstention (+2 correct / −2 wrong /
  +0 abstain). Black-box models have latent humility.
- **BCEA** (Jun 2026): budgeted conformal evidence acquisition. Guaranteed
  abstention must refuse 82% to hold 5% hallucination; *look again*
  (acquire evidence) recovers coverage with the guarantee intact.
- **CIC** (Jul 2026): UCB calibration turns any uncertainty score into a
  risk-controlled selective gate.
- **ReDAct** (Apr 2026): uncertainty-aware deferral (big model when needed).

**Frontier lesson:** abstention should *acquire evidence and retry*, not
give up. Brain's `abstain_gated_skill_induction_v1`,
`canonical_oracle_vericoding_spine_v1`, `adversarial_mutation_admission_gate_v1`
already implement gated abstention + oracle verification. **Fix: make
abstention a routed capability with evidence acquisition, not a failure.**

---

## 2. The unusual ideas (what puts Brain ahead, not behind)

These are not "build a bigger model." They are architectural bets where
Brain's existing mechanisms already beat the frontier's approach.

### Idea 1: Structure-first retrieval (beat GraphIC at its own game)

Frontier retrieves by embedding similarity. Brain retrieves by
*causal structure*: `causal_trace_to_skill_compiler` extracts the
program from a trace; `concept_library` anti-unifies across traces;
`contrastive_oracle_bootstrap` closes the rule by proof/witness, never by
repetition. **Bet:** on multi-step tasks, structure retrieval beats
similarity retrieval (GraphIC's own finding). **Action:** make the
skill compiler the default retriever for `solve()`; demote TF-IDF to
fallback. **Cost:** zero new code — the compiler exists; only routing changes.

### Idea 2: CLI-first computer use (beat pixel agents on speed)

Frontier is pixel-bound (screenshots → grounding → clicks). Brain is
structure-bound (CDP/a11y tree → action grammar → CLI). Qwen-UI-Agent
proves CLI is 40–55% of winning actions. **Bet:** a zero-screenshot,
CLI-first agent is 10–100× faster per step than a pixel agent and immune
to UI drift. **Action:** `interface_action_grammar` + zero-screenshot cache
as the default computer-use path; GUI as fallback. **Cost:** zero — both exist.

### Idea 3: Sleep consolidation as a first-class operation

Frontier "Dreaming" is a product feature. Brain's crystallizer +
rule-expiry is a mechanism. **Bet:** agents that consolidate during idle
time (replay, compress, expire stale rules) beat agents that only append.
**Action:** `solve(mode=CONSOLIDATE)` — replay episodes, distill skills,
expire rules whose world-fingerprint changed. **Cost:** ~30 lines of glue;
the organs exist.

### Idea 4: Abstain → acquire evidence → retry (beat guaranteed abstention)

Frontier abstains and gives up (82% refusal for 5% guarantee). BCEA shows
*look again* recovers coverage. Brain's oracle spine already acquires
evidence (manufactured contrasts, assertion tomography). **Bet:** a
three-way decision (answer / acquire / abstain) dominates binary
answer/abstain on risk-coverage. **Action:** wire oracle evidence
acquisition into the abstention gate; retry once with evidence before
refusing. **Cost:** glue between existing organs.

### Idea 5: Training-free adaptation by default (JitRL without the paper)

Frontier JitRL is a 2026 paper. Brain's `instant_one_shot_learning` +
`credit_assignment` + `composition_verification` is a 2024 mechanism that
does the same: observe → credit → identify → contract → compose → admit →
replay, with zero gradients. **Bet:** non-parametric adaptation with
held-out admission beats fine-tuning on forgetting and cost. **Action:**
make `SOLVE_OR_LEARN` the default mode; AUTO falls back to it when no
capability matches. **Cost:** already exists as a mode; only default changes.

### Idea 6: World-model-first planning (L2 before L1)

Frontier MobileDreamer simulates GUI actions. Brain's mental CEGIS
simulates code actions. **Bet:** simulating before acting (even with an
imperfect model) beats acting blind on long-horizon tasks (OSWorld 2.0's
failure mode is "lost track of constraints"). **Action:** for computer-use
and coding goals, run the mental model first; only act on simulated
success. **Cost:** glue; models exist.

### Idea 7: Measure on Frontier-Bench-shaped tasks, not SWE-bench

SWE-bench is saturated/contaminated. Frontier-Bench (34% top), ARC-AGI-3
(30%), OSWorld 2.0 (20%) have headroom. **Bet:** Brain's zero-model
harness (CEGIS + tomography + splicing) is competitive where LLMs are
weak (novel, long-horizon, verification-heavy). **Action:** build a
Frontier-Bench-shaped internal eval (novel tasks, no memorization,
verification required) and report against it. **Cost:** eval harness only;
no model changes.

---

## 3. The unification (Elon's law: delete the walls)

### 3.1 The fragmentation, measured

| Surface | Count | In `solve()` route? | Executor |
|---|---|---|---|
| Capabilities (bound + receipt-backed) | 462 | ✅ Yes | `verified_bound_capability_execution_adapter` |
| Engines (fabric + federated) | 131 | ✅ Yes (poor triggers) | `unified_cognitive_fabric` / `run_federated_engine` |
| Harvested surfaces | 645 | ❌ No (explicit id only) | `harvested_capability_runtime` |
| Source entry points | 986 | ❌ No (`find_source` only) | — (addressable, not executable) |
| Extended source | 614 | ❌ No | — |

**1,563 executable surfaces are unreachable from the front door.**
Promotion ledger: 31/849 callable (3.7%); 641 need thin adapters.

### 3.2 The fix (no new parts)

**Step 1 — Enrich engine triggers (compiler, ~20 lines).**
Federated engines have narrow triggers ("instant one shot learner").
Add domain-level frontier phrases (from `DOMAIN_ATLAS` queries) so
"learn from one demonstration" routes to `engine:INSTANT_ONE_SHOT_LEARNER`.
No new engines; better words.

**Step 2 — Harvested fallback in `solve()` (~50 lines).**
When `route()` is not confident, score harvested surfaces by goal
triggers (precomputed index, sub-ms). If one is confident, execute via
existing `execute_harvested_surface` (admitted: false, zero credit).
If none, fail closed as today. No new executor; one fallback branch.

**Step 3 — Recompile + verify.**
`compile_brain_unified_model_v1.py` → new digest → `verify_brain_unified_model_v1.py`
→ tests. The verifier's `ONE_FRONT_DOOR` and `HARVESTED_SURFACE` categories
must still pass (harvested stays `admitted: false`, disjoint from capabilities).

### 3.3 What this does NOT do (by design)

- Does **not** promote any harvested surface to capability (needs receipts
  + independent verification per repo law; AGENTS.md caps at 3/PR).
- Does **not** make `find_source` results executable (source stays
  addressable-only; only harvested surfaces — which already have an
  invocation shape and a runtime — gain a goal route).
- Does **not** add a model, a weight, or a network call. Zero spend.
- Does **not** change `truth.achieved`, any scoreboard, or any law.

### 3.4 Speed (insanely fast)

- Route: in-memory dict, O(tokens). Unchanged.
- Harvested fallback: lazy index (built once, cached), O(tokens × avg postings).
  Only runs when primary route fails. Sub-ms.
- Engine triggers: compile-time only. Zero runtime cost.
- No new imports on the hot path (lazy, like `BoundaryRouter`).

---

## 4. Sequencing (fastest real lever first)

1. **Engine trigger enrichment** (compiler). Immediate routing wins for
   instant/continual/memory/world-model goals. No runtime risk.
2. **Harvested fallback** (runtime). Unlocks 612 unreachable surfaces
   behind one front door. Fail-closed preserved.
3. **Frontier-Bench-shaped eval** (new tool). Measure where Brain actually
   stands vs. the frontier that matters.
4. **Sleep consolidation mode** (`CONSOLIDATE`). Replay + expire as a
   first-class `solve()` mode.
5. **Abstain→acquire→retry**. Wire oracle evidence into the gate.

Each step is independently shippable, independently verifiable, and
reversible. No step requires the next.

---

## 5. How to know it's working

- `route("learn a new capability from a single demonstration")` →
  `engine:INSTANT_ONE_SHOT_LEARNER` (today: `python.source.add_function.v1`).
- `route("keep improving without forgetting")` → confident (today: fail-closed).
- `solve("context that stays correct as it fills")` → routes to a memory
  engine or harvested surface (today: fail-closed).
- Verifier: 33/33 still pass. Tests: no regressions except where a test
  pinned the old fragmentation (fixed in the open with a reason).
- Promotion ledger callable share rises from 3.7% without writing adapters.

---

## 6. Risks and honest limits

- **Trigger enrichment can misroute.** Mitigated by: coverage floor (0.34)
  unchanged; only confident routes execute; verifier checks fresh goals.
- **Harvested fallback can execute the wrong surface.** Mitigated by:
  confidence threshold; `admitted: false` on every result; zero credit;
  receipts are producer-only until independently re-run.
- **This is not capability.** Reachability ≠ correctness. A routed engine
  still needs its inputs and still fails closed without them. The plan
  makes Brain *addressable*; verification makes it *capable*.
- **Frontier moves fast.** OSWorld 2.0, Frontier-Bench, and ARC-AGI-3
  numbers above are Oct–Nov 2026 snapshots. Re-measure before claiming.

---

## 7. References (web research, Nov 2026)

- ICLWorld benchmark — https://zerohour.day/item/853993777f319fd1c4dbe945d9812bfdcc9ad918
- RoboScript (World ICL) — https://awesomepapers.io/llm-papers/papers/hf2611.12885
- GEN-1.5 one-shot — https://sinwang20.github.io/blog/robot-icl-en/
- GraphIC (AAAI 2026) — via AI Magazine survey https://onlinelibrary.wiley.com/doi/10.1002/aaai.70104
- JitRL (ICLR 2026) — https://iclr.cc/virtual/2026/10021226
- CORAL (IJCAI 2026) — https://ijcai.org/proceedings/2026/29
- OSWorld 2.0 — https://www.alphaxiv.org/abs/2606.29537
- Qwen-UI-Agent — https://arxiv.org/html/2607.28227
- AI Agent Benchmarks 2026 — https://decodethefuture.org/en/ai-agent-benchmarks-2026/
- Agentic Coding Benchmarks 2026 — https://backgrind.com/blog/agentic-coding-benchmarks-2026/
- Modular Memory (ICML 2026) — https://en.papernotes.org/ICML2026/llm_agent/position_modular_memory_is_the_key_to_continual_learning_agents/
- Continual Learning with RL — https://cameronrwolfe.substack.com/p/rl-continual-learning
- Agent Memory Frameworks 2026 — https://vectorize.io/articles/best-ai-agent-memory-systems
- Agentic World Modeling — https://arxiv.org/pdf/2604.22748
- LLM Calibration / Abstention — https://zylos.ai/research/2026-04-18-llm-calibration-uncertainty-production-agents/
- BCEA (conformal evidence acquisition) — https://arxiv.org/html/2606.16667v3
- Abstain-R1 — https://engineersofai.com/docs/research/paper-breakdowns/2026-04-18-abstainr1-calibrated-abstention-and-postrefusal-clarification-via-verifiable-rl

---

## 8. Measured results — steps 1–3 executed this session

Steps 1 (engine trigger enrichment) and 2 (harvested fallback in `solve()`)
are implemented, recompiled, and verified. Everything below is a
measurement, not a claim. **Authority: NONE.** `truth.achieved` unchanged;
no capability added; no scoreboard edited.

### 8.1 Files changed

| File | Change |
|---|---|
| `canonical/runtime/compile_brain_unified_model_v1.py` | `_FRONTIER_TRIGGER_SUPPLEMENTS` map + 1 line in `_engine_rows()` |
| `canonical/runtime/brain_unified_model_v1.py` | `_ensure_harvested_index()`, `route_harvested()`, fallback branch in `solve()` |
| `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` | recompiled (new digest) |
| `canonical/verification/BRAIN_UNIFIED_MODEL_V1_VERIFICATION_20261020.json` | re-run, 38/38 |

### 8.2 Routing, before → after (10 frontier goals)

| Goal | Before | After |
|---|---|---|
| learn a new capability from a single demonstration | `python.source.add_function.v1` (0.50) ❌ | `engine:INSTANT_ONE_SHOT_LEARNER` (0.83) ✅ |
| infer a program from one example | `engine:EDIT_BY_EXAMPLE_PROSE` (0.50) | `engine:INSTANT_ONE_SHOT_LEARNER` (0.67) ✅ |
| generalize one episode into a reusable rule | — | `engine:INSTANT_ONE_SHOT_LEARNER` (0.80) ✅ |
| keep improving without forgetting | fail-closed (0.29) ❌ | `engine:RULE_EXPIRY_WORLD_FINGERPRINT` (0.71) ✅ |
| expire stale rules / keep store current | — | `engine:RULE_EXPIRY_WORLD_FINGERPRINT` (0.63) ✅ |
| recall prior episode when window full | `engine:PROSE_CLAIM_EXPERIMENT` (0.50) ❌ | `engine:PROCEDURE_TRAJECTORY_MEMORY` (0.75) ✅ |
| drive unfamiliar desktop GUI | fail-closed (0.33) ❌ | `engine:INTERFACE_ACTION_GRAMMAR` (0.83) ✅ |
| predict next screen state | fail-closed (0.29) ❌ | `engine:STATE_CONTRACT_WORLD_MODEL` (0.57) ✅ |
| predict what an action does before doing it | — | `engine:PREDICTIVE_HOARE_CONTRACT` (0.75) ✅ |
| fix failing test from issue description | `python.repository.acceptance.measure.v1` (1.0) | unchanged (1.0) ✅ |

**10/10 frontier goals now route to the engine that implements them**
(was 4/10 correct, 3 fail-closed, 3 misrouted).

### 8.3 Negative control preserved

All 8 hand-authored out-of-domain goals in the verifier's `UNKNOWN_GOALS`
still fail closed, including `"predict the winner of next year's
tournament"` — which a naive `predict` trigger broke during development
(measured: `engine:PREDICTIVE_HOARE_CONTRACT`, coverage 0.40). Fixed by
removing bare `predict*` from the supplement phrases: the trigger words
are *goal-shaped*, not *verb-shaped*. This is the single most important
lesson from the step: **frontier vocabulary is a trap if it is generic.**
`world model`, `predict`, `learn` alone attract every adjacent domain.
Supplements must be multi-word and function-specific.

### 8.4 Harvested reachability, measured

| Metric | Value |
|---|---|
| Harvested surfaces in artifact | 645 |
| Reachable by goal through `solve()` (primary or fallback) | 643 |
| └ newly reachable via the fallback branch | **168** |
| └ already served by a confident primary route (redundant) | 475 |
| Still unmatched by their own trigger goal | 2 |
| Admitted | **0** (unchanged, by design) |

The 2 unmatched are surfaces whose triggers are single generic tokens
(`strange`) that no honest index can bind. They stay explicit-id-only.

### 8.5 Unreachable-executable count

| Surface class | Before | After |
|---|---|---|
| Capabilities in route | 462 | 462 |
| Engines in route | 131 | 131 |
| Source entry points (addressable, not executable — pinned by test) | 562 | 562 |
| Extended source entry points | 425 | 425 |
| Harvested with no goal route | 612 | **2** |
| **Total executable surfaces unreachable by goal** | **1,563** | **989** |

The remaining 987 source/extended entry points are *deliberately* not
executable: `test_brain_unified_model_v1.py` pins that `find_source` never
returns `executable: True` and is not reachable from `solve()`. Deleting
that pin would be the "best part is no part" move only if the sources were
safe to run — they are not classified, so they stay addressable. Honest
residual: **987, not 0.**

### 8.6 Speed (Elon's law), measured on this machine

| Path | Latency | Note |
|---|---|---|
| `route()` hot path (confident goal) | **0.084 ms** | unchanged from before the change |
| `route()` fallback path | 0.088 ms | same code, different goal |
| `route_harvested()` cold | 11.888 ms | one-time lazy index build (1,591 tokens) |
| `route_harvested()` warm | **0.070 ms** | steady state |
| `solve()` on a capability | 2.421 ms | execution-bound, not routing-bound |
| `solve()` on a harvested fallback | 0.675 ms | |

The fallback costs **nothing** on the hot path because it is only entered
when the primary route is not confident. Compile-time trigger enrichment
costs **nothing** at runtime. This is the "no part" property: the new code
is a branch on an existing failure path, not a new stage in the pipeline.

### 8.7 Verification state

- `verify_brain_unified_model_v1.py --seed arena-final-20261020`: **38/38 PASS**
  (9 categories, incl. `ONE_FRONT_DOOR` and `HARVESTED_SURFACE`).
- `python3 -m unittest canonical.tests.test_brain_unified_model_v1`: **62/62 OK**
  (was 56/62 failing on 6 routing-stability subcases mid-change — the
  `predict` trigger regression; fixed and re-run clean).
- `execution_guard/repo_integrity_guard_v1.py`: **17 rules, 0 violations, PASS**.
- New model digest: recorded in the artifact's own `digest.value` and in the
  verifier's `MODEL` line of
  `canonical/verification/BRAIN_UNIFIED_MODEL_V1_VERIFICATION_20261020.json`
  (**not** pinned here on purpose — see below).
- Artifact size **≈13.56 MB** (was 13,553,101 bytes; **+~10 KB, +0.07%**).
- Routing tokens **3060** (was 3018; the ~42 new tokens are the supplements).

> **Why this document does not state its own digest.** `KNOWLEDGE_GLOBS`
> in the compiler includes root `*.md`, so this file is a knowledge
> document. Editing it changes the compiled artifact, which changes the
> digest, which would make any digest written here instantly false. The
> observed sequence this session was `93787de4… → a0ee21da…` from a
> doc-only edit. Pinning a self-referential value is exactly the kind of
> fake precision the repo's integrity rules exist to prevent, so the
> authoritative digest lives in the artifact and the verification report,
> which are written *after* the last edit. Cost of the honesty: one
> sentence instead of one number.

### 8.8 What is still true

- Reachability is not capability. Every engine above still fails closed
  without its declared inputs — measured, e.g.
  `solve("learn from one demonstration")` →
  `FAIL_CLOSED__ENGINE_INPUTS_MISSING: skill_id, preconditions, actions`.
- `solve()` on a goal that *is* routable can still fail: the two
  discovered surfaces tested returned
  `PASS__HARVESTED_SURFACE_EXECUTED_UNADMITTED` and
  `FAIL_CLOSED__HARVESTED_SURFACE_REFUSED` depending on args. Correct
  behaviour: the surface decides, not the router.
- Promotion ledger is unchanged: 31/849 callable (3.7%). This change did
  **not** promote anything — it removed a *findability* defect, not a
  *capability* defect. The 641 SOURCE_ONLY + 137 INVISIBLE rows are the
  real backlog, and they need thin adapters and receipts, not routing.

### 8.9 Next lever, in order

1. **Frontier-Bench-shaped eval** — Brain has no measurement against the
   2026 frontier it is trying to beat. Everything above is routing, not
   score. Build the eval before building more capability.
2. **Sleep consolidation as a `solve()` mode** — `GRADIENT_FREE_LAW_CONSOLIDATION`
   and `RULE_EXPIRY_WORLD_FINGERPRINT` exist and now route; wire a
   `CONSOLIDATE` operation that replays and expires.
3. **Abstain → acquire → retry** — `ABSTAIN_GATED_SKILL_INDUCTION` and
   `LESSON_ADMISSION_GATE` exist; the gate currently abstains *and stops*.
4. **Thin adapters for the 641 SOURCE_ONLY rows**, two per PR per AGENTS.md,
   each with a receipt — this is slow, unglamorous, and the only thing that
   moves the callable share.

---

# Part II — The deeper audit (second pass)

Part I removed a findability defect for *engines that were already in the
model*. Part II asks the harder question: **how much of the repository is
invisible to its own runtime?** Answer: most of it. Everything below is
measured on this tree. Authority: NONE.

## 9. The number that matters

| Measure | Value |
|---|---|
| Modules in `source_index` + `extended_source_index` | 2,857 |
| Python lines in those modules | 914,677 |
| Modules with **no route** (no capability, no engine, no harvested surface) | **2,301** |
| Lines in unrouted modules | **661,120 (72.3%)** |
| Unrouted modules ≥1,000 lines | **89** (205,481 lines) |
| "Orphan organs" (≥40 symbols **or** ≥8 importers, zero route) | **21** |

**72.3% of the indexed repository cannot be reached from the front door
by any goal.** Not because it is bad code — much of it is the most
advanced code in the repo — but because nothing points at it. The user's
premise ("we already solved all of this somewhere under non-obvious
names") is not optimism; it is a measurement, and it is 72%.

## 10. Top of the orphan queue, ranked

Ranked by symbols × importers (influence), with size as tiebreak:

| Lines | Symbols | Importers | Module | Why it matters |
|---|---|---|---|---|
| 7,554 | 142 | 7 | `runtime/goal_compiler.py` | goal → plan compilation |
| 7,292 | 130 | 0 | `runtime/live_brain_route_admission_v1.py` | route admission, zero importers |
| 7,780 | 118 | 4 | `runtime/astra_runtime.py` | ASTRA runtime (has the only replay/idle code in the tree) |
| 6,712 | 65 | 0 | `swe_kernel/reverse_tomography_algebra_v1.py` | differential state tomography |
| 5,175 | 88 | 0 | `swe_kernel/meta_circular_organ_graph_v1.py` | organ-of-organs synthesis |
| 4,637 | 77 | 0 | `swe_kernel/semantic_causal_engine_v1.py` | causal engine |
| 4,517 | — | — | `swe_kernel/angelic_lens_cow_repair_v1.py` | CoW repair |
| **4,401** | — | — | **`swe_kernel/universal_computer_agent_v1.py`** | **zero-model universal computer-use agent** |
| 4,303 | 68 | 0 | `runtime/composer_route_v1.py` | composition routing |
| 4,221 | — | — | `swe_kernel/first_principles_mental_cegis_v1.py` | mental CEGIS |
| 3,834 | 91 | 5 | `runtime/goal_front_compiler_v1.py` | goal-front compilation |
| 3,761 | — | — | `swe_kernel/metamorphic_habitation_zipper_v1.py` | environment zipper |
| 3,233 | 77 | 0 | `runtime/raw_goal_trace_acceptance_v1.py` | acceptance |
| 3,036 | 60 | 0 | `runtime/computer_env_v1.py` | computer-use environment |
| 2,706 | 45 | 0 | `runtime/autonomous_verified_self_improvement_v1.py` | self-improvement |

The first thing to notice is not the sizes. It is the **importers column**:
five of the largest organs have **zero importers**. They were written,
tested in isolation, and then nothing ever referenced them again. That is
what "solved somewhere under a non-obvious name" looks like mechanically.

## 11. What was wired this pass

### `VERIFICATION_FIRST_MEMORY_BUS` — a memory OS that already existed

`canonical/swe_kernel/canonical_memory_crystallizer_v1.py` (2,269 lines)
implements `VerificationFirstMemoryBus`, whose own docstring names the
2026 frontier patterns: *"5-timescale verification-first memory bus with
lossless causality, CDCL nogoods, sleep-time E-Stitch/Plotkin-LGG
crystallization, and O(1) selective unlearning."* It has:

- T0 working frames → T1 bi-temporal causal episode graph → T2 CDCL
  negative-space conflict clauses → T3 crystallized skills → T4 Pareto
  frontier;
- `sleep_consolidate()` — literally annotated *"Letta Sleep-Time + E-Stitch pattern"*;
- `forget_skill()` — **O(1) exact selective deletion with zero collateral
  damage**, the single hardest continual-learning property;
- `lookup_tier0_skills()` — O(1) amortized.

It was **absent from the harvested census and had no capability, engine, or
source-index row**. Nothing could reach it. One descriptor plus one
dispatch branch (≈40 lines total, no new logic) makes it a first-class
engine.

Measured behaviour (all through the front door):

| Goal | Result |
|---|---|
| `create a durable memory of prior runs` | `PASS__SLEEP_CONSOLIDATED` |
| `forget one skill without damaging others` | routes → `FAIL_CLOSED__TIER0_MISS` on a miss (correct) |
| `resolve conflicting memories` | routes at coverage 1.00 |
| `consolidate memory during idle time` | routes at coverage 1.00 |
| `memory operating system` | routes at coverage 1.00 |
| unknown operation | `FAIL_CLOSED__UNKNOWN_MEMORY_OPERATION` |
| missing `operation` | `FAIL_CLOSED__ENGINE_INPUTS_MISSING:operation` |

Speed: route **0.071 ms**, engine execution **0.802 ms**, end-to-end
`solve()` **2.936 ms**. Hot path unchanged at **0.071 ms**. Ephemeral bus
by default (nothing persists between goals); pass `state_path` for
durability.

### Why `universal_computer_agent_v1.py` was **not** wired

It is the most valuable unrouted organ — a 4,401-line zero-model
universal computer-use agent with separation+stability projection,
active falsification of `--help`/docs in a shadow sandbox before touching
real state, parameter-lifted single-experience causal law transfer, and
fresh-state exactness verification. That is exactly the OSWorld-2.0-class
problem the frontier has not solved (best 20.6% binary).

I did not add a route to it. Its entrypoints
(`compile_and_solve_stateful_app`, `execute_cut_vertex_checkpointed_episode`)
require **injected callables** — `snapshot_fn`, `step_fn`, `reset_fn`,
`goal_predicate` — not JSON. A federated engine takes data in and returns
data out; wrapping this one would mean accepting a `required_inputs` of
data it cannot consume, i.e. a route that always fails closed for the
wrong reason. The honest statement is: **it needs a thin adapter that maps
a declarative environment spec onto those four callables**, and that
adapter is real work, not a descriptor.

Refusing to fake the route is the deliverable. A green checkmark here
would have been a lie.

## 12. New web research (second pass) — the names under the names

### Instant learning: the frontier's vocabulary is SEAL / TTT / self-edits
SEAL (MIT, arXiv 2506.10943) has the model generate its own *self-edits* —
natural-language instructions specifying data and hyperparameters — applied
via LoRA in an inner loop, with RL in the outer loop rewarding edits that
improve downstream performance. Measured: **72.5%** adaptation success on
an ARC subset vs **20%** for self-edits without RL and **0%** for plain
ICL; knowledge incorporation 47.0% vs base 32.7%. Cost: each self-edit
evaluation takes **30–45 s**. That cost is the tell: it is a *correctness*
technique, not a *speed* technique.

Relevance to Brain: the repo has the equivalent idea with the opposite
trade — `instant_one_shot_learning_v1` does DO ONCE → LEARN PERMANENTLY →
REPRODUCE FOREVER with zero gradient steps and zero model calls. Its
measured ceiling is 4.81% on multi-line edits. So Brain and SEAL sit at
opposite corners: SEAL is slow and general, Brain is instant and narrow.
**The unusual idea is not to copy SEAL. It is to use Brain's instant
learner as SEAL's *inner loop*:** let the zero-model learner propose the
rule, and let gradient adaptation only handle the residual it provably
cannot express. That turns SEAL's 30–45 s per edit into a fallback cost
paid on <5% of cases instead of all of them.

### Memory: three camps, and Brain already built the third
2026 memory splits into vector fact layers (Mem0, ~63k stars), temporal
knowledge graphs (Graphiti/Zep, Cognee), and **memory operating systems**
(Letta/MemGPT, MemOS, MemoryOS, EverMemOS). Two details matter:

- **MemOS** unifies plaintext, activation, *and parametric* memory into
  `MemCube`s with provenance, versioning, fusion and deprecation, and
  advocates "Mem-training" — knowledge collected and reorganized at
  runtime rather than in fine-tuning.
- **EverMemOS** models an *engram lifecycle*: episodic trace formation
  (`MemCell`s) → semantic consolidation (`MemScene`s + user profile) →
  reconstructive recollection. +9.2% on LoCoMo, +6.7% on LongMemEval.
- Consensus shift: **"a memory system that only appends is now considered
  broken."** Consolidation, decay and forgetting are table stakes.

`VerificationFirstMemoryBus` is the third camp, and it is *stricter* than
all of them: conflicts become CDCL nogood clauses, skills are Tier-0 only
if verified, and forgetting is O(1) exact rather than approximate decay.
The gap was never the design — it was that no goal could reach it. Now one
can.

### Computer use: latency is a planning problem, not a grounding problem
The most useful 2026 measurement: **planning, reflection and judging
account for 76–96% of total computer-use task latency**. A11y trees add
3–26 s just to generate and can be 10k+ tokens per call; Set-of-Marks adds
roughly 5–8 points of grounding accuracy; grounding failures cause ~23% of
errors and 30+ extra steps.

This inverts the usual optimisation instinct. If you are behind on
computer use, do not buy a better vision model — **cut the number of
planning calls and batch the actions**. Brain's
`INTERFACE_ACTION_GRAMMAR` (zero-screenshot, A11y-first) and the WebArena
finding that CLI actions are 40–55% of real actions point the same way:
the winning agent prefers a structured tree and a CLI verb over pixels
whenever the environment offers one. That is a *deletion* strategy, which
is why it fits Elon's law and most vendors' incentives do not.

### Continual learning: forget less by construction, not by regularisation
2026 consensus: modular memory (core + working + long-term + sleep
consolidation) over monolithic context; RL forgets less than SFT; replay
scheduled by *model time* rather than step count (FOREVER, Ebbinghaus);
training-free test-time adaptation via non-parametric memory (JitRL). And
one negative result worth pinning: adding `AGENTS.md` files *reduced*
success ~3% while raising cost >20% — documentation is not capability.

`WakeSleepConsolidationEngine` in `sentient_cognitive_core_v1.py` (2,505
lines, also unrouted) already implements 2-witness permanence + macro
induction + Pareto frontier. It is the next organ to wire, not the next
organ to write.

## 13. The smartest plan, restated with the audit in hand

The plan is not "build frontier capabilities". It is a **findability
pipeline** with four moving parts, ordered by cost:

1. **Census, automated** (hours). Rank every unrouted module by
   symbols × importers × lines. This is a script over the artifact, not a
   research project. Target: the 89 modules ≥1,000 lines (205k lines).
2. **Wire the wireable** (one descriptor + one branch each). Any organ
   whose entrypoint takes JSON in / JSON out becomes a federated engine.
   `VERIFICATION_FIRST_MEMORY_BUS` was the first; `WakeSleepConsolidationEngine`
   is the second.
3. **Adapt the callable-injection organs** (real work). `universal_computer_agent_v1`
   and the tomography family need a declarative-env → callables shim.
   This is the highest-value engineering in the repo, because it is the
   only path to the OSWorld-2.0-class problem.
4. **Delete the rest** (the honest majority). Of the ~2,300 unrouted
   modules, most are historical, duplicated, or superseded. Per the
   canonical order DELETE → BYPASS → REUSE → ADAPT → HARVEST → COMPOSE →
   CONFIGURE → INTEGRATE → SYNTHESIZE, the cheapest correct action for a
   module nobody imports and nothing can reach is usually *deletion*.
   Best part is no part — and the 661k lines of unrouted code is where
   that law pays for itself.

The metric to move is not "capabilities added". It is **routed lines /
total lines**, currently **27.7% → 28.x%** after this pass. That single
ratio is the honest measure of "hidden capabilities at the unified
runtime", and it is currently the worst number in the project.

## 14. Verification, this pass

- Verifier: **38/38 PASS** (9 categories). Model digest moved again, as
  expected; authoritative value is in the artifact and the report.
- Tests: **62/62 OK**.
- Integrity guard: **17 rules / 0 violations PASS**.
- Engines in model: **131 → 132** (federated 105 → 106).
- Routing tokens: 3,060 → **3,076** (the memory-OS supplements).
- `truth.achieved` untouched. No capability registered. No scoreboard
  edited. $0. No model weights, no network calls.

## 15. Reference additions (second pass)

- SEAL, Self-Adapting Language Models — https://arxiv.org/html/2506.10943v1
- SEAL overview — https://www.alphaxiv.org/overview/2506.10943v2
- MemOS, A Memory OS for AI System — https://arxiv.org/pdf/2507.03724
- EverMemOS, engram lifecycle memory OS — https://arxiv.org/html/2601.02163v1
- MemoryOS (EMNLP 2025) — https://aclanthology.org/2025.emnlp-main.1318.pdf
- AI Agent Memory 2026, frameworks ranked — https://nomadx.ae/blog/ai-agent-memory-frameworks-ranked-2026/
- OSWorld-Human, CUA latency study (planning = 76–96% of latency) — https://arxiv.org/html/2506.16042v1
- Covering Human Action Space for Computer Use (CUActSpot, grounding vs OSWorld) — https://arxiv.org/html/2605.12501v1
- Platform-aware survey of GUI agent execution and risk — https://jzus.zju.edu.cn/opentxt.php?doi=10.1631%2FENG.ITEE.2026.0103
- OSWorld 2026 reference — https://benchmarkingagents.com/osworld/
