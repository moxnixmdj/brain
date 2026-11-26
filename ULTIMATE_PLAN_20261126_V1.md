# The Single Ultimate Plan: Minimal, No Wasted Parts

**Date:** 2026-11-26 · **Branch:** `arena/fe676c2a-brain`
**Principle:** Elon's law — remove before adding. Every component must justify its existence. The best part is no part.

## 1. The bottleneck (single, ranked)

**The false-green oracle + unwired writer + missing front-end.** Fixing any one alone unlocks nothing:
- Fix the oracle without the writer → correct reads that evaporate.
- Wire the writer without the oracle → false reads crystallised as false laws.
- Build the front-end without both → cold-start goals reach a lying, forgetful engine.

So the plan is one inseparable unit of three fixes, in dependency order. Everything else (GUI tomography, Petri unification, e-value gates, Doc-to-LoRA) is explicitly deferred — it multiplies a policy that does not yet generalise.

## 2. The build (4 parts, all K3=0, all external-store)

### Part 1 — Honest oracle (fix, not new code)

**Problem:** `canonical_swe_spine_v1.solve_swe_repo_native_multifile._run_suite_in_dir` uses `python -m unittest <file>`, which discovers only `unittest.TestCase` subclasses. Plain `def test_*` functions (the dominant style in SWE-bench and in this repo's own tests) are invisible, so the baseline reports green when red.

**Solution:** replace the `unittest` invocation with `stdlib_cow_test_runner_v1.run_targets_cow_fork` (already in the tree, already supports plain functions + pytest nodeids + assertion-value rewriting, zero dependencies, `os.fork()` CoW). One function changed, no new engine.

**Rejected:** installing `pytest` as a runtime dependency (violates zero-dep K3=0; the stdlib runner already exists and is faster); writing a new runner (duplication — Elon's law).

### Part 2 — Wired writer (wire, not new code)

**Problem:** multi-statement fixes never crystallise (`learned_skill_id=None`) because `CanonicalLawStore.add_verified_diff` handles only single-line-block diffs and the spine only calls it for single-file changes. `SkillStoreV2` (statement-level anti-unification) and `ASTSubtreeAntiUnifier` (schematic holes) exist but are never called.

**Solution:** in the spine's crystallization path, after a verified fix, call `SkillStoreV2.learn(before, after)` for Python single-file fixes (including multi-statement) and record the returned `morphism_id` as `learned_skill_id`. Keep `CanonicalLawStore` for single-line fast path. Wire `NegativeInvariantStore.record` on refuted candidates so dead ends become pre-compilation filters. All stores are external JSON, `O(1)`-deletable, with provenance + witness + `refutations`.

**Rejected:** building a new store (duplication); storing raw action traces as the main asset (environments change, exact actions rarely recur — keep raw episodes only as short-lived evidence until abstracted, per §9.2); neural weight updates (violates zero-knowledge house; external JSON is the correct boundary).

### Part 3 — Cold-start front-end (one new module, minimal)

**Problem:** `UnifiedModel.solve()` fails closed on NL goals because engines need structured inputs. The 11 unwired modules (quotient-of-trace, contrast-probe, seed-corpus, metamorphic) were built to bridge this gap but are unreachable.

**Solution:** new `canonical/swe_kernel/cold_start_swe_adapter_v1.py` (~300 LOC): takes `(issue_text, repo_root)`, scans the repo (test files, source files), runs existing localization (`causal_dataflow_graph`, `assertion_localisation`, `line_localisation`) to derive `(test_targets, candidate_files)`, extracts value obligations from the baseline failure (`causal_nexus.extract_value_obligations`), then calls `solve_swe_repo_native_multifile`. Exposed as `UnifiedModel.solve_swe_cold_start()` via a thin `boundary_router` route (to respect the 7,534 LOC cap on `brain_unified_model_v1.py`). No model calls, no new search grammar.

**Rejected:** LLM spec parser (forbidden at runtime); hand-written NL→structured rules per bug class (rule accumulation — the exact failure mode §9.3 forbids); pluggable Rung-3 proposer as the default (allowed only as untrusted cold-start generator behind the verifier, and only after K3=0 is measured — deferred to Wave 47).

### Part 4 — Honest local benchmark (one new module, no Docker)

**Problem:** official benchmarks need Docker (absent locally) + gated data. No local harness reports per-task results with ablations, so "progress" is unmeasurable.

**Solution:** new `canonical/swe_kernel/swe_bench_local_harness_v1.py` (~250 LOC): runs the spine on hard local tasks (the 6 verified relation rows' shapes, a lens/codec case, a multi-statement guard/fallback case, a boundary-fuzz case, plus the two live repros from this session), reports per-task `pass/fail + mechanism + elapsed + model_calls`, and runs memory ablations (empty store vs seeded store, generalised morphisms vs raw traces). Container path (Harbor runner + GitHub Actions) is wired but marked `BLOCKED__DOCKER_UNAVAILABLE`, never faked.

**Rejected:** synthetic-only benchmarks (not ultimate-hard); claiming SWE-bench Pro numbers without Docker (dishonest); retesting what already works (harness tests only unseen hard failures).

## 3. Rejected ideas (and why)

| Idea | Why rejected |
|---|---|
| Dual-program splicing (Play 2) | Selection cannot create missing content. `witness_inversion_v1` measured 18 witnesses, 0 verified. Splicing two existing programs cannot produce the 75.2% of fix pieces that are new. |
| 16-way CoW rollouts (Play 3) | Throughput multiplies a near-zero per-attempt policy. Build only after the policy generalises. |
| Cross-modal Petri compilation as a total function (Play 4 as stated) | Presumes distinctions are already expressible. Salvaged as: one representation + computed distinctions + acquisition step (the cold-start adapter). |
| Repo-native component mining as the lead (Play 1) | Real but second-order. Mining adds pieces to a population already 75% unusable-in-advance. |
| Bidirectional lens synthesis as a separate engine | Already implemented as `infer_transducer` in `causal_nexus_v1`. Wire it, don't rebuild it. |
| Angelic perturbation fault localisation as a separate engine | Already implemented as `angelic_nexus_blame` + `force_the_value_and_see_v1`. Wire it via the adapter, don't rebuild it. |
| Articulation-point sub-goal slicing for OSWorld | Correct for 300-step tasks, but OSWorld needs Docker + display (absent). Deferred until the SWE front-end works. |
| Federated skill distillation / overnight self-play | Correct flywheel, but premature without an honest oracle and admission gate. Deferred to Wave 47. |
| Merging PR #7144 / #7142 from this branch | Violates the one-branch rule. This session builds Wave 45 here and opens a PR from here. |

## 4. How this maps to the prompt's §11 sequence

| Prompt §11 | This plan |
|---|---|
| 1. Wire Iteration 75 into SWE-bench Pro / Terminal-Bench / OSWorld adapters, honest baseline | Part 4 (local harness now; container adapters wired but Docker-blocked, honestly reported). Iteration 75 does not exist — the live engine is `canonical_swe_spine_v1` at head `ac5c1015`. |
| 2. Upgrade `typed_invention_v1` from forward enumeration to backward propagation + L2 composition | Deferred. `typed_invention_v1` is not the bottleneck (the spine's fast lane already solves binop/operand fixes). Backward propagation is `causal_nexus` (built, unwired) — wired in Part 2. |
| 3. Extend `epistemic_scan_acquire_compress_v1` with AX + file/IPC tomography | Deferred. No such file exists; computer-use needs Docker/display. Recorded as blocked. |
| 4. Implement §9.2 admission filter + generalising compression, run transfer + ablation tests | Part 2 (writer + invariants) + Part 4 (ablations). |
| 5. Start offline self-play on failing baseline | Deferred until Parts 1–4 pass. |

## 5. Success criteria (this session)

- [ ] False-green repro now correctly reports failure (no `PASS__BASELINE_ALREADY_GREEN` on a failing repo).
- [ ] Multi-statement fix crystallises with `learned_skill_id != None` and replays on a held-out file.
- [ ] Cold-start adapter turns an NL issue + repo into a verified fix (or an honest `FAIL_CLOSED` with a named missing fact — never a guess).
- [ ] Local harness reports per-task results + ablations, `model_calls: 0` on every task.
- [ ] All new tests pass; no existing test regresses (honest suite delta reported).
- [ ] `brain_unified_model_v1.py` stays ≤ 7,534 LOC (new logic lives in new modules + `boundary_router`).

## 6. What this does NOT claim

- Not DONE per §6 (no hardest-benchmark scores, no OSWorld, no Docker). This is progress, not completion.
- Not "100% provable correctness" — only what the project's own suite verifies on disk.
- Not frontier-beating numbers. The harness measures our system honestly; it does not compare to Opus 5.5 / GPT-6 Astra.
