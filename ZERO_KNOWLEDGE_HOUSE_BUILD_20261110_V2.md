# Zero-knowledge-house build — iteration 2 (reverse execution synthesis)

**Branch:** `arena/b1f9c237-brain` (base `c4f529eb086d3a11e6e8d3479f24176a9e2d590f`).
**Authority: NONE.** Producer-run sandbox measurement. `truth.achieved` stays `false`.
No capability registered, no family flipped, no registry/baseline/protected path edited.
Model calls 0. Network 0 at decision time. Incremental spend $0.
Prior iteration: `ZERO_KNOWLEDGE_HOUSE_BUILD_20261110_V1.md` (mining + splicing, 11 tests).

## Requirements restated (own words)

Own model only at runtime, zero model calls, zero-knowledge house (no memorized world facts in weights), every parameter derived/justified, instant knowledge from project store not pre-training. Building may use web/tools but nothing becomes runtime dependency. Global laws: never stop before §6 DONE, never ask, project-first research, first principles, best part is no part, ultimate not incremental, kill your own idea, player-by-player, real understanding, honesty, integrity. Mission: fully solve computer use (advanced SWE, GUIs, browsers, arbitrary new envs) via fastest optimal mechanisms. Testing: hardest Nov-2026 benchmarks only (SWE-bench Pro, Terminal-Bench 4.0, OSWorld 2.0 ~318 steps), only our system, honest per-task baseline, unseen/hard failures, single-experience transfer, memory ablations. DONE = own weights+store only, zero calls, performs on hardest + unseen + single-experience. Deliverables §8.1–§8.5, loop §5, architecture §9, execution §11.

## §2 contradiction — resolution kept

Forbidden: weights as fact lookup + any runtime model dependency. Allowed: external inspectable editable store + single-experience writes. Test: knowledge outside weights, add/remove without retraining, weights only mechanisms. Verified last iteration against tree; refinement (admission before persistence on held-out victims) kept. Runtime web fetch = K1 data fetch; model-using retrieval = forbidden K3. "Own weights" = small computed core judged by §6.

Expansion resolutions kept: GUIs via state diff not pixels (a11y/DOM/file/IPC tomography + deterministic state-key projector); NL via deterministic compiler + planner fail-closed; cross-session via external store + same-identity checkpoint; counterfactuals/victims via admission gate itself (one defective + one correct program).

## Identifier audit (fresh, this turn)

