# ONE-SHOT PLAN (V2) — MAKE EVERY CAPABILITY IN BRAIN WORK AND FUNCTION PERFECTLY AS ONE ALIVE CREATURE

Date: 2026-10-15 (authored this session, revised after challenge). Status: PLAN. Authority: none. Credit: 0. Spend: $0.

## 0. First principles (deepest layer)

Objective (verbatim, immutable except by owner):
`BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`
terminality: OPEN_ENDED_CAPABILITY_OPTIMIZATION_NO_FINITE_FRONTIER_MODEL_OR_BENCHMARK_DEFINES_FINAL_MISSION_COMPLETION
spend: ZERO_INCREMENTAL_SPEND

Theory: effective intelligence = Brain-owned capability mechanisms + external JIT knowledge + general computation substrate. Knowledge is fetched when needed and never counted as capability. Capability is what Brain owns and can still run with every outside model deleted.

Law: `NO_MODEL_PRODUCER_COGNITION`. `HOSTING_DOES_NOT_LAUNDER`. `ZERO_CREDIT_WITH_ANY_MODEL_DEPENDENCY`. `UNKNOWN_PROVENANCE_FAILS_CLOSED`.

Therefore the only real metric: Brain's own mechanisms, passing true tests, on fresh instances, judged by an independent oracle, zero model dependency, zero spend. Benchmarks (the 13 open bars) are instruments — audit, falsifier, calibration, causal probe — never the product. A red score is not a reason to start work. We do not treat benchmarks as mystical. We work backwards from the output a benchmark measures to the mechanism that produces it, and we build/verify that mechanism. The score then follows or it doesn't.

Definition of "alive creature" (operational, falsifiable):
The one public entry `canonical/runtime/live_brain_route_admission_v1.solve` accepts a plain sentence, routes it through compiler + planner + controller to a bound capability, produces a real artifact, and that artifact passes an independent stdlib oracle on a fresh instance Brain has never seen. Every bound capability reachable from some sentence. Every reachable capability runnable on the public runner. Any regression turns the heartbeat red within one day. No model does the thinking. Spend $0.

## 1. Honest answer to "is the previous plan optimal?"

No. The V1 plan was competent, safe, and incremental, but not optimal. Four corrections:

C1. **Reuse-first collapse of the model-dependent families.** V1 assumed the 8 `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` families need invention (weeks). But Brain already owns: doc verify (ooxml), chart read from pixels, source ranking (BM25), model-free test-guided Python repair loop, authenticated Pareto scheduler, same-identity supervisor, PDF text/OCR binding. The question is not "invent" but "which of the 8 are actually integration gaps over already-owned mechanisms?" Integration is CONFIGURE/INTEGRATE (days), not SYNTHESIZE (weeks). V1 skipped a reuse audit and jumped to invention. Fix: do the reuse audit first; it may collapse 4–6 of the 8 from weeks to days.

C2. **Collapse verification phases into one "provably alive" push.** V1 split reachability, runnability, measurement coverage, and public receipt into 4 phases. They are all verification, not invention, and verification is the precondition for all credit. They should be one parallel push, not a serial chain. The creature is already ALIVE locally (heartbeat says so); the gap is proof, not capability.

C3. **Profile the 344 failures by root cause before planning 344 fixes.** 15 are import errors, 1 is a missing file. The remaining 328 likely cluster into a handful of root causes (stale pins, path drift, missing fixtures). One reconciliation pass may clear dozens. V1 planned "fix by family" without profiling.

C4. **Audit the 13 bars against owned mechanisms.** Work backwards from each bar's required output to the mechanism. Some bars (e.g. CHARTOGRAPHY_TOOLS_GE_89) may be achievable by mechanisms already owned (chart read from pixels). V1 put bars last as "months"; some may be days.

C5 (added). **The true critical-path blocker is user-gated, not code.** Hosted Actions billing (prestep failures, 100/100 runs) blocks CI verification. No code work produces a signed public-runner receipt while billing is broken. The plan must start with a user action and sequence code work to not depend on it where possible (local measurement first).

## 2. Measured state (non-stale, this session)

