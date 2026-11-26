# Research Findings: What Exists in the Project + What the Frontier Did

**Date:** 2026-11-26 · **Branch:** `arena/fe676c2a-brain` · **Head:** `ac5c1015`
**Method:** project-first exhaustive search (including non-obvious names), then web. Everything below is either a file path, a live run this session, or a cited web source. Claims from earlier reports were treated as inputs to verify.

## Part A — What exists in the project (verified by search + execution)

### A.1 The live front door (real, running)

- `canonical/runtime/brain_unified_model_v1.py` (7,533 LOC) — `UnifiedModel` with `status()`, `route()`, `solve()`, `recall()`, plus 200+ federated methods. Live read this session: **462 capabilities, 153 bound, 309 receipt-backed, 234 engines, 208 federated kernel engines, 18 skills, 754 knowledge docs, 2,264 source-index modules, 7,444 research records**. Digest `3b07552726d7c057…`. Declares `NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS`, `model_calls: 0` on every path.
- `canonical/runtime/creature_runtime_v1.py` (4,028 LOC) — `Creature` with `boot()`, `solve()`, `solve_multifile_repo_futamura()`. State on disk, crash-resumable.
- `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` + `BRAIN_UNIFIED_CORE_V1.json` — compiled artifact, digest-verified on load. `compile_brain_unified_model_v1.py` is the only writer.
- Routing is deterministic token-overlap + CSR mmap. `route("fix a python bug where None causes crash")` → confident, coverage 0.83. `solve("what is 2+2")` → `FAIL_CLOSED: GOAL_NOT_REPRESENTED_IN_MODEL` (by design — unknown goals fail closed, never guessed).

### A.2 The SWE engine (real, verified this session)

- `canonical/swe_kernel/canonical_swe_spine_v1.py` (4,055 LOC) — `solve_swe_repo_native_multifile()` via `UnifiedModel.solve_swe_repo_native()`. **Verified live:** tiny repo `add(a,b)=a-b` with failing test → `PASS__K3_0_CANONICAL_SOLVER_VERIFIED`, `SOLVED_BY_COW_DEMAND_FAST_LANE:binop_invert:Sub->Add`, 0.13s solver / 0.81s end-to-end, `model_calls: 0`. This is the project's one proven K3=0 repair.
- `canonical/swe_kernel/typed_invention_v1.py` (446 LOC) — CEGIS(T) with type pruning, `max_depth=3`, `budget=200`, small-int constants. The ~80k explosion is documented in its own header. Real, but depth-capped as the prompt says.
- `canonical/swe_kernel/causal_nexus_v1.py` (1,547 LOC) — **the most important file for this session.** Implements: expected-value abduction (`extract_value_obligations`), bidirectional lens/transducer inference (`infer_transducer` + `lens_expression`, invertible `str/bytes.translate`), statement-level tree-rewrite morphisms (`SkillStoreV2` with `learn`/`propose`/`mark_transfer`/`mark_refutation`/`remove`/`stale`), negative-space invariants (`NegativeInvariantStore`), boundary fuzzing (`differential_boundary_scan`). Header explicitly names the `learned_skill_id=None` gap and claims to close it. **But `canonical_swe_spine_v1` never calls `SkillStoreV2`** — it only calls `extract_value_obligations`. The crystallization path uses `CanonicalLawStore.add_verified_diff` (single-line-block only, `len(changed)==1` required), so multi-statement fixes return `crystallized_law_id=None`. **Built but unwired.**
- `canonical/swe_kernel/petri_cow_splicing_engine_v1.py` (3,210 LOC) — `ASTSubtreeAntiUnifier` (minimal diff slice + schematic holes `_V0_`/`_ATTR0_` + Knuth-Bendix expansion). Also built but **never imported by the spine** (`petri_splicer` lazy module is declared, never used).
- `canonical/swe_kernel/stdlib_cow_test_runner_v1.py` — zero-dependency `os.fork()` CoW runner supporting plain `def test_*` functions, pytest-style nodeids, assertion-value rewriting. **Verified live:** correctly reports `1 failed, 1 passed` on a plain-function suite in 8.5ms. This is the correct oracle.
- `canonical/swe_kernel/zygote_worker_pool_v1.py`, `cow_angelic_zygote_v1.py`, `cow_zygote_speculative_verifier_v1` — CoW fork infrastructure. Real.
- `canonical/swe_kernel/harbor_in_container_runner_v1.py` (925 LOC) + `canonical/runtime/harbor_swe_zero_model_agent_v1.py` (876 LOC) — Harbor container transport with SHA-256 kernel transfer, `model_calls==0`. Real, but **Docker is unavailable in this sandbox** (`docker: command not found`), so container benchmarks cannot run locally. GitHub Actions is the only container path.

