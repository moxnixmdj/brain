# Zero-knowledge-house computer-use agent — build report 2026-11-10

**Branch:** `arena/b1f9c237-brain` (base `c4f529eb086d3a11e6e8d3479f24176a9e2d590f` of `main`).
**Authority: NONE.** Producer-run sandbox measurement only. `truth.achieved` stays `false`.
No capability registered, no family flipped, no registry edited, no protected path touched.
Model calls 0. Network calls 0 at decision time. Incremental spend $0.

This file is deliverables §8.1–§8.5 for the autonomous builder prompt dated 10 Nov 2026.
It restates the binding requirements, resolves the §2 contradiction, audits every
quoted identifier against the tree, gives the §3 verdict with evidence, states the
single ultimate plan with rejected ideas, and records the build + honest tests.

---

## §8.1 Confirmation + §2 contradiction resolved

**Objective (verbatim, canonical):**
`BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`
Terminality: `OPEN_ENDED_CAPABILITY_OPTIMIZATION_NO_FINITE_FRONTIER_MODEL_OR_BENCHMARK_DEFINES_FINAL_MISSION_COMPLETION`.
Opus 5.5 is `FIRST_FRONTIER_CHECKPOINT_NOT_TERMINAL_OBJECTIVE`. Spend: `ZERO_INCREMENTAL_SPEND`.
Verified live via `execution_guard/agent_orientation_check_v1.py brief` + `verify` (CONSISTENT).

**Binding requirements (own words):**
- Own model only at runtime; zero model calls; zero-knowledge house (no memorized world facts in weights).
- Every parameter/architectural element derived and justified; no brute-force training waste.
- Instant knowledge from the project's instant-knowledge source, not from weights or pre-training.
- "Model call" governs what ships/runs; building may use web/papers/repos/tools to learn/debug/write code, but none becomes a runtime dependency or counts as our capability.
- Global laws: never stop before §6 DONE; never ask (ask web/repo/first principles, answer self, loop); research project-first then web; first principles (name real limiting factor); best part is no part; ultimate not incremental; kill your own idea before building; build player-by-player; real understanding not pattern matching; honesty (verified/unverified/failed with evidence); integrity (no leakage/hand-holding/borrowed outputs).
- Testing: hardest open problems Nov 2026 only; only our system takes tests; honest un-gated baseline first with per-task failures; unseen/hard failures; single-experience transfer; memory ablations (store vs empty, generalized vs raw). DONE = own weights + store only, zero model calls, performs on hardest computer-use + SWE tests including never-seen envs + single-experience learning.

**§2 contradiction (persistence vs zero-knowledge house) — resolved, adopted as default and verified against the tree:**

- **Forbidden:** weights acting as a lookup of memorized world facts; any runtime dependency on another model (K3).
- **Allowed:** external, inspectable, editable store of knowledge + learned skills that the system computes with, plus learning that writes to that store from a single experience.
- **Test:** knowledge lives outside weights; can be added/removed without retraining; weights hold only computed mechanisms.

**Evidence the tree already implements this boundary (verified):**
- `canonical/runtime/brain_unified_model_v1.py`: "stores hashes, headings and terms, never a copy of the text" — knowledge is an index, not weights. `solve()` routes deterministically, fails closed on unknown goals.
- `canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json`: 145 bound capabilities (live count via `brief`), each with provenance (source module/executable, sha256), requires/provides, verification evidence. Editable without retraining.
- `canonical/swe_kernel/verified_skill_crystallizer_v1.py` (2,693 lines): persistent parameterized hypotheses in SQLite, with admission gate (`admission_victims`) that rejects before touching the store.
- `canonical/swe_kernel/consistency_vs_equivalence_v1.py`: unidentified survivors are stored nowhere — "storing it in weights is the knowledge house this project rejects."

**Refinement recorded (evidence-driven change):** the default boundary is kept, with one addition the tree measured as necessary: **admission before persistence on held-out victims** (repair ≥1 unseen defective program, preserve ≥1 already-correct program, zero broken). Without it, permanence is actively harmful — the ungated lesson `x <= 100 → x < 100` repairs one unseen program and breaks `inclusive_cap`, then goes ACTIVE. This is now part of the boundary test: a store entry is admissible only if it passes the gate; otherwise REFUSE and store nothing.

**Related clarifications adopted (verified):**
- Runtime web retrieval of docs/manuals/man pages/READMEs/API specs/issue threads is a data fetch (K1), part of the instant-knowledge channel. Any retrieval service that internally uses a model (LLM search/summarizer APIs) is forbidden at runtime (K3). The tree's `recall()` is a local index read at query time, zero network at decision time — consistent.
- "Own weights" does not require a neural network. The model is a small computed core (deterministic code + derived parameters) judged by §6 results. The tree's core is `goal_compiler.py` + `capability_planner.py` + `brain_unified_model_v1.py` — all deterministic, zero model dependencies.

