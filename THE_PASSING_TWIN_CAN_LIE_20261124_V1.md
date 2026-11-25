# The passing twin can lie: manufactured contrasts on 12 fresh commits

**Date:** 2026-11-24. **Status:** strict method FAIL (0/12 pairs, 0/12 repairs). **No merge.** All results are from real click commits with parent-source worktrees and the project's own pytest runner; no commit diff, model, network, or stored parameter was used.

## The chain of falsification

| variant | rule for accepting a FAIL→PASS twin | paired rows | verified repairs | seconds |
|---|---|---:|---:|---:|
| input-only | mutate a literal outside `assert` | **2/12** | 0/12 | 2555.6 |
| + path filter | also require *identical* source-file line set | **1/12** | 0/12 | 2971.7 |
| strict | also preserve truthiness | **0/12** | 0/12 | 2857.2 |

Budget per commit: 8 input literals × 16 one-character/one-unit mutations, 20 s oracle cap.

The two pairs in the first column were:

- `8d7f03dac873`, `test_empty_envvar[AUTO_MYPATH]`: `auto_envvar_prefix="AUTO"` → `"UTO"` / `" UTO"` / `"!UTO"`. The mutated prefix stops supplying the env var, so the test passes by no longer exercising the defect. Its executed `src/click/core.py` line set drops from **332 to 323 lines**; the path filter rejects it.
- `144f3701b231`, `test_show_default_precedence[True-False-False]`: `show_default=1` → `0`. The line set is identical (186 lines), but flipping truthiness disables the very option under test; the truthiness filter rejects it.

These are not repairs and not legitimate counterexamples. They are evidence that **a passing test obtained by weakening the input only proves the test was weakened**. This is why "manufacture a passing twin" cannot be accepted on verdict flip alone, even when the mutated literal is outside an assertion.

## What the implementation now does

`canonical/swe_kernel/manufactured_contrast_v1.py`:

1. collects only literals outside `ast.Assert` (an expected value is the specification, not an input);
2. excludes mutations that change `bool(value)`;
3. runs the real failing node and each candidate with pytest;
4. traces the exact source-file lines executed by a small pytest plugin (`sys.settrace`, JSON at teardown) and accepts a PASS twin only when its line set equals the failing run's;
5. only then hands the failing/passing values to repo-native component mining and verifies any candidate against the whole test file.

The earlier unrestricted variant (which could change expected values) was abandoned after this flaw was identified; its partial logs are not counted as a result.

## What this establishes and what it does not

- Established: computed filters can detect vacuous twins; a general one-literal manufacturer produces **zero admissible contrasts** on this 12-commit corpus; repository mining therefore has nothing to mine on those commits.
- Not established: that no real contrast exists for these bugs (a semantically informed generator might find one), that GUI/browser or unseen-environment transfer works, or any benchmark capability.
- Rejected idea, for now: scaling mutation count or adding more parsers. The missing ingredient is a constraint that keeps the specification and execution path fixed while changing the outcome; neither more mutations nor a bigger model (forbidden at runtime) supplies it.

## Files

- Receipts: `MANUFACTURED_CONTRAST_INPUT_ONLY_20261124_V1.json`, `MANUFACTURED_CONTRAST_PATH_FILTERED_20261124_V1.json`, `MANUFACTURED_CONTRAST_STRICT_20261124_V1.json` in `canonical/verification/`.
- Unit checks: `canonical/tests/test_manufactured_contrast_v1.py` → 5 OK.
- Related earlier falsifications: `PYTEST_KNOWS_THE_PARAMETERS_BUT_NOT_THE_CONTRAST_20261124_V1.md`, `REPO_NATIVE_COMPONENTS_ARE_NOT_ENOUGH_20261124_V1.md`.