### A.3 The "unwired dark matter" (real files, mostly unwired)

All 11 files named in the prompt exist with the claimed LOC (±2 lines):

| File | LOC | Wired into UnifiedModel? |
|---|---|---|
| `canonical/swe_kernel/differential_witness_inversion_v1.py` | 1,370 | No (0 hits) |
| `canonical/tools/the_goal_is_a_quotient_of_the_trace_v1.py` | 620 | No |
| `canonical/tools/force_the_value_and_see_v1.py` | 623 | No |
| `canonical/tools/a_contrast_is_a_probe_v1.py` | 342 | No |
| `canonical/swe_kernel/the_repository_is_the_seed_corpus_v1.py` | 353 | No |
| `canonical/swe_kernel/metamorphic_laws_v1.py` | 545 | No |
| `canonical/swe_kernel/producer_lineage_graph_v1.py` | 518 | Partial (via `route_producer_lineage_holes`) |
| `canonical/runtime/verified_zero_screenshot_action_cache_v1.py` | 595 | Yes (organ `play_b_verified_zero_screenshot_cache`) |
| `canonical/runtime/osworld_verified_task_ledger_v1.py` | 808 | No (0 hits) |
| `canonical/runtime/verifier_falsification_v1.py` | 1,633 | No |
| `canonical/swe_kernel/learned_skill_verdict_v1.py` | 736 | No |

`grep` for all 11 names in `brain_unified_model_v1.py` returns only 13 hits (zero-screenshot + producer-lineage). The "1,394 unwired modules" claim is directionally true: the tree has 6,369 Python files under `canonical/`, and the unified model exposes 234 engines. Most modules are reachable only via bespoke test files, not via `UnifiedModel.solve()`.

### A.4 Evaluation (real, honest, and damning)

- `execution_guard/honest_suite_baseline_v1.py` (237 LOC) + `canonical/verification/HONEST_SUITE_BASELINE_20261103_V1.json`: **16,361 cases, 15,255 passed, 984 failed, 42 error, 344 files with failures** at `407cc3c3`, dirty tree. Authority `NONE`, measurement not receipt. The "344" is files.
- `canonical/verification/THE_VERDICT_ON_SECTION_3_20261124_V1.md` + `AUDIT_THE_PROMPT_CLAIMS_20261124_V1.json` + `FOUR_PLAYS_AND_THE_IDENTIFIER_AUDIT_20261124_V1.md`: the project's own prior audits already marked the 9 commit hashes FAILED, 75.2% as context-bound, and 11 phantom names as absent. This session re-verified those audits at the new head — they still hold.
- PR #7080 (OPEN): first claimable benchmark number in the tree is `swe-pro-v2-hard51-receipt.json` at **0.0%** (oracle 51/51, nop 0/51) — a cold-start ablation because `load_store()` fails closed on an absent skill store by design. This is the honest baseline: **0/51**.
- PR #7144 (OPEN, CONFLICTING/DIRTY), PR #7142 (OPEN, MERGEABLE/BEHIND). Neither is merged. Per branch rules, this session builds on `arena/fe676c2a-brain` and does not merge other PRs.

### A.5 What does NOT exist (phantom names)

`209bbc6c`, `92b6db85`, `d6c1661a`, `ac0e297`, `c53d373`, `05f6fd0`, `fc518e4`, `884437ae`, `051fd663` — not git objects. `BRAIN_POLYGLOT_CST_SKILL_STORE_V1`, `MealyAPICompiler`, `APIphany` — mention-only. `repo_component_and_cow_engine_v1`, `instant_swe_skill_store_v1` — mention-only (live code: `repo_component_petri_v1`, `causal_nexus_v1.SkillStoreV2`). `epistemic_scan_acquire_compress_v1` — no such file (live: `epistemic_computer_agent_v1`, `epistemic_admission_and_self_play_v1`). `CUMentalWorldModel` — single mention (live: `executable_mental_model_v1`, `executable_simulator_mental_model_v1`).

## Part B — What the frontier did (web-verified, Nov 2026)

### B.1 SWE-bench Pro V2 (real, current)

