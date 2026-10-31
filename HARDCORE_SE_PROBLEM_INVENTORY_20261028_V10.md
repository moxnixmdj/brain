# HARDCORE SOFTWARE-ENGINEERING PROBLEM INVENTORY — V10

Version 10. Supersedes V9. Measured on this tree, not asserted.

---

## 1. The change in this unit

V9 left exactly one hollow pass and named its cause: `Change the signature of the function add …`
was answered by `python.source.change_impact.testselect.v1`, which reads `change` as the noun in its
own name. The act was genuinely absent, and no routing fix could honestly cover for it.

**The act now exists: `python.refactor.change_signature.v1`.**

The unit was built by reuse, not synthesis, because the pieces were already here:

| already in the brain | reused as |
|---|---|
| `python.refactor.rename_symbol.v1` / `rename_parameter.v1` | the whole helper shape: `_fail`, `_safe_path`, `_sha256`, `_modname_of`, `_params_of`, `_binds_name` scope law, `_resolve_def`, `_import_table`, token-span splice, test-gate with sha256 rollback |
| `python.source.crossfile_edit.choreograph.v1` | the convention that a STRUCTURED EDIT SPEC IS A FILE (`edits_path`), so a signature is stated as a JSON document of `renames` / `add` / `remove` / `set_defaults` / `call_default`, never inferred from prose that never said it |
| python stdlib `ast` + `tokenize` | the parameter list is re-rendered from the parsed def and spliced as ONE span; annotations and unstated defaults are carried through byte-exactly |

### 1.1 What the verb does

* **renames** — the `def`, the body by lexical scope, and every `old=` keyword at a call site.
* **add** — appended with a default (callers untouched), or without one when the spec supplies
  `call_default` (then **every resolved call site is rewritten**, and a call site this verb cannot
  resolve refuses the edit).
* **remove** — only a trailing parameter with a default that the body never reads and no call site
  passes.
* **set_defaults** — a default value replaced, nothing else touched.

Call-site law: a call is edited only when it **provably binds this function** — `sym(...)` in the
defining module, `from mod import sym`, or `import mod [as m]` then `m.sym(...)`. A call inside a
scope that rebinds the name (a nested `def add`, a lambda parameter) is a *different* function and is
left alone; a function that ESCAPES as a value forces a refusal when the change is not backward
compatible (`FUNCTION_OBJECT_ESCAPES`), because this verb cannot follow it to every call.

Refusals, each leaving every byte untouched: `SIGNATURE_NOT_STATED`, `SYMBOL_NOT_FOUND`,
`NOT_A_FUNCTION`, `INVALID_PARAM_NAME`, `DUPLICATE_PARAM`, `PARAM_NOT_FOUND`,
`REMOVAL_SHIFTS_ARGUMENT`, `PARAM_IN_USE`, `REQUIRED_PARAM_NEEDS_CALL_VALUE`,
`CALL_KEYWORD_COLLISION`, `CALL_ARITY_INCOMPATIBLE`, `FUNCTION_OBJECT_ESCAPES`,
`DEFAULT_ORDER_VIOLATION`, `EDITS_SPEC_*`, `SPAN_INTEGRITY`, `SYNTAX_ERROR_*`,
`TESTS_RED_AFTER_EDIT` (all bytes restored), `PASS_BLIND` + `verified:false` when no suite is named.

Pins: `canonical/tests/test_python_refactor_change_signature_v1.py` — **14 passed**.
Receipt: `canonical/astra_runtime/evidence/ASTRA-VERIFY-CHANGESIG-001__RECEIPT.json`.

---

## 2. Measured state

### 2.1 The 43-act missing-verb probe

```
python3 execution_guard/hardcore_se_missing_verb_probe_v1.py
{"ANSWERED_BY_OWNING_CAPABILITY": 24, "HONEST_REFUSAL": 18, "WRONG_TOOL": 1}
silently answered (hollow pass): none
```

