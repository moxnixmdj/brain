# FIRST-PRINCIPLES AUDIT — the whole Brain, deepest layer first (2026-10-16)

Status: ANALYSIS + EXECUTED (this PR). Authority: none. Credit: 0. Spend: $0.
Objective (verbatim): `BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`

Rule applied to every line below: *is this the optimal, smartest, best plan/approach?*
Anything that failed that question was not accepted.

## 0. What the creature is (first principles)

A problem solver = understand goal → select mechanism → execute mechanism → verify artifact.
Minimum parts: ONE registry of executable mechanisms, ONE matcher, ONE executor, ONE verifier.
Everything else must justify its existence in milliseconds, bytes, or newly provable behavior —
or it is over-engineering. Best part is no part.

Definition of alive (operational, falsifiable, unchanged): `solve` takes a plain sentence,
routes compiler → planner → controller → bound capability, produces a real artifact, and an
independent stdlib oracle passes it on a fresh instance. Every bound capability reachable from
a sentence. Every reachable capability runnable. Regression turns red within a day. No model
thinks. $0.

## 1. Measured state (this session, non-stale)

| Quantity | Before | After (this PR) |
|---|---|---|
| Bound capabilities | 67 | **70** |
| Reachable from a sentence | 66 | **69** (1 genuinely zero-input) |
| Heartbeat execution families | 29 | **32** |
| Heartbeat in-scope (complete env) | 29/29 | **32/32**, OOS 1.0, 0 errors |
| solve() fail-closed (OOS) | 14 ms | 12 ms |
| solve() missing-dependency | **735 ms** (pip-retry noise) | **10 ms** (true reason, 73×) |
| solve() success (jq) | 65 ms | 45 ms |
| Registry load per solve | 5.1 ms | 0.01 ms (510×, mtime-guarded cache) |
| Live-path reachable modules | 32 of 2111 (1.5%) | same (inventory, not deleted yet) |
| Total runtime | 2032 files / 427,536 lines | −1 superseded duplicate |
| Governance / verification / tests | 3212 / ~13M / 1979 files | unchanged (batches queued) |
| Workflows | 317 | unchanged (batches queued) |
| Honest suite | 11,525 cases, 344 fail | no new failures (150/150 affected green; 4 pre-existing fails reproduced on clean tree) |

## 2. What is REAL (evolving — preserved, surfaced, never killed)

1. **79 bound-adapter files**: nearly all stdlib-only, ZERO model imports. The crown jewels.
   67 were bound; this PR binds 3 more run-ready ones. ~8 more run-ready + ~11 library
   mechanisms (thin `run()` needed) form the binding queue (§5).
2. **Planner (245 lines), Pareto scheduler (measured), supervisor (substrate),
   front compiler + admission (earned fail-closed rules R1–R9).** Kept byte-stable where
   pinned; routed around, never forked into a third layer.
3. **True harness + ledger + heartbeat.** The instruments. Extended, not rewritten.
4. **Internalized deterministic skills** (office excel/pptx/word read/write, agent_replay)
   and **H100 typed-effect packs**: real, model-free, promotable (§5).
5. **11 frontier specs**: several already have bound implementations; the rest are the
   invention frontier AFTER the binding queue drains (reuse before synthesis).

## 3. What is OVER-ENGINEERING (ranked kill list)

K1. **Extended registry: 2309 auto-inventory rows, 0 verified, parsed on every solve.**
    2032 rows are literally "every runtime .py file is a capability". Files are not
    capabilities. This PR bypasses the cost (cache); deletion of the noise concept is queued
    (needs the 1 test that reads it to move to the real promotable-inventory first).
K2. **Kernel pip/apt-install inside the hot path.** Measured 735 ms producing a lie (pip
    error instead of the missing import). Killed in this PR: fail closed fast with
    `IMPORT_UNAVAILABLE` + the true reason. Deps are declared outside the hot path (the
    heartbeat install block already does this — reused, not reinvented).
K3. **Version proliferation**: 21× r2_adequacy, 19× osworld_subject, 15× source_aligned_proof,
    12× retrieval_arena, 12× universal_solver, … Git keeps history; the tree keeps ONE.
    Queued in DELETE batches (≤20 test deletions per PR per the referee).
K4. **614 benchmark/race-specific runtime files (125k lines: livebench 96, osworld 89,
    professional_quality 75, bytes 56, p3 37, …).** The law says benchmarks are instruments,
    never the product — yet 30% of runtime IS benchmark code. Keep what the heartbeat/true
    harness runs; delete the dead race scaffolding in batches.
K5. **317 workflows**, most spent one-shots. Keep referee + heartbeat + consistency +
    admission + drift + live carriers; delete the rest (git has them).
K6. **56 MB `tmp/` committed to git** (PNGs, probe wheels). Build artifacts in the control
    plane; also slows every `search_text` (rglob over canonical). Queued: .gitignore + tree
    removal after fixture-use audit.
K7. **Superseded duplicate adapters.** `qr_qrencode.py`: registry itself records it as
    `previous_specialized_adapter` (routed via generic `cli_command` since). DELETED this PR.
K8. **Pinned 5107-line matcher + stacked 888-line front compiler.** Frozen by pins; a third
    layer was considered and REJECTED (risk ≫ 10 ms). Optimized around, not through.

Explicitly NOT killed: anything in §2; the 8 EXTERNAL families' integration work (ADAPT/
COMPOSE over owned mechanisms per the reuse audit — re-confirmed, still the right route);
any receipt/record the referee marks fail-closed.