Scale AI released SWE-bench Pro V2 on 2026-09-22 (paper `arXiv:2610.24206`, Oct 2026). 480 of 731 original tasks were repaired/retired; **642 tasks remain**, graded in a locked sandbox with no internet. Best system: **Claude Opus 5 (xhigh) in Claude Code at 99.4%** full-set. **Hard split (51 tasks)** selected from model failures + expert audit: systems range **52.9%–98.0%** (Haiku 5.5 52.9%, Inkling 56.9%, Gemini 3.8 Flash 58.8%, GLM-5.3 84.3%, Kimi K3 88.2%, GPT-6 Astra 90.2%, Fable 5.1 92.2%, Opus 5 98.0%). Every task is solved by at least one frontier model. The original Pro (1,865 tasks, 41 repos, avg 107 lines / 4.1 files) remains the contamination-resistant variant; Verified (500 tasks) is saturated at 87–94% and no longer separates frontier systems. Sources: [1](https://arxiv.org/pdf/2610.24206) [2](https://www.rlresearch.ai/blog/swe-bench-pro-v2-480-of-731-tasks/) [3](https://baeseokjae.github.io/posts/swe-bench-coding-benchmarks-guide-2026/).

### B.2 Terminal-Bench 4.0 (real, current)

Terminal-Bench 4.0 (2026-08-28) contains **66 tasks** (from 3.0's 74, minus 8 removed, 19 fixed), each attempted 5 times, graded by verification scripts against end state. Leaderboard (2026-11-05): **Opus 5.5 (max) 64.8% ±3.1% ($4.7k), Sonnet 5.5 (max) 61.8% ±2.9% ($7.3k), GPT-6 Astra (max) 58.2% ±2.8% ($3.3k), GPT-6.1 Sol 58.2%, Fable 5.1 57.9%**. Version history matters: 2.1 (89 tasks, top ~83%) → 3.0 (74 tasks, top ~34%) → 4.0 (66 tasks, top ~65%). The prompt's "Sonnet 5.5 70.6% TB4.0" does not match the Nov 2026 board. Sources: [3](https://capitalandcompute.net/ai-benchmarks/terminal-bench/) [5](https://personalagentbench.com/benchmarks/terminal-bench/).

### B.3 OSWorld 2.1 (real, current)

OSWorld 2.0 (`arXiv:2606.29537`, Jun 2026) + 2.1 bug-fix release (2026-09-16) benchmark **108 long-horizon workflows** (median 1.6h human time, avg 318 tool calls for Opus 4.7, 500-step limit, checkpoint-driven scoring). At release, best was **Opus 4.8 at 20.6% binary / 54.8% partial**; current leaderboard has **Opus 5 at 44.3% binary / 77.7% partial**. Failure mode is not GUI control but constraint loss, missed mid-task information, and skipped verification — exactly the long-horizon drift the prompt describes. Sources: [1](https://arxiv.org/abs/2606.29537) [2](https://github.com/xlang-ai/OSWorld-V2) [3](https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/).

### B.4 Frontier failure modes relevant to this project

- **Memory flattening:** KAIST MEME (`arXiv:2605.12477`) — all 6 public memory systems average 3% Cascade / 1% Absence; deeper top-k and stronger LLMs do not fix it. Kwon 2026 (`arXiv:2606.29279`) + LAPSE (`arXiv:2609.36457`) prove LLM summarizers strip hedges and coerce progressive facts into false present truths. Brain's DBSP + semiring JTMS + MEME 6-op engine (PR #7145, merged) is the correct shape of answer, but it is not yet wired to `UnifiedModel.solve()` for raw-text transcripts.
- **Self-evolution collapse:** Anytime-valid certificates (`arXiv:2607.00871`) + SCoRE conformal e-values (`arXiv:2603.24704`) prove endogenous loops void static PAC bounds; only e-value supermartingales + held-out gates prevent silent collapse. Brain has `verifier_falsification_v1` (1,633 LOC, "prove the verifier can say no") + `learned_skill_verdict_v1` + `conformal_evalue_gate` — all unwired.
- **Action bias / slop:** FixedBench (`arXiv:2605.07769`) — agents edit already-fixed code; SlopCodeBench — Opus 5.5 94.25% slop lines at Medium; SWE-EVO (`arXiv:2512.18470`) — frontier drops 72.8% → 22.9% on release-sized evolution. Brain's `NegativeInvariantStore` + `FixedBench abstention` (PR #7142, open) + metamorphic pins are the right answers, unwired.
- **Instant learning:** Doc-to-LoRA/Text-to-LoRA (Sakana, `arXiv:2602.15902`) — hypernetwork converts docs to LoRA in one forward pass; SEAL (`arXiv:2506.10943`) — self-edits jump ARC few-shot 0% → 72.5%. Both still forget on sequential updates. Brain's quotient-of-trace + minimax CoW probes + `JitRL` is exact and auditable, but the quotient front-end is unwired.

**Frontier takeaway:** the frontier's walls (memory flattening, endogenous collapse, action bias, long-horizon drift) are exactly the walls Brain's unwired modules were built to solve. The gap is wiring + cold-start, not invention.
