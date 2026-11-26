# Wave 45 — Build and Honest Results

**Date:** 2026-11-26 · **Branch:** `arena/fe676c2a-brain` · **Base:** `ac5c1015`
**Model digest:** `3b07552726d7c05719f7c905570656d98293ea93bd9b8a52f865ac4505a3e864`
**Harness receipt:** `canonical/verification/SWE_BENCH_LOCAL_HARNESS_20261126_V1.json`

## 1. What was wrong before this session (all reproduced live, not inferred)

Four independent defects. Each one alone was enough to make "instant learning" false.

| # | Defect | How it was found | Evidence |
|---|---|---|---|
| 1 | **Lying oracle.** `solve_swe_repo_native_multifile` ran `python -m unittest <file>`, which discovers only `unittest.TestCase` subclasses. | Ran a repo whose plain `def test_*` suite fails → engine returned `PASS__BASELINE_ALREADY_GREEN`. | `_run_suite_in_dir`, now replaced by `_honest_suite_verdict`. |
| 2 | **Stale bytecode.** The CoW runner imported `calc` once; a `.pyc` in the repo then made later runs execute the pre-patch module. | Patched a repo, re-ran the same runner: still reported the old traceback `assert -1 == 5` after the source said `a + b`. | `stdlib_cow_test_runner_v1._execute_suite_in_current_process`. |
| 3 | **Unreplayable skills.** `SkillStoreV2` persisted a hole witness via `repr(list_of_ast_nodes)` → `"<ast.If object at 0x7f...>"`. Every stored morphism was dead on arrival. | `store.learn(before, after)` then `store.propose(before)` returned `[]` — it could not replay its own witness. | `causal_nexus_v1._dump`. |
| 4 | **Test-data laundering.** A suite-green patch that hardcoded a witness value was accepted as a repair. | `get_name(None) == ""` was "fixed" by `return ((user or '') and 'bob')`, so `get_name({"name":"alice"})` returned `'bob'`. | `repair_admission_v1` measured it: `TEST_LITERAL_LEAK: 'bob'`. |

Defect 4 only became visible *because* defect 1 was fixed. The lying oracle had been hiding the overfit patch behind a false green.

## 2. What was built (minimal; one new file each, everything else a wire)

| Change | File | What it does |
|---|---|---|
| Honest oracle | `canonical_swe_spine_v1._honest_suite_verdict` | Runs the real suite through `stdlib_cow_test_runner_v1` (plain functions, `Test*` classes, `unittest`, `file.py::nodeid`). No test discovered / crash / timeout / any failing nodeid ⇒ **failure**, never green. |
| Admission gate | `canonical/swe_kernel/repair_admission_v1.py` (new, 250 LOC) | Refuses a repair that introduces a data literal absent from the source (`TEST_LITERAL_LEAK`), that stops using a parameter the original used (`PARAM_AMNESIA`), or whose whole value is a non-canonical constant (`CONSTANT_BODY`). Pure AST, no model, no parameters. |
| Skill writer | `canonical_swe_spine_v1._crystallize_verified_repair` | Writes every disk-verified repair into `SkillStoreV2` (statement-level morphisms) and `CanonicalLawStore` (single-block laws). Returns `learned_skill_id` / `crystallized_law_ids`; `learned_skill_id=None` for multi-statement fixes was the measured gap and is now closed. |
| Skill recall | `canonical_swe_spine_v1` Stage 1.7 | Asks the store *before* synthesising. Acceptance goes through the same verified CoW oracle; success increments `verified_transfers`, failure increments `refutations` and the morphism retires. |
| Generalisation | `causal_nexus_v1` | (a) recursive `_dump` so statement-list holes have a real witness; (b) `_blind_string_constants` so hole comparison is literal-blind; (c) consistent-literal slots (`@lit{k}`) so a key the fix did not change becomes a slot; (d) declared-name slots (`?d{k}`) so a law learned on `get_name(user)` fires on `read_nickname(rec)`; (e) identifier holes store their raw string, matching what the matcher hands back. |
| Harness | `canonical/swe_kernel/swe_bench_local_harness_v1.py` (new, 250 LOC) | Three arms + two mandatory ablations, independent re-verification of every result, `model_calls` counted. |
| Tests | `canonical/tests/test_wave45_honest_oracle_and_skill_transfer_v1.py` (new, 12 tests) | Each defect gets a regression test, plus store isolation via `BRAIN_SKILL_STORE_PATH` / `BRAIN_LAW_STORE_PATH` so tests never write product state. |

