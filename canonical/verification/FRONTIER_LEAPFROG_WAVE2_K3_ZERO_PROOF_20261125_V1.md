# Frontier Leapfrog Wave 2 (`K3 = 0`) — Empirical Measurements & Negative Bounds (`2026-11-25`)

- **Authority**: `NONE` (Arena sandbox measurement receipt; independent external verification remains open).
- **Model Dependency Count**: `0` (`0` external LLM API calls, `0` local neural weights, `$0.00` incremental spend).
- **Receipt Bundle**: `canonical/verification/frontier_leapfrog_wave2_k3_zero_20261125_V1.json`
- **Base Commit**: `b28dffd863a00fca76e52fc09f16c1f5edc08b44`

---

## 1. Play A — Witness-Conditioned AST Discrimination-Tree Router & Rubin Counterfactual Utility Gate
**Module**: `canonical/runtime/counterfactual_discr_tree_skill_router_v1.py`

### Part 1: Empirical `189`-Commit Syntax-Only Negative Bound
Audited all `189` real OSS single-line commits (`canonical/corpus/single_line_fix_candidates_20261123_V1.json` [`181` tasks] + `canonical/corpus/heldout_unseen_repos_20261124_V1.json` [`8` unseen-repo tasks]):

| Metric | Measured Value |
| --- | ---: |
| Total OSS commits audited | `189` |
| Parseable single-line Python statement pairs | `142` |
| Distinct non-identity AST alpha-skeleton rewrites (`old_skel != new_skel`) | `95` |
| Non-identity AST alpha-skeleton rewrites repeating `>= 2` times across `189` commits | **`0`** |
| Specific guard families repeating `>= 2` times (`IF_GUARD_CONJUNCT_STRENGTHEN:Compare:1_TO_2`: `3`, `IF_GUARD_CONJUNCT_STRENGTHEN:Name:1_TO_2`: `2`, `STATIC_STR_TO_FSTRING_DIAGNOSTIC:Assign`: `2`) | `3` |

**Conclusion**: Bare syntax-only triggers (`old_line -> rewrite`) without a runtime failure witness either abstain everywhere (`0` repeating non-identity skeleton rewrites across `189` commits) or collide with healthy code (`If(test=$v0)`). Transferable skills must key on `(failure_witness_kind, preorder_ast_keys...)` and earn admission via live `(WITH, WITHOUT)` execution.

### Part 2: Witness-Conditioned `AstDiscrTree` + Rubin `(WITH, WITHOUT)` Counterfactual Gate

| Benchmark Arm | Precision | Defective Repaired | Safe-Code Regressions | Wasted Fires | Net Causal Utility |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ungated Held-Out Split B (`24` probes) | `0.500` | `12 / 15` (`0.800`) | `9 / 9` | `3` | `+2.25` |
| Counterfactual-Gated Calibration Split A (`16` probes) | **`1.000`** | **`10 / 10`** (`1.000`) | **`0 / 6`** | **`0`** | **`+10.00`** |
| Counterfactual-Gated Held-Out Split B (`24` probes) | **`1.000`** | **`15 / 15`** (`1.000`) | **`0 / 9`** | **`0`** | **`+15.00`** |

- **Convicted skills**: `4 / 9` quarantined (`3` `CONVICTION_SAFE_CODE_REGRESSION`, `1` `CONVICTION_NON_POSITIVE_MARGINAL_UTILITY`); `5 / 9` retained; `split_ab_sign_flip = false`.
- **Retention replay**: `15 / 15` (`1.000`) under matching `rule_expiry_v1.world_fingerprint()`.
- **`1,086`-rule scaling benchmark**: `AstDiscrTree` p50 lookup **`5.427 us`** vs linear scan p50 **`34,697.603 us`** (**`6,393.51x` speedup**, well below the `50.0 us` kill ceiling).

---

## 2. Play B — Verified Zero-Screenshot Data-Layer Elevator & Pre-Probe CDP Action Cache
**Module**: `canonical/runtime/verified_zero_screenshot_action_cache_v1.py`

| Subsystem / Metric | Measured Value | Kill Threshold |
| --- | ---: | --- |
| Screenshots captured | **`0`** | `== 0` |
| Tier-0 real file/DB workflows verified (`sqlite3` WAL DB, OOXML `.docx` `word/document.xml`, JSON config) | **`3 / 3`** | `>= 3` |
| Tier-0 median execution + state-verification latency (`tier0_p50_ms`) | **`1.1663 ms`** | `< 20.0 ms` |
| Trace elevation step compression (`causal_trace_to_skill_compiler_v1`) | `5` GUI steps -> **`1`** API/DB step | `<= 1` |
| Tier-1 volatile noise trials (`20` runs mutating timestamps, ports, UUIDs, PIDs) | **`20 / 20` hits (`0.0` false invalidation)** | `== 0.0` |
| Tier-1 blind stale executions across `3` modal/disabled/relabelled drift traps | **`0`** | `== 0` |
| Automatic eviction on 3rd consecutive pre-probe miss | **`true` (`CACHE_MISS` on step 4)** | `true` |
| Silent backend drop detection | **`FAIL_CLOSED_POST_CONTRACT`** | fail-closed |
| Tier-1 local cached dispatch median latency (`local_dispatch_p50_ms`) | **`0.0653 ms` (`65.3 us`)** | `< 5.0 ms` |

---

