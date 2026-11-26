# The Single Ultimate Plan — Wave 47–48 (Minimal, No Wasted Parts)

**Date:** 2026-11-26 · **Branch:** `arena/adb67314-brain` · **Base:** `3e652cf2`
**Authority:** NONE__PRODUCER_RUN_SANDBOX. Model calls: 0. Spend: $0. `truth.achieved` stays `false`.

## 1. The bottleneck (single, if fixed unlocks most capability)

**Federation is shallow; composition is missing.** The 20 titans are already federated as isolated engines with narrow inputs, but `UnifiedModel.solve()` never composes them into the §9.1 loop with a Futamura fast path first. Wiring 1,529 more modules would violate Elon's law and add zero capability (reachability ≠ correctness). Composing the 20 that matter into one pipeline that runs Goal → Scan → Recall → Acquire → Predict/Act → Verify → Compress end-to-end is the single bottleneck.

Evidence: `UnifiedModel.solve()` routes to capabilities/engines but never calls `futamura_solve()`, reverse tomography, angelic lens, CoW zygote, e-graph, or effect oracle in sequence for a SWE task. Each is reachable only via explicit mode + exact input keys. The pipeline in Wave 47–48 makes them reachable via one front door with fail-closed fallthrough.

## 2. Design: TitanPipeline (4 rungs, K3=0 default)

```
Goal
  → Rung 0: Futamura compiled-skill fast path (0.2 ms, O(1) operator rule)
      hit + verified → return (never pay search tax twice)
      miss → Rung 1
  → Rung 1: Reverse tomography + CoW zygote + angelic lens
      (compute angelic value from failing assertion; synthesize via lens;
       screen in POSIX os.fork() CoW; reject outside symbol ownership)
      verified → compile to Rung-0 + sleep-crystallize → return
      fail → Rung 2
  → Rung 2: E-graph + semantic-causal equivalence + deductive synthesis
      (reason over equivalence classes; anti-unify; vericoding spine)
      verified → compile + crystallize → return
      fail → Rung 3 (only if proposer explicitly provided)
  → Rung 3: Untrusted proposer (optional, gated)
      (SCoRE e-value + effect oracle + mutation falsification must all pass;
       on verify, compile back to Tier-0)
      fail → honest refusal with missing discriminator (refusal is curriculum)
  → Compress: §9.2 admission filter (verified, goal-relevant,
      prediction-error-bearing, reusable, compressible) + anti-unification
      generalization (abstract identifiers/versions/layouts; keep concrete
      witness for check/rollback/specialize). Versioned, editable, removable.
```

**Computer-use branch (parallel, same gates):** `ShadowInterfaceEvolutionKernel` — compile CLI help / HAR / D-Bus / WebMCP / AT-SPI into shadow interface (Agent S4 style), route via HCU 3-channel (CLI/Code → Semantic AX/Mental-Model → Visual fallback), verify via byte effect oracle (header + round-trip), confine via kernel boundary (namespaces + chroot + no caps, 18-attempt escape payload). Evolve interfaces on held-out validation, never on benchmark tasks.

**Memory branch:** `SleepCrystallizerAdmissionGate` — 5-timescale verification-first bus + DBSP Z-set incremental maintenance (exact O(|Δ|)) + AGM belief revision + anti-manufactured-confidence (hedged hearsay never upgraded to fact) + LAPSE temporal guard. Zero write amplification (provenance-aware, no per-message LLM calls).

**Self-improvement branch:** `MetaCircularOrganGraph` + `concept_library_v1` (Stitch compression) + GEPA Pareto evolution behind anytime-valid e-values (Ville/SCoRE) + mutation-tested falsification + Thompson-poisoning gate. Self-improvement that cannot collapse.

## 3. Rejected ideas (and why)

| Idea | Why rejected |
|---|---|
| Wire all 1,529 unwired modules | Violates Elon's law; reachability ≠ correctness; 571K LOC of infrastructure (astra, goal_compiler, Harbor agents) adds no SWE/CU capability. The 20 titans already cover the 8 moves. |
| Merge PR #7144 (Waves 43–46) into this branch | §7: one branch, merge once. PR #7144 is a separate branch (`arena/ec636d41-brain`); cherry-picking it here would duplicate work and break the referee (protected paths, 2-family/4-predicate caps). Wave 47–48 builds on Waves 40–42 on `main`; Waves 43–46 merge separately. |
| Add a neural weight layer (LaCT/LaCET/LoRA) | Forbidden by `GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md` (identity/hosting-independent); impossible on 2 CPU/3GB/no GPU/no torch; downstream of experience layer (3.8% vs 64.8% ablation). BiSpace (Nov 2026) proves external memory beats weight editing +20–32% after 10K edits. |
| Use an open-weight proposer by default (Qwen3.8-27B / Goedel-Prover-V2 / Holo1) | Violates K3=0 default. Allowed only as strictly Rung-3, untrusted, gated, and compiled back to Tier-0 on verify. Default is honest abstention when Rungs 0–2 cannot solve. |
| Forward enumeration with larger budget (depth-3 → depth-5, 80K → 1M candidates) | Round 21 measured: more seeds, one part lost, zero gained. Budget scheduling without information repeats the failure. Backward constraint propagation replaces forward enumeration. |
| Pixel-based GUI grounding (VLM) | Violates §2 (no model calls). Structural observation (a11y tree, DOM, FDs, SQLite, IPC) + state diff replaces pixels. Pure-canvas/legacy GUIs get minimal own-model perception that obeys §2 (structural, never pixels alone). |
| Broad-ingest (crawl everything) vs goal-directed | Default: goal-directed with lazy on-demand acquisition. Cross-environment generalization emerges from compressing goal-driven experiences into shared abstractions, not crawling. Tested against broad-ingest baseline in `TitanPipeline` (held-out transfer). |
| Save raw action traces as main asset | Environments change; exact actions rarely recur. Raw episodes kept only as short-lived evidence until abstracted. Save causal/structural facts, decompositions, typed morphisms, cross-env laws, "how to ask" — each with provenance + re-validation probe. |
| Special-case pluggy/click/pyjwt | Same patch shape appears in any optional-selector API. The search must be right, not the rule. |