`brain_unified_model_v1.py` grew by 2 lines (parameter forwarding only): 7,533 → 7,535.

## 3. Honest results (measured, this session)

### 3.1 Tests

```
canonical.tests.test_wave45_honest_oracle_and_skill_transfer_v1 .... 12 passed
canonical.tests.test_canonical_swe_spine_v1 ....................... 8 passed
canonical.tests.test_petri_cow_splicing_engine_v1 ................. 6 passed
canonical.tests.test_parallel_cow_rollouts_v1 ..................... 3 passed
```

No regression observed in the suites run. Not a full-suite claim: the last recorded full-suite baseline is `HONEST_SUITE_BASELINE_20261103_V1.json` (984 failed cases of 16,361 at `407cc3c3`), and re-running it in full was not attempted here — that is a separate, multi-hour job and is recorded as **not done**, not as passing.

### 3.2 Harness (un-gated, local, `model_calls` counted)

| Arm | Tasks | Independently verified passes | Model calls |
|---|---|---|---|
| `EMPTY_STORE_NO_PROPOSER` (cold-start floor) | 3 | **1** (BINOP_INVERT; GUARD and held-out fail closed) | **0** |
| `SEEDED_STORE_NO_PROPOSER` (teach 1, transfer to renamed repo) | 2 | **2** | 1 (the untrusted proposer, once) |
| `OVERFIT_LITERAL_ADMISSION` (the `'bob'` patch) | 1 | **0** (refused) | 1 |

### 3.3 The two mandatory ablations

**Memory (empty vs seeded), held-out repo with a different function name, parameter name and key:**

```
empty_store_held_out_pass : false
seeded_store_held_out_pass: true
```

The only difference between the two runs is the store. One exposure, then a held-out variant: `read_nickname(rec)` / `rec["nick"]` was fixed by a law learned from `get_name(user)` / `user["name"]`, in a separate repository, with **zero** proposer calls on the held-out run. This is the first verified single-experience transfer in this project.

**Admission gate:**

```
overfit_patch_status  : FAIL_CLOSED__RESIDUAL_PROPOSALS_REJECTED_BY_COW_ORACLE
overfit_patch_verified: false
```

The patch that passed the suite by hardcoding `'bob'` is now refused before evaluation.

### 3.4 Speed (measured, not claimed)

- Cold-start `BINOP_INVERT` end-to-end: **0.099 s**, `model_calls=0`.
- Skill-store recall on the held-out repo: **~0.43 s** including teaching; recall itself is millisecond-scale (`propose` is pure AST matching).
- These are micro-benchmark numbers on tiny repos. The historical "0.35 s" figure remains **unverified** as a general claim.

## 4. What is still NOT done (and is not claimed)

