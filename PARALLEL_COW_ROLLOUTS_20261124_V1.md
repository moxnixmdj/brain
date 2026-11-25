# Parallel CoW rollouts: the mechanism works, the 16-way speedup does not

**Date:** 2026-11-24. **Status:** mechanism PASS; performance claim FAIL on this hardware. **Branch:** `arena/3fc9b5f0-brain`. No merge.

## What was changed

`canonical/swe_kernel/cow_impact_repair_engine_v1.py` now evaluates a patch batch in parallel CoW forks:

- `partition_candidates()` distributes candidates round-robin while keeping their **global** indices, so a winner from shard 9 still reports the index the repair loop needs.
- `evaluate_patch_batch_in_cow_zygote(..., parallel_shards=16, timeout_s=30)` uses `ZygotePrewarmedPool.run_parallel_sharded`, takes the first verified shard, and cancels/reaps siblings. `parallel_shards=1` preserves the old sequential path.
- When pytest is needed, each shard receives its own zero-copy hardlink clone, so concurrent `cow_write_text` calls cannot race on the shared worktree.
- `ZygotePrewarmedPool(prewarm_enabled=False)` adds a model-free pool for the benchmark. Evaluation itself reads no weights and calls no model; the repair engine's existing caller may still pass a prewarmed pool, which is recorded as an existing dependency, not credited to this mechanism.

## Hard measurements

Two receipts, same two fresh click commits, 16 generated AST candidates each (diagnostic only — none is a real fix):

| shards | mechanism gates | mechanism speedup | real commit `8d7f03dac873` seq → par | `e00333155105` seq → par |
|---|---|---|---|---|
| 16 | PASS (M1–M4) | **0.377×** (21.8 → 57.9 ms) | 1650.8 → 2363.9 ms | 1409.3 → 2321.7 ms |
| 2 | PASS (M1–M4) | 1.035× (25.9 → 25.0 ms) | 566.2 → 611.5 ms | 662.0 → 639.4 ms |

The winner attribution test is explicit: with 16 candidates, only candidate 7 passes; both sequential and parallel rollouts report global index 7, not shard-local index 0, and the parallel arm cancels the remaining 8 sibling forks.

`nproc` reports **2 logical CPUs**. Sixteen forked pytest runners are oversubscribed; the proposed "16-way" setting is slower here. This is a measured hardware limit, not evidence that 16-way is generally useless on a 16-core machine, and no such claim is made.

## What this does and does not establish

- Established: parallel shard dispatch, isolated workspaces, correct global winner attribution, sibling cancellation, model-free evaluation, and honest accounting of candidates evaluated.
- Not established: any repair. Both real arms found **0/16** candidates that pass the failing test. Parallelism accelerates a search only after the search can generate a candidate that can pass; neither the repo miner nor the manufactured contrast has yet supplied one.
- Not established: ungated benchmark capability, GUI/browser transfer, or unseen-environment behavior.

## Files

- Receipts: `canonical/verification/PARALLEL_COW_ROLLOUTS_20261124_V1.json`, `canonical/verification/PARALLEL_COW_ROLLOUTS_2_SHARDS_20261124_V1.json`
- Reproducer: `canonical/tools/parallel_cow_rollouts_benchmark_v1.py`
- Unit checks: `canonical/tests/test_parallel_cow_rollouts_v1.py` (3 tests OK); existing zygote tests 5 OK.
