# Confirmation: Requirements Read, Contradiction Resolved

**Date:** 2026-11-26
**Branch:** `arena/fe676c2a-brain` (from `ac5c1015` = merge of PR #7145)
**Head verified:** `ac5c1015e62612ec85a2efbfab0ac6f7e6b28468`
**UnifiedModel:** `canonical/runtime/brain_unified_model_v1.py`, 7,533 LOC, digest `3b07552726d7c057…`, 462 capabilities / 234 engines / 18 skills (live `status()` read this session).

## 1. Requirements restated (in my own words)

- Build our own K3=0 system (zero model calls at runtime, zero memorized world knowledge in weights) that solves computer use: coding, GUIs, browsers, arbitrary new environments.
- Knowledge comes from an external, inspectable store + instant retrieval (docs, help, source), not from pre-training. Runtime web fetch is allowed; runtime LLM search/summarizer APIs are forbidden.
- "Own weights" = small computed core judged by results, not by neural fashion.
- Test honestly on the hardest open benchmarks (SWE-bench Pro, Terminal-Bench, OSWorld), only our system, no leakage, with single-experience transfer and memory ablations. DONE = K3=0 + hardest benchmarks + never-seen environments + one-exposure learning, all at once.
- Loop autonomously: find bottleneck → research → design ultimate minimal solution → try to kill it → build → test hard → record. Never ask, never stop before §6.

## 2. Contradiction resolved: persistence vs. zero-knowledge house

**Resolution (adopted, verified against repo evidence):**

- **Forbidden:** weights as a lookup of memorized world facts; any runtime dependency on another model (including LLM retrieval/summarizer APIs).
- **Allowed:** an external, inspectable, editable JSON store of verified skills/laws/invariants that the system computes with, plus learning that writes to that store from a single verified experience.
- **Test (applied to every new component this session):** knowledge lives outside weights, can be added/removed without retraining, weights hold only computed mechanisms. Every new module below passes this test: `SkillStoreV2` morphisms are JSON with provenance + witness + `refutations`, `O(1)`-deletable via `remove()`; `CanonicalLawStore` laws are JSON with `delete()`; no new parameters are stored anywhere.

**Evidence for the boundary:** the repo already implements exactly this boundary — `CanonicalLawStore` (external JSON, `O(1)` delete), `SkillStoreV2` (JSON morphisms with provenance/staleness), `NegativeInvariantStore` (JSON invariants), `BRAIN_UNIFIED_MODEL_V1.json` (hashes/headings/terms only, never copied text). The prompt's "instant-knowledge source already in my project" is this store + `recall()` index. No evidence suggests a better boundary; the boundary is kept.

## 3. Other defaults adopted (verified)

- Runtime web retrieval = data fetch (allowed). LLM search/summarizer = forbidden. This session's web research used search only to *learn*, never as a runtime dependency.
- "Own model" does not require a neural net. `UnifiedModel` declares `NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS` and is judged by `solve()` results. Kept.
- Expansions (GUI/NL input/cross-session learning/auto-discovery) each get the minimal K3=0 solution that breaks no constraint; if impossible, show why and record. This session: NL input → cold-start adapter (retrieval + localization, no model); cross-session learning → `SkillStoreV2` crystallization (external JSON); GUI → not attempted this session (no Docker/display), recorded as blocked, not faked.

## 4. Claims from earlier reports: verified / unverified / failed

| Claim | Verdict | Evidence |
|---|---|---|
| Iteration 70/71/75, commit `209bbc6c` | **FAILED** | `git cat-file -t 209bbc6c` → not a valid object name. Only appears as quoted claim in prior reports. Repo's own `AUDIT_THE_PROMPT_CLAIMS_20261124_V1.json` marks all 9 hashes FAILED. |
| Iteration 83 `92b6db85`, Iteration 84 `d6c1661a` | **FAILED** | Same: not git objects. |
| click@ac0e297, click@c53d373, click@05f6fd0, click@fc518e4, werkzeug@884437ae, werkzeug@051fd663 | **FAILED** | Not commits in this repo. |
| `__CST_ID0__`, `FOREIGN_IDENT_UNBOUND`, `BELIEFWEAVER` | **VERIFIED as concepts, FAILED as prompt-described engines** | Now present as mentions/concepts (3/10/1 py files) but the live implementations are `tree_sitter_cst_skill_skeleton_v1`, `causal_nexus_v1`, etc. Prompt's engine descriptions do not match tree. |
| `BRAIN_POLYGLOT_CST_SKILL_STORE_V1`, `MealyAPICompiler`, `MultiLayerSnapshot`, `APIphany` | **FAILED as named engines** | 1/1/4/3 py-file mentions only; live code is `cross_modal_tomography_petri_v1`, `speculative_cow_petri_agent_v1`, `universal_semantic_ir_v1`. |
| `typed_invention_v1` depth-3 cap, ~80k search | **VERIFIED** | `canonical/swe_kernel/typed_invention_v1.py` (446 LOC): `max_depth=3`, `budget=200`, comment documents `~200*4*200=80k` explosion. |
| `HONEST_SUITE_BASELINE` 344 failing cases | **FALSE as stated, TRUE as files** | `HONEST_SUITE_BASELINE_20261103_V1.json`: 16,361 cases, 15,255 passed, **984 failed**, 42 error, **344 files** with failures. "344" is files, not cases. |
| 75.2% outside fixed grammars | **UNVERIFIED as grammar ceiling, VERIFIED as context-bound statistic** | Repo corpus measured 16/45 (35.6%) introduce identifier absent from old line. 75.2% = fix pieces rebuilt by no other task's operator over 500 SWE-bench Verified tasks (coverage 18.7%), not a grammar ceiling. |
| 0.35s runtime | **UNVERIFIED** | Appears 39× in code, 12× in reports, never measured as a benchmark. This session measured `solve_swe_repo_native` at 0.13s (solver) / 0.81s (end-to-end) on a tiny repo — real but not 0.35s as a general claim. |
| 447 capabilities, 226 tricks, 244 commits | **UNVERIFIED / STALE** | Live: 462 capabilities, 153 bound, 309 receipt-backed. "447" is stale by 15. "226 tricks" has no registry. "244 commits" impossible: repo has 1 commit in this clone (`git log --all` = 1, shallow). |
| SWE-bench Pro, Terminal-Bench 4.0, OSWorld 2.0/2.1 as hardest benchmarks | **VERIFIED real and current (Nov 2026)** | Web-verified: SWE-bench Pro V2 (642 tasks, Hard-51, Opus 5 99.4%); Terminal-Bench 4.0 (66 tasks, Opus 5.5 64.8%); OSWorld 2.1 (108 workflows, ~318 steps, Opus 5 44.3%). See RESEARCH doc. |
| Opus 5.5 / GPT-6 Astra / Muse Spark 1.1 scores in prompt | **UNVERIFIED / STALE** | TB4.0 leader is Opus 5.5 64.8% (not Sonnet 5.5 70.6%); SWE-Pro V2 leader Opus 5 99.4%. Prompt's numbers do not match Nov 2026 boards. |
| PR #7144 (22/22 CI, CLEAN, 239 engines) | **FAILED** | PR #7144 is OPEN, `mergeable: CONFLICTING`, `mergeStateStatus: DIRTY`. Not merged, not clean. |
| PR #7080 Docker HARD-51 0/51 | **VERIFIED** | PR #7080 OPEN; its body documents `swe-pro-v2-hard51-receipt.json` at 0.0% cold-start ablation (`load_store()` fails closed by design). This is the honest baseline. |
| `zygote_worker_pool_v1` 1ms CoW forks | **VERIFIED as mechanism, UNVERIFIED as 1ms** | `zygote_worker_pool_v1.py` + `stdlib_cow_test_runner_v1` (`os.fork()` CoW) exist and run (measured 8.5ms for a 2-test suite this session). "1ms" is aspirational; real is ~1.5–8ms. |
| `UnifiedCrossModalPetriNet`, `repo_component_and_cow_engine_v1`, `instant_swe_skill_store_v1` | **FAILED as named modules, VERIFIED as concepts** | 7/1/1 py-file mentions. Live: `repo_component_petri_v1`, `speculative_cow_petri_agent_v1`, `causal_nexus_v1.SkillStoreV2`. |

**Net:** the prompt describes a project that is ~half real. The real project is thinner and more useful: a working K3=0 SWE instrument (`solve_swe_repo_native` verified this session on a real bug), a false agent (cold-start NL → structured call missing), and a false-green oracle bug (see VERDICT doc). Nothing this session is built on phantom names.