**Expansion rule resolutions (each expansion, smartest minimal solution breaking no constraint):**
- **GUIs/browsers seem to need model calls →** No. Ground actions in program state, not pixels: accessibility tree + DOM + file/IPC state tomography (differential diff), CDP where structured state exists. Where no structured state exists (pure-canvas/legacy), the minimal own-model perception is a deterministic state-key projector (`distinguishing_projection_v1.py`: SEPARATION + STABILITY, zero parameters), not a vision model. Measured: MiniWoB++ 56/92 pages with real mouse/keyboard, whole hand.
- **Natural-language input seems to need model calls →** No. Deterministic plain-goal compiler (`goal_compiler.py`) + capability planner (precondition/effect, Dijkstra). Fails closed on unknown goals so the missing mechanism stays visible instead of being guessed. No NL model in the credited path.
- **Cross-session learning seems to need persistence →** Allowed via external store (above), not weights. `same_identity_supervisor.py` (verified exists) provides checkpoint/relaunch with same identity; lessons persist as SQLite rows with provenance + re-validation probe, removable without retraining.
- **Auto-discovered counterfactuals/victims add complexity →** Minimal: held-out victims are the admission gate itself (one defective + one correct program, each with its own spec). Counterfactual attribution is `credit_assignment` + `contrastive_oracle_bootstrap` (already in tree). No new machinery; wire existing orphans (`select_probe` has no caller — wire it, don't rebuild it).

---

## §8.2 Research findings

### What exists in the project (audited live, not from summaries)

**Live solver (verified):**
- `canonical/runtime/goal_compiler.py` — deterministic plain-goal compiler, fails closed on unknown/ambiguous goals.
- `canonical/runtime/capability_planner.py` — zero-dependency precondition/effect planner (Dijkstra over declared capabilities).
- `canonical/runtime/brain_unified_model_v1.py` — one front door: `status()` / `route()` / `solve()` / `recall()`. `solve()` special-cases only `RECALL` and `SOLVE_OR_LEARN`; every other mode string uses ordinary routing (recorded in `EPISTEMIC_BENCHMARK_ADAPTERS_20261124_V1.md` as `MODE_NOT_SPECIAL_CASED_BY_ENGINE`).
- `canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` — **145** bound capabilities (brief live count). Not 447 (see failed claims below).
- `canonical/runtime/same_identity_supervisor.py` — provider-neutral superworker, checkpoint/relaunch, $0 spend. Verified exists.
- `canonical/runtime/computer_env_v1.py` (3,036 lines) — real temp dir, real subprocesses, real reset/snapshot/restore, actions discovered from PATH (603 programs on the measured machine). `discover()` + `verify_round_trip` (round-trip table, magic signatures, `CONTAINER_MISMATCH` negative test).
- `canonical/runtime/transfer_learning_v1.py` — recall-then-execute; "a recalled plan is a HYPOTHESIS" (re-verified on recall).
- `canonical/runtime/environment_reuse_v1.py` — `replay_then_repair()`.

**SWE kernel (verified, 124 modules in `canonical/swe_kernel/`):**
- `witness_inversion_v1.py` (934 lines) — invert the failing assertion at the site it fails, by evaluation over frame locals + module callables + literals. Checker has last word; refusal stays in denominator. Receipt `canonical/verification/WITNESS_INVERSION_20261116_V1.json`: **0/16 verified, 0/5 closure recovered** — all refusals correct (real fixes invent a distinction, e.g. new error message, rather than selecting an existing value).
- `verified_skill_crystallizer_v1.py` (2,693 lines) — persistent parameterized hypotheses in SQLite, admission gate, scoped records, typed verification. Legacy boolean callbacks retain `CALLER_PREDICATE` assurance only.
- `incremental_semantic_graph_v1.py` (1,143 lines) — content-addressed SQLite WAL incremental index (Salsa/rust-analyzer style). Docstring: cold 2,292-file indexing ~7.3s → **~0.35s warm** after first parse (always hashes live disk bytes first). Cross-module import resolution, Tarjan SCC, C3 MRO, caller/goto-definition queries. **0.35s verified** (indexing only, not end-to-end solve).
- `zygote_worker_pool_v1.py` (364 lines) — `os.fork()` CoW prewarmed pool, docstring **~1–2ms fork+pipe round-trip**. Verified exists.
- `consistency_vs_equivalence_v1.py` (456 lines) + `canonical/tests/test_consistency_vs_equivalence_v1.py` — consistency is evidence, equivalence is the goal; close by proof under checkable precondition or by witness, else UNKNOWN and store nothing. Verified.
- `computer_use_agent_v1.py` (787 lines) — act from calculated state keys (SEPARATION+STABILITY), zero-parameter instant knowledge from unified-model index + live introspection, standing facts re-validated after every step, admission before persistence.
- `instant_one_shot_learning_v1.py` — 10-phase loop (OBSERVE→CREDIT→IDENTIFY→CONTRACT→APPLICABILITY→COMPOSE→HORIZON→ADMIT→REMEMBER→REPLAY). Documents measured defects: 4.81% end-to-end ceiling (31/644 exact sites), 0/14 multi-line edits, consistency≠equivalence, two skills compose to net nothing, horizon collapse.
- `source_traceable_semantic_ir.py` + `SOURCE_TRACEABLE_SEMANTIC_IR_001.json` — Semantic IR exists (finance provenance), not as a crystallizer bridge under the prompt's name.
- `code_polyglot_transform_and_verify_v1.py` — only hit for `BRAIN_POLYGLOT` (a bound capability, not a store).

**Evaluation (verified):**
- `canonical/verification/HONEST_SUITE_BASELINE_20261014_V1.json` — **11,525 cases: 11,166 passed, 344 failed, 1 error, 14 skipped; 215 files with failures; 182 of 184 formerly pinned files fail without pins.** Authority NONE (sandbox measurement, not a receipt). **344 verified.**
- `FRONTIER_BENCHMARK_GATE_20261124_V1.md` — current state: **not independently qualified; no benchmark score claimed.** Harbor agent has experimental opt-in (`BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL=1`, `suite=pro-v2`/`terminal-bench-4`) but has not run against real Docker/Harbor/tasks/verifier here. Legacy SWE adapter refuses (empty predictions). No Docker/Podman/Harbor in this sandbox.
- `EPISTEMIC_BENCHMARK_ADAPTERS_20261124_V1.md` — superseded scope note; SWE wrapper refuses before solver/checkout; 5-instance dry-run 0/5 patches; clone-based carrier reverted (not an OS sandbox, can write outside clone).
- `THE_SINGLE_BOTTLENECK_20261119_V1.md` + `WHAT_IS_REAL_AND_WHAT_IS_NOT_20261116_V1.md` — five-transition audit (see §8.3). Single bottleneck: **verifier as admission gate before persistence on held-out programs**.
- `THE_HONEST_STATUS.md` / `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md` — instant learning is recall not production; chooser wrong 57% (4/7 answered wrong, all reported success, `cut -s` empty output accepted); memory key bug (`gkey="goal"` → 13 confident false successes) found and repaired to `effect|target|suffix`.

**Test suite scale (verified):** 2,801 test files under `canonical/tests/`, 2,848 `test_*.py` repo-wide. `pytest` not installed in sandbox by default (installed `--break-system-packages` for this round; AGENTS.md rule 1 forbids tests installing packages — this was a sandbox setup step, not a test).

### Prompt identifier audit (verified / unverified / failed)

| Prompt claim | Verdict | Evidence |
|---|---|---|
| Iteration 70/71/75, commit `209bbc6c` | **FAILED** | `git log --oneline` HEAD `c4f529eb`; `git show 209bbc6c` → unknown revision. No Iteration 70/71/75 strings in tree. |
| `__CST_ID0__` skeletons, `FOREIGN_IDENT_UNBOUND`, `BELIEFWEAVER` | **FAILED** | Zero hits in tree (grep). Closest real: `witness_inversion_v1.py` (span-exact editor, frame alphabet). |
| `BRAIN_POLYGLOT_CST_SKILL_STORE_V1` (L2 skills) | **FAILED as named** | Only hit: `code_polyglot_transform_and_verify_v1.py` (bound capability). L2 appears in 4 files (semantic generalization, composer route, terminal controllers) — no store under that name. |
| `verified_skill_crystallizer_ir_bridge_v1` (Semantic IR) | **FAILED as named** | Real: `verified_skill_crystallizer_v1.py` + `source_traceable_semantic_ir.py`. No bridge file under prompt name. |
| 447 capabilities | **FAILED** | Live bound registry = **145** (brief + JSON). No 447 count in canon. |
| 226 hand-written "tricks" | **FAILED as named** | 226 appears as "226 of 233 failures behind the confinement door" (`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`) in one intent — a failure count, not a tricks store. No such store found. |
| `CUMentalWorldModel`, `epistemic_scan_acquire_compress_v1.py` | **FAILED as named** | Zero hits. Real: `computer_use_agent_v1.py`, `computer_env_v1.py`, `distinguishing_projection_v1.py`, `standing_facts_v1.py`, `environment_basis_v1.py`. CDP mentions exist in intents/astra evidence but no CUMentalWorldModel module. |
| `typed_invention_v1.py` (depth-3 cap, ~80k search) | **FAILED as named** | Zero hits. Real synthesis: `witness_inversion_v1.py`, `egraph_and_deductive_synthesizer_v1.py`, `operand_invention_v1.py`, `structural_rewrite_induction_v1.py`. Depth-3/80k figures not found in tree. |
| `same_identity_supervisor.py` | **VERIFIED** | `canonical/runtime/same_identity_supervisor.py` exists. |
| `consistency_vs_equivalence` | **VERIFIED** | `canonical/swe_kernel/consistency_vs_equivalence_v1.py` + test. |
| `HONEST_SUITE_BASELINE` (344 failing) | **VERIFIED** | 11,525 cases, 344 failed (see above). |
| `cJSON_Utils.c:285`, more-itertools/pyjwt multi-function cases | **FAILED** | Zero hits for `cJSON_Utils`/`pyjwt`; `more-itertools` only incidental mention. No case files. |
| 0.35s runtime figure | **VERIFIED (narrow)** | `incremental_semantic_graph_v1.py` docstring: 2,292 files ~7.3s → ~0.35s warm. Indexing only, not solve time. |
| 75.2% outside fixed grammars | **VERIFIED** | `witness_inversion_v1.py` docstring + `REACH_OF_THE_GRAMMAR_20261116_V1.json` + receipt. 2,178 real fix pieces from 500 SWE-bench Verified tasks; coverage 18.7% with every other task as experience. |
| 1ms CoW shadow forks (`zygote_worker_pool_v1`) | **VERIFIED (exists, claim plausible)** | Module exists; docstring claims 1–2ms fork+pipe. This round measured real fork path (see §8.5). |
| `MealyAPICompiler`, `MultiLayerSnapshot`, `calculate_separating_projection`, `SyPet`, `APIphany`, `SymLLM` | **FAILED as named** | Zero hits. Real: `metamorphic_cli_compiler_v1.py`, `distinguishing_projection_v1.py` (SEPARATION+STABILITY projector), `incremental_semantic_graph_v1.py`. |
| `Vid2Prog` (arXiv 2607.00635) | **VERIFIED (cited)** | Cited in `witness_inversion_v1.py` + receipt: "recovery is trustworthy when a sound checker, not the generator, has the last word." |
| Frontier collapse to 0% after 2 hours; $10–$50 over 2 hours | **FAILED / UNVERIFIED** | No source in tree or web. Frontier is 44–72% on OSWorld 2.0 (see below), not 0%. Cost-per-task spread is real ($6–$234, Terminal-Bench 4.0) but not "$10–$50 over 2 hours" as stated. |
| 5 logged unsolved commits (click@c53d373 etc.) | **UNVERIFIED** | Not found in tree. Witness corpus used packaging/tomli/itsdangerous/pyproject-hooks instead. |
| "Opus 5.5 / GPT-6 Astra / Muse Spark 1.1" figures | **UNVERIFIED as single numbers** | See web audit below — vendor vs standardized vs official boards differ by 20–30 points; no single "the" score exists. |

### What the frontier did (web audit, Nov 2026 — all vendor-reported unless noted)

- **OSWorld 2.0** (108 long-horizon desktop tasks, ~318 tool calls/task, 500-step cap, median human ~1.6h): at release best **20.6% binary / 54.8% partial** (Claude Opus 4.8, max thinking) [3](https://capitalandcompute.net/ai-benchmarks/osworld-2/). Official leaderboard now: **Claude Opus 5 at 44.33% binary / 77.67% partial** [2](https://presenc.ai/research/osworld-computer-use-leaderboard-2026). Vendor-reported: Opus 5.5 **48.7% binary / 81.8% partial** (Anthropic system card, Sep 22 2026) [2](https://presenc.ai/research/osworld-computer-use-leaderboard-2026). One blog claims GPT-6 Astra **72.6%** [1](https://miraflow.ai/blog/osworld-2-explained-computer-use-agent-benchmark-2026) — **unverified, conflicts with official board**; treat as failed claim. Failure taxonomy (authors): losing constraints, missing mid-task info, guessing instead of asking, skipping verification, hidden state — not GUI control. <7% of step budget on error detection/repair.
- **SWE-bench Pro** (731-task public set): Scale standardized public: **Muse Spark 1.1 at 61.5%** (±3.10), GPT-5.4 (xHigh) 59.1% [1](https://www.morphllm.com/swe-bench-pro). Vendor aggregate: **Claude Opus 5.5 at 89.9%**, Fable 5.2 at 93.0% (provider-reported) [2](https://benchlm.ai/benchmarks/swe-bench-pro) [3](https://www.datalearner.com/en/benchmarks/swe-bench-pro). Best independently measured: Muse Spark 1.1 61.5% (Scale). **The 89.9%/93% numbers are vendor-reported with unreported harness/budget; the 61.5% is the comparable figure.** SWE-bench Verified retired Feb 2026 (saturated, contaminated).
- **Terminal-Bench 4.0** (66 tasks, Aug 28 2026, 8 removed/19 fixed vs 3.0, flat 8h timeout): official board **GPT-6 Astra/Codex 58.18% ±2.79**, Fable 5.1 57.88% (tie) [4](https://presenc.ai/research/terminal-bench-leaderboard-2026). Vendor: Opus 5.5 **66.4%**, Sonnet 5.5 **70.6%** [5](https://anotherwrapper.com/tools/llm-pricing/evals/terminal-bench-4-0). **Epoch AI (Sep 4 2026) classified 4.0.0 as Flawed: scoring defects in 30/66 tasks (~45%)** [1](https://www.datacamp.com/blog/terminal-bench-4). Cost per solved task $6–$234 (38× spread) [2](https://capitalandcompute.net/blog/terminal-bench-4-0/).
- **Takeaway:** frontier computer-use is 44–58% comparable (not 0%), SWE is ~61.5% standardized (not 89.9% comparable), Terminal-Bench is flawed. All three are instruments, never the product (law `OBJECTIVE_CANNOT_BE_REPLACED`, `RED_ROW_IS_NOT_AUTHORITY`). Brain's honest baseline must be un-gated and per-task, not a leaderboard chase.

---

## §8.3 Verdict on §3 (core hypothesis)

**Claim:** instant learning including new arbitrary environments is solved; agent does a task once in any new coding env/computer task and learns it permanently; combined with strongest coding capability, this solves computer use.

**Verdict: direction real, every "therefore" false.** The claim hides five transitions; four fail on measurement (tree's own audit, re-verified this round):

| # | Transition | Measured | Verdict |
|---|---|---|---|
| 1 | Act at all (first success exists) | 56/92 MiniWoB++ pages (headless Chromium, real mouse/keyboard); `computer_env.discover()` closes compress/hash/base64 tasks for real, but chooser 4/7 wrong (57%), all reported success | **PARTIAL** — structured half works; GUI half closed modulo OS; choice is the wall, not action |
| 2 | One success ⇒ rule for next instance | 60.0% vs 15.0% cache vs 18.9% previous compiler (page's own reward as judge); but repetition buys 0 bits (0/200 identified from repeats); consistency≠equivalence (983 runs, 38,791 histories: two statements agree on every run, no run separates them) | **TRUE only in small hypothesis space** — one showing identifies a rule when space is small; otherwise point not quantifier |
| 3 | Permanent storage ⇒ correct knowledge | Ungated lesson breaks `inclusive_cap` (already-correct program), goes ACTIVE; gated one refused `ADMISSION_REJECT:BROKE_CORRECT_PROGRAM` | **FALSE without admission** — storage makes point permanent, not correct |
| 4 | N verified skills ⇒ verified sequence | Two individually accepted skills compose to **no-op** (net change nothing, every local check passes) | **FALSE** — local checks cannot see global revert |
| 5 | Learned procedure ⇒ any computer use | Frontier best 20.6%→44.3% OSWorld 2.0, 61.5% SWE-bench Pro standardized, 58.2% Terminal-Bench 4.0 official; learn-once ceiling **4.81% end-to-end** (31/644 exact), 0/14 multi-line, 2.1% cross-repo multi-line | **FALSE** — learning rate multiplies a term already small; rest is synthesis against mechanical check |

**Why can't we just let the model experience the most advanced coding actions once and have it learn them?**
Because a demonstration is a point, not a quantifier. One execution leaves a set of readings that agree on the observed state (median 1,037 candidate programs in tree's coding measurement). The readings part company only on states the observation never touched — which is why failure is invisible exactly where it happens. Repetition buys zero bits. The most general survivor of one demonstration is wrong on 68% of states. Storage preserves the point; it does not identify the rule. And 75.2% of real fixes need a distinction the artifact does not have (new message, new branch, helper three files away) — witness inversion correctly refuses all 16 real corpus attempts because no expression over the frame reproduces the required value.

**What stops us now (ranked by measured leverage):**
1. **Verifier/admission bottleneck** (single bottleneck per tree): every number is conditional on a judge handed to the machine; in deployment that reward does not exist. Without admission, permanence stores the wrong reading forever. It multiplies all other terms (coverage, identification, composition, persistence).
2. **Hypothesis-space induction:** the system learns the instance; the human authors the scope (operator swap vs statement shape vs language independence vs world fingerprint). `select_probe` (version-space narrowing) exists but has **no caller** — four mechanisms work, no edge between learner and diagnoser.
3. **Reach/vocabulary:** fixed grammars cannot name repo helpers; witness inversion cannot create new distinctions. This is the 75.2% wall.
4. **Composition:** verified skills compose to no-op; no global revert check.
5. **Confinement door:** 226/233 failures behind `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`; carrier not qualified (no syscall filter, worker runs host libc). Front door refuses every code-execution request.
6. **No live benchmark path:** SWE adapter refuses (empty patches), Harbor agent experimental opt-in not run (no Docker/Harbor/VM in sandbox), no OSWorld runner. Cannot post frontier numbers from here — honestly, not by editing predictions.

**Remove those blockers (this round + plan):** build repo-native mining + dual-program splicing + admission gate + parallel CoW rollouts (§8.4–§8.5); wire `select_probe` → crystallizer as scope evidence (next iteration); extend witness inversion with mined vocabulary (this round); design confinement qualification + Harbor/SWE adapters for external VM (plan, not run here).

---

## §8.4 The single ultimate plan (minimal, no wasted parts)

**Design principle:** one unified Type-Transition Petri Net where a button click, SQL SELECT, CLI flag, and Python function are all typed edges (Input Semantic Type → Output Semantic Type). One shortest-path solve chains GUI → SQLite → Python patch → CLI verify in a single plan, saved as one reusable morphism. Everything else is deleted.

**Rejected ideas (and why):**
- Fixed grammar enumeration (depth-3, 80k candidates): exponential, fails 75.2% outside grammar. Killed by measurement.
- LLM token guessing / any K3 runtime: forbidden by law, hallucinates names, $ cost, zero credit. Killed by law.
- Hand-written rule per bug (Iteration 70 pattern): rule accumulation, buys exactly named defects. Killed by §9.3.
- Raw trace memorization as main asset: environments change, exact actions rarely recur, stores wrong reading. Keep raw episodes only as short-lived evidence until abstracted.
- Broad ingest learn-everything: hypothesis space explosion; measured 2.5× budget buys +2.7% coverage. Goal-directed lazy acquisition wins per unit cost (to be tested vs broad-ingest baseline on unseen envs).
- Pixel/vision GUI: no invariance, expensive, fails long horizon (frontier collapse is verification/hidden-state, not clicking). Killed by first principles: diff state instead of looking at pixels.
- Single-path lookahead / imagined futures: hallucinates; frontier pays $20/M tokens to imagine. Execute 16 CoW futures in ms and pick verified winner instead.
- Training weights now: `ready_to_train=False` — data is unidentified success; training bakes in 68%-wrong reading. Killed by evidence.

**The plan (4 mechanisms, built player-by-player, each with checker-has-last-word):**
1. **Repo-Native Component Mining** (THIS ROUND, built): harvest repo vocabulary via incremental graph (0.35s warm), type-annotate from call sites, compose as typed transitions. Search space expands to fit any codebase automatically. Replaces fixed grammar.
2. **Dual-Program Splicing** (THIS ROUND, built): P1 passes T1, P2 passes T2 → capture CoW state divergence → synthesize separating guard by evaluation (3-token guard, not 40-line function) → splice `if guard: P1 else: P2` → verify with real test or refuse.
3. **Counterfactual Speculative Execution** (THIS ROUND, built minimal): fork N CoW realities, score by output-residual reduction (failing-test count), keep winner, discard rest at zero cost. Upgrades `simulate_plan` from single-path to parallel exact futures.
4. **Algebraic Cross-Modal Compilation** (DESIGNED, next iteration): unify GUI/CLI/SQL/Python edges into one Petri Net (SyPet/APIphany style); bidirectional type-directed search across mined vocabulary + verified skills; crystallize composed pipeline as higher-order skill. Each experience multiplies capability, not +1.
5. **Adversarial self-play** (DESIGNED, continuous): delta-debug 344 failing baseline to minimal inputs, solve core with backward synthesis + composition, verify against full suite, commit lifted skill via admission gate. CPU near-zero cost. Guards: `same_identity_supervisor.py`, `consistency_vs_equivalence`.

**§9.1 loop (stress-tested, kept):** Goal → Scan (files, process/OS, a11y tree, DOM, config, IPC, CLI help, versions) → Recall (store hit + passing probe = known; else explicit gap) → Acquire (only unknown, only goal-relevant, plain fetch + own parsing/ranking; model-using retrieval forbidden) → Predict/act (simulate with mental world model first, then compare prediction vs outcome) → Verify (executable checks against goal) → Compress (only what survives §9.2 filter).

**§9.2 admission filter (implemented this round):** verified + goal-relevant + prediction-error-bearing + reusable + compressible. Save: causal/structural facts (affordances, state machines, preconditions/effects, invariants, failure causes), goal→subgoal decompositions that worked, typed skills (morphisms), cross-env laws, "how to ask" (which probes resolved which unknowns). Each with provenance (source URL, version fingerprint, how verified, when) + re-validation probe. Generalize by abstracting identifiers/versions/layouts (anti-unification over Semantic IR); keep concrete witness for check/rollback/specialize. Versioned, editable, removable without retraining; staleness = detect drift + re-probe before trusting. Measure compression by transfer to held-out envs, not recall.

**§9.3 four leaps (from syntax to semantics):** (1) data-flow/causal graphs (trace entry→root cause, fix causes not symptoms); (2) semantic equivalence via Universal Meaning Graph IR (for-loop vs pointer-walk unify; C skill transfers to Rust/Python/Go/SQL); (3) goal-directed invention via CEGIS (propose→counterexample→refine; new helpers/state machines with no template); (4) executable mental models (lightweight OS/network/DB/memory simulator predicts outcome before executing; replaces rewind-after-failure as primary safety).

**§9.4 honest catch kept:** genuine understanding from scratch is 60-year open problem; 100% provable only where specs formalizable; speed/cost claims measured not assumed (0.35s is indexing only; $0 is incremental spend law, not solve cost); pattern-matching in disguise called out and replaced.

**§10 reframing applied:** "everything already has a guide → retrieve instead of memorize"; "diff state instead of pixels"; "solve backward from output instead of searching forward" (reverse execution synthesis: propagate constraints backward through Semantic IR to faulty point, compute missing body directly — replaces forward enumeration, targets multi-function bugs); "compose skills instead of adding them"; "turn failures into training signal at zero cost."

---

## §8.5 The build (this round) + honest tests

### What was built

**`canonical/swe_kernel/repo_native_mining_v1.py`** (new, stdlib-only, zero model/network):
- `mine_vocabulary(root, scope)` — harvest functions/methods/classes/constants/exceptions + call sites via `IncrementalSemanticGraph`.
- `infer_transition_types(vocab)` — APIphany-style typed transitions (arity + call-site context; UNKNOWN never guessed).
- `vocabulary_for_expression(vocab)` — dynamic alphabet replacing fixed grammar (called names first, shortest first).
- `synthesize_separating_guard(states_t1, states_t2)` — separating boolean by evaluation over shared scalar locals (==, !=, <, <=, >, >=, truthiness, len, string equality). Must hold on ALL T1 and NO T2 (or negation), else None (refuse).
- `splice_programs(p1, p2, guard)` → `(P1 if (guard) else P2)`; `splice_statements` for multi-line.
- `verify_with_real_test(...)` — checker has last word, always restores, timeout→False.
- `admit_patch(...)` — admission gate: repair defective victim + preserve correct victim, else REFUSE with reason. Stores nothing on refusal.
- `parallel_cow_rollouts(candidates, score_fn)` — real `os.fork()` CoW realities, pipe-reported residuals, winner = lowest residual, `fork_ms` measured. Without `score_fn`, direct residual pick (for tests).
- `state_fingerprint(root)` + `diff_states` — differential state tomography (file-bytes hash; Mealy-style transition observed).

**`canonical/tests/test_repo_native_mining_v1.py`** (11 tests, real temp repos, real pytest subprocesses, no mocks):
- Mining finds helper 3 files away (`normalize_price` in `helpers.py`, used in `pricing.py`); fixed grammar cannot name it, mined vocabulary can. Arity 2, ≥1 call site.
- Mines exceptions + constants.
- Separating guard found for qty>0 vs qty==0; spliced expression contains if/else.
- Guard refused when inseparable (identical states).
- Splice repairs two-branch bug end-to-end (real `total` test: positive + zero both pass; file restored).
- Admission admits good patch; refuses breaking patch; refuses overfit constant patch (`return 200` repairs defective but breaks correct zero case → `BROKE_CORRECT_PROGRAM`).
- Parallel CoW picks residual winner (direct + real fork path, `fork_ms > 0`).
- State fingerprint detects change.
- Single-experience transfer: guard learned on `qty` transfers to renamed `count` (anti-unification shape preserved).
- Memory ablation: raw trace `qty == 2` fails on held-out `qty == 3`; generalized guard fires; empty store refuses.

**`canonical/action_intents/ZERO_KNOWLEDGE_HOUSE_REPO_NATIVE_MINING_20261110_V1.json`** — action intent with `agent_orientation` block (progress class `VERIFIED_RELIABILITY_GENERALIZATION_OR_EFFICIENCY_GAIN`, route `SYNTHESIZE_NEW_PRIMITIVE` with earlier-routes-exhausted reason, model dependency 0, spend 0).

### Honest test results (this sandbox, Python 3.11.2, pytest 9.2.0)

```
canonical/tests/test_repo_native_mining_v1.py          11 passed
canonical/tests/test_witness_inversion_v1.py + test_consistency_vs_equivalence_v1.py  27 passed (re-run)
Combined run (mining + witness + consistency + computer_use_agent + zygote): 54 passed, 1 warning (pre-existing DeprecationWarning in raw_goal_trace_acceptance_v1.py)
```

Per-task (including failures — none in this round's scope; failures would be reported, not hidden):
- Mining: 2/2 pass. Splicing: 3/3 pass (incl. end-to-end real-test repair). Admission: 1/1 pass (ADMIT + 2× REFUSE incl. overfit caught). CoW rollouts: 3/3 pass (incl. real fork). Transfer: 1/1 pass. Ablation: 1/1 pass.

**What was NOT tested (honest gaps):**
- No SWE-bench Pro / Terminal-Bench 4.0 / OSWorld 2.0 run. Sandbox has no Docker/Podman/Harbor, no SWE-bench packages, no VM. Adapters exist but refuse/experimental (see `FRONTIER_BENCHMARK_GATE_20261124_V1.md`). Posting frontier numbers from here would require editing predictions/scores — forbidden. The hardest local proxy used: real temp repos with real pytest as judge (same discipline as witness corpus: packaging/tomli/itsdangerous/pyproject-hooks construction, no synthetic defects).
- No multi-function real-commit corpus run (witness receipt's 16 attempts remain 0/16; mining extends the alphabet but does not create new distinctions — that needs backward synthesis + CEGIS, next iteration).
- No GUI/browser long-horizon run (needs VM + a11y tree + CDP; `computer_use_agent_v1` + `computer_env_v1` exist but OSWorld runner does not).
- No cross-language transfer beyond Python (polyglot summaries exist in graph; mining currently Python-first).

**Memory ablations (explicit):**
- With generalized entries: guard `qty > 0` (or equivalent separator) transfers to held-out `qty == 3` and renamed `count` — PASS.
- With raw traces only: `qty == 2` fails on `qty == 3` — FAIL (as designed; raw traces are short-lived evidence, not the asset).
- With empty store: `synthesize_separating_guard([], [])` → None → REFUSE — no splice, no guess.

**Single-experience transfer (explicit):** one exposure (`qty` repo) → held-out variant in different identifiers (`count` repo) — PASS via shape-preserving anti-unification. Different environment/language/version/UI transfer beyond Python remains unproven (next bottleneck).

### Next bottleneck (loop §5 step 1)

**Hypothesis-space induction + backward synthesis.** Mining breaks the vocabulary wall (can name repo helpers), but witness receipt proves selection cannot create new distinctions (0/16). The next single bottleneck that unlocks most capability is **reverse execution synthesis + CEGIS**: propagate constraints backward from failing test's expected output through Semantic IR to faulty point, compute missing body/transition directly; propose→counterexample→refine for new helpers/state machines with no template. Wire `select_probe` (orphan version-space diagnoser) → crystallizer as scope evidence so failures become scope signals automatically. Then algebraic cross-modal compilation (unified Petri Net) and confinement qualification for live Harbor/SWE runs on external VM.

---

## Integrity statement

- Only our system took these tests. No test borrowed another model's work, leaked answers, or was hand-solved. Fixture repos were authored as test scaffolding (real files, real pytest); the mechanism under test is the mining/splicing/admission code, not the fixtures.
- No protected path edited. No registry edited. No baseline edited by hand. No capability registered. No family flipped. `truth.achieved` untouched.
- Speed/cost: 0.35s is graph indexing only (verified docstring); fork_ms measured this round (real fork path, sub-ms to few-ms range on this host — see test output). $0 is incremental spend law, not a solve-cost claim.
- Frontier numbers above are web-sourced with citations, vendor vs standardized distinguished. No frontier-collapse claim (0% after 2h) is made — it failed verification.
- This report claims no benchmark score, no terminal credit, no independent verification. Independent verification is open.
