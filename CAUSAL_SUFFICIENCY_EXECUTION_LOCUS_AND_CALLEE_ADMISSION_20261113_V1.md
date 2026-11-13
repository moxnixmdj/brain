# Causal Sufficiency in Multi-Hunk Lesson Localization, Dynamic Execution-Locus Scope Identification, and Cross-Module Callee Dependency Admission (2026-11-13)

- **Date:** 2026-11-13 (UTC)
- **Authority:** `NONE` (`truth.achieved = false`; zero capability, family, benchmark, or terminal credit claimed)
- **Incremental Spend:** `$0.00` (`producer_cognition_model_dependency_count = 0`; zero external API calls; zero pretrained weights)
- **Verification Artifact:** `canonical/verification/CAUSAL_LOCALIZATION_AND_DEPENDENCY_ADMISSION_20261113_V1.json`

---

## 1. Executive Summary

Independent 2026 empirical results in self-improving agent memory and automated program repair converge on two failure modes that appear whenever an autonomous software engineering system attempts to learn reusable repair skills and close multi-file repository defects without human supervision:

1. **Unlocalized or unpaginated skill extraction produces either inert whole-file snapshots, spurious bystander edits, or harmful over-generalizations.** On `origin/main` (`391a707d`), teaching a real multi-hunk historical commit (`boltons/strutils.py`, `1,317` lines) without statement localization crystallized an inert 13-hole whole-file rule (`0` proposals on every other file); teaching a multi-site historical repair (`more_itertools/more.py`, `ichunked_zero`, 4 `<= 0` sites) failed `skill_recheck_v1.recheck` because single-shot application tested only site `#0`; and static AST scope learning (`applicability_v1.learn`) over file-unioned comparison sites across the 4 pinned historical defects collapsed to `INCONSISTENT__NO_REQUIREMENT_EXPLAINS_THE_EVIDENCE` (`0` survivors, `77` static proposals, `26` subprocess `pytest` runs) because unexecuted bystander comparisons in `175 KB` `more_itertools/more.py` formed a strict fact superset of the smaller repaired modules.
2. **Input-read gates alone fail under multi-file synthesis shift when a patch severs cross-module callees.** On `origin/main`, `test_closed_loop_repair_must_generalise_v1.py` failed (`5/8` passed, `3/8` failed): bottom-up observational synthesis in `multistep_repo_closed_loop_solver_v1` replaced `compute_invoice(items, disc)` in `billing/invoice.py` with `return (sum(items) - disc)`. Because that expression still read both formal parameters (`items` and `disc`), `repair_input_dependency_gate_v1` returned `PASS`, allowing the solver to delete the call to `from billing.discounts import apply_discount`, leave `billing/discounts.py` (`return price + disc`) broken, pass the two narrow visible assertions (`len(items) == 1` and `disc == 0.0`), and fail on every unseen multi-item discounted invoice (`18.0 != 16.0` on `([7.0, 13.0], 2.0)`).

This round closes all four measured gaps in owned `$0` Python code:

| Subsystem | Baseline on `origin/main` (`391a707d`) | Measured After This Change |
|---|---|---|
| Coupled 2-file closed-loop generalisation (`test_closed_loop_repair_must_generalise_v1.py`) | `5/8` passed (`3` failed: `billing/discounts.py` left broken; `apply_discount` bypassed) | **`8/8` passed** (`PATCH_STOPPED_CALLING_IMPORTED_DEPENDENCY` refuses bypass; both files repaired; unseen inputs pass) |
| Pinned historical cross-issue transfer (`test_historical_repair_transfer_v1.py`) | `12/13` passed (`zero_consumption-0` failed: `ichunked_zero` rejected at recheck) | **`13/13` passed** (`ichunked_zero` crystallizes via bounded 64-candidate recheck and transfers to `chunked_even_zero` with `0` search invocations) |
| Multi-hunk whole-file crystallization (`unit_boundary`, `1,317` lines) | Inert 13-hole whole-file rule (`0` candidates on other files) or unverified static hunk | Localized to lines `565–566` (`<= -> <`), incidental docstring stripped, **counterfactual causal sufficiency** verified on `before.py`, harmful contrast rejected pre-write (`ADMISSION_REJECT`) |
| Historical candidate & oracle load (`unit_boundary`, `bits_capacity`, `ichunked_zero`, `chunked_even_zero`) | `77` raw static candidates; `26` subprocess `pytest` oracle runs | **`2` execution-locus candidates (`97.40%` reduction)**; **`2` subprocess oracle runs (`92.31%` reduction)**; `bits_capacity` exact upstream fix at rank `1`; `0` oracle runs on `more-itertools` |
| Version-space scope learning (`applicability_v1.learn`) on real historical corpus | `INCONSISTENT__NO_REQUIREMENT_EXPLAINS_THE_EVIDENCE` (`0` survivors) | **`IDENTIFIED__ONE_CONSISTENT_REQUIREMENT` (`1` survivor: `['baseline.violates_own_spec', 'executed_locus.syntax_valid_site']`)**, preserving `bits_capacity/after.py` (`ALREADY_CORRECT`, `0` oracle runs) |

