# Confirmation of Requirements & §2 Contradiction Resolution — Wave 47–48

**Date:** 2026-11-26 · **Branch:** `arena/adb67314-brain` · **Base:** `3e652cf2`
**Authority:** NONE__PRODUCER_RUN_SANDBOX. Runtime model calls: 0. Runtime network calls: 0. Incremental spend: $0. `truth.achieved` stays `false`.

## 1. Restatement of binding requirements (in my own words)

I have read all of §§0–11 and the appended Wave 47–48 dossier. The binding constraints are:

- **Mission:** Build our own engine (weights + architecture + agent) that fully solves computer use — any software engineering, GUI, browser, and arbitrary new environment — by the fastest, most optimal mechanisms. Long-term aspiration: a creature-like system that understands.
- **Runtime constraints (what ships):** Own model only; zero model calls at runtime; zero-knowledge house (parameters compute, never warehouse memorized world facts); every parameter/element derived and justified; instant knowledge from the external store already in the project, not from pre-training.
- **Scope of "model call":** Governs what ships/runs. While building I may use web search, papers, repos, and any tool to learn/debug/write code. None of it becomes a runtime dependency or counts as our capability.
- **Global laws:** Never stop before §6 is met; never ask questions (ask the web/repo/first principles, answer myself); research before building (project first, then web); first principles over fashion; Elon's law (remove before adding; everything insanely fast); ultimate solution never incremental; try to kill every design before implementing; build player-by-player; real understanding not pattern matching; honesty (verified/unverified/failed with evidence); integrity (no leakage, no hand-holding, no borrowed outputs).
- **Testing (§6):** Hardest open benchmarks as of Nov 2026 (SWE-bench Pro, Terminal-Bench 4.0, OSWorld 2.0); only our system takes tests; honest un-gated baseline first with per-task failures; test unseen hard failures in never-seen environments; test single-experience learning explicitly (one exposure → held-out variant in different environment/language/version/UI); report memory ablations (store vs empty, generalized vs raw traces). DONE = all of: own weights + instant-knowledge store only with zero model calls; performs on hardest computer-use + SWE tests; includes never-seen environments and single-experience learning. Anything less is progress, not completion.
- **Workflow (§7):** One branch, merge once when complete. No repeated merges.
- **Deliverables (§8):** (1) this confirmation with §2 contradiction resolved, (2) research findings, (3) §3 verdict, (4) single ultimate plan with rejected ideas, (5) build + hard honest tests looping via §5 until §6 is met.

## 2. §2 contradiction (persistence vs zero-knowledge house) — resolution

**Contradiction:** Cross-session learning seems to need persistence; zero-knowledge house seems to forbid it.

**Resolution (adopted, exercised in this build, with evidence):**

- **Forbidden:** Weights acting as a lookup of memorized world facts; any runtime dependency on another model (including open-weight models, vendored weights, self-hosted servers, llama.cpp/vLLM/Ollama/transformers — per `GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md`).
- **Allowed:** An external, inspectable, editable store of knowledge and learned skills that the system computes with, plus learning that writes to that store from a single experience.
- **Test:** Knowledge lives outside the weights, can be added or removed without retraining, and the weights hold only computed mechanisms.
- **Implementation in this tree:** Weights = code (zero parameters). Knowledge lives in plain-JSON/SQLite stores: `CausalLawStore` (UIR laws), `SkillStoreV2` (tree-rewrite morphisms), `NegativeInvariantStore` (refutations), plus Petri net and `RelationalActionStore`. Each entry carries provenance (source URL, version fingerprint, how verified, when) and a re-validation probe, is removable in O(1), and is admitted only if it was executed, changed state, and passed the §9.2 filter (verified, goal-relevant, prediction-error-bearing, reusable, compressible). The test passes: add/remove knowledge without retraining; mechanism unchanged.

**Related defaults adopted (verified):**

