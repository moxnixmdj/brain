# Hidden-tool wiring: human SWE sentences reach the typed capability selector

Measured 2026-10-27 on `arena/f537ad9f-brain` (merged from main `34648e4f1b`).
Authority: **NONE**. Credit: **0**. Model dependency: **0**. Incremental spend: **$0**.
This is a measurement, not a capability claim.

## The owner's instruction, followed literally

> "All of your problems I already solved in the brain or somewhere on the internet hidden as
> tools or hidden somewhere on the repos, or there are perfect ideas on some research papers.
> Do the optimal in the fastest way. Everything must be insanely fast, only the right way."

So nothing below is invented. The route order was walked: DELETE and BYPASS do not apply
(the repair/refactor mechanisms are needed and already exist); REUSE and ADAPT are the whole
slice. The perfect idea is from `COMPOSITION_LEVERAGE_20261018_V1.md` §9 — **when a relation
cannot be derived from names, enumerate the candidate space and let execution be the oracle** —
applied here to *binding*: derive the missing input from bytes the request already states.

## Hidden machinery that was already in the repository

| existing module | what it already does | was it wired? |
|---|---|---|
| `capability_selection_retrieval_v1.py` (733 lines) | typed admission: shortlist → `admit()` → effect/margin disambiguation; refuses ambiguity | yes, but F17 only accepts `receipt_projection` capabilities |
| `capability_type_surface_v1.py` (696 lines) | `ARGV`, `PATH_DIR`, `KEY_ALIASES` ("test command" → `test_argv`) | yes |
| `goal_front_compiler_v1.py` (2,458 lines) | pinned binder, 26 declared defect fixes | yes |
| `acceptance_clause_v1.py` (217 lines) | separates routing prose from a stated acceptance contract | yes |
| `capability_composer_v1.py` (349 lines) | `requires`/`provides` graph + `plan()` | yes (composer fallback) |
| `bridge_enumeration_v1.py` (457 lines) | enumerate (producer, type), execute, keep survivors | yes, but output unused by planner |
| `program_synthesis_v1.py` / `documentation_mining_v1.py` | write a program, prove it by running it | yes (last-resort fallback) |
| `flywheel_v1.py` (405 lines) | instant learning keyed on pathology | partly (`_recall_for`) |
| `execution_guard/goal_chase_v1.py` | `chase_until_met` persistence | not wired into `solve()` |
| `true_capability_harness_v1.py` (500 lines) | fresh instances, ≥2 independent oracles, public-runner credit | not wired into PR admission |

## The measured gap

On five fresh, human-shaped SWE sentences (rename a parameter, repair a bug, fix a broken
function, one-line imperative, bug report), `capability_selection_retrieval_v1.select()`
shortlisted the RIGHT capabilities and then refused all of them:

```
status NOT_SELECTED   reason NO_TYPED_ADMITTED_PROPOSAL
BINDING_REFUSED:new_param:not_stated
BINDING_REFUSED:source_root:0_existing_directories_named
BINDING_REFUSED:test_argv:not_stated
BINDING_REFUSED:index_path:0_type_compatible_existing_files_named
```

Root cause, measured: the registry declares **slots the adapter already defaults**
(`python_refactor_rename_parameter.py:247-249` reads `args.get("python_executable") or
sys.executable`), and declares **slots in a different shape than a human states them**
("fix calc.py" states a FILE; the loop declares `source_root`, a DIRECTORY).

## What was wired (3 files, no registry change, no kernel change)

1. `canonical/runtime/declared_input_derivation_v1.py` (new). Derives declared inputs only
   from **stated evidence**, each row carrying its rule and evidence:
   - `source_root` ← parent directory of the single stated source file;
   - `test_argv` / `test_paths` ← the stated test file, or **discovered** by a bounded scan
     of the stated source directory when the request says "its tests" but names no test;
   - `module` ← the stated `.py` file;
   - `old_param`/`new_param`/`old_symbol`/`new_symbol`/`new_name` ← a strict rename grammar;
   - `qualname` ← **proved by parsing the stated source file's AST**: exactly one function
     declaring that parameter may match; zero or several yields no value;
   - configuration-only slots (`python_executable`, `timeout_s`, `run_tests`, `max_*`) are
     removed from the binding contract **only when the adapter's AST proves it defaults them**.
     Semantic path/root/argv slots are NEVER defaulted away — a mutation test caught that
     this let `output_path` bind onto the user's source file, and the rule was tightened.
