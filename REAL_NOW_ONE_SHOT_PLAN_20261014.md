# REAL-NOW ONE-SHOT PLAN — `OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1`

Date: 2026-10-14 · Branch: `arena/9672736d-brain` · Base: `main@11d4d83` · Spend: $0 · Credit claimed: 0

This document is the one-shot plan you asked for. It is built from (a) the live gate, scheduler and
registry outputs at HEAD, (b) a live census of every public surface that could contain a solution
(`canonical/governance/EXTERNAL_WAKE_EVENT_CENSUS_20261014_V1.json`), and (c) first-principles
accounting of what kind of object each open obligation is missing. Every probability below is written
as a number with its basis; where I had to predict, I predicted, and the prediction is labelled.

---

## 0. The verdict, stated once and not softened

**P(terminal predicate true within 40 minutes | no user action, no external reply) = 0.** Exactly zero,
not "small", and here is the four-line proof the Brain's own laws force:

1. T ≡ (19/19 families PASS) ∧ (8/8 meta closed) ∧ (donor V2 requalified, 12/12) ∧ (aggregate predicate
   + scheduler root sound) ∧ (global postconditions re-proved). Live: 7/19 families, 16 failed predicates,
   20 unresolved atoms, donor 0/12.
2. The registry (`OPUS_5_5_PROTOCOL_GAP_REGISTRY_V2`) admits exactly three evidence classes for an atom:
   **E1** owner/matched-epoch receipt, **E2** exact private bytes + Brain execution + independent
   verification, **E3** scope-complete stronger certificate + independent verification.
3. For every one of the 20 atoms, the admissible object is one of: a third party's measurement of this
   system (E1 — not started by any owner; one owner refused), bytes behind a login the agent cannot
   perform (E2 — AA 91 tasks, 657 AutomationBench tasks, gated HF sets, Vals private splits), compute
   that $0 cannot buy inside 40 min (TB4 ≥ 55 wall-hours at 16 cores), or independent verification whose
   only two carriers are down (hosted Actions billing-blocked, self-hosted runner offline).
4. 40 min < min(any owner latency, 55 h, carrier repair by someone other than me). Hence 0 atoms close,
   12 families stay open, the first conjunct is false, T is false. Declaring otherwise would be the exact
   failure the repo already revoked once (`FALSE_TERMINAL_REAL_991AC_REVOCATION_20261007_V1.json`).

What *is* real now is in §2: four committed artifacts and the first honest measurement plan.

---

## 1. First-principles result: why "the answer is already on the internet" fails here

Your hypothesis is **true for methods and false for results**, and the Brain already acted on the true half:
Harbor runner semantics, Valkyrie native adapter (verified 6/6), Stirrup/ARCHIE inlining, the Crowd-BT Elo
kernel, the AA-Briefcase rubric-judge prompt, the Chartography deterministic scorer, the OSWorld adapter —
all harvested, all in `canonical/`. The census (7 channels, live) found **0** new policy-changing facts and
**1** new comparator-identity fact (TB4, §4.3).

The 20 unresolved atoms are missing objects of four kinds, none of which is knowledge:

| Kind | Atoms | Why no search can produce it |
|---|---|---|
| A. A measurement of *this system* by a third party on a private set | AA-Briefcase, GDPval-AA, AutomationBench-AA, FrontierCode, CursorBench, Finance Agent v2, Finance Index, MysteryMechanism | A measurement that has never been taken does not exist anywhere to be found |
| B. Bytes behind a login/terms gate | Chartography (100-task pack), OSWorld-V2 (tasks + assets), HLE (dataset) | Agent cannot perform the login; anonymous fetch returns 401 (verified, do not retry) |
| C. Compute hours | TB4 (≥ 55 wall-h @ 16 cores for 330 slots, 5 trials/task), TB-Science (210 slots, serial) | $0 policy; both free carriers currently unusable |
| D. A capability that does not yet exist in the mechanism library | TB-Science (clean zero-model run: 0 reward, credit authority true), HLE no-tools, TB4 beyond 1 slot | Must be built and measured, not retrieved |