| revision | owned | honest | hollow | wrong | owned-but-failed |
|---|---|---|---|---|---|
| V6 baseline | 0 | 23 | 18 | 2 | — |
| + analysers | 7 | 10 | 19 | 3 | — |
| + R13 (act vocabulary) | 12 | 14 | 15 | 2 | — |
| V7 (+8 capabilities) | 16 | 15 | 8 | 4 | — |
| V8 | 15 | 17 | 7 | 4 | — |
| V9 (routing + fixtures) | 23 | 18 | 1 | 1 | 0 |
| **V10 (this unit)** | **24** | **18** | **0** | **1** | **0** |

**Zero hollow passes.** Every sentence in the probe is now either answered by a capability that
performs the act, or refused by a capability that says what is missing.

### 2.2 The rest of the surface

```
python3 execution_guard/hardcore_se_git_surface_v1.py     12/12 selected, pass, artifact, repo changed
python3 execution_guard/hardcore_se_git_surface_v1.py --refusals   10/10 named, 10/10 untouched
python3 execution_guard/hardcore_se_reachability_v1.py    bindable 22/22  selected 22/22  pass 22/22
python3 execution_guard/adapter_failure_law_probe_v1.py   17 adapters that could end the process -> 17 TYPED_REFUSAL
```

### 2.3 Regression baseline

`canonical/tests/test_goal_front_compiler_v1.py` — **14 failed**, the identical pre-existing node
ids measured at `fec9e26` and at `2754cf0` (V9 §2.4). The three sibling refactor suites and the new
one are green (14 + 45 + … passed). No new failure.

---

## 3. What is still open (measured, ranked)

1. **18 acts are honestly missing.** The refactor family is now complete for signatures; the
   remaining high-value ones and the exact tool that already does them:
   - `move_function` — `python.source.crossfile_edit.choreograph.v1` already computes the PLAN
     (`move_symbol`, with collision law and ambiguous-site honesty); what is missing is the APPLY
     step, and `change_signature`'s splice + gate is that step.
   - `inline_function` — the inverse of `python.refactor.extract_function.v1`, which already does
     scope inference and statement alignment.
   - `docstrings` — AST + the same splice/gate; nothing else needed.
   - `flake_detect` — rerun ordering/seed variance (`pytest -p no:randomly` + `PYTHONHASHSEED`), a
     measurement, not a linter.
   - `api_compatibility` — public-API AST diff between two trees; pure stdlib.
   - `memory_profile` — stdlib `tracemalloc`.
   - `dependency_add`, `build_package`, `ci_config`, `schema_migration`, `merge_conflict`,
     `resource_leak`, `retry_design`, `observability`, `crash_repro`, `interactive_debug`, `fuzz`.
2. **One wrong-tool answer remains** (`differential_test` → `code.impact.tree_sitter.testselect.v1`
   with `INDEX_UNREADABLE`): the act is absent and the nearest capability cannot index the tree.
3. **`change_signature` is reached by a stated edit spec, not by prose.** The sentence form
   "…to take the parameter scale with the default 1" ranks the right capability first (37 points)
   but the binder has no prose→spec rule yet; the spec-file form is the house convention
   (`choreograph.edits_path`) and is what the probe measures. A prose rule is the next refinement,
   not a missing ability.
4. **19 pre-existing test failures** on this branch (identical node ids at `fec9e26`) remain the
   largest single red area, untouched by this unit.

---

## 4. Reproduce

```bash
.venv/bin/python execution_guard/hardcore_se_missing_verb_probe_v1.py --json /tmp/mv.json
.venv/bin/python execution_guard/hardcore_se_git_surface_v1.py [--refusals]
.venv/bin/python execution_guard/hardcore_se_reachability_v1.py
.venv/bin/python execution_guard/adapter_failure_law_probe_v1.py
.venv/bin/python -m pytest -q canonical/tests/test_python_refactor_change_signature_v1.py
```
