# SWE_SELF_IMPROVEMENT_BRIDGE_20261112_V1.md — re-measured, 2026-11-12 (seventh asking)

**2026-11-12.** Branch `arena/ab235d52-brain`, forked from `537368bb` (main).
Authority: **NONE**. `truth.achieved` stays `false`. $0 spend. Zero model dependency.

The owner re-sent the same verbatim question for the seventh time; main contains a claim
many readers will now read as *"the loop works"*: `canonical/swe_kernel/swe_self_improvement_bridge_v1.py`
(#6769) reporting an end-to-end teach → cross-scope recall → induce → unseen-scope reuse
sequence. Nobody had re-run it. This is the second run, on a fresh checkout of the merged
tree, by a session that did not write the bridge.

## 1. Reproduction check (2026-11-12, this branch)

Command: `python3 canonical/swe_kernel/swe_self_improvement_bridge_v1.py --json`

| Endpoint | #6769 reported | This run | Match |
|---|---|---|---|
| ep_swe_1 status | `VERIFIED_EPISODE_PERSISTED__MORE_EVIDENCE_NEEDED_FOR_SKILL` (skill `skill_54cbfc801c82ee777bf3a0f4`, recheck 1 PASS / 0 FAIL) | identical values, `recheck_counts {PASS:1, FAIL:0, ABSENT:0}`, `verified_episode_count=1`, `active_skill_count=0` | **yes** |
| ep_swe_2 status | `VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE` (`skill:dd9f1d8f…c6bd748`) | identical; `verified_episode_count=2`, `active_skill_count=1`, `verified_skill_count=1` | **yes** |
| ep_swe_3 check | `reuse_first=True`, `fallback_used=False`, `successes=1`, reuses ep_swe_2 skill | identical; `reuse_stats {attempts:1, effectful_failures:0, pre_effect_failures:0, successes:1}`, `verified_episode_count=3`, `verified_skill_count=2` | **yes** |
| CF1 broken candidate | `REFUSED__CRYSTALLIZE_FAILED:TRAINING_VERIFICATION_FAILED` | identical | **yes** |
| CF2 overfit constant | `REFUSED__CRYSTALLIZE_FAILED:ORACLE_PROBE_BREAKS:3_OF_4_FAILED` | identical | **yes** |
| CF3 passing baseline | `REFUSED__FAILING_TEST_BASELINE_REQUIRED` | identical | **yes** |
| CF4 corrupted rule, recall | `REFUSED__NO_VERIFIED_SKILL_RECALLED` | identical | **yes** |
| `truth.achieved` | false | false | **yes** |

**The reproduction matches exactly, including the four fail-closed counterfactuals.**

## 2. What this reproduction does — and does not — establish

Establishes, minimally and honestly:

- The code merged in #6769 is deterministic and honest on a second machine-shaped checkout:
  it does not "work on paper only."
- A real Python `unittest` suite, run as an isolated subprocess, can be wired end-to-end
  through `verified_skill_crystallizer_v1` → successor authenticated skill → unseen-scope
  reuse with no fallback and no human re-entry.
- Fail-closed gates in the negative paths still refuse: weak test, broken candidate,
  failing-baseline absent, corrupted store. This is the 2026 consensus position — the
  evaluator must sit **outside the optimization loop** — and it is satisfied here.

Does **not** establish:

- **Any persistence.** The run happens inside a `tempfile.TemporaryDirectory()`; its
  `SELF_IMPROVEMENT_STATE_V1.json` is created there and deleted when the temp dir dies.
  **No state file from that experiment has ever existed in this checkout** — nothing the bridge
  "learned" is in the repo — and the only contribution stored in-tree is numbers in merged docs.
- **Any real repair** — all three scopes are the discount-shaped rule `price + price//10 →
  price − price//10` (function names differ: `discount`, `apply_markdown`, `net_payout`).
- **Any capability claim.** Door admits 8/149 realistic sentences; 19/38 realistic
  advanced-coding goals still refuse with
  `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` (#6733, #6750);
  the corpus of real executed work is still **empty by construction** (532 receipts, 1 argument each;
  296 OIDC attestations, all zero-argument; 56 file-input capabilities × 0/56 fixture runs);
  claims ledger still **8/8 holds**, re-run 2026-11-12.
- **Continual reliability** — the November field's sharpest result says harness evolution
  itself forgets (Meta-Harness: SWT-bench 100% → 62% after evolving on FeatureBench; SWE-bench
  94% → 32% by round five — [arXiv:2611.03219](https://arxiv.org/html/2611.03219)). Nothing in
  a single subprocess loop addresses that; it addresses one scaffolded repair.

## 3. The one next experiment that would make this progress rather than a demonstration

Pre-registered here, **not executed this turn**: replay one *real* repair from this repo's own
history through the bridge — a merged PR whose body shows one failing→passing test, with the
pre-merge failing state reconstructed from the PR's parent commit, its tests pointed at the
unmodified package, and the post-merge package as the acceptance side — with **persisted state
committed under `canonical/runtime/state/`** (requires the owner's say-so on committing a state
file minted by an agent; three lines of provenance metadata inside the episode record keeps it
reviewable). Kill rule: any counterfactual refusal failing open, or any non-`verified` step in
the chain, and the replayed episode is discarded and the PR abandoned.

Until that pair exists, the honest summary remains:

> **The formal loop runs end-to-end on synthetic repairs (re-measured 2026-11-12); it has not
> persisted anything; it has not touched real repository code; the door still refuses the 19.
> The wall is admitted execution + an empty real-work corpus, not the learning algorithm.**

## 4. Standing invariants

No mechanism touched, no tolerance widened, no gate opened by this document. `truth.achieved`
false. $0. Authority NONE. The two owner decisions pending (#6750 §2.1 effect adoption; which
capabilities declare effects first) remain the only unblock of the permanent-capability claim.