## 4. Defects found by measurement (honesty section)

D1. **Pinned cells kernel fail-open**: `evaluate_cells` returns `pass: not failed`, so an
    UNBOUND obligation still passes — contradicting its own hard nonclaim
    (`UNBOUND_RAW_TASK_OBLIGATIONS_REMAIN_BLOCKING`). Kernel bytes are verification evidence
    for another capability → left byte-unchanged (FINANCE precedent); the BINDING enforces
    strictness (every obligation bound AND passing) and proves it with a fail-closed test.
D2. **Sentence-quoted binding cannot carry inner quotes** (binder takes the first quoted
    span). Cells specs need inner quotes → bound via task FILE instead of quoted text.
    No grammar change, no kernel change. Decompose/focus keep quoted binding (plain-word
    objectives; fail closed otherwise).
D3. **Pre-existing, reproduced on clean tree, NOT touched**: `GOAL_COMPILATION_AMBIGUOUS`
    (barcode: zint vs kstar), 3 `open_research_source_frontend` test errors (test-side
    KeyError). They belong to the honest-suite backlog, not this PR.

## 5. ALL capabilities, not 67 (the binding queue — each one real in the creature)

Bound this PR (70): + `research.objective.decompose.broad.v1`, + `research.query.focus.v1`,
+ `python.software.request.semantic_cells.v1` — each reachable, runnable, heartbeat-measured.
Next (3 per PR, each with fresh-goal oracle + OOS probes, same pattern):
 - run-ready: `browser_chromedriver_interact` (needs chromedriver on runner),
   `chart_positioned_ocr_axis_binding_v1`, `image_ocr_tesseract_positioned` (need tesseract),
   `open_research_source_frontend` (needs signature ADAPT + network policy),
   4× SEC natives (need fixture-mode ADAPT for hermetic oracles),
   `python_source_tree_codec` (infrastructure; bind only if a sentence needs it).
 - library → thin `run()`: `grounded_executable_composition` (+verify), `wikidata_*` (3),
   `open_web_source_candidate_discovery`, `relevant_source_evidence_extract`,
   `first_party_objective_relevance_verify`, `research_query_focus`(done),
   `broad_objective_decompose` (done), `source_candidate_provenance_verify`.
 - internalized deterministic: 6 office skills + agent_replay via thin adapters.
 - H100 packs as executable typed-effect tools.
NOT capabilities (noise concept to delete, honestly): the 2032 "every .py file" auto-rows,
reconciliation records, historical cuts. Deleting the inventory deletes no mechanism.

## 6. Why this plan is optimal (the never-accept check, per decision)

- Speed via BYPASS (cache + fail-fast), not rewrite: zero PASS-path behavior change, proven
  by A/B (29/29→32/32, OOS 1.0 both). A matcher rewrite was rejected (risk ≫ gain).
- Bindings via INTEGRATE (thin adapter + one row, kernels unchanged): the FINANCE-precedent
  reuse path; no SYNTHESIZE anywhere (nothing new was invented — it all existed).
- One deletion (registry-documented superseded file): smallest DELETE that proves the
  kill-list is real; bulk DELETE batches follow within referee limits.
- One PR, one intent, one route narrative: three capabilities + the speed they inherit.
  (Single-branch session: follow-up DELETE/BIND PRs queue after merge.)
- Everything claimed is measured: ms with perf_counter, pass sets with seeded + unseeded
  runs, reachability from the live entry, oracles on real artifacts. No tolerance was
  widened, no harness touched, no pin chased.

## 7. Queued after merge (in order)

1. DELETE batch 1: dead version intermediates with no test/pin refs (bulk, no test deletions).
2. DELETE batch 2+: version/test mirrors (≤20 test deletions each) + dead workflows + tmp/.
3. BIND PRs (3 each) down the §5 queue with heartbeat families v7+.
4. B1 zero-input: `terminal.kstar.root.assess.stdlib` input contract (the last BLOCKED one).
5. Extended-registry noise removal (after promotable-inventory replacement + 1 test move).
6. Re-measure honest suite + heartbeat wall-clock; report suite-time delta as the
   efficiency evidence for the DELETE batches.

## §8 — Heartbeat timeout episode (same day, same PR)

PR #4727's first heartbeat run TIMED OUT at the 30-minute job limit. Three
concurrent PR heartbeats timed out in the same window; a fourth (perf-only,
zero new families) passed at 29m06s with 54s of margin. Root cause: the base
heartbeat sits at ~29 minutes (50 instances × 29 families × 2 entries + 100
OOS × 2 = ~3100 real tool executions) and ANY family-adding PR tips it over.
Without a fix, no binding PR can ever prove itself on the runner again, and
the "regression turns red within a day" mechanism dies exactly when growth
starts. Binding PRs are the future; the heartbeat must carry 100+ families.

Rejected: raising the timeout (papers over sloth, dies at 100 families);
shrinking the matrix (weakens the one regression signal).

Fix (this PR, commit 2): `--jobs N` on the measurement tool. Generation stays
serial in RNG order (fixed seeds replay identical goals); case execution fans
out to worker processes; oracles judge in the original order. Verdicts are
order-free by construction (unique task ids, owned artifact paths). Proof:
fixed-seed serial vs 4-worker receipts are verdict-identical (32/32, OOS 1.0
both). Same goals, same oracles, same entries, same verdicts — only wall
clock changes. Receipt records `jobs`. Heartbeat workflow passes `--jobs 4`.