| Quantity | Value |
|---|---|
| Bound capabilities | 66 |
| Runnable here | 44 (22 blocked: 11 env deps + 11 adapter imports) |
| Reachable from a sentence | 63 (3 zero-input) |
| In-scope families measured | 12 of 27 (10 pass, 2 env-blocked) |
| Families not measured | 15 |
| Out-of-scope fail-closed | 20/20 (1.0) |
| Ownership families | 19 (7 verified-owned, 8 external specimen, 2 owned-component, 2 pending) |
| Families with model in quoted route | 15 of 19 (4 of the "verified-owned" ones included) |
| True-capability ledger | 9 rows, all MEASURED_SANDBOX, authority NONE |
| Honest suite | 11525 cases: 11166 pass, 344 fail, 1 error, 14 skip |
| Open obligation bars | 13, all open |
| Terminal truth | false |
| Spend | $0 |

## 3. The one-shot plan (V2)

### Phase A — Reuse audit (FIRST, before any invention) — 1 day
For each of the 8 `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` families, map its required output to Brain's owned mechanisms (doc verify, chart read from pixels, source ranking, repair loop, scheduler, supervisor, PDF/OCR, XLSX). Classify each as: (i) already owned, needs integration (CONFIGURE/INTEGRATE), (ii) owned component + gap (ADAPT), (iii) genuine invention needed (SYNTHESIZE, with exhausted-reasons). Also audit the 13 bars the same way (work backwards from output to mechanism).
- P: 1.0 (it's analysis, no code).
- Impact: determines whether Phase E is days or weeks. Expected: 4–6 of 8 are integration, 2–4 need invention. This is the highest-information, lowest-cost step.
- Oracle: a written reuse map with evidence paths; reviewed by the user.

### Phase B — "Provably alive" push (parallel, 2–3 days) — the "real now" proof
All verification, no invention. Run in parallel:

B1. Reachability 63→66: add input contracts to the 3 zero-input capabilities (`docx.document.verify.ooxml`, `task.acceptance.objective.lossless.v1`, `terminal.kstar.root.assess.stdlib`). CONFIGURE. P 0.95. Oracle: heartbeat `zero_input: []`.

B2. Runnability 44→66: fix the 11 adapter import failures (make optional imports fail-closed with `IMPORT_UNAVAILABLE` rather than crashing) + confirm the 11 env deps install on the public runner. ADAPT. P 0.85 (shared pattern). Oracle: heartbeat `adapter_import_failed: []`, `external_dep_missing_here: []`.

B3. Measurement coverage 12→27: write fresh-goal oracles for the 15 unmeasured families (reuse the existing harness). COMPOSE. P 0.7/family → ~10.5 in pass 1, ~15 in pass 2. Oracle: `families_not_measured_here: []`.

B4. Public receipt: trigger `live-brain-heartbeat.yml` on the public runner (gated on billing — user action). CONFIGURE. P 0.80. Oracle: workflow conclusion success + artifact.

B5. Promote ledger rows SANDBOX→PUBLIC_RUNNER only on referee-signed receipts. P 0.90. Oracle: ledger authority real.

Combined impact: every bound capability reachable and runnable and measured on fresh instances, with a public signed receipt. This is the "real now" proof — not a claim, a measurement. Wall-clock: 2–3 days of code work + 1 workflow run. Gated on billing for B4.

### Phase C — Honest suite root-cause profile (1 day, before fixing)
Group the 344 failures by root cause (import error, missing file, stale pin, path drift, fixture). Fix the root causes, not the symptoms.
- P: 0.95 that ≥50% of failures clear from ≤5 root-cause fixes.
- Impact: 344→~<100 in one pass; then per-family fixes for the rest.
- Oracle: honest baseline re-measure with `honest_suite_baseline_v1.py`.

### Phase D — Requalify model-dependent families (reuse-first, parallel lanes)
Using Phase A's reuse map: for each family, walk DELETE→BYPASS→REUSE→ADAPT→SUBSTITUTE→COMPOSE→CONFIGURE→INTEGRATE→SYNTHESIZE. Harvest white-box donors (OmniParser, UniChart, etc.) only through the transfer gate: causal ablation, held-out, donor deletion, full dependency accounting, post-deletion qualification. 
- P per family: 0.25–0.60. E[≥2 requalified in 45 d] ≈ 0.6; E[≥4] ≈ 0.3.
- Impact: ownership 7→~9–11; model-dependent 15→~4–6. This is the only credit-changing phase.
- Governance: 2 families/PR max → 4 PRs minimum; 3 capabilities/PR.
- Oracle: true-capability harness on untouched held-out instances, donor deleted, referee-signed receipt.

### Phase E — Open obligation bars as downstream outputs
Only after Phases A–D produce owned, measured, non-model mechanisms. Work backwards from each bar's required output to the mechanism (per user's first-principles point). Audit which bars are already achievable by owned mechanisms (some, like chartography ≥89% with tools, may be close now). 
- P(T ≤ 120d) ≈ 0.08–0.15 (unchanged, dominated by TB4 physics and owner channels). Do not inflate.

