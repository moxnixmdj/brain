# FIRST-PRINCIPLES ONE-SHOT PLAN — 2026-10-14 (V1)

## 0. Standing order (binding on every agent, every step, every future plan)

**No agent may call, email, message, or ask any person, benchmark owner, vendor, or community for help, access, evaluation, credentials, normalization, or results — not through Gmail, not through any channel. Outreach is not a valid route to anything in this repository. Nobody will help for free. Every step below is executable by the Brain alone, at $0.**

Encoded as governance: `canonical/governance/NO_EXTERNAL_OUTREACH_OWNER_INSTRUCTION_AND_OWNER_PRIVATE_OBLIGATION_RECLASSIFICATION_20261014_V1.json` (narrows `EXTERNAL_OUTREACH_VALUE_GATE_V1`: the `OWNER_EXCLUSIVE` route class is now forbidden).

## 1. What the goal literally is (no paraphrase)

Checkpoint `OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1` is `terminal_real = true` iff

```
(19/19 families PASS) ∧ (8/8 meta obligations) ∧ (donor V2 requalification)
∧ (aggregate predicate ∧ scheduler root sound) ∧ (global postconditions re-proved)
```

Live gate on 2026-10-14 (`python3 -m canonical.runtime.terminal_reality_gate_v1`): `terminal_real=false`, 7/19 families owned, 12 open, 18/38 atoms proved, donor authority invalidated.

Under the constraints in force: Mission Lock V10 (no general-purpose-model cognition in any credited path — API, local, open-weight, distilled general reasoner all excluded), Cognition Law V4 (unknown provenance fails closed), $0 hard spend, and the standing order in §0.

## 2. First principles: what each open benchmark's output actually IS

Every acceptance row is a number `S = M(X, D)`: a scorer `M` applied to the Brain's outputs `X` over a task set `D`. To "make S real" the Brain must (a) possess `D`, (b) produce `X`, and (c) have `M` applied by whoever the ledger says applies it. Whether that is possible is a property of `(M, D)`, not of effort.

| Row (frozen target) | `D` | `M` | Who executes `M` | Brain can produce `X` under V10? | Verdict |
|---|---|---|---|---|---|
| GDPval-AA ≥ 1846 Elo | 220 tasks (public gold on HF), but **AA's Elo is over AA's private panel runs** | pairwise LLM-judge Elo | Artificial Analysis | `X` = expert deliverables (docs, decks, spreadsheets); no zero-model producer exists | **unproducible**: `M` and the Elo pool are owner-held |
| AA-Briefcase ≥ 1822 (+ ARTIFACT shared measurement) | private | private LLM judge | Artificial Analysis | no | **unproducible** |
| FrontierCode ≥ 54.4 | private held-out | hidden tests | owner | no | **unproducible** |
| CursorBench ≥ 57.8 | private | hidden tests | Cursor | no | **unproducible** (scope proved 10-02; adequacy unprovable) |
| AutomationBench ≥ 40 (private split) | private split | hidden | owner | public split would need LLM agent | **unproducible** |
| Finance Agent v2 ≥ 58.59 / Finance Index ≥ 61 | private (Vals) | private + inner normalization | Vals.ai | no | **unproducible** |
| MysteryMechanism non-inferiority | Anthropic-internal | internal | Anthropic | no | **unproducible** |
| TB4 ≥ 66.36 % (219/330) | public (TB 2.0 tasks, Docker) | deterministic tests | anyone (Harbor) | 1/219 recorded, and that pass is `authored_preverification` with unrecorded cognition provenance → fails closed under V4 | **capability floor** |
| TB-Science (coding family second bar) | public | deterministic | anyone | 0/20; and the planner lineage is a local Qwen/llama.cpp model → non-creditable even if it scored (census F2) | **capability floor** |
| OSWorld-Verified ≥ 81.8 % partial | public, pinned bytes self-fetchable | deterministic | anyone | OSWorld policy lineage is a local Qwen model (census F3) → non-creditable | **capability floor** |
| HLE (tools) ≥ 67.7 % | 2,500 questions, free HF account acceptance (self-service, not outreach) | exact/LLM-match | anyone | no zero-model solver for expert questions exists anywhere | **capability floor** |
| Chartography (tools) ≥ 89 % | 100 tasks, free HF account (self-service) | deterministic | anyone | Brain parser: 0 gold parsed | **capability floor** |

