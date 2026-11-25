# Splicing is wired into the miner, but this corpus has nothing to splice

**Date:** 2026-11-24. **Status:** wiring regression FAIL 0/12 (same as before); no merge.

`canonical/swe_kernel/dual_program_splicing_v1.py` computes line-level edits of two candidate programs, combines non-overlapping edits, and accepts a splice only when the project's own pytest runner verifies the union of the test partitions each candidate fixes. `canonical/swe_kernel/repo_native_component_mining_v1.py` now calls it when a candidate fixes a strict subset of failing tests without breaking a stable passing test and a second candidate fixes a different subset.

Regression on the 12 already-used click commits:

| arm | verified | rows with partial candidates | spliced and verified |
|---|---:|---:|---:|
| imported-module control | 0/12 | 0 | 0 |
| repo-mined treatment | 0/12 | 0 | 0 |

The splicing branch therefore never fired on real data. Its mechanism is separately verified by `canonical/tests/test_dual_program_splicing_v1.py`: two candidates that each fix one of two tests are spliced, and the combined program passes both after verification; the parent file is restored.

This is integration work, not a capability gain. The remaining blocker is still candidate supply: neither pytest parameter acquisition nor strict manufactured contrasts produced a candidate that fixes any subset of a real failing test on this corpus.

Receipt: `canonical/verification/REPO_NATIVE_WITH_SPLICING_REGRESSION_20261124_V1.json`. Tests: 3 splicing OK, 5 miner OK.