## 4. Aggregate probability (honest)

- P(reachability 66/66 within 1 day) ≈ 0.95.
- P(all 66 runnable on public runner within 1 week) ≈ 0.85 × 0.95 ≈ 0.81.
- P(all 27 families measured within 2 weeks) ≈ 0.9 (two passes).
- P(at least one public-runner signed receipt within 2 weeks) ≈ 0.80 × 0.90 ≈ 0.72 (gated on billing).
- P(honest suite <100 failures within 2 weeks) ≈ 0.8 (root-cause profile).
- P(≥2 families requalified within 45 days) ≈ 0.6.
- P(≥4 families requalified within 45 days) ≈ 0.3.
- P(any terminal credit within 120 days) ≈ 0.08–0.15 (unchanged).

The creature is "real" at the end of Phase B (provably alive, publicly, with a signed receipt) — days, not months. Credit (Phase D) and bars (Phase E) take longer. "Real" ≠ "credited"; it means every bound capability is reachable, runnable, and measured on fresh instances, with any regression turning red. That is achievable in days and is not fake.

## 5. What makes this real and not fake

- Phase B changes real files and is verified by real heartbeat runs with `zero_input: []`, `adapter_import_failed: []`, `families_not_measured_here: []`, and a public signed receipt. Measurements, not claims.
- No score is moved by editing numbers. No test weakened. No harness touched. No model added to a credited path. No protected path changed.
- Every step has an independent oracle. A step failing its oracle is not counted.
- `truth.achieved` stays false until the owner countersigns. This plan does not claim terminal credit.

## 6. Critical-path honesty (the thing V1 buried)

The single biggest blocker to a signed public receipt is **hosted Actions billing** (prestep failures, 100/100 runs, account payments/spending limit, 11+ days). This is a user action, not a code action. Until it's resolved, B4 cannot produce a signed receipt. Code work (B1–B3, C, D, E) can proceed in parallel and does not depend on billing. I will not pretend code work unblocks the receipt. The plan sequences billing as step 0 (user) and code as step 1 (agent), running in parallel.

Secondary blockers (user-gated): AA-Briefcase send approval (only route to obligation #5), self-hosted `brain-regression` runner (drains 24/24 promotion queue), Buildkite free-tier preflight, Ubuntu-26 runner migration deadline 2026-10-19.

## 7. Governance compliance

- Objective verbatim: §0.
- Phase B progress class: VERIFIED_RELIABILITY_GENERALIZATION_OR_EFFICIENCY_GAIN (reachability + runnability + measurement coverage, no regression) or GOVERNANCE_GUARD_NO_PROGRESS_CLAIM if framed as measurement plumbing. I'll use VERIFIED_RELIABILITY... with evidence path `canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json`.
- Route class: CONFIGURE (Phase B), ADAPT (Phase C), and per-family for Phase D.
- Producer cognition model dependency: 0. Incremental spend: $0.
- One action intent per PR. Phase B is ~3 PRs (B1, B2, B3; B4/B5 are workflow/config). Phase C is 1 PR (root-cause fixes). Phase D is 4 PRs (2 families each). Phase E is separate.
- Protected paths untouched. No merge over red referee. Auto-merge only.

## 8. Immediate next action (real, now)

1. Re-run `brief` (done this session).
2. **Phase A first** (reuse audit, 1 day, no code, no risk) — I'll produce the reuse map and present it before any code. This is the highest-information step and may collapse Phase D from weeks to days.
3. In parallel: user resolves billing (step 0) so B4 can run.
4. Then Phase B (provably alive) as governed PRs.

I will start Phase A now (analysis only, no code, no risk) and present the reuse map before touching any registry or adapter. That is the smartest, most honest first move: find out what we already own before deciding what to build.

If you want me to skip the audit and go straight to Phase B (reachability fix), say so — but I recommend the audit first, because it may make Phase D 5x faster and changes the whole plan's timeline. Your call.