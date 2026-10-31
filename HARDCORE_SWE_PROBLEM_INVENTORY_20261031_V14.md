# Hardcore software-engineering problem inventory — V14

Measured 2026-10-31 on `ecfc9fb` (branch `arena/7a6872b9-brain`).
Supersedes V13. **V13's structure was right and its #1 priority was wrong**: this document
shows the engines work and the sequencing does not. Document-format, image, chart and
office rows are excluded from every count on purpose.

---

## §0 The answer in one paragraph

Three layers, and only one of them is broken. **Execution works**: invoked directly with
correct arguments, the analysis engines return verified artifacts in **0.5–80 ms** (dead
code 2 ms, complexity 1 ms, AST audit 0 ms, symbols 2 ms, change-impact 4 ms, test audit
80 ms, mutation score 166 ms with a real 1.0 score). **Derivation is thin**: a sentence
rarely yields the arguments those engines need, and the slots with no producer at all are
`symbol`, `task_text`, `to_module`, `edits`, `index_path`, `selection_path`, `pr_intent_path`
and the budget knobs. **Sequencing is absent**: 43 of 84 hardcore rows declare a
precondition only another row can produce, and the door executes exactly one row, so every
repair, verification and landing capability is dead on arrival. On top of that the door
spends **69% of every request re-parsing adapter source files with a quadratic AST walk**,
which is why a request that does 80 ms of work takes 218 ms. Ranked: sequencing, the
quadratic default-argument scan, derivation slots, the magnet rows, then the seven domains
with no substrate on this machine.

---

## §1 What was measured, on what

| instrument | scope | result |
|---|---|---|
| `swe_capability_matrix_v1.py` | 54 ordinary team cases, per-case oracle | **17 REAL / 0 FALSE / 37 REFUSED / 0 DAMAGED**, median 142 ms |
| `swe_advanced_probe_v1.py` | 49 advanced requests, 11 axes | **2 served / 47 refused**; 39 are write requests and **0 of 39 served** |
| registry anatomy | 440 rows | 293 `.auto.v1` law rows · **147 real** · **84 SWE** · **43 chain-bound** · 41 standalone |
| **direct engine audit (new)** | 11 key adapters called **with the door bypassed** | **8/11 return a verified artifact**; the 3 failures are fixture/substrate, not logic |
| **latency decomposition (new)** | `cProfile` over 3 warm `solve()` calls | `binding_view` **69%** of the request, of which `adapter_defaulted_keys` is **1.34/1.95 s** and `ast.walk` iterates **593,916 nodes** |
| substrate probe | `importlib.metadata` for the pinned wheels | `tree_sitter` / `tree_sitter_languages` metadata **absent in this sandbox**; the index row now fails closed (`TREE_SITTER_SUBSTRATE_IDENTITY_UNAVAILABLE`) |

Direct-engine table (repo-relative args, output under `canonical/astra_runtime/tmp/`):

| engine | args | result |
|---|---|---|
| `python.source.dead_code.v1` | `source_root` | **2 ms**, `output_verified` |
| `python.source.complexity.v1` | `source_root` | **1 ms**, `output_verified` |
| `python.source.audit.ast` | `source_root` | **0 ms**, `output_verified` |
| `python.source.symbols.resolve.v1` | `source_root`, `queries` | **2 ms**, `output_verified` |
| `python.source.change_impact.testselect.v1` | `source_root`, `changed_paths` | **4 ms**, `output_verified` |
| `python.tests.audit.unittest` | `source_root` | **80 ms**, `output_verified` |
| `python.tests.mutation_score.v1` | `source_root`, budgets | **166 ms**, score **1.0** |
| `python.tests.generate.scaffold.v1` | `source_root` | 4 ms, `output_verified` but `complete: false` — and it wrote outside its output path (P6) |
| `python.source.test_adequacy.v1` | `source_root` | **fails** `TEST_ROOT_MISSING` on a flat layout |
| `code.index.tree_sitter.incremental.v1` | `source_root` | **fails** `TREE_SITTER_SUBSTRATE_IDENTITY_UNAVAILABLE` |

Authority: **NONE.** One tree, one machine, one commit.

---

## §2 The three layers, separated for the first time

| layer | verdict | evidence |
|---|---|---|
| **execution** (does the engine do the work) | **works, and is fast** | 8/11 engines verified, 0.5–166 ms, zero model calls |
| **derivation** (does the sentence produce the args) | **thin** | `derive()` fills 22 slot names; 85 distinct slots are declared across 84 rows |
| **sequencing** (does the door run more than one row) | **absent** | 43 of 84 rows require another row's artifact; the door admits exactly one |

That split is the whole answer. V12 and V13 both measured layer 3 and blamed layer 2. The
engines were never the problem.

---

## §3 Ranked problems

