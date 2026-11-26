# The expected output is a literal hole — but blind insertion is not enough

**Date:** 2026-11-24. **Branch:** `arena/3fc9b5f0-brain`. **No merge.** §6 remains unmet.

## The new bottleneck experiment

The five logged failures had already been run through witness inversion + repo mining + splicing: **0/5**, because no assertion witness was captured and no parameter contrast existed. Rather than invent a rule, I asked: can the assertion itself give us the differential?

`canonical/swe_kernel/assertion_operand_tomography_v1.py` rewrites comparison operands **only in a throwaway worktree** with a recorder that returns the original object (`_brain_record(key, value) -> value`). The assertion verdict is unchanged; a pytest plugin writes the operand reprs. The uninstrumented file remains the oracle.

`canonical/swe_kernel/expected_actual_literal_v1.py` then computes the differing substrings by sequence alignment, proposes edits to trace-executed source string literals, and accepts only when the project's whole test file passes.

## Measured result on the same five exact commits

| commit | operand capture | string differential | literal candidates tried | repaired |
|---|---|---|---:|---:|
| click `c53d3732b98c` | CAPTURED | yes | 24 | 0 |
| click `05f6fd0df4ec` | CAPTURED | none usable | 0 | 0 |
| click `fc518e41218b` | CAPTURED | none usable | 0 | 0 |
| werkzeug `884437aef93e` | CAPTURED | none usable | 0 | 0 |
| werkzeug `051fd66352cf` | CAPTURED | yes | 24 | 0 |

**0/5 repaired.** All five oracles were real; no gold patch, diff, model, network-at-solve, or stored parameter was used. Receipt: `canonical/verification/WIRED_FIVE_LOGGED_COMMITS_20261124_V2.json`. Reproducer: `canonical/tools/wired_commit_probe_v1.py`.

## What this establishes

- A computed, verdict-preserving instrumentation can recover the operands of a real failing assertion even where the earlier witness plugin returned `NO_REPORT` (5/5 captures).
- A string differential can be computed from those operands without reading the answer (2/5 commits).
- Naive literal insertion/replacement from that differential does **not** repair these bugs: 48 candidates, 0 verified, with stable-passing tests explicitly protected.

A third loop then localized the runtime producer of the observed value with `canonical/swe_kernel/value_producer_localization_v1.py` (a source-frame tracer that admits only frames holding the observed value). It narrowed trace-executed string holes from 24 to **4** on `c53d3732b98c` and from 24 to **14** on `051fd66352cf`, and added whole-producer-expression replacement. **Still 0/5 verified** (`canonical/verification/WIRED_FIVE_LOGGED_COMMITS_20261124_V3.json`): narrowing the site is not the same as knowing the transformation that builds the expected output.

The missing part is still not throughput. For `c53d3732b98c`, the expected output contains a rendered help fragment while the source literal is a template/format string; the needed edit is structural (how the envvar text is assembled), not a single concatenated substring. For the auth case, the difference is a trailing space produced elsewhere than the candidate literal. This is the same 75.2%-wall observation in concrete form: the value is known, the *production path* for the value is not.

## Rejected ideas, recorded

- More literal insertions or a larger candidate budget: the two usable differentials were exhausted at 24 candidates each with no verified patch.
- Reading the commit diff to identify which literal to edit: forbidden leakage.
- Wiring into `typed_invention_v1.py`: that file does not exist in this checkout; the real entry point `witness_inversion_v1.py` was wired instead.
- Counting the quoted 344-case baseline or cJSON case as tested: neither has a runnable manifest here.

## Tests and next loop

`test_assertion_operand_tomography_v1.py` 3 passed; `test_expected_actual_literal_v1.py` 3 passed; `test_witness_inversion_v1.py` 18 passed. Next: use the captured operands to locate the **producer** of the actual value in the Semantic IR and synthesize at that site, instead of editing every trace-executed literal. That is the first-principles reframe; no new fixed grammar is added.