1. **No real benchmark number.** SWE-bench Pro V2, Terminal-Bench 4.0 and OSWorld 2.1 were **not** run. `docker: command not found` in this sandbox; the Harbor container runner cannot execute here. The harness reports those as `NOT_RUN__DOCKER_UNAVAILABLE`, never as a score.
2. **The honest baseline is still 0/51** on SWE-bench Pro V2 Hard-51 (PR #7080's measured receipt). Nothing here changes that: the harness shows mechanisms, not benchmark results.
3. **Cold-start natural language is still unsolved.** `UnifiedModel.solve("Fix the bug where add returns subtraction…")` still fails closed: the engine needs `(repo_root, test_targets, candidate_files)`. Part 3 of the plan (the cold-start adapter) was not built this session — the oracle and writer defects were more fundamental and had to come first.
4. **`canonical/eval/` is absent** on this branch, so the container adapters from PR #7080 are not wired here.
5. **Only one morphism class was tested for transfer** (guard → fallback). Binop inversion still comes from the ANGELIC_OE path, not from the store — the store learned a morphism for it but recall was not the winning path. That remains a real gap.
6. **Not DONE per §6.** Zero-model execution: yes. Hardest benchmarks: no. Never-seen environments: partially (one held-out repo). Single-experience learning: yes, one class. Four of four are required; two are missing.

## 5. Next bottleneck (ranked, and why)

1. **Cold-start spec discovery.** The instrument is now honest and it learns, but it cannot be reached from a natural-language goal. That is what keeps the SWE-bench number at 0. This is the single highest-leverage remaining item.
2. **Transfer breadth.** One morphism class transfers. Real repos need guards-on-tuples, None-coalescing in returns, exception-message rewrites, and multi-file import zippers. The store format supports them; nothing has measured them.
3. **Container evaluation.** Without Docker there is no public number, and without a public number none of this can be compared to the frontier. GitHub Actions is the only path available from this sandbox.

---

# Addendum: cold-start adapter (Part 3) — built and measured

## A1. What it is

`canonical/swe_kernel/cold_start_swe_adapter_v1.py` (new, ~290 LOC) + `UnifiedModel.solve_swe_cold_start()`
+ `route_swe_cold_start`. It turns `(repository, one sentence)` into the structured inputs the spine
needs, with **zero model calls**:

1. **Scan** — test files, source files, frameworks actually present (`pytest` / `unittest` / plain functions).
2. **Bind targets** — issue-term match against test names and bodies; falls back to the full test set
   (bounded) so a lexically poor issue still gets *measured* rather than skipped.
3. **Bind candidates** — files that define a symbol the tests import, then term overlap. The import graph
   decides, not the wording.
4. **Hand off** to `solve_swe_repo_native_multifile`, which is honest about failure.
5. **Refuse** with `NO_ORACLE_TARGET__NO_TEST_FILE_IN_REPO` when there is no test: no oracle ⇒ no
   verification ⇒ no repair. This is the module's most important line.

Every result carries `binding.evidence.steps`, so a wrong binding is inspectable.

## A2. Measured results (cold start from a sentence, `model_calls = 0` everywhere)

| Task | Issue | Status | Verified |
|---|---|---|---|
| `CS_BINOP` | "addition returns the wrong answer" | `PASS__REPO_NATIVE_ANGELIC_OE_STRUCTURAL` | yes |
| `CS_COMPARISON` | "rejects eighteen year olds, off by one" | `PASS__REPO_NATIVE_ANGELIC_OE_STRUCTURAL` | yes |
| `CS_OFF_BY_ONE` | "total skips the last element" | `PASS__…` (writes `len(xs) - 1 + 1`, equal to `len(xs)`) | yes |
| `CS_NONE_COALESCE` | "crashes when the tag is missing" | `FAIL_CLOSED__RESIDUAL_HOLE_NEEDS_PROPOSER` | no |

**3 of 4 solved cold from a sentence, zero model calls.** The fourth (string concatenation with a
missing-None fallback) fails closed, honestly, naming `RESIDUAL_SEMANTIC_HOLE_NEEDS_PROPOSER`.

## A3. Real-code probe (not synthetic)

A 436-line module copied out of this repo (`canonical/tools/line_localisation_v1.py`) with a genuine
single-site bug injected (one `-` dropped from the sort key in `fuse`, causing reciprocal-rank fusion to
return the worst line first):

- **Binding: correct.** `test_targets=['test_loc.py']`, `candidate_files=['loc.py']`, evidence
  `TARGETS_BY_ISSUE_TERM_MATCH` + `CANDIDATES_BY_IMPORT_GRAPH_AND_TERMS`.
- **Baseline: correctly detected as failing** (the honest oracle). Stage 0, Stage 3 and Stage 4 all run.
- **Repair: FAILED, honestly.** `FAIL_CLOSED__RESIDUAL_HOLE_NEEDS_PROPOSER`. No patch, no false green.

This is the real frontier: reaching the right file and test is solved; flipping a sign inside a
`lambda` used as a `sorted` key argument is not. Recorded as a failure, not smoothed over.

## A4. A gate that was designed and removed

"Refuse patches whose expressions simplify to the original value" looked correct against
`range(len(xs) - 1 + 1)`. It was wrong: that expression **is** `len(xs)`. Symbolic equality proves a
change is safe; it cannot prove a change is worthless. Removed, with the reasoning recorded in
`repair_admission_v1.py` so it is not re-proposed.

## A5. Test suite (this session)

```
canonical.tests.test_wave45_honest_oracle_and_skill_transfer_v1 .... 16 passed
canonical.tests.test_canonical_swe_spine_v1 ....................... 8 passed
canonical.tests.test_petri_cow_splicing_engine_v1 ................. 6 passed
canonical.tests.test_parallel_cow_rollouts_v1 ..................... 3 passed
```

## A6. Still not done

- No SWE-bench Pro V2 / Terminal-Bench 4.0 / OSWorld 2.1 number: `docker` absent. Reported as
  `NOT_RUN__DOCKER_UNAVAILABLE`, never as a score. Honest baseline remains **0/51**.
- Repair of real multi-token semantic bugs (sign inside a keyword lambda, string concatenation
  fallbacks) is unsolved: 3/4 synthetic cold-start tasks pass, 0/1 real-code probe passes.
- Only one morphism class has a verified transfer (guard → fallback).
- **Not DONE per §6.**