### P1 — No sequencing: 43 of 84 hardcore rows can never be a first step
`requires` already names another row's `provides`; `_try_composed` already exists but only
runs after a raw-goal compilation failure, and a decisive typed plan explicitly forbids it.
So `code.patch.tree_sitter.verify.v1` (needs `index_path` + `selection_path`),
`python.tests.advance.mutation_kill.v1` (needs `source.file.available`),
`python.fault.localize.dynamic.dataflow.v1` (needs `test.corpus.available`),
`python.pr.land.composer.v1` and both review pipelines are unreachable by construction.
**Reaches:** every repair, verification and landing request — the entire class the question
is about. **Mechanism:** topological walk of the `requires ∩ provides` closure from the
admitted row; each artifact is already a content-addressed file on disk. **Cost:** one
function, no new subsystem. **Expected:** the only lever that moves 43 rows at once.

### P2 — The door re-parses adapter source on every request, quadratically
`declared_input_derivation_v1.adapter_defaulted_keys` (L204) calls `ast.parse` on the
adapter file **and then `ast.walk(tree)` once per `args.get(...)` call site** to find a
boolean-`or` parent. `cProfile` over three warm `solve()` calls: `binding_view` = **1.368 s
of 1.954 s (69%)**, `adapter_defaulted_keys` = 1.344 s, `ast.walk` = 1.035 s over
**593,916 `iter_child_nodes` calls**. Eight calls per request.
**Reaches:** every request, all 54 matrix cases and all 49 census cases. **Mechanism:** two
independent fixes, both small — (a) memoise the (path, sha256) → defaults map, (b) build one
parent map per parse instead of re-walking per call site. The work itself is 1–80 ms; the
door's median is 142 ms. **This is the single biggest latency defect in the tree and it is
in the routing layer, not the engines.**

### P3 — Derivation covers 22 of 85 declared slots
Rows blocked by a slot nobody produces (`output_path` excluded — it has a dedicated
relocation path): **25 of 84**. The recurring ones: `symbol` (4 rows), `task_text` (4),
`index_path` (3), `to_module`/`target_module` (4), `edits`, `selection_path`, `test_cwd`,
`pr_intent_path` (2), `time_budget_s` (2), `page`/budget knobs. Measured consequence:
`python.refactor.move_function.v1` returns `NO_DECISIVE_TYPED_PLAN` for "Move the function
add from `pkg/mod.py` into `pkg/calc.py` and update every caller" — both files are stated,
`symbol` and `to_module` are not derived. **Mechanism:** six rules in the existing table.

### P4 — Sibling rows share an effect token, so a family is never decisive
Mutation family token `mutation` matches both `python.tests.mutation_score.v1` (measures)
and `python.tests.advance.mutation_kill.v1` (improves) → ambiguous → fallback → the
measuring row answers "increase the mutation score". Git token `git` also matches
`git.history.bisect_regression.v1`, so the git family can never win and all five git probes
fall to bisect. **Mechanism:** effect-named tokens. **Measured caveat:** alone it moves the
census 2/49 → 2/49 — it is a prerequisite for P3, not a lever.

### P5 — Five magnet rows absorb 24 of 49 selections, then refuse their own inputs
`dead_code` ×6, `bisect_regression` ×6, `mutation_score` ×4,
`software.repair.choreograph.crossfile.v1` ×4, `inline_helper` ×4. The choreographer
declares 40+ keywords (`race`, `concurrency`, `thread`, `unused`, `deprecated`,
`sql injection`, `fix the code`) so it claims questions it can only answer by mutating.
**Mechanism:** the analysis-only guard already exists; apply it where magnets are chosen.

### P6 — An engine's contract is narrower than its declaration
`python.source.test_adequacy.v1` refuses `TEST_ROOT_MISSING` on a layout where tests sit
beside the module; `python.tests.generate.scaffold.v1` returns
`output_verified: true, complete: false` (a partial success reported as success);
`python.tests.mutation_score.v1` refuses `BASELINE_TEST_SUITE_FAILED_OR_EMPTY` when the
suite's import path does not match its cwd. Each is a tiny contract fix and each currently
reads as a capability gap.

**One of them changes files outside its declared output.** During this audit,
`python.tests.generate.scaffold.v1` — given `source_root` and `output_path` under
`canonical/astra_runtime/tmp/` — **deleted and recreated
`generated_tests/pkg/test_generated_smoke_*.py` at the repository root**. The run was
reverted by hand (`git checkout -- generated_tests/` plus removing the untracked file) and
the tree is clean, but the defect is real and is exactly the class this repository exists
to refuse: an engine whose writes are not bounded by its declared contract, invisible to
the census because the census only hashes the fixture directory it built.

### P7 — Substrate identity is proved from wheel metadata, so vendored deployments fail
`code.index.tree_sitter.incremental.v1` verifies its parser by
`importlib.metadata.distribution("tree-sitter")`. In this sandbox the modules import, parse
and index (measured in V13: **11 files, 7 languages, 22 definitions, 69 references, 71 ms**)
but the dist-info is gone, so the row refuses
`TREE_SITTER_SUBSTRATE_IDENTITY_UNAVAILABLE`. A vendored or unzipped wheel — the exact
deployment the registry's own `pip-download-only-binary` closure describes — is
unusable by design. **Mechanism:** fall back to hashing the located package files when
metadata is absent, and record which evidence was used.