- Runtime web retrieval of docs/manuals/man pages/READMEs/API specs is a data fetch, not a model call, and counts as part of the instant-knowledge channel. Any retrieval service that internally uses a model (LLM search/summarizer APIs) is forbidden at runtime. Use plain fetch + our own parsing/ranking. (This build uses zero runtime network; retrieval is via local index.)
- "Own weights" does not require a conventional neural network. The model is a small computed core (algorithmic engine + derived parameters) judged by results under §6, not architecture fashion. This build's core is `UnifiedModel` + `Creature` + federated kernels: zero parameters, pure stdlib Python.

**Expansion rule applied:** For each expansion (GUIs/browsers, NL input, cross-session learning, auto-discovered counterfactuals), the solution is: retrieve instead of memorize; diff state instead of looking at pixels; solve backward from output instead of searching forward; compose skills instead of adding them; turn failures into training signal at zero cost. No constraint is broken. Where a mechanism turns out to be pattern-matching in disguise, it is named and replaced (see §3 verdict and `WAVE47_48_VERDICT_ON_INSTANT_LEARNING_20261126_V1.md`).

## 3. Claims audit (inputs to verify, not facts)

Every iteration number, commit hash, benchmark name/score, and "Opus 5.5 / GPT-6 Astra" figure in the prompt was treated as input to verify. Full audit in `canonical/verification/AUDIT_THE_PROMPT_CLAIMS_20261124_V1.json` (re-verified this session) and `WAVE47_48_RESEARCH_FINDINGS_20261126_V1.md`:

| Claim | Verdict | Evidence |
|---|---|---|
| Iteration 70/71/75, commit `209bbc6c` | **FAILED** — not a commit, no such engine module | `AUDIT_THE_PROMPT_CLAIMS_20261124_V1.json`: 0/9 commits resolve; `__CST_ID0__`, `FOREIGN_IDENT_UNBOUND`, `BELIEFWEAVER`, `BRAIN_POLYGLOT_CST_SKILL_STORE_V1` exist only as mentions in `audit_the_prompt_claims_v1.py`, not as modules |
| `same_identity_supervisor.py`, `consistency_vs_equivalence` | **VERIFIED** — code files exist | `canonical/runtime/same_identity_supervisor.py`, `canonical/swe_kernel/consistency_vs_equivalence_v1.py` |
| 447 capabilities, 226 tricks, 344 failing, 0.35s | **UNVERIFIED** — appear elsewhere, no single authority | Audit: all 6 figures `UNVERIFIED__APPEARS_ELSEWHERE_TOO`. Honest baseline doc records 11,525 cases / 344 failed on 2026-10-14, but it is a sandbox measurement, not a receipt |
| 1,746 unwired ≥180 LOC (876,219 LOC), 756 open PRs, 100 DARK awakened | **VERIFIED (order-of-magnitude) / FAILED (exact titans)** | This session: 1,783 non-test ≥180 LOC (891,310 LOC), 1,529 unwired non-test (571,476 LOC); 756 open PRs fetched via `gh`. The 20 "unwired titans" in the dossier are **already wired** via `unified_hidden_capability_federation_v1.py` (source_path + dispatch) — see research findings |
| SWE-bench Pro, Terminal-Bench 4.0, OSWorld 2.0 (318 steps) | **VERIFIED** — real, current, hardest open | Web search Oct–Nov 2026: SWE-bench Pro public top 61.5%, Terminal-Bench 4.0 top 64.8%, OSWorld 2.0 top 20.6% binary / 54.8% partial (108 long-horizon tasks). See citations in research findings |
| Agent S4 arXiv:2610.28601 (21.3% OSWorld V2, 3.8×) | **VERIFIED** — real paper, vendor-reported | arXiv:2610.28601, Simular, Oct 2026. Qwen3.8-27B + evolved interfaces 21.3% binary, beating GPT-5.5 13.0% and Opus 4.8 20.6% at 1.5–4.3% cost. Independent caveats noted |
| LaCT/LaCET, Gated DeltaNet-2, MesaNet, delayed supervision | **VERIFIED** — real papers | LaCT arXiv:2505.23884 (ICLR 2026), LaCET arXiv:2604.07350, delayed supervision arXiv:2609.32312 |
| 91.81% precision / 29.45% coverage / 0/4,444 cross-kind | **VERIFIED** — measured in-tree | `WHY_WEIGHT_SPACE_IS_NOT_THE_MISSING_LAYER_20261112_V1.md` + `canonical/verification/WHY_WEIGHT_SPACE_IS_NOT_THE_MISSING_LAYER_20261112_V1.json` |
| PRs #7144 (22/22 CI green), #7071, #7049, #6933, #6857, #7019, #6613, #6605, #4726/#4723 | **VERIFIED as OPEN PRs** (not merged) | `gh pr view` this session: #7144 OPEN (Waves 43–46, 100 cumulative), #7071 OPEN (confinement+effect oracle), #7049 OPEN (minimax interrogation), #6933 OPEN (site-general synthesis), #6613/#6605 OPEN. None merged to `main` at base `3e652cf2` |