## 4. "Am I sure this is the smartest approach?" — kill attempts

- **Kill 1: "Just merge #7144 and call it Wave 47–48."** Killed: #7144 is Waves 43–46 (MEME/WebMCP/nested learning), not the 20 titans. Merging it doesn't compose titans into a pipeline. It also violates §7 and the referee.
- **Kill 2: "The titans are already wired, so nothing to do."** Killed: wiring is shallow (one function per titan, exact-key inputs, fail-closed). No test composes Futamura → tomography → e-graph → effect oracle → crystallize end-to-end. Wave 47–48 proves composition with zero-mock tests.
- **Kill 3: "E-graph is overkill; string repair is enough."** Killed: string repair is the 0/4,444 wall. E-graph reasons over equivalence classes (for-loop vs pointer-walk unify); without it, cross-language transfer (C → Rust/Python/Go/DB) is impossible.
- **Kill 4: "Effect oracle is redundant with tests."** Killed: PR #7071 measured four correct-looking passes, four wrong artifacts (goal was a name in an observation, not an effect in the world). Tests check assertions; effect oracle checks bytes on disk. Both needed.
- **Kill 5: "Sleep crystallizer is just a store."** Killed: without the §9.2 admission filter + anti-unification, the store accumulates raw traces that don't transfer. The filter is what makes one experience multiply capability instead of adding +1.

## 5. Build (files)

| File | Change | LOC |
|---|---|---|
| `canonical/runtime/wave47_48_titan_unification_v1.py` | NEW: `TitanPipeline`, `ShadowInterfaceEvolutionKernel`, `SleepCrystallizerAdmissionGate`, `RefusalCurriculumKernel`, `MetaCircularOrganGraph`, `DualRungGate`, `Wave47To48UnifiedModelMixin` | ~1,800 |
| `canonical/runtime/brain_unified_model_v1.py` | 2 lines: import `Wave47To48UnifiedModelMixin`, inherit it (0 net LOC growth; 7,533 → 7,533) | 0 net |
| `canonical/runtime/unified_hidden_capability_federation_v1.py` | +4 federated engines (`W47_FUTAMURA_FASTPATH`, `W47_REVERSE_TOMOGRAPHY_PIPELINE`, `W47_EGRAPH_VERICODING`, `W47_SHADOW_INTERFACE_EVOLUTION`) | +~200 |
| `canonical/runtime/creature_runtime_v1.py` | +1 method (`titan_pipeline_solve`) delegating to `UnifiedModel` | +~30 |
| `canonical/tests/test_wave47_48_titan_kernel_v1.py` | NEW: zero-mock tests for all 8 moves + §9.1 loop + §9.2 filter + single-experience transfer + memory ablations | ~600 |

Total new runtime: ~2,030 LOC. No new dependencies (pure stdlib). No model calls. No network. No capability registered (AGENTS.md: ≤3/PR; this PR registers 0). No scoreboard edited. `truth.achieved` unchanged.

## 6. Tests (hardest open problems, honest)

- **Single-function Python repair** (held-out, never-seen): operator-swap, guard-synthesis, and e-graph-equivalence tasks. Per-task results including failures. No hand-solved tests; only our system takes tests.
- **Single-experience transfer:** One exposure → held-out variant in different function name / variable names / constants (alpha-normalized). Proves Futamura Rung-0 generalization.
- **Memory ablations:** With store vs empty; generalized entries vs raw traces. Proves compression quality by transfer, not recall.
- **Interface evolution:** CLI help → shadow interface → HCU route → effect-oracle verify on a real `gzip` round-trip (PR #7071 pattern, re-measured).
- **Refusal curriculum:** Unresolvable task → typed refusal naming missing discriminator (not a guess).
- **Dual-rung gate:** Rung-3 proposer without gates → refused; with gates → admitted only on verify.

§6 DONE is not claimed. This is progress toward it. The §6 blocker (Docker/Harbor/VM for SWE-bench Pro / Terminal-Bench 4.0 / OSWorld 2.0) is logged once; everything else proceeds.

## 7. Sequencing (fastest real lever first)

1. **TitanPipeline Rungs 0–2 + §9.2 filter** (this build). Immediate composition wins; no runtime risk (fail-closed).
2. **Shadow interface evolution + effect oracle** (this build). Unlocks computer use without pixels.
3. **Sleep crystallizer + DBSP** (this build). Unlocks zero-forgetting memory.
4. **Meta-circular + GEPA behind e-values** (this build). Unlocks self-improvement that cannot collapse.
5. **VM/Harbor execution** (blocked, logged). Unlocks §6 measurement when infrastructure arrives.

Each step independently shippable, independently verifiable, reversible. No step requires the next.