## 3. Play C — Relational Guard-Addition & Symbolic Boundary Witness Repair
**Module**: `canonical/runtime/relational_guard_addition_symbolic_repair_v1.py`

### Part 1: Empirical Addition Census (`fix_vocabulary_taxonomy_20261124_V1.json` + `real_fix_pairs_20261119_V1.json`)
- `fix_vocabulary_taxonomy_20261124_V1.json` (`28` tasks, `667` edit sites): **`482 / 667` (`72.3%`)** sites add statements (`0.0` single-substitution ceiling); **`22 / 28` (`78.6%`)** tasks (`161` sites) add AST statement shapes already present in the same file.
- `real_fix_pairs_20261119_V1.json` (`87` full `before`/`after` Python files): **`35 / 87`** commits add `if` guards, **`20 / 87`** add `raise` contracts, **`22 / 87`** add `return` statements.

### Part 2: Closed-Loop Non-Substitution Synthesis + First-Order `GuardDrop` Mutation Gate

| Task ID | Single-Substitution Baseline | Relational Addition Synthesizer | Synthesized Family | First-Order Mutants Killed |
| --- | :---: | :---: | --- | ---: |
| `add_01_none_or_blank_sibling_guard` | `0 / 1` (`false`) | **`1 / 1` (`true`)** | `RELATIONAL_ADD:NONE_GUARD_ADD:[]` | **`3 / 3` (`1.000`)** |
| `add_02_sibling_exception_contract` | `0 / 1` (`false`) | **`1 / 1` (`true`)** | `RELATIONAL_ADD:RAISE_NEGATIVE_CONTRACT:ValueError:shard_count` | **`4 / 4` (`1.000`)** |
| `add_03_dict_bucket_init_guard` | `0 / 1` (`false`) | **`1 / 1` (`true`)** | `RELATIONAL_ADD:DICT_BUCKET_INIT_GUARD` | **`2 / 2` (`1.000`)** |
| `add_04_metamorphic_container_dual_sync` | `0 / 1` (`false`) | **`1 / 1` (`true`)** | `RELATIONAL_ADD:CONTAINER_DUAL_SYNC:_active_set` | **`5 / 5` (`1.000`)** |
| **Total** | **`0 / 4` (`0.0%`)** | **`4 / 4` (`100.0%`)** | — | **`14 / 14` (`1.000`, `0` surviving `GuardDrop`)** |

---

## 4. Play D — Copy-on-Write (`os.fork()`) Zygote Speculative Verifier & AST Test Impact Slicer
**Module**: `canonical/runtime/cow_zygote_speculative_verifier_v1.py`

| Metric (`48` Speculative Candidates Including Global & `os.environ` Mutators) | Measured Value | Kill Threshold |
| --- | ---: | --- |
| Impacted test slicing (`4` suite tests -> `2` transitive callers of `compute_fee_bps`) | **`0.50` (`50%` skipped)** | `> 0.0` |
| CoW `os.fork()` candidate verification p50 / p95 latency | **`1.5785 ms` / `1.7742 ms`** | `p50 < 5.0 ms` |
| Cold `subprocess.run` candidate verification p50 latency | `15.0543 ms` | baseline |
| Speedup vs cold `subprocess.run` | **`9.54x`** (`~633.5` candidates/sec/core) | `> 3.0x` |
| Verdict disagreements vs cold `subprocess.run` across `48` candidates | **`0 / 48`** | `== 0` |
| Cross-worker parent memory / `os.environ` state leaks | **`0`** | `== 0` |

---

## 5. Unified Model & 7-Domain Atlas Reachability Alignment
Extended `canonical/tools/domain_atlas_v1.py` (`_model_status` and `reachability`) so federated `engine:<MODE>` candidates resolve to their backing `source_path` module stem (falling back to `carrier_path` for fabric engines) and `extended_source_index` modules are reflected in `_model_status`; federated `15` zero-model engines (`90 -> 105` federated engines, `116 -> 131` total engines) using strictly intrinsic module/substrate names (zero query-phrase stuffing) and wired Wave-2 Plays A–D into `brain_unified_model_v1.py` (`17 -> 21` `frontier_organs()`).

| Frontier Domain | Pre-Fix `frontier_route_hit_recall` | Post-Fix `frontier_route_hit_recall` | Post-Fix `native_route_hit_recall` | Chance Route Baseline | Invisible Modules |
| --- | ---: | ---: | ---: | ---: | ---: |
| `coding_agents` | `1.000` | **`1.000`** | **`1.000`** | `0.1113` | `0 / 293` |
| `computer_use` | `0.000` | **`0.667`** | **`1.000`** | `0.0523` | `0 / 147` |
| `continual_learning` | `0.000` | **`0.333`** | **`0.667`** | `0.0202` | `2 / 29` |
| `instant_learning` | `0.000` | **`1.000`** | **`1.000`** | `0.0995` | `1 / 174` |
| `memory` | `0.000` | **`1.000`** | **`0.333`** | `0.0590` | `0 / 190` |
| `verification_abstention` | `0.667` | **`0.667`** | **`0.333`** | `0.1231` | `9 / 325` |
| `world_model` | `0.000` | **`0.667`** | **`0.667`** | `0.0422` | `1 / 124` |

- `verify_brain_unified_model_v1.py`: **`38 / 38 PASS`** (`0` out-of-domain false positives on `UNKNOWN_GOALS`, `0` model imports).