---

## 2. 2026 External Research Grounding

1. **Write-Time Falsification & Counterfactual Skill Contracts:**
   - *Dynamic Agent Skills* (`arXiv:2607.10113`, TMLR July 2026, surveying 124 papers) establishes that unbounded or unverified skill accumulation degrades downstream agent performance via spurious retrieval and negative transfer unless gated at write time by executable verification and counterfactual contrast checks.
   - *Skill-V: Verified Skill Learning with Falsifiable Contracts* (`arXiv:2610.11781`, Oct 2026) formalizes reusable skills as falsifiable contracts paired with replay counterexample gating and boundary revision whenever contract predictions diverge from execution outcomes (`72.7% -> 85.9%` on WebShop).
   - *Learning by Doing* (`arXiv:2611.01386`, Zep Agent Skills, Nov 2026) compiles skills strictly from verified attempt trajectories behind conflict and applicability admission gates rather than raw transcript diffs.
   - *SkillsBench* (`arXiv:2602.12670` v4) measures `+16.6 pp` average improvement across `87` tasks (`33.9% -> 50.5%`) for curated procedural skills while finding negative transfer from unverified self-generated skills; *SWE-Skills-Bench* (`arXiv:2603.15401`, 2026) independently finds that `92/98` static SWE skills fail to improve issue resolution and cause up to `-17 pt` regressions when applied without execution-grounded applicability boundaries.
   - *ASCENT* (`arXiv:2610.05303`, Oct 2026) and *EDGE* (`arXiv:2608.21946`, Aug 2026) demonstrate that retaining only transitions with positive counterfactual marginal gain prevents incidental co-occurring actions from polluting persistent memory.
2. **Distribution Shift in Patch Correctness & Multi-File Dependency Bypass:**
   - *Patch Correctness in Automated Program Repair Technical Report* (`arXiv:2611.10837v1`, 7 Nov 2026) proves that static and learned patch-correctness validators degrade sharply when candidate patch distributions shift from single-operator templates to multi-hunk or synthesized expressions; differential auditing (`PatchDiff`) exposes `68/877` test-suite-plausible patches that fail broader developer specifications and `260/877` with differential behavioral discrepancies.
   - *Reward Hacking Benchmark* (`arXiv:2605.02964`, May 2026), *Know Before Fix* (`arXiv:2607.11111`, July 2026), *SWE-Bench Pro V2* (`arXiv:2610.24206`, Oct 2026), and *OSWorld 2.0* (`arXiv:2606.29537`, Sept 2026 update: frontier binary pass rates `20.6%–31.43%`, with `<7%` of step budget spent on error detection and repair) show that visible-test overfitting routinely manifests as bypassing cross-module helper contracts rather than repairing coupled callee definitions.

---

## 3. Architecture & Exact Changes

### 3.1 Cross-Module Imported Callee Preservation (`repair_input_dependency_gate_v1.py` + `multistep_repo_closed_loop_solver_v1.py`)
- Added `_STDLIB_ROOTS`, `_collect_non_stdlib_imports`, `_local_shadows`, `_attr_root_name`, `imported_callee_use`, and `lost_imported_callees` to `canonical/swe_kernel/repair_input_dependency_gate_v1.py`.
- For every function present in both `before_source` and `after_source`, any non-stdlib imported module actually invoked via `ast.Call` in `before_source` (`from pkg.mod import fn`, `from pkg import submod; submod.fn(...)`, or `import pkg.mod as m; m.fn(...)`, excluding locally shadowed parameter/store names) registers a module-origin dependency obligation.
- If `after_source` drops all references to that non-stdlib origin module inside the function, `gate()` returns `status: "REFUSED"` with `reason: "PATCH_STOPPED_CALLING_IMPORTED_DEPENDENCY: <fn>(<callee>)"`.
- Keying by origin module preserves legitimate refactorings that swap one helper from the same non-stdlib module for another (`apply_discount -> apply_tiered_discount`) and never blocks stdlib simplifications (`math.floor(x) -> int(x)`).
- Wired `_input_dependencies_preserved` across all three candidate admission points in `canonical/swe_kernel/multistep_repo_closed_loop_solver_v1.py` (intermediate beam expansion, single/multi-step winning admission, and 2-file saddle-plateau pair evaluation), eliminating cross-module call amputation before any candidate can poison the beam or claim victory.