**The deepest limiting factor, stated plainly.** The Brain's runtime is model-free by law (model dependency
count = 0 in every adapter; donor deletion required). Thirteen of the nineteen bars are frontier-LLM scores.
The only clean model-free measurements against those bars so far are TB-Science rank 22 (reward 0) and one
TB4 success slot. At the same time the scheduler reports `admitted_capability_deficit_count = 0` because
`benchmark_failure_alone_is_capability_deficit = false` — a correct anti-rebase safeguard that also makes a
0/20 result register as *no gap*. Consequence: the capability-first scheduler never schedules the capability
work that kind-D atoms require. This is not a bug to patch silently (it is governance); it is the single fact
that most changes the time-to-terminal forecast (§5).

---

## 2. What became real in this session (receipts, zero credit)

| # | Artifact | Commit | Effect | Credit |
|---|---|---|---|---|
| R1 | `tests/test_bytes_canonical_wiring.py` repaired: reads the live pointer, asserts version floors (MISSION_LOCK ≥ V9, ENGINE ≥ V8, HARVESTING ≥ V2, CAPSULE ≥ V2, ARBITRAGE ≥ V8), V3 hard rules (donor/external/teacher = 0, fail-closed, transfer gate present). 5/5 green; other top-level modules green. | `98959cf` | Removes the only red top-level test; rot-proof for future pointer bumps | 0 |
| R2 | 292 `runs-on: ubuntu-latest` → `ubuntu-24.04` across 275 workflows; all 314 YAML parse. | `4eb9aa6` | Identical image today; blocks the 2026-10-19 drift to 26.04 that would silently change the verification carrier | 0 |
| R3 | `canonical/governance/EXTERNAL_WAKE_EVENT_CENSUS_20261014_V1.json` | `30061ac` | 7 surfaces, 0 wake events, one comparator-identity fact for governance, same-surface retry authority = false | 0 |
| R4 | Local full `canonical/tests` regression evidence run (this sandbox, Python 3.11, 2 cores) — result appended in §7 | not committed (scratch, excluded) | First full-suite signal since 2026-10-02; **not** an authorized carrier | 0 |

| R5 | `canonical/governance/TEST_SUITE_HISTORICAL_VIRTUALIZATION_FINDING_20261014_V1.json` — see the box below | this branch | Measures how much of the suite's green is a HEAD property | 0 |

**Finding R5 — the test suite's green is partially virtualized (this changes what "verified" means).**
Commit `0015770a2` (2026-10-12, "…close all 11,468 repository tests") added `canonical/tests/conftest.py`
(1,082 lines) and `historical_test_commits.json` (184 entries). While any of those 184 test modules runs, the
conftest monkey-patches `Path.read_text/read_bytes/open/exists/glob` and `importlib` so repository reads are
served **from a pinned historical commit** (98 data overlays, 81 modules that import *historical runtime
source*, 5 explicit file pins; 181 distinct commits, 2026-09-26…10-14). Independently of pins,
`_apply_memory_fixes` patches the source of ≥ 5 runtime modules **in memory on every import** (tested code ≠
committed code), and four modules receive a **fabricated `docker` success transcript** from a patched
`subprocess.run`. I measured both states in this sandbox (conftest restored byte-identically afterwards):

| Run | Failed / 11,523 | Notes |
|---|---|---|
| A — as committed | 21 | 10 deterministic at HEAD (pinned data now older than the 10-13 test edits), 7 `openpyxl/pptx` (not in CI pins either), 3 runner-provisioned LiveBench assets, 1 git object unreachable from `main` |
| B — pins off, memory patches off, docker shim off | **322** | +310: 287 inside pinned modules, 1 docker-shim, 22 elsewhere; 196 modules; 255 AssertionError / 24 KeyError |

