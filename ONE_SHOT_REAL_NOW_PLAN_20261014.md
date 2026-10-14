# REAL-NOW PLAN — 2026-10-14 (Arena session, branch arena/b129ad9d-brain)

**Classification:** PLANNING ARTIFACT — NOT CANONICAL AUTHORITY. Zero credit claimed. Every number below is either (a) read live from the repo or GitHub on 2026-10-14 10:30 UTC, (b) recomputed in this session, or (c) an explicitly labelled repo self-estimate. Nothing here is a probability dressed up as a fact.

---

## 0. Verdict first (what "real now" can and cannot mean)

**The terminal goal cannot become real in 30–40 minutes. Probability ≈ 0, and this is provable, not a matter of effort.**

Terminal = (19/19 families accepted) ∧ (8/8 meta) ∧ (donor requalified 10/10) ∧ (aggregate predicate) ∧ (global postconditions). Live gate today: 7/19 owned, 12 open, donor authority revoked, meta 8 open.

The single term that rules out "now" is the Terminal-Bench 4.0 coding predicate, computed here:

- Required: ≥219 successes of 220 creditable trials (44 reopened tasks × 5), slack 1.
- P(≥219 of 220 | per-trial success p), binomial, computed in this session:

| per-trial p | P(≥219/220) | P(≥219/225) | Source of p |
|---|---|---|---|
| 0.664 | 8.5e-38 | 2.9e-31 | Opus 5.5 published TB4 task-level |
| 0.973 | 0.0172 | 0.594 | repo's lower requirement |
| 0.990 | 0.353 | 0.992 | — |
| 0.995 | 0.699 | 0.9998 | repo's upper requirement |

Meaning: at Opus 5.5's own rate, the predicate is unreachable by any amount of effort. It needs roughly p ≥ 0.99 per trial, which the brain has not measured on any TB4 task.

**Correction to my previous answer.** I repeated the repo's "≥55 wall-hours on a 16-core carrier" floor. That floor assumes every trial occupies all 16 cores. The repo's own data does not support that: `TB4_FULL_CARRIER_COMPATIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json` reports only 12 of 66 tasks exceed the standard 4-CPU runner, and `TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1.json` lists their per-task CPU needs. If the other 54 tasks fit under 4 CPUs, wall time at 4-way concurrency is about 220 × 15 min / 4 ≈ 14 h (estimate; assumes memory fits, 16 GB/task). That is still not "now", and the per-trial success term above still binds. The 55-hour figure should not be quoted as a hard floor.

**What CAN be real within the hour** is narrower: reproduced truth, unblocked carriers, repaired red tests, and the first measured brain-owned numbers. Those are listed in §2 with their gate impact.

---

## 1. The measurement rule (your principle, made mechanical)

A benchmark result counts toward ownership only if all of these hold. Each is checkable in the repo:

1. **Output-defined.** The scorer and the exact task identities are pinned by hash (the TB4 universe is already pinned to release commit `452bf305…` in `TB4_EXACT_66_TASK_TARGET_SCOPE_20261008_V1.json`).
2. **Brain-operative route.** The route that produced the output is a Brain-owned configuration with zero model calls on the operative path. The repo states this is currently **unproved**: the 2026-10-11 donor invalidation (`CAPABILITY_TRANSFER_V2_DONOR_AUTHORITY_INVALIDATION_20261011_V1.json`) revoked donor authority because "network denial does not exclude a local copied or rehosted general-purpose model." This is the real first-principles gap. Every "Brain passed" claim is conditional on it.
3. **Matched comparator.** Opus 5.5 at the same effort setting. Anthropic's TB4 66.4 is at xhigh; the default effort is medium; Artificial Analysis's independent run is 59.6. Any bar comparison must state which effort it uses.
4. **Hidden-scorer identity.** Result is the scorer's output on the frozen task set, not a proxy or a sample chosen after the fact.

Under this rule, the existing "PASS" claims for 7 families are only as strong as the donor-independence proof, which is currently revoked. That is why the gate reads 7/19 and not 19/19.

---

## 2. The plan: steps, mechanisms, impact

Each step names the existing Brain asset it reuses, the gate predicate it moves, its cost, and its probability with basis. Impact is stated as predicates moved, since credit is zero until independent promotion.

### Phase U — user-only actions (minutes, $0)

| ID | Action | Unblocks | P(effect) | Basis |
|---|---|---|---|---|
| U1 | GitHub → Billing & plans: fix failed payment, or leave $0 limit and wait for reset. Do not raise the limit if it risks spend. | Hosted Actions for all 314 workflows, including the PR-target guards that currently fail with 0 steps | 0.75 | Repo, C1 in previous answer |
| U2 | Approve sending the drafted AA-Briefcase follow-up | Only route to AA-Briefcase ≥1822 (1 truth) | 0.20 reply in 14 d, 0.30 in 30 d | Repo, 0 of 3 replies to date |
| U3 | Tell me CPU cores and RAM of the machine that would host the `brain-regression` runner, and whether it is online | Decides self-hosted full regression and the TB4 carrier option | — | Repo: runner not visible to my token (HTTP 403) |
| U4 | Ubuntu-26 pin decision before **2026-10-19** (275 of 314 workflows use `ubuntu-latest`) | Keeps verification surface alive | — | Live `ubuntu-latest` count |

### Phase A — agent steps, zero spend, start now

