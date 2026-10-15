# Failure root-cause profile (Phase C) — 344 honest-suite failures

Date: 2026-10-15. Source: HONEST_SUITE_BASELINE_20261014_V1.json (11525 cases, 11166 pass, 344 fail, 1 error, 14 skip).

## Buckets

| Bucket | Count | Likely root cause | Fix strategy | Est. effort |
|---|---|---|---|---|
| ASSERTION | 245 | Real assertion failures (logic/contract) | Per-family fix of runtime code or governance docs in the open | 1–2 weeks |
| CURRENTNESS_GUARD__DRIFT | 34 | Stale pointer / currentness drift | Reconcile stale pointers to current authority | 1–2 days |
| OTHER | 31 | Unclassified | Investigate per file | 2–4 days |
| CURRENTNESS_GUARD__SOURCE_BLOB_DRIFT | 16 | Pinned blob sha stale (registry/adapter/kernel changed) | Reconcile blob shas in verification files | 1–2 days |
| IMPORT_ERROR | 15 | Missing module/import path | Fix imports or add deps | 1 day |
| NETWORK | 3 | Network access (env) | Env/fixture; may be env-blocked | 1 day |
| MISSING_FILE | 1 | Missing file | Create the file | 0.5 day |

## High-leverage batches

- **Batch 1 (governance currentness):** 34 + 16 = 50 failures. Likely fixable by reconciling stale pointers and blob shas to current authority. Effort 2–4 days. Impact: 344 → ~294.
- **Batch 2 (imports + missing file):** 15 + 1 = 16 failures. Fix imports and create the missing file. Effort 1–2 days. Impact: 294 → ~278.
- **Batch 3 (network):** 3 failures. Env-dependent; may need fixture changes. Effort 1 day. Impact: 278 → ~275.
- **Batch 4 (OTHER):** 31 failures. Investigate per file. Effort 2–4 days. Impact: 275 → ~244.
- **Batch 5 (assertions):** 245 failures. The real backlog. Per-family fixes. Effort 1–2 weeks. Impact: 244 → 0.

## Honest ceiling

- 66 failures (50 + 16) are governance/currentness — likely clearable in 4 days.
- 245 assertion failures are the real backlog — 1–2 weeks of per-family work.
- Total: ~2 weeks to green, not 344 individual fixes.

## What I will NOT do

- Touch the test harness, conftest, or pins (AGENTS.md rule 1).
- Widen tolerances (NEVER_WIDEN_THE_TOLERANCE).
- Claim "all green" via any mechanism other than re-measurement with honest_suite_baseline_v1.py.