No claim was taken on trust. Where the dossier and the tree disagreed (titan wiring), the tree won and the dossier was corrected.

## 4. What I will do (single ultimate plan, minimal)

The bottleneck is **not** "wire 20 more modules" — they are already federated. The bottleneck is that federation is **shallow**: each titan is reachable as an isolated engine with narrow inputs, but `UnifiedModel.solve()` never composes them into the §9.1 loop (Goal → Scan → Recall → Acquire → Predict/Act → Verify → Compress) with a Futamura fast path first.

**Wave 47–48 (this branch):** One thin composition kernel (`wave47_48_titan_unification_v1.py`) + one mixin (`Wave47To48UnifiedModelMixin` subclassing `Wave40To42UnifiedModelMixin`, 0 net LOC in `brain_unified_model_v1.py` except import/inheritance) that:

1. Runs a **0.2 ms Futamura Rung-0 fast path** first (compiled skill store); only novel residuals touch expensive synthesis.
2. Runs **reverse-execution tomography + 1 ms CoW zygote + angelic lens** synthesis for SWE (compute what interior value would make the assertion pass before touching a token; reject edits outside symbol ownership).
3. Runs **universal-meaning e-graph + equality saturation** for equivalence (reason over equivalence classes, not strings).
4. Runs **Agent-S4-style interface evolution + kernel confinement + effect oracle** for computer use (compile apps into APIs; physically impossible to lie about changes).
5. Runs **active-inference refusal curriculum** (every refusal names the exact missing discriminator).
6. Runs **5-timescale sleep crystallizer + DBSP incremental maintenance + anti-manufactured-confidence** for memory (exact O(|Δ|) invalidation, zero write amplification).
7. Runs **meta-circular organ graph + LILO/Stitch compression + GEPA Pareto** behind anytime-valid e-values for self-improvement that cannot collapse.
8. Keeps **K3=0 as sovereign default** (Rungs 0–2); any open-weight proposer is strictly Rung-3, untrusted, gated by confinement + effect oracle + e-graph + mutation falsification + SCoRE e-value, and compiled back to Tier-0 on verify (never pay neural tax twice).

Rejected ideas and reasons are in `WAVE47_48_ULTIMATE_PLAN_20261126_V1.md`.

**Done (§6) is not claimed.** This is progress: a composed, measured, zero-mock pipeline that proves the §9.1 loop end-to-end on real Python repair + interface-evolution tasks, with honest per-task results including failures. §6 remains open until the system performs on SWE-bench Pro / Terminal-Bench 4.0 / OSWorld 2.0 in never-seen environments with single-experience learning — which requires Docker/Harbor/VM infrastructure not present on this host (logged as blocker, work continues on everything else per §1.2).
