# The five logged failures: wired, run, still unsolved

**Date:** 2026-11-24. **Branch:** `arena/3fc9b5f0-brain`. **No merge.** §6 remains unmet.

## Requirement resolution applied

Own model core only; zero runtime model calls; no knowledge house in parameters; external, editable typed store; computed/justified parameters; project-first then web research; minimal first-principles design; hardest ungated tests; honest receipts. The prompt's date `10/11/2026` is an unverified input and is overridden by the system date **2026-11-24**. Quoted iterations, hashes, benchmark scores and frontier names are inputs to verify, not facts.

## Identifier audit (project searched first)

| quoted identifier | audited status |
|---|---|
| `209bbc6c` / "Iteration 75" | not a git object in this checkout; only repeated as a quoted claim in our own prior report — **unverified** |
| `__CST_ID0__`, `FOREIGN_IDENT_UNBOUND`, `BELIEFWEAVER` | no source file found; only quoted in our prior report — **unverified** |
| `BRAIN_POLYGLOT_CST_SKILL_STORE_V1`, `verified_skill_crystallizer_ir_bridge_v1` | no matching file found; only quoted — **unverified** |
| `typed_invention_v1.py`, `epistemic_scan_acquire_compress_v1.py` | named files **absent**; generic `canonical/runtime/epistemic_closure_kernel_v1.py` and `canonical/tools/swebench_verified_epistemic_adapter_v1.py` do exist |
| `same_identity_supervisor.py` | found at `canonical/runtime/same_identity_supervisor.py` |
| `consistency_vs_equivalence` | found at `canonical/swe_kernel/consistency_vs_equivalence_v1.py` |
| `HONEST_SUITE_BASELINE` / 344 failing cases | quoted in `README.md` and analysis reports; the 344-case manifest is not present as a runnable artifact here — **unverified** |
| `cJSON_Utils.c:285`, more-itertools/pyjwt multi-function cases | cited in reports; no corresponding source case file found in this checkout — **unverified** |

Because `typed_invention_v1.py` does not exist, the requested wiring was made into the real entry point `canonical/swe_kernel/witness_inversion_v1.py`: a `use_mining=True` arm now runs repo-native component mining plus dual-program splicing after direct witness inversion, and verifies proposals with the project's own pytest runner. Environment passthrough was fixed so the child oracle can actually import pytest in this sandbox.

## Real-run result on the five named commits

Each commit was reconstructed from its parent worktree plus the real post-commit test file. **No gold patch, commit diff, model, network-at-solve, or stored parameter was used.** The first genuinely failing test was the oracle, and the full test file decided every proposal.

| commit | real oracle | wired witness+mining+splicing | repo miner |
|---|---|---|---|
| click `c53d3732b98c` | `test_show_envvar_empty[...]` (9 failures in file) | `REFUSED__NO_INVERTIBLE_SITE` | 0 terms, no verification |
| click `05f6fd0df4ec` | `test_argument_get_help_record_never_none[None]` | `REFUSED__NO_INVERTIBLE_SITE` | 0 terms, no verification |
| click `fc518e41218b` | `test_interrupt_while_reporting_abort[prompt-1]` | `REFUSED__NO_REPORT` | 0 terms, no verification |
| werkzeug `884437aef93e` | `TestNoDomainMatching::test_build_relative` | `REFUSED__NO_REPORT` | 0 terms, no verification |
| werkzeug `051fd66352cf` | `TestHTTPUtility::test_www_authenticate_header` | `REFUSED__NO_REPORT` | 0 terms, no verification |

**Result: 0/5 repaired; 5/5 real oracles; 0 model calls, 0 network calls, 0 stored parameters, 0 gold-patch reads.** Receipt: `canonical/verification/WIRED_FIVE_LOGGED_COMMITS_20261124_V1.json`. Reproducer: `canonical/tools/wired_commit_probe_v1.py`.

## Why the augmentation could not fire

The mining arm needs a failing/passing value pair. On these five tasks the witness inverter produced no captured witness (`NO_INVERTIBLE_SITE` / `NO_REPORT`), and pytest parameter acquisition produced no same-function contrast; consequently `mine_terms` received empty differential lists and returned zero terms. This is the same bottleneck measured earlier, now on the exact five logged failures: **candidate supply, not search or verification throughput**.

## Next bottleneck and rejected ideas

Next: obtain the differential from the failing test's runtime assertion state without using the answer, or derive a structural edit directly from the failing path. Rejected: wiring into a nonexistent `typed_invention_v1.py`; adding more fixed rules; reading the human patch to manufacture a differential; increasing CoW shard count (measured slower on 2 CPUs); counting quoted frontier scores as our capability.

Tests: `test_witness_inversion_v1.py` 18 passed after the wiring; static integrity guard previously reported 0 violations and will be re-run before any merge. No merge is appropriate while §6 is unmet.