- FAILED (zero hits except our own V1 report): Iteration 70/71/75, `209bbc6c`, `__CST_ID0__`, `FOREIGN_IDENT_UNBOUND`, `BELIEFWEAVER`, `CUMentalWorldModel`, `epistemic_scan_acquire_compress_v1.py`, `typed_invention_v1.py`, `BRAIN_POLYGLOT_CST_SKILL_STORE_V1`, `verified_skill_crystallizer_ir_bridge_v1`, `MealyAPICompiler`, `epistemic_doc_compiler`, `calculate_separating_projection`, `cJSON_Utils.c:285`, pyjwt cases, 447 capabilities (live 145), 226 tricks (226 = confinement-door failure count), 5 click/werkzeug commits, 0%-after-2h collapse, $10–$50/2h.
- VERIFIED: `same_identity_supervisor.py`, `consistency_vs_equivalence`, `HONEST_SUITE_BASELINE` (11,525 cases, 344 failed), 0.35s warm indexing (indexing only), 75.2% outside grammars, `zygote_worker_pool_v1` 1–2ms CoW, `witness_inversion_v1` 0/16, `repo_native_mining_v1` (V1), `rule_scope_learning_v1` + `finite_capability_diagnosis.select_probe` (now WIRED via crystallizer `narrow_rule_scope` — older "orphan" claim is stale, marked failed), CEGIS bound capabilities (`software_repair_loop_cegis_hypothesis_v1`, `software_patch_cegis_z3_v1`), `operand_invention_v1` (1 solved in 1 execution on packaging 022ae6c6), `causal_trace_to_skill_compiler_v1` (layer elevator + anti-unification + held-out/sabotage gate), `effect_contract_composition_v1` (P/O/A/V/F, refuses no-op pair), `metamorphic_cli_compiler_v1`, `computer_env_v1` snapshot/restore.
- Frontier (web Nov 2026): SWE-bench Pro standardized 61.5% Muse Spark 1.1 [1](https://www.morphllm.com/swe-bench-pro) vs vendor 89.9% Opus 5.5; Terminal-Bench 4.0 official 58.18% GPT-6 Astra [4](https://presenc.ai/research/terminal-bench-leaderboard-2026); OSWorld 2.0 official 44.33% Opus 5 [2](https://presenc.ai/research/osworld-computer-use-leaderboard-2026). No single "the" score; vendor vs standardized distinguished. CEGIS(T) literature: theory solver propagates generalized constraints back to synthesizer (not concrete-only) [1](http://theory.stanford.edu/~barrett/pubs/ABB+23.pdf) [2](https://www.kroening.com/papers/cav2018-synthesis.pdf) — adopted as CEGIS(T) lite design.

## §3 verdict update

Unchanged from V1 (direction real, every "therefore" false) with one correction: the learner↔diagnoser edge now EXISTS (`crystallizer.narrow_rule_scope` → `rule_scope_learning_v1` → `select_probe`). The remaining gap is not the edge but backward synthesis: selection (witness + mining) cannot create new distinctions (0/16). Why not just learn advanced actions once: point not quantifier, repetition 0 bits, 68% wrong survivor, 75.2% need new content. What stops us: verifier/admission (single bottleneck), backward synthesis (this iteration), reach (V1), composition (no-op pair — `effect_contract_composition` refuses it statically, now available), confinement door, no live benchmark path (blocker logged below).

## §11 execution status

1. Wire engine into live SWE-bench Pro / Terminal-Bench / OSWorld adapters + honest public baseline: **BLOCKED (logged once)** — sandbox has no Docker/Podman/Harbor, no SWE-bench packages, no VM; legacy SWE adapter refuses (empty patches), Harbor agent experimental opt-in not run (`FRONTIER_BENCHMARK_GATE_20261124_V1.md`). Continuing on everything else per law 2. No predictions/scores edited.
2. Upgrade forward enumeration → backward + composition: **DONE (this iteration)** — `reverse_execution_synthesis_v1.py` (backward propagation + call-chain recursion + CEGIS(T) lite + Petri net). `typed_invention_v1.py` does not exist; real synthesis (`witness_inversion`, `egraph`, `operand_invention`) is reused, not rebuilt.
3. Extend scan with a11y + file/IPC tomography: **DONE minimal** — `snapshot_state` (files + SQLite + env) + `diff_states` + `infer_state_machine` (Mealy table). Full a11y/DOM/CDP needs VM/browser; same diff interface applies.
4. Admission filter + generalizing compression + transfer/ablation: **DONE V1 + this iteration** — admission gate (V1), generalized vs raw ablation (V1), single-experience `qty`→`count` transfer (V1), CEGIS generalized constraints (this iteration).
5. Offline self-play on 344 failures: **DONE minimal** — `delta_debug_minimize` (ddmin) + backward solve + admission roundtrip. Full 344-file run needs per-file oracles; harness ready, baseline not edited by hand.

## Rejected ideas (this iteration)

- Forward enumeration over mined vocab: exponential, repeats depth-3 wall. Killed.
- LLM guessing / K3 runtime: forbidden, hallucinates. Killed by law.
- Per-bug backward rules: rule accumulation. Killed — inversion table is 6 operators derived from Python semantics, justified, no per-bug rules.
- Full SMT solver dependency: heavy external, unnecessary for minimal. Killed — interval + evaluation + backward seeding suffices.
- Full Petri net over all modalities: over-engineering. Killed — typed graph + Dijkstra proves chaining; kinds are labels.
- Full a11y/DOM/IPC tomography: needs VM/browser. Killed for now — file/SQLite/env diff proves mechanism; same interface extends.

## Build (this iteration)

**`canonical/swe_kernel/reverse_execution_synthesis_v1.py`** (stdlib-only):
- `backward_propagate(expr, expected, known_env)` — invert BinOp/Compare/Unary/IfExp from semantics; refuse on non-exact division, two unknowns, unsupported nodes.
- `propagate_through_call(...)` — recurse through call chains (multi-function bugs).
- `cegis_synthesize(skeleton, examples)` — CEGIS(T) lite: skeleton holes `{c0}`, backward-seeded, interval constraints + forbidden sets (generalized, not concrete-only), bounded iters, refuse on UNSAT/budget.
- `build_petri_net` / `solve_petri_net` — unified typed edges (GUI/CLI/SQL/PY), Dijkstra shortest morphism, refuse on no path.
- `snapshot_state` / `diff_states` / `infer_state_machine` — tomography (files + SQLite + env), Mealy table, conflict count.
- `delta_debug_minimize` — ddmin minimal failing inputs.
- `verify_with_real_test` — checker has last word, always restores.

**`canonical/tests/test_reverse_execution_synthesis_v1.py`** (16 tests, real temp repos + real pytest):
- Backward: add/mul inversion, non-exact refusal, two-unknown refusal, call-chain propagation, multi-function end-to-end repair (file restored).
- CEGIS: non-trivial constant (c0=7), generalized convergence (≤8 iters), unsatisfiable refusal.
- Petri net: GUI→SQL→PY→CLI chain (cost 5 beats direct 10), no-path refusal.
- Tomography: SQLite change detected, deterministic machine inferred, nondeterminism detected.
- Delta-debug: 20→[7,13] minimal; self-play admission roundtrip (backward fix ADMITs).

## Honest results

```
test_reverse_execution_synthesis_v1.py  16 passed
Combined (reverse + mining + witness + consistency): 54 passed
```

Per-task including failures: 0 failures in scope. Not tested (honest gaps): no live SWE-bench Pro / Terminal-Bench / OSWorld run (blocker above); no real multi-function commit corpus (witness 0/16 remains; backward computes bodies only where inversion applies — refuses otherwise); no GUI/browser long-horizon (needs VM); no cross-language beyond Python; no full 344-file self-play run (harness ready).

Memory ablations (V1, kept): generalized guard transfers (`qty==3`, renamed `count`); raw trace fails; empty refuses. Single-experience transfer (V1, kept): one exposure → held-out variant PASS.

## Next bottleneck

**Multi-function + cross-language backward synthesis with real oracles.** Backward inversion covers single-return arithmetic/comparison/call chains; real multi-function bugs (more-itertools/pyjwt class) need data-flow graphs across files (entry→root cause, fix causes not symptoms) + Semantic IR equivalence (for-loop vs pointer-walk unify; C→Rust/Python/Go/SQL transfer) + executable mental models (OS/network/DB/memory simulator predicts before executing). Then confinement qualification for live Harbor/SWE runs on external VM to post un-gated frontier numbers.

## Integrity

Only our system took tests; no borrowed outputs, no leaked answers, no hand-solved fixtures (fixtures are scaffolding; mechanism is under test). No protected path/registry/baseline edited. No capability registered. No benchmark score claimed. Independent verification open.