Two facts the table forces:

1. **8 of 12 open rows are owner-executed measurements.** With outreach forbidden, `M` can never run on Brain output. Substituting a public proxy (e.g. GDPval gold-220 + OpenAI's public grader) computes a different `M'`, which the frozen ledger's envelope rule forbids, and the 2026-10-02 reconciliation already replaced the deleted private routes with "scope-complete stronger-proof" obligations that cannot be proved without the owner's evaluator (CursorBench: scope proved, dominance unprovable). This is the **measurement-function theorem** in the governance artifact: those 8 rows are unreachable while the ledger, V10, and §0 all hold.
2. **4 of 12 are public and deterministic, and access costs $0 without outreach** (public `verification-capsule-runner` Actions carrier, 4-CPU standard runners — Docker rejected 8-CPU tasks, 46 TB4 tasks fit ≤4 CPU; free HF accounts for HLE/Chartography; self-service OSWorld bytes). **The blocker is the producer.** Every system that has ever scored on these bars is a general-purpose LLM agent (every Terminal-Bench 2.0 leaderboard entry; SOTA ≈ 82 %, Opus 4.7 ≈ 68.5 %). V10 excludes that producer class. The Brain's deterministic producers score 1 (authored) / 0 / 0 / 0.

## 3. The impossibility result, stated plainly

```
P(terminal_real = true | ledger frozen ∧ V10 ∧ V4 ∧ $0 ∧ no outreach) ≈ 0
```

Not "low." The 8 owner-private rows have **no producing action**, so their closure probability is exactly 0 under §0; the conjunction is therefore 0 regardless of how the other 11 conjuncts go. Any plan that reports a nonzero terminal probability under these constraints is fabricating closure. The previous estimate (P(T≤120 d) ≈ 0.08–0.15) implicitly assumed owner channels; it is withdrawn.

Deleting those rows is not available either: the ledger marks 8 families `NOT_DELETABLE` and records the invariant `ROUTE_DELETION ≠ REQUIREMENT_REMOVAL`.

## 4. The one lever that makes the goal reachable (owner decision — not an agent action)

The 7 families that *did* close all used one route: **a Brain-defined, frozen, finite protocol + a scope-complete/absolute-ceiling proof + independent verification** (AGENCY: theoretical optimum over the frozen six-dimension protocol; TOOL_DISCOVERY: 180/180 + universal scope proof; INSTRUCTION_FOLLOWING: pointwise clean-case dominance over the LiveBench public bar). That route is closed to the 12 open families only because their acceptance basis is an external bar.

**Decision fork (verbatim in the governance artifact):**

- **A. Keep all bars and all laws (default).** Checkpoint unreachable; P ≈ 0 in any horizon. Correct action: stop scheduling family-closure work, redirect to the open-ended real mission with internal instrumentation.
- **B. Amend the acceptance ledger for the 12 open families** — explicit written amendment, naming each row, its new Brain-executable frozen scope-complete protocol, and the envelope-rule exception (same style as V4's permanence clause). Then the proven route applies. Per-family closure probability 0.45–0.80 over weeks, with meaningful capability built along the way. Checkpoint semantics change from "external parity" to "internal protocol parity" — the owner must accept that openly.
- **C. Rescind V10 to allow model cognition.** Rejected: it turns the mission into wrapping a model, and it still does not touch the 8 owner-private rows.

No agent can take this fork. It must be the owner, in writing, in `canonical/laws/`.

## 5. What is real NOW — executed this turn, $0, no outreach

Each step: what it produces, P(success) (calibrated to what the gate actually consumes), impact on the terminal conjunction.

### Step 1 — Zero-model producer-cognition dependency census (EXECUTED)
- Runtime: `canonical/runtime/zero_model_runtime_dependency_census_v1.py` (AST-level; import, endpoint, local-inference, identifier evidence; fail-closed on parse errors).
- Receipt: `canonical/verification/ZERO_MODEL_RUNTIME_DEPENDENCY_CENSUS_RECEIPT_20261014_V1.json`.
- Result over `canonical/runtime` + `execution_guard` (2,116 files): **2,050 CLEAN, 56 string-reference-only, 8 call-level model dependencies, 2 parse errors → exit 2.**
- Material findings (all new, all verifiable by line number):
  - **F1 — `canonical/runtime/astra_runtime.py` still carries a general-model planner.** `_planner_post` (4393–4452, default model `Qwen3.5-9B-M-Q4_K_M-local`, llama.cpp backend) is called four times inside `_run_goal_unstamped` (6454, 6484, 6518, 6575) for next-action selection and final-answer composition. It is only env-gated (`ASTRA_DISABLE_MODEL_PLANNER`, checked by `runtime_cognition_credit_guard_v1.py` and `verify_external_cognition_runtime_lock_v1.py`). Env gating is not removal; `DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V2` requires post-removal qualification with model dependency count 0.
  - **F2 — TB-Science planner lineage (`harbor_science_planner_v1/v5/v6/v7`) is model-dependent** and imported by `harbor_science_agent_v1/v10/v11/v12/v13`. The 0/20 record is not even a creditable failure baseline.
  - **F3 — OSWorld V21 policy lineage (`osworld_v21_qwen35_planner_v1`, `osworld_v21_local_qwen_policy_v1`) is model-dependent.**
  - **F4 — two runtime files do not parse** (`livebench_legacy_predecessor_compiler_audit_v1.py` line 139, `osworld_v21_app_policy_overlay_v1.py` line 152). Any receipt citing them as executed is suspect.
  - **F5 — `root1_contrastive_semantic_candidate_runner_v1.py` posts to a chat-completions route**; zero governance references; must be deleted or quarantined.
- P(success) = 1.0 (executed). Terminal impact: converts 5 unknown dependency facts into known facts on the **donor requalification** conjunct — a conjunct that is required under every branch of the fork, so this work is never wasted. Credit delta 0.

### Step 2 — Owner instruction + reclassification (EXECUTED)
- `canonical/governance/NO_EXTERNAL_OUTREACH_OWNER_INSTRUCTION_AND_OWNER_PRIVATE_OBLIGATION_RECLASSIFICATION_20261014_V1.json`: encodes §0, proves the measurement-function theorem, moves 8 rows `WAKE_GATED → CLOSED_OFF_UNDER_CURRENT_CONSTRAINTS__OWNER_DECISION_REQUIRED`, keeps 4 rows wake-gated on the capability floor, records the fork.
- P = 1.0. Terminal impact: 0 credit; prevents every future plan from re-spending effort on routes that cannot produce `S`.

### Step 3 — F4/F5 repairs (EXECUTED, second pass)
- Both parse errors fixed (`livebench_legacy_predecessor_compiler_audit_v1.py`, `osworld_v21_app_policy_overlay_v1.py`; regex bodies byte-identical, module imports). Dead chat-completions runner `root1_contrastive_semantic_candidate_runner_v1.py` deleted with its test. Post-repair census: **0 parse errors, 7 model-dependent files remain** (`ZERO_MODEL_RUNTIME_DEPENDENCY_CENSUS_RECEIPT_20261014_V2.json`).
- The 7 remaining files are blob-pinned in up to 26 governance artifacts each and used by workflows; removing them is a dedicated rebind change (queue rows 4–5), not a one-shot edit.
- **Truth this exposes:** under V10 the Brain has *no* creditable producer for TB-Science or OSWorld at all — its only producers for those families are the seven model-dependent files.

### Step 3b — Truncated-plan repair (EXECUTED)
- `ONE_SHOT_FRONTIER_EXECUTION_PLAN_20261014.md` line 62 carried a literal `[truncated 9113 chars]` marker (Steps 2.5–9 and §§3–5 lost; history is a single shallow commit, unrecoverable). Marker replaced by an explicit supersession note pointing here.

## 6. The ordered queue after this turn (each $0, no outreach, Brain-executable, with honest numbers)

| # | Step | Output | P(success) | Terminal impact |
|---|---|---|---|---|
| 4 | Delete `_planner_post` + its 4 call sites from `astra_runtime.py` (or split `_run_goal_unstamped` into a deterministic-only path), re-run census to exit 0 on the credited surface, add a unit test that fails on reintroduction | model-dependent count on credited surface → 0 | 0.85 (mechanical; risk = hidden callers in the 77 governance refs) | required for `donor_dependent_required_behaviors_zero` and `final_donor_deletion_cleanroom_pass`; no family credit |
| 5 | Quarantine F2/F3/F5 files into `canonical/quarantine/model_dependent/` with a content-addressed ledger; update the 13 importers to fail closed | credited surface census exit 0 | 0.80 | same conjunct; removes the possibility of a V10-violating receipt ever being credited |
| 6 | Fix F4 parse errors (two mechanical syntax repairs) and run both modules' existing tests if any | parseable runtime | 0.95 | hygiene; unblocks whatever those audits were meant to prove |
| 7 | Donor requalification wave: new independent-runner receipt (`INDEPENDENT_PUBLIC_RUNNER_PASS`) on the public capsule-runner bound to the current `terminal_global_ownership_postconditions_reducer_v1.py` blob; revise the reducer's hard-coded 3352-case wave/TERMINAL_SHA to read the new wave | DONOR_AUTHORITY predicate satisfiable | 0.55 (reducer revision touches pinned blobs across several guards) | 1 of 5 terminal conjuncts |
| 8 | ARTIFACT necessity countermodel (pattern: `COMPOSITION_COMPONENT_SCOPED_PROOF_NECESSITY_COUNTERMODEL_20261006_V1.json`) | may demonstrate ARTIFACT's component-scoped proof is unnecessary, collapsing it into the AA-Briefcase row | 0.40 | if it succeeds, 12 → 11 open obligations (still 0 for the checkpoint under fork A) |
| 9 | COMPOSITION necessity countermodel + clearance of the 4 quarantined channels (#4694) | same style | 0.45 | 12 → 10 at best |
| 10 | 5 meta mapping checks (5 domain certs; Multilingual, Long-context, Creative/Diagram remain) | ROOT1 V6 meta rows | 0.75 each | 8/8 meta conjunct progress |
| 11 | Capability-floor work that is *legal and useful* regardless of the fork: deterministic Chartography parser (chart-type grammar + axis OCR-free SVG/vector extraction where tasks provide vector data), TB4 ≤4-CPU 46-task deterministic attempt on the public carrier with provenance-recorded Brain-authored solutions | scores will be far below bars | TB4 ≤ 10/46 (0.3), Chartography ≤ 20/100 (0.35) | 0 family credit under current bars; real capability under fork B |

Nothing in rows 4–11 closes a family. Under fork A the checkpoint stays at P ≈ 0 after all of them; under fork B rows 4–7 are prerequisites and rows 8–11 become the first real closures.

## 7. Internet research used (no outreach, read-only)

- Terminal-Bench 2.0 leaderboard snapshots (2026-09/10): top-20 all LLM agents; SOTA ≈ 82; Opus 4.7 ≈ 68.5. Conclusion: no non-model system has ever scored on TB — V10's floor is empirical, not hypothetical.
- GDPval gold-220 subset public on Hugging Face with OpenAI's public automated grader (win-rate vs expert deliverable). Conclusion: proxy exists but is a different `M` than AA's Elo; cannot satisfy the frozen row.

## 8. Truth statement

This plan does not close any family, meta obligation, donor conjunct, or the checkpoint. It makes three things real: a content-addressed inventory that the donor conjunct required and did not have; a governance encoding of the owner's no-outreach order with the proof of what it implies; and an honest terminal probability (≈ 0 under fork A) with the exact owner lever that changes it. `terminal_real` remains `false`.

---

## 9. Hypothesis test (2026-10-14, second pass): "the Brain already has perfect solutions, and perfect solutions exist on the internet"

### 9.1 What the Brain actually contains (measured, not assumed)
`canonical/runtime`: 2,027 Python files. By name class: 890 governance/verification, 662 other, **475 producer-like** (82 osworld, 46 terminal, 41 solver, 40 synth, 28 hle, 26 finance, 12 harbor_science, 6 chartography). What those producers have ever scored on a real bar:

| Producer | Real-bar measurement on record | Zero-model? |
|---|---|---|
| `chartography_deterministic_professional_solver_v1` | **2 of 2 official non-held-out samples PASS** (independent public runner, 2026-10-11); explicit non-claim of the 100-task score | yes |
| `hle_native_total_solver_v1..v3`, `hle_native_research_solver_v3..v5` | synthetic only; `achieved_score: null`; abstention-based totality | yes |
| `coding_finite_candidate_exact_oracle_solver_v1` | constructive liveness verified; reward 0 on real tasks | yes |
| OSWorld V21 deterministic app-policy overlay | file did not parse until today; V7 workflow "verified" on fixtures | yes |
| TB-Science / OSWorld planner lineages | 0/20, 0 | **no** (Qwen) |
| mini-swe-agent / stirrup (vendored donors) | the only agentic producers | **no** (require a model) |

Verdict on hypothesis 1: the Brain has **prototypes with zero real-bar evidence**, except Chartography (2/2). "Perfect solutions for similar problems" is not supported by any receipt.

### 9.2 What exists on the internet (read-only research, no outreach)
- **TB4 (bar 66.36 %)**: open-weight models at/above the bar exist — Kimi K2.6 66.7 % (Modified MIT), DeepSeek-V4-Pro 67.9 % — i.e. the "perfect solution" is a 1T-parameter language model plus an agent harness like the one already vendored (`mini_swe_agent`).
- **OSWorld-Verified (bar 81.8 %)**: best open weights EvoCUA-32B 56.7 %, UI-TARS-2 47.5 %, OpenCUA-72B 45.0 %. **No open solution reaches the bar**; the bar is proprietary-frontier only.
- **HLE w/ tools (bar 67.7 %)**: open-weight tool agents sit at roughly 30–50 %. No open solution reaches the bar.
- **Chartography (bar 89 %)**: VLM-based; no published open-weight system at the bar.
- **Free inference tiers ($0, self-service)**: Cerebras 1M tok/day but **8K context cap** (unusable for 30–100K-token agent trajectories); Groq / NVIDIA NIM / Z.ai ≈ 1,000 req/day; OpenRouter 50 req/day free. TB4 full pass ≈ 330 tasks × ~40 calls = 13,200 calls → ≥ 13 days per pass at 1,000 req/day, if the right model is hosted free at all (Kimi K2.6 free hosting unconfirmed).

Verdict on hypothesis 2: **true, with one catch** — every existing solution that reaches any of these bars is a general-purpose language model. That is exactly the class Mission Lock V10 excludes, and the two best (TB4) solutions are already vendored in this repo in harness form. The thing standing between the Brain and the internet's "perfect solutions" is not discovery; it is V10 plus $0.

### 9.3 Computed scenario matrix — P(checkpoint real) and best reachable row, 30-day horizon, no outreach

| Scenario | 8 owner-private rows | TB4 | OSWorld | HLE | Chartography | **P(checkpoint)** |
|---|---|---|---|---|---|---|
| S0: current laws | 0 | ≈0 (no zero-model producer) | ≈0 | ≈0 | 0.03–0.05 (2/2 → posterior under a realistic prior) | **0** |
| S1: V10 rescinded, $0 kept | 0 | 0.10–0.20 (Kimi-class via free tiers; rate/context limits) | 0 (best open 56.7 < 81.8) | ≈0 | ≈0.05 | **0** |
| S2: V10 rescinded + paid frontier models | 0 | ~0.9 | ~0.7 | ~0.6 | ~0.6 | **0** (8 rows) |

The checkpoint is 0 in every row of the matrix because of the 8 owner-private measurements. Only a ledger amendment (fork B) or revoking the no-outreach order changes the last column — and in S1/S2 the capability would belong to the model, not the Brain.

### 9.4 The only step that produces a *real new measurement* without any law change
Owner self-service (not outreach; ~5 minutes): accept the Chartography and HLE dataset terms on a free Hugging Face account and add `HF_TOKEN` as a secret on the public `verification-capsule-runner`. Then run the Brain's zero-model Chartography solver over all 100 tasks and the HLE native stack over 2,500 questions on the public runner with provenance.
- P(runs complete) ≈ 0.85. P(Chartography ≥ 89) ≈ 0.03–0.05; P(≥ 50) ≈ 0.15. P(HLE ≥ 67.7) ≈ 0.
- Impact: the first real, zero-model, bar-grade numbers this repository has ever produced for two families — true either way, and the only honest starting line for capability work.