2. `capability_selection_retrieval_v1.admit()` — uses the derivation view on SWE requests to
   SWE capabilities only; every other goal keeps the byte-for-byte original gate.
3. `capability_selection_retrieval_v1.select()` — E30: when several candidates are honestly
   bindable, the effect the request states ("rename", "repair", "fix", "lint"…) plus the noun
   it names ("parameter", "test", "loop"…) disambiguates; a tie falls back to shortlist rank;
   an unresolved tie still refuses. Ambiguity is never silently resolved.

`canonical/tests/test_declared_input_derivation_v1.py` — 7 fresh-instance tests, filesystem
and adapter AST as independent oracles, negative controls for ambiguity and out-of-scope
requests, plus a mutation control that breaks `stated_existing_files` and asserts selection
stops. All 7 pass.

## Measured result

| metric | before | after |
|---|---|---|
| human SWE sentences with a decisive typed selection | **0 / 5** | **5 / 5** |
| …selecting a capability that can actually do the job | **0 / 5** | **5 / 5** |
| admitted candidates per repair sentence | 0 | 5–7 |
| selector wall clock | — | **119 ms / goal** (5 goals in 597 ms) |
| `test_capability_naming_rule_v1.py` + `test_capability_selection_retrieval_v1.py` | 19 pass | **19 pass** |
| new derivation tests | — | **7 pass** |
| `test_goal_front_compiler_v1.py` (fleet drift, pristine vs wired) | 12 failed / 32 passed | **12 failed / 32 passed — identical set, zero regressions** |
| fresh execution oracles (patch applied, tests run) | 2/2, 2/2, 2/2 | **2/2, 2/2, 2/2** |

Selected capabilities on the five sentences:
`python.refactor.rename_parameter.v1`, `python.patch.search.test_guided.ast.v1`,
`python.software.repair.apply.verified.v1` (×2), `python.software.repair.loop.test_guided.ast.v1`.

## What this deliberately does NOT claim

`select()` is a **proposal** surface; `live_brain_route_admission_v1.solve()` still routes
primarily through the pinned lexical compiler. Wiring the derivation into the primary binder
was attempted (F31) and **reverted** because it let an ambiguous two-file sentence bind —
the ambiguity guard regression is visible in `test_f24_an_ambiguous_statement_still_keeps_the_request_open`.
The honest next step is a scoped retry that re-checks ambiguity after derivation, measured on
the full 37-family suite before it can land. Nothing here changes the registry, the unified
model, any protected path, or any scoreboard.

## Post-merge update (main `c57b21730d`)

The fleet landed two more SWE fixes while this PR was open — `RUN_THE_TESTS_MEANS_RUN_THE_TESTS`
(discover `test_paths` from the tree, drop `test_argv` from the template, real pass-rate report)
and `WRITE_THE_TESTS_FOR_THIS_TREE_MUST_WRITE_TESTS` (derive scaffold targets from the symbol
index, run under `unittest` when pytest is absent). Both are the same pattern as this slice:
**reuse the adapter's own defaults and derive missing inputs from the tree**, not invent them.

Merging that main into this branch exposed two infrastructure facts, both now fixed here:

1. `verify_brain_unified_model_v1.py` failed `ARTIFACT_INTEGRITY` (5/6) because the compiled
   9.4 MB model is a hash of the whole tree — including `canonical/action_intents/*.json`.
   **Every intent edit changes the model digest**, so the model must be recompiled after the
   final intent bytes, and a re-run of the verifier is 33/33 PASS. This coupling is a real
   speed/consistency problem: a one-line governance edit forces a 9.4 MB artifact rebuild.