Consequence for T: the conjuncts "aggregate predicate + scheduler root sound" and "global postconditions
re-proved" are evidenced partly by this suite; 759 tests (351 against historical runtime source) are evidence
about their pinned commits, not about HEAD. The regression receipt binds `subject sha == origin/main`, so a green
receipt produced under this conftest would overstate what is verified at that sha. No authorized full-suite
receipt exists for any commit since `0015770a2` (last non-cancelled runs: 2026-10-11, all "runner lost
communication"). Three governance options are written in the artifact (declare / repair / split). I changed no
test and no conftest.

Governance finding (reported, not self-fixed): the live `WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V3.json` is a
transfer-safety schema and **dropped** V2's `byte_accounting`, `resource_bounds`, `elicitation_scan_evidence`,
`mechanism_cover_membership`, while the pointer still asserts `resource_bounded_capability_bytes_required: true`
and `RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW_V1.md` never mentions capsule byte accounting. Capsule-level byte
accounting is therefore unbound by any live schema. Needs a V4 schema (re-bind the four fields) or an explicit
bytes-law amendment — a governance decision, not an agent edit.

---

## 3. Reuse map — the nearest solved Brain artifact for every open obligation, and the exact delta

(Your thesis, applied honestly: what the Brain already solved, and what remains.)

| Obligation (frozen bar) | Nearest solved Brain artifact | Already proves | Remaining delta | Delta class |
|---|---|---|---|---|
| AA-Briefcase ≥ 1822 Elo | `AA_BRIEFCASE_*` protocol compiler + Crowd-BT kernel + 3 outreach sends | Scoring math reproduced; outreach drafted/sent | AA runs or admits the Brain (91 private tasks, no API) | A (owner) |
| GDPval-AA ≥ 1846 Elo | `GDPVAL_TARGET_RELATIVE_INFORMATION_CUT_V2`, `CONTROLLED_INTERFACE_PROVENANCE_PASS_1_PARTIAL_ARTIFACTS_BOUND` | Comparator identity corrected; 1-pass partial artifacts bound | Shared measurement with AA's judge state | A (owner, same channel as AA) |
| AutomationBench-AA ≥ 40 | `AUTOMATIONBENCH_PRIVATE_SPLIT_RECONCILIATION_V1` | Public/private split and metric reproduced | 657-task private set is unreleased | A (owner, AA) |
| FrontierCode v1.1 ≥ 54.4 | `canonical/action_intents/FRONTIERCODE_PARTNER_INTAKE_REQUEST_20261011_V1.json` | Intake request compiled | Mercor/Cognition reply + evaluation | A (owner) |
| CursorBench 4.0 ≥ 57.8 | CursorBench decoupling + 5-region complement non-identifiability record | Private scoring objects shown unidentifiable from public data | Owner policy change (refused) or scope-complete certificate | A (owner refused) |
| Finance Agent v2 ≥ 58.59 | `FINANCE_AGENT_V2_VALKYRIE_NATIVE_ADAPTER_VERIFICATION_20261011_V1` (6/6) | Adapter runs natively under Valkyrie, model-free | Vals tenant authorization + private core split run | A (owner) |
| Finance & Accounting Index ≥ 61 | same adapter family | — | Vals tenant | A (owner) |
| MysteryMechanism non-inferiority | intrinsic protocol compile | Protocol bound | Vals tenant | A (owner) |
| HLE with tools ≥ 67.7 | HLE harness-identity records | Harness under-specification documented; now sharper (§census) | HF terms (user) + $0 live web-search/fetch + code-exec tool bound into protocol + 2,500×5 trials + conservative scorer + Brain reasoning at that level | B + C + D |
| Chartography with tools ≥ 89 | deterministic scorer + 2-sample verification + HF 401 boundary record | Scorer exact on samples | 100-task pack bytes (user HF terms) → first real score | B |
| OSWorld 2.1 partial ≥ 81.8 | OSWorld adapter + self-service gated-access reconciliation; grounding internalization #4340/#4343 | Adapter verified; route known | Task/asset bytes (user HF terms) + VM carrier + capability | B + C + D |
| TB4 ≥ 66.4 (219/330) | `TB4_CURRENT_OWNER_TARGET_ATTAINABILITY_RECOMPILE_20261008_V1`, 1 success slot bound, Harbor runner semantics | Attainability math; carrier envelope | ≥ 55 wall-h @ 16 cores + 218 more real successes (slack 1) — or 196 if governance binds the matched AA protocol (§4.3) | C + D |
| TB-Science 0.1 ≥ 58.7 | `TB_SCIENCE_V01_PUBLIC_GITHUB_CARRIER_ATTAINABILITY_V1`, slot ledger V8 | 70 tasks × 3 trials = 210 slots; 57 tasks fit a public runner; 20 slots consumed as failures | 124 successes needed; ≤ 151 compatible slots remain → **≥ 82.1 % success rate on every remaining compatible slot**, from a clean baseline of 0 | C + D |
| Composition interfaces 8/12 | `capability_parallel_frontier_post_composition_v3.py` | 4/12 bound | 8 scoped proofs | internal |
| Meta 8 | `NECESSITY_COUNTERMODEL_AUDIT_20261014_V1` pattern | audit pattern exists | mapping checks; new evidence if any meta is not family-reducible | internal (0.6 each) |
| Donor V2 requalification 12 | donor exit/clean-room laws | law text | serialized after families; 12 requirements | internal, serialized |

---

## 4. The one-shot plan, with math

Notation: Δ = obligations advanced; P = my predicted probability the step achieves its stated outcome
within its window; h = wall-clock hours of agent/user work. Steps inside a wave are independent and run in
parallel. Nothing in this plan edits a target, a bar, or an evidence rule.

### 4.1 Wave 0 — user, today, ≈ 25 minutes total (the only steps with P ≥ 0.9)

| Step | Action (you) | Unblocks | P(done ≤ 1 d) | Impact |
|---|---|---|---|---|
| U1 | Fix GitHub Actions billing/spending limit on `moxnixmdj` (hosted carrier E1) | all hosted independent verification; 2×24/24 promotions already queued | 0.90 | highest: every E2/E3 object needs this or U2 |
| U2 | Bring the self-hosted `brain-regression` runner online (carrier E2) | full private regression → main-sha receipt | 0.85 | required for aggregate soundness re-proof |
| U3 | Accept HF terms for `surgeai/chartography`, `xlang-ai/osworld_v2_tasks`, `cais/hle`; place a read token in the sandbox/CI secret | kind-B atoms (3) | 0.75 | converts 3 obligations from "no bytes" to "measurable this week" |
| U4 | Approve the 4th AA send (`AA_BRIEFCASE_OUTREACH_STATE_20261011_V1` next action) | AA channel (3 obligations) | 0.90 | only lever on 3 rows |
| U5 | Open/approve a Vals evaluation-tenant request (Finance v2, Index, MysteryMechanism) | 3 obligations | 0.85 | only lever on 3 rows |
| U6 | Merge this branch's R1/R2 (test repair, Ubuntu pin) | CI stability on 10-19 | 0.95 | protects verification carrier |
| U7 | Governance decision on TB4 comparator identity (§4.3) and on capsule schema V4 (§2) | TB4 slack 1 → 23; capsule bytes re-bound | 0.70 | decides whether TB4 is a 0.1 or a 0.3 bet |

### 4.2 Wave 1 — agent, days 1–7, parallel, all contingent on Wave 0

| Step | Action (me) | Depends | P | Δ | h |
|---|---|---|---|---|---|
| A1 | Promote the two 24/24 verified objects once E1 is live; re-run `terminal_reality_gate_v1` and recompute the scheduler root | U1 | 0.90 | credit conversion (0 families) | 1 |
| A2 | Chartography: pull the 100-task pack, run the deterministic lower-bound scorer, bind the first real Brain score with content hashes | U3 | 0.95 for a *measurement*; **P(score ≥ 89) = 0.10** (prediction: Brain lower-bound lands 35–60 %; July-2026 best-of-30 frontier configs scored 45 %) | 1 measured | 6 |
| A3 | OSWorld: download pinned release, run adapter on the free-VM carrier subset, bind partial score lower bound | U3, U1 | 0.80 measurement; **P(≥ 81.8) = 0.05** | 1 measured | 12 |
| A4 | HLE: bind no-tools baseline protocol (exact-match conservative scorer), run on a 250-question stratified sample first | U3 | 0.85 measurement; **P(≥ 67.7 with tools, ≤ 120 d) = 0.02** | 1 measured | 10 |
| A5 | TB4: preflight 16-core carrier on Buildkite/CircleCI free tiers; bind envelope; run first 33-slot tranche | U1 or new carrier | 0.60 tranche completes; **P(≥ 219/330 ≤ 120 d) = 0.10; ≥ 197/330 = 0.25** | 1 advanced | 20 |
| A6 | TB-Science: pick the 10 highest-fit compatible tasks, build mechanisms, run 1 slot each (no replay) | U1 | 0.70 for 10 clean slots; **P(≥ 82.1 % on remaining compatible slots) = 0.03** | 1 advanced | 24 |
| A7 | Composition: scoped proofs for 8 interfaces | — | 0.50 all 8 | 1 | 16 |
| A8 | Meta ×8 mapping checks against the necessity-audit pattern | — | 0.60 all reducible | up to 8 | 8 |
| A9 | Follow-ups: Mercor/Cognition (day 7), Cursor policy re-ask (day 14, P reply 0.05) | — | 0.35 / 0.03 | 2 | 1 |

### 4.3 Governance option found by the census (decision, not a rebase)

The frozen TB4 bar is bound to Anthropic's self-run protocol (Claude Code `--bare`, effort xhigh, 219/330).
Artificial Analysis' **independent** harness measures Opus 5.5 at **59.6 %** on the same benchmark. If the
Brain executes under the AA public-harness protocol, the matched same-protocol comparator is 59.6 % →
required successes = ⌈0.596 × 330⌉ = **197**, slack 23 of 220 creditable slots instead of slack 1.
This is a comparator-identity question of exactly the kind the Brain has corrected before
(`GDPVAL_TARGET_RELATIVE_INFORMATION_CUT_V2`). It is recorded in the census for your decision; I applied
nothing and claim nothing.

### 4.4 Critical path (longest dependency chain to T)

U1/U2 (1 d) → owner replies for AA channel (≥ 30–90 d, P 0.2 for all three rows) → Vals tenant (30–90 d) →
TB4 execution (≥ 55 wall-h after carrier; realistically 2–6 weeks on free tiers) → TB-Science capability
build (open-ended) → composition/meta (2–4 weeks, parallel) → donor V2 requalification (serialized after
families, 1–2 weeks) → reducer + global postconditions re-proof (1 week, needs E1 or E2).
**Earliest date on which T can even be evaluated for truth with all evidence in hand: ≈ 2026-12-01**, and
only if every owner channel answers yes.

---

## 5. Forecast — the number, computed from its terms

P(T ≤ horizon) = P(carriers) × P(AA rows) × P(FrontierCode) × P(CursorBench) × P(Vals rows) × P(HLE) ×
P(TB4) × P(TB-Science) × P(Chartography) × P(OSWorld) × P(composition) × P(meta) × P(donor).
Correlations are already folded into the grouped terms (AA rows share one channel; Vals rows share one tenant).

| Term | ≤ 14 d | ≤ 45 d | ≤ 120 d | Basis |
|---|---|---|---|---|
| Carriers E1/E2 (user) | 0.85 | 0.95 | 0.97 | user-controlled; monthly quota reset |
| AA rows (3) | 0.00 | 0.08 | 0.20 | 0/3 replies in 11 d; "no public API"; same org |
| FrontierCode | 0.02 | 0.15 | 0.35 | intake exists; terms unknown |
| CursorBench | 0.00 | 0.01 | 0.03 | owner refused; complement non-identifiable |
| Vals rows (3) | 0.00 | 0.10 | 0.30 | adapter ready; tenant is the lever |
| HLE with tools ≥ 67.7 | 0.00 | 0.005 | 0.02 | §1 kind B+C+D; no-tools Opus bar itself is 64.4 |
| TB4 ≥ 219 (or 197) | 0.00 | 0.02 (0.05) | 0.10 (0.25) | compute + 218 (196) more successes from 1 |
| TB-Science ≥ 124/210 | 0.00 | 0.005 | 0.03 | needs ≥ 82.1 % on remaining compatible slots from clean 0 |
| Chartography ≥ 89 | 0.00 | 0.05 | 0.10 | first measurement in ≤ 7 d once bytes exist |
| OSWorld partial ≥ 81.8 | 0.00 | 0.02 | 0.05 | bytes + VM carrier + capability |
| Composition 8/12 | 0.10 | 0.45 | 0.70 | internal |
| Meta 8 | 0.15 | 0.50 | 0.75 | internal |
| Donor V2 12 | 0.00 | 0.30 | 0.65 | serialized after families |
| **Product** | **0** | **≈ 1 × 10⁻¹⁰** | **≈ 1 × 10⁻⁷ (≈ 3 × 10⁻⁷ with the TB4 option)** | — |

Read this correctly: the earlier repo plans quoted P(T ≤ 120 d) ≈ 0.08–0.15. That figure is reproducible
only if one assumes every owner channel answers yes **and** the model-free mechanism library already matches
Opus 5.5 on HLE, TB4, TB-Science, OSWorld and Chartography. The evidence at HEAD for the second assumption is
0/1 clean (TB-Science) and 1 slot (TB4). Under the frozen predicate **as written**, the honest expectation is
that T is not reached in 2026; the dominating terms are the four kind-D capability bets and CursorBench's
owner refusal, in that order.

Sensitivity (what moves the number most, per unit of your time): U3 (HF terms, 5 min) converts three
obligations from unmeasurable to measured within a week — it does not raise P(T) much, but it replaces faith
with the first real Brain-vs-Opus numbers, which is the only input that can legitimately change every
capability term above. U1+U2 (10 min) restore the ability to *credit* anything at all.

---

## 6. What I will not do, and why

- Not declare T, a family, or any atom closed on the basis of this plan, the census, or local test runs
  (`FALSE_TERMINAL_REAL_991AC` precedent; registry evidence classes).
- Not rebase any bar, including TB4: §4.3 is a comparator-identity question for governance, with the numbers.
- Not fetch gated HF bytes anonymously again (verified 401; terms require a human account holder).
- Not patch the capsule-schema byte-accounting gap or the `admitted_capability_deficit` rule myself — both
  are law-level and need your decision.

---

## 7. Local regression evidence (this sandbox; Python 3.11.2, 2 cores, not an authorized carrier)

Scratch outputs `.local_regression*.txt/.xml` are excluded from Git; summary:

- Run A (committed conftest): `21 failed, 11488 passed, 14 skipped, 297 subtests passed in 479.04s` (RC=1).
  Failure split: 10 deterministic at HEAD · 7 missing `openpyxl`/`pptx` (also absent from the CI pin list:
  `pytest numpy pydantic python-docx Pillow opencv-python-headless langdetect cadquery pypdf sympy mpmath lark`)
  · 3 LiveBench asset/langdetect-blob pins provisioned only on the self-hosted runner · 1 `git show` of
  `fd60e692…` (exists on GitHub, not reachable from `main`).
- Run B (virtualization disabled, see R5): `322 failed` of 11,523; +310 vs A.
- The 10 deterministic failures are all of one kind — persisted authority/receipt artifacts out of step with
  live computation after the 10-13 commits (#3740, #3743): pinned R2 artifact V57 vs expected `__V91__`;
  pinned 4/19 data vs expected 7/19; `PostCompositionFrontierV2Error: R2_SCHEDULER` in the sky-impact
  planner/executor; reality-closure V2 reports a PASS fixed point where the test expects not-pass.
- Actionable, zero-credit, no-governance-needed items that fall out: add `openpyxl` and `python-pptx` to the
  regression workflow pins; add `fetch-depth: 0` or drop the unreachable-commit dependency; the 10 state
  failures need a human decision on which side (artifact or test) is the truth.

---

## 8. Bottom line

Real now = five committed, zero-credit artifacts (two fixes, two findings, one census) and a measurement plan that produces the first honest
Brain-vs-Opus-5.5 numbers within seven days of a five-minute user action (U3), plus carrier restoration (U1/U2)
that lets the Brain credit anything at all. Real terminal = not within 40 minutes, not within 14 days, and —
under the frozen predicate as written — not in 2026 unless the capability bets turn positive once measured.
The plan above is the fastest truthful path; the first thing it produces is measurements, because measurements
are the only objects on the critical path that nobody else has to hand us.

---

## 9. Self-audit (added after the question "are you sure this is optimal?") — no, and here is exactly where

A plan can only be shown optimal relative to an objective and a constraint set; here the objective is
max P(T) per unit of scarce resource (your minutes, compute, owner attention) under $0 and fail-closed truth.
Three parts of this plan are **forced** (every feasible plan contains them): a truthful verification carrier,
every zero-cost external ask sent immediately, and measurement before blind building. The rest is judgment.
Re-checking the judgment turned up four corrections, two of which change Wave 0.

**9.1 The carrier outage is endogenous and will recur (changes Wave 0).** Hosted runs in this repo succeeded
until 2026-10-13T15:12Z; billing refusals start in the same hour. Cause, from the Actions API: 314 workflows,
180 of them `pull_request`-triggered and 199 `push`-triggered (branch/path filtered); this month the API
reports ≥ 2,500 push runs and ≥ 2,500 PR runs (the count is capped), while `main` received 689–1,779 commits
per day on 10-07…10-11. Each run lasts ≈ 15–18 s but is billed as ≥ 1 minute per job, so the fan-out costs
≈ 100 billable minutes per PR update against a 2,000–3,000-minute monthly allowance on a User account. A single
push of this branch today triggered 26 runs. Consequence: **fixing billing (U1) alone restores the carrier for
roughly one to two days at the 10-13 activity level.** Add to Wave 0: consolidate the per-PR verification
fan-out into one job (the whole `canonical/tests` suite runs in ≈ 8 min on 2 cores, i.e. ≈ 3–5 billable
minutes on a 4-core hosted runner, versus ≈ 100 for the fan-out) — a ≥ 20× cost reduction with identical
commands as steps. This touches verification semantics (one receipt per PR instead of ~100), so it is your
call; I can implement it in under an hour once you say which form you want.

**9.2 The public carrier may still be alive (1-minute check, changes U1's urgency).**
`moxnixmdj/verification-capsule-runner` (public) ran successfully at 2026-10-12T06:24Z, before the lock began;
public repositories do not consume paid minutes, but an account-level payment lock can still disable them.
Re-running its latest workflow from the GitHub UI tells us in one minute whether independent verification is
blocked at all. If it runs, A1 (promotion of the two 24/24 objects), TB-Science public-envelope slots and the
Chartography/OSWorld measurements can proceed without waiting for billing.

**9.3 The Brain cannot currently plan for itself.** `one_shot_sky_impact_planner_v1/_executor_v1` raise
`PostCompositionFrontierV2Error: R2_SCHEDULER` at HEAD, and the reality-closure V2 reports a PASS fixed point its
own test says is wrong. "Use all the Brain's capability" was therefore bounded by the Brain's own incoherence;
the ten deterministic test failures in §7 are the repair list, and they precede any Brain-generated plan.

**9.4 Re-ranking inside Wave 1.** TB-Science (70 tasks) and TB4 (public task set) need **no** gated bytes — their
only blockers are compute and capability. Chartography and OSWorld need U3. So the internal step with the
fewest dependencies is a TB-Science or TB4 tranche on whatever carrier is alive, not Chartography; Chartography
stays the fastest route to a *complete-benchmark* number once the token exists. The §5 probabilities are
predictions with roughly ± 1 order of magnitude per term; the conclusion they support (not in 2026 under the
frozen predicate) is insensitive to that, the ordering of A2–A6 is not.

What did not change on re-audit: P(T ≤ 40 min) = 0; the four-kind classification in §1; the finding that
the suite's green is partially virtualized (R5); the user-only actions list; zero credit claimed.