### P8 — Eight hardcore domains have no row, and seven of them have no substrate here
No rows: build systems, packaging/release, dependency vendoring, distributed services,
observability, tracing, memory/leaks, API/ABI design. No substrate either: `rustc cargo go
javac clang cmake gdb lldb py-spy scalene hyperfine yq pytest hypothesis ruff mypy bandit
coverage`. Those lanes are **unmeasurable on this machine**, not failing.

### P9 — One confirmed false answer is served, and nothing compares effect to row name
"Review `pkg/service.py` for API design problems" → `python.source.secret_scan.v1` →
`PASS`. `implementation_effect_error` already compares stated effects to declared
contracts; it is not applied to served answers.

### P10 — 29 adapter modules on disk have no registry row
Including `python_source_tree_codec.py`, `python_test_corpus_discovery_v1.py`,
`concrete_execution_oracle.py`, `grounded_executable_composition.py`.

### P11 — The tree's own suite is red
11,754 cases, **380 failed**, 0 errors, 223 files (`HONEST_SUITE_BASELINE_20261017_V1.json`,
authority NONE, subject `370005ad`). Plus one goal-compiler test red on `main` since
`9f80823`.

---

## §4 The ladder, and where the machine actually sits

| level | definition | position |
|---|---|---|
| L0 | **report** on a file it is given | **reached**, 7 engines, 0.5–80 ms |
| L1 | **edit** one file it is given | **partly**: 8 standalone refactor rows, 0 census hits |
| L2 | **edit several files coherently** | **not reached**: change-set planner exists, never binds `edits_path` |
| L3 | **repair and prove it** — patch + run the suite + report | **not reached**: verifier chain-bound (P1) |
| L4 | **drive a task** — issue → plan → patch → test → PR | **not reached**: `issue_to_pr` chain-bound on three producers |
| L5 | **self-extend** — notice its own gap and close it | **not attempted** |

L3 is the level the question is asking for, and P1 is the only thing between L2 and L3.

---

## §5 Order of work

| # | work | reaches | cost |
|---|---|---|---|
| 1 | **memoise + de-quadratic `adapter_defaulted_keys`** | every request; ~69% of latency | tens of lines, no intent needed beyond one |
| 2 | **chain runner** over `requires ∩ provides` | 43 rows: L3 and L4 | one function + tests |
| 3 | **six derivation rules** (`symbol`, `to_module`, `edits`, `index_path`, `task_text`, budgets) | 25 rows | one rule each |
| 4 | **effect-named family tokens** | 9 requests, unblocks #3 | one line per family |
| 5 | **magnet containment** | 24 wrong selections | reuse `_ANALYSIS_ONLY_TRIGGERS` |
| 6 | **contract fixes** (P6) + **bounded writes** + **substrate fallback** (P7) | 3 engines, 1 crown row, no unauthorised edits | small |
| 7 | **effect-faithfulness gate** on served answers | the false-answer class | reuse `implementation_effect_error` |
| 8 | rows for build/packaging/dependency/CI-YAML | 4 domains | after 1–4 |

Do **not** rebuild: the engines, the tree-sitter index and patch verifier, the AST editor,
the typed selector, `declared_input_derivation_v1`, `requires/provides`, the acceptance
chain. All are measured working in §1.

---

## §6 Limits of this document

* The direct-engine audit used **hand-written arguments** — that is exactly the door's job,
  so it proves the engines work, not that a sentence can reach them.
* The advanced census has **no per-request oracle**; `served` means `pass: true` and no
  unauthorised edit.
* The tree-sitter measurement in V13 (71 ms, 7 languages) was taken in an environment with
  the pinned wheels installed; **this sandbox no longer has them**, which is why P7 exists.
* Estimates marked "reaches N rows/requests" are row counts and census hits, not verified
  end-to-end successes.

---

## §7 Reproduction

```bash
python3 execution_guard/swe_capability_matrix_v1.py          # 17 REAL / 0 FALSE / 0 DAMAGED
python3 execution_guard/swe_advanced_probe_v1.py             # 2 served / 47 refused

# the three layers, in one go
python3 - <<'PY'
import sys, time; sys.path.insert(0,'.')
from canonical.runtime.live_brain_route_admission_v1 import load_verified_registry, solve
from canonical.runtime.swe_typed_plan_v1 import _FAMILY_SWE_PREFIXES
reg = load_verified_registry()
real = {c:e for c,e in reg.items() if not c.endswith('.auto.v1')}
swe  = {c:e for c,e in real.items() if c.startswith(_FAMILY_SWE_PREFIXES)}
prov = {p for e in real.values() for p in (e.get('provides') or [])}
chain = [c for c,e in swe.items() if set(map(str,e.get('requires') or [])) & prov]
print("rows", len(reg), "real", len(real), "swe", len(swe), "chain", len(chain))
PY

# where the latency goes (binding_view dominates; adapter_defaulted_keys is quadratic)
python3 -m cProfile -s cumulative -m canonical.runtime.goal_compilation_benchmark_v1 2>/dev/null | head -20
```

Authority: **NONE**.
