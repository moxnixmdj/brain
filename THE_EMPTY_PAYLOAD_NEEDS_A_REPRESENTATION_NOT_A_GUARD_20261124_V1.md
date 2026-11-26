# The empty payload needs a representation change, not just a guard

**Date:** 2026-11-24. **Branch:** `arena/3fc9b5f0-brain`. **No merge.** §6 remains unmet.

## The loop

The expected/actual differential on click `c53d373` showed that the failing test expected `'  --units TEXT\n'` while the program emitted a help row containing `[env var: ]`. A runtime trace of empty local values (`canonical/swe_kernel/empty_payload_suppression_v1.py`) found the empty `envvar` payload at line 3450 of `src/click/core.py`, and AST tightening generated the exact guard change:

```
if envvar is not None:   ->   if envvar:
```

That change makes the two target help tests pass. It also breaks **7 other tests** in the same file, because the same `envvar` value is used to build the error hint, where a tuple must be joined rather than rendered by `repr`. Applying the analogous tightening to `self.envvar` at line 3273 reduces the breakage to 5 tests but still fails: the representation of the tuple-valued envvar is wrong.

## Measured result

| repo | commits | observed empty payloads | guard/splice candidates | verified repairs |
|---|---:|---:|---:|---:|
| click | 3 | 391 | 70 + 35 splices | 0 |
| werkzeug | 2 | 152 | 5 | 0 |

Receipt: `canonical/verification/EMPTY_PAYLOAD_SUPPRESSION_20261124_V1.json`. Reproducer: `canonical/swe_kernel/empty_payload_suppression_v1.py`. Tests: `test_empty_payload_suppression_v1.py` 3 passed, including a real tiny repository where the same tightening is verified by pytest.

## What this establishes

- Runtime observation of an empty payload can find the precise guard that admits an undesired decoration. This is computed from execution, not from the commit diff.
- The exact locally correct guard exists in the proposal set and was found.
- Whole-file verification nevertheless rejects it. The bug is a **representation/transition** problem across call sites (help text vs error hint), not a missing boolean check. This is a concrete instance of the 75.2% wall: the needed change spans multiple producers of the same value.

## Rejected next moves

- More guard variants at the same site: the correct guard is already present and is insufficient by measurement.
- Reading the human patch or adding a click-specific rule: leakage and rule accumulation.
- Treating the two help tests passing as success: the project's whole test file is the authority.

Next loop must compose a typed transformation over both producers (join/format semantics for string vs tuple envvar), verify the composed patch on the whole file, and only then crystallize a generalized rule. §6 remains open.