| ID | Step (reused asset) | Predicate moved | Time | P(success) | Impact |
|---|---|---|---|---|---|
| A1 | Reproduce the reality gate and focused tests | Confirms state | **done this session** | — | `test_terminal_reality_gate_v1.py`: **8 passed**. `test_bytes_canonical_wiring.py`: **2 failed** (stale V9 expectations vs V10 pointer; the repo confirms the same failure on main). 0 credit. |
| A2 | Repair the 2 stale Bytes wiring tests against the live pointer (truth repair, not new capability) | Green focused suite | 30–60 min | 0.90 | Removes a known red. 0 credit. |
| A3 | Recompute TB4 carrier floor from per-task CPU metadata only (no instructions, solutions, or tests read — the repo's own exposure rule) | Replaces the overstated 55 h with a measured floor | 1–2 h | 0.80 (data available in task metadata) | Corrects the timeline, which is currently overstated. Reopen condition for TB4 attainability. |
| A4 | Donor requalification: complete census + dependency inventory under `DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V2` | Donor authority; 2 invalidated gate predicates (global postconditions, donor cleanroom) | 2–5 d | census 0.80; all 10 requirements pass 0.60 (repo estimates) | Without it, the terminal predicate fails even at 19/19 acceptance. |
| A5 | Bind the HLE-with-tools harness (public MIT) and run capability propositions before any score claim | MULTIDISCIPLINARY family measurement | ≤2 d | 0.80 harness binding (repo) | Creates the first brain-owned measurement for a family with no owner dependency. Bar 67.7 is not yet reached. |
| A6 | Necessity-countermodel sweep, executed rather than just classified | Possible truth deletions | 1–2 d | E[deletions] 1.47 (repo audit `NECESSITY_COUNTERMODEL_AUDIT_20261014_V1.json`) | Only a verified falsifier deletes a truth. The audit itself deleted nothing. |
| A7 | Five domain-mapping certificates (CYBERSECURITY, BIOLOGY_R&D, AUTOMATED_AI_R&D, HEALTHCARE, ARXIVMATH) via the frozen envelope audit V6 | 5 of 8 meta | 1–3 d | repo estimate 0.75 each | Pure internal; low external dependency. Each still needs independent verification. |
| A8 | Verify the 12 open families' acceptance predicates one at a time with exact oracles, via `verified_improvement_loop_v2` (branch-and-verify, rollback) | 12 open families | Continuous | not estimable from the repo | This is the real capability work. No family is closed by reading receipts. |

### Phase G — gated on U1/U3

| ID | Step | P(effect) | Impact |
|---|---|---|---|
| G1 | Drain the full private regression on the self-hosted runner (or PR-transported capsule shards first, as the repo's own adversarial review proposed) | pass 0.70 (repo); capsule pre-clear could cut failure to ~0.15 (repo, unverified) | Unblocks promotion of Professional 24/24 and Assurance 24/24 |
| G2 | Promote those two families through existing gates | 0.85 given G1 green (repo) | Two families' promotion preconditions |

### Phase X — external and final

| ID | Step | Gate |
|---|---|---|
| X1 | Owner channels (AA-Briefcase, GDPval-AA, FrontierCode, CursorBench, AutomationBench) | Owner replies. Base rate 0 of 3 in 8 days. Composite P(≥1 channel open in 30 d) = 1 − 0.70·0.75·0.80·0.80·0.75 = **0.748** (repo channel estimates, recomputed here) |
| X2 | TB4 execution (220 trials) | Requires U3 carrier + A3 measured floor + measured per-trial p ≥ ~0.99 (from A8). At p = 0.664 the predicate is unreachable |
| X3 | TB-Science slots (0 of 14 successes; no rerun authority) | Each slot preceded by the improvement loop |
| X4 | MysteryMechanism private 222-score | External; not derivable from public data |
| X5 | Final proof bundle rebuild and independent finality reducer | Only after all above |

---

## 3. Aggregate, honestly

- **Within 40 minutes:** the reachable set is U1–U3 (user), A1 (done), A2, and the start of A3. Impact on the terminal predicate: zero. Impact on truth and unblocking: real.
- **Within 2–5 days, if U1 and U3 happen:** A3, A4, A5, A7 and G1 can complete. This could move the gate from 7/19 toward a larger number, but the 12-family acceptance is not closed by any step above alone.
- **Terminal:** the repo's own estimate is P(≤45 d) ≈ 0.02–0.05 and P(≤120 d) ≈ 0.08–0.15. I did not improve on those numbers. The binding terms are per-trial success on TB4 (A8 must measure it), owner-reply latency (X1), and the donor requalification (A4).

---

## 4. Immediate execution (in order)

1. **You:** U1 (billing check), U3 (runner host specs), U2 (approve AA send) — ~5 min.
2. **Agent, now:** A2 (fix stale Bytes tests), A3 (measured TB4 floor from per-task CPU metadata).
3. **Agent, next:** A4 (donor census), A5 (HLE harness binding), A7 (domain mappings).
4. **Agent, after U1/U3:** G1 (regression or capsule shards), then G2.
5. **Continuous:** A8 with exact oracles; X1 owner channels; X2–X5 only when their inputs exist.

## 5. What would falsify this plan

- A3 finds that more than 12 tasks exceed 4 CPUs, which would restore the carrier constraint.
- A4 finds a model dependency in the operative route, which would revoke the brain's claim to every family it has passed.
- A8 measures per-trial p below 0.9 on the TB4 task set, which would close the TB4 predicate at any budget.
- U1 reveals a non-billing policy block on Actions, which would move G1 to a permissions diagnosis.

## 6. Source notes and conflicts

- The "Astra HLE with tools 82.9" figure in the repo appears to be HLE-Diamond. Public tables list HLE-with-tools for Opus 5.5 at 67.7 and Astra at 57.2. The two must not be mixed.
- The plan documents cite `main` at `5ec8b7d`; live `main` is `11d4d83`.
- Issue #3739 is still open despite a repo note that it was repaired; the token lacks `issues:write`.