2. `test_capability_naming_rule_v1.py::test_f29_a_request_that_names_nothing_fails_closed`
   now fails on **pristine main** (verified by checking out main's two runtime files):
   `"Run the thing."` selects `python.repository.acceptance.measure.v1` instead of failing
   closed. That is fleet drift from the `RUN_THE_TESTS` change, not a regression from this PR.
   It is a fail-open on a request that names nothing and must be fixed before any routing
   claim is trusted.

## The fastest remaining wiring, in order

1. Land the scoped F31 retry (keep the ambiguity re-check) so `solve()` uses the same derived
   contract; measure the 10 human SWE tasks from `HARDCORE_SE_PROBLEM_INVENTORY_20261027_V1.md`.
2. Wire `bridge_enumeration_v1` output into `capability_composer_v1.graph()` as
   `provides_as`/`requires_as` aliases (`astra_runtime.py` already implements them) — execution
   proved 1 bridge on the old registry; re-run it on the 125-row registry with the derived
   fixtures from this module.
3. Install `requirements/software_engineering_kernel_v1.txt` in the heartbeat workflow (the
   pinned wheels are still installed by no workflow), and shard the 37 families with the
   existing `--families` flag so the daily proof finishes instead of being cancelled.
4. Put `true_capability_harness_v1` in front of every new SWE capability: fresh instances,
   ≥2 independent oracles, public-runner receipt. Until then no SWE row has credit.

## LANDED 2026-10-27 (PR #6287 + #6299, both merged to main)

The scoped retry described above as "the honest next step" is now DONE and on `main`.
This supersedes the "What this deliberately does NOT claim" section above.

**Wiring (PR #6287):** `live_brain_route_admission_v1.solve` now wraps its unchanged
primary body (`_solve_body`); on a pre-execution failure of a decisive SWE request it
re-enters the SAME full gate chain with a typed plan from `swe_typed_plan_v1.build_plan`
(REUSE of `capability_selection_retrieval_v1.select` + `declared_input_derivation_v1`).
Ambiguity preserved; non-SWE and executed verdicts never touched.

**Measured (fresh instances, filesystem via the real gate chain as independent oracle):**
- 5 human SWE sentences: **1/5 -> 3/5 honest PASS**, zero false passes.
- Front-door regression failure set byte-identical to pristine (A/B worktree); the 8
  failures are pre-existing fleet drift from main #6292's selection-rate change.
- New suite `test_swe_typed_plan_v1.py` 11/11; verifier 33/33; model 60+863; all four
  local gates PASS; signed referee green on both PRs.

**False-PASS fix (PR #6299):** measuring the 10 held-out `INV_` real-SWE tasks exposed a
fail-OPEN that the first wiring introduced: `select` admits by declared-input CONTRACT,
not effect, so with a single bindable candidate (F17) "Type-check the file X" bound to a
repair choreographer that no-op'd to PASS with the source unchanged. `build_plan` now
applies the selector's OWN E30 `_EFFECT_WORDS` as an admission gate even for
single-candidate selections; effect-inconsistent goals keep their fail-closed verdict.
Re-measured: the false PASS is gone (typecheck/lint honest fail-closed).

**Rename family (PR #6299):** the three refactor adapters resolve `module` relative to
`source_root`; the derivation emitted the full path (doubled prefix -> PATH_MISSING).
Normalizing it yields `gate=PASS, edit_count=2`; 3/4 fresh rename phrasings pass
end-to-end with source bytes genuinely changed and every honesty gate clean.

**Honest residual on the 10 `INV_` tasks:** 1 honest PASS (`git_log`) + 9 honest
fail-closed, zero false credit. The other 9 need their OWN adapters (callers, test
authoring, lint, typecheck, git commit, debugger, patch extraction) — this is the
documented "45/52 SWE capabilities never measured from a sentence" gap, NOT a routing
gap. Fabricating those adapters to raise a headcount would be a false claim.

**Fastest remaining wiring (unchanged priorities):** the effect-guard fix is the template
for the rest — when a family binds the wrong capability, encode the family's OWN effect
vocabulary as an admission gate, then build its dedicated adapter with fresh held-out
instances and >=2 independent oracles (`true_capability_harness_v1`). Owner-only:
heartbeat still not a required check, protected-path receipt/verifier blind spots.