### 3.2 Multi-Site Statement Recheck & Counterfactual Causal Localization (`skill_recheck_v1.py` + `verified_skill_crystallizer_v1.py`)
- Updated `canonical/swe_kernel/skill_recheck_v1.py` so default `recheck(rule)` (when `apply is None`) checks up to `64` candidates from `iter_crystallized_code_rule_candidates(before, rule)` instead of only candidate `#0`, while keeping custom `apply` callables strictly single-shot (`10/10` in `test_skill_recheck_v1.py`).
- Updated `_try_candidate_batch` in `canonical/swe_kernel/verified_skill_crystallizer_v1.py` so `SCOPE_STATEMENT` rules evaluate directly against `ProjectTestOracle` (`13/13` in `test_historical_repair_transfer_v1.py`).
- Added `localize_lesson: bool = False` to `VerifiedSkillStore.crystallize_code_fix`:
  1. Runs `lesson_localization_v1.localize_operator_lesson(before_snippet, after_snippet)` when `language == "python"`.
  2. **Counterfactual Causal Sufficiency Check:** When `contract` and `training_verifier` are supplied, generates candidate rewrites of the localized rule on the *original* `before_snippet` (prioritizing the localized line span) and requires at least one single-hunk rewrite to pass `evaluate(training_verifier, ...)` on its own (`LOCALIZED_LESSON_NOT_CAUSALLY_SUFFICIENT` if all fail). This prevents an incidental single-operator edit in a multi-hunk commit from being crystallized when another hunk actually fixed the bug.
  3. Preserves `"localization"` and `"causal_sufficiency"` metadata across SQLite `ON CONFLICT` upserts.

### 3.3 Dynamic Execution-Locus Filtering & Scope Identification (`verified_lesson_pipeline_v1.py`)
- Created `canonical/swe_kernel/verified_lesson_pipeline_v1.py`:
  - `trace_project_target(project_root, target_path, test_paths)`: runs the target's unmodified tests once in a disposable copy under `sys.settrace` on `before.py` (`0` access to `after.py`), recording `(verifiable, returncode, test_count, executed_lines)` and failing closed when `test_count == 0`.
  - `propose_execution_locus_candidates`: restricts `operator_generalization_v1.propose_operator_swaps` to `ast.parse`-valid candidates whose modified line lies in `executed_lines` (eliminating `->=` return-annotation splices, `>=>` shift splices, and unexecuted bystander functions).
  - `execution_locus_facts` & `learn_execution_locus_scope`: extracts AST context facts strictly at syntax-valid sites inside `executed_lines` and runs `applicability_v1.learn`. Across the 4 broken historical targets plus real green control `bits_capacity/after.py`, version-space learning converges to `IDENTIFIED__ONE_CONSISTENT_REQUIREMENT` (`survivor_count == 1`, `required == ["baseline.violates_own_spec", "executed_locus.syntax_valid_site"]`).

---

## 4. Honest Limits, Falsifiers, and Non-Claims

1. **Dynamic Reachability Is Necessary, Not Sufficient:** `executed_locus.syntax_valid_site` proves that a syntax-valid candidate comparison executed during the failing test run; it does *not* prove that comparison is the root defect. `test_execution_locus_reaches_innocent_guard_without_false_repair_claim` explicitly constructs a repository where an innocent `<=` guard runs before an arithmetic bug (`return x + 99`), demonstrating that `apply_localized_skill_with_locus` still invokes `ProjectTestOracle` and honestly returns `NOT_REPAIRED`.
2. **Scope of Operator Generalization:** Operator-family rules do not synthesize missing zero-guard clauses (`more-itertools` `ichunked_zero` / `chunked_even_zero` require explicit `if n <= 0: raise ValueError(...)` guards; execution-locus filtering cleanly skips them in `0` oracle calls as `DID_NOT_FIRE_IN_EXECUTED_LOCUS`, while statement-tier anti-unification transfers across the pair in `test_historical_repair_transfer_v1.py`).
3. **Scope of Callee Dependency Preservation:** `lost_imported_callees` refuses structural amputation of non-stdlib imported callees inside edited functions. It does not by itself prove full behavioral correctness on arbitrary specifications; unseen-input perturbation and full test-suite verification remain mandatory.
4. **Zero Authority Claim:** `authority` is `"NONE"`, `truth.achieved` remains `false`, `incremental_spend_usd` is `0`, and zero benchmark, family, or terminal credits are claimed.

---

## 5. Reproducible Verification Commands

```bash
.venv/bin/python canonical/swe_kernel/verified_lesson_pipeline_v1.py \
  --write canonical/verification/CAUSAL_LOCALIZATION_AND_DEPENDENCY_ADMISSION_20261113_V1.json

.venv/bin/python -m pytest -q \
  canonical/tests/test_causal_localization_and_dependency_admission_v1.py \
  canonical/tests/test_historical_repair_transfer_v1.py \
  canonical/tests/test_lesson_localization_v1.py \
  canonical/tests/test_operator_generalization_v1.py \
  canonical/tests/test_skill_scope_acquisition_v1.py \
  canonical/tests/test_lesson_admission_gate_v1.py \
  canonical/tests/test_skill_recheck_v1.py \
  canonical/tests/test_repair_input_dependency_gate_v1.py \
  canonical/tests/test_closed_loop_repair_must_generalise_v1.py \
  canonical/tests/test_fast_internal_seams_and_zygote_v1.py \
  canonical/tests/test_optimal_unified_creature_and_prc2_v1.py
```
Result measured on this branch: **`147 passed` (`0` failed)**.
