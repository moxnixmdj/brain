# What is between this machine and being the most advanced software engineer — V3

Measured 2026-10-29 on `arena/47739ce8-brain` @ `3fb8e01`, branched from `main` `e2d7981`;
S-1 was closed after this stamp and re-measured at HEAD (its table carries both columns).
Authority: **NONE**. Sandbox measurement, not independent verification. Credit: **0**.
Producer cognition model dependency: **0**. Incremental spend: **$0**.
Scope: hardcore software engineering. PDF/DOCX/XLSX/chart/archive work is excluded except where it is
the *wrong-domain destination* of an SWE request.

Supersedes V2 where they differ. V3 adds the measurement V2 said was missing (§2 P0-6): the machine
was measured **on this repository** — 5,419 Python files, 2,143 test files, 147,285 lines in
`canonical/` — with an independent AST oracle, and that is where the biggest problems turned out to
be. Every number below is from a probe that ran on this branch; the sentence matrix is
`execution_guard/swe_capability_matrix_v1.py`.

---

## 0. The answer in one paragraph

On **47 synthetic requests on 8-file trees** the machine is now honest and fast: **10 real answers, 1
false answer, 36 honest refusals, 0 damaged files, median 66 ms** (the harness's own oracles were
blob-substring tests and are now typed; see S-1). That number is misleading in the
one way that matters: **every one of those 47 trees is tiny.** Measured on *this repository*, the same
machine:

* answers "find every caller of X in `<dir>`" with a **whole-tree parse index** instead of callers,
  and **PASSES** (independent AST oracle: 32 call sites; the door names none) — the same sentence is
  a *real* answer on a 3-file tree;
* answers "find the dead code in `<dir>`" the same way: an index, PASS, no dead-code list;
* takes **313–325 seconds** to answer one change-impact question (toy tree: 36 ms — an 8,700× gap);
* writes a **103 MB** JSON for a single parse and a **284 MB** index for a single index request;
  `canonical/astra_runtime/tmp` grew to **494 MB** from a handful of real queries;
* still cannot compose: "write a unit test for X, run it, save a report" and "find the bug in X, fix
  it, run the tests" both fail, in 393 ms and 47 ms.

So the frontier is no longer truthfulness on toy trees, and it is no longer reach for the review
family (that closed this round: `Lint <file>` and `Type-check <file>` went refused → REAL). It is
**scale**: correctness that survives a real repository, latency that survives a real repository, and
an index representation that does not cost hundreds of megabytes to answer a question about one
symbol.

---

## 1. What is genuinely advanced, and measured

Keep these; everything else is judged against them.

| what | evidence |
|---|---|
| cross-file symbol rename with provable-binding scope law | `Rename the parameter old_price to price in <util.py>` → `def total(price, qty)`, body rewritten, 1.2 s, verified by the file's bytes |
| test-guided repair, five families + verified apply | `the add function in <calc.py> is broken, fix it so its tests pass` → REAL, ~1.0 s, real `unittest` exit code as the oracle |
| AST symbol index (small scope) | `call_edge_count` + `caller_index_size` for a named function, 159 ms |
| review gates, now reachable | `Lint <file>` → ruff on changed lines only; `Type-check <file>` → mypy; 0.6 s |
| dead-code / impact / counts (small scope) | 36–47 ms, artifacts name the actual answer |
| whole-repo multigenerational indexer | 2,256 files, 15,732 definitions, **916,734 references** parsed in one pass |

The machinery is real. The problems are around it.

---

## 2. The problems

### S-1 · At directory scale a *parse* is accepted as the *answer*, and it passes

| scope | files | door | verdict | independent oracle |
|---|---|---|---|---|
| 3-file toy tree | 3 | `python.source.symbols.index.ast`, 159 ms | **REAL** (call edge map) | callers found |
| `canonical/tests` | 2,143 | `code.index.tree_sitter.incremental.v1`, **8.7 s** | **PASS**, reports `definition_count` | **32 call sites** for `load_verified_registry`; door names none |
| `canonical/runtime/bound_capabilities` | 146 | `code.index.tree_sitter.incremental.v1`, **2.0 s** | **PASS**, reports `file_count` | 0 call sites |

The sentence is identical; only the size of the scope changes. Small scope → the capability that
answers. Large scope → an indexer that does not answer, and the door still says PASS.

**Closed in the same PR, by declaration.** The seam already had one table of it — `_STATED_EFFECTS`
(`live_brain_route_admission_v1.py:1254`, applied by `stated_answer_errors`) — so this is two more
rows (a caller map, dead code) plus one call *before* execution: a capability that does not declare
the stated effect is refused without being run, `executed=False`, so no verdict is overwritten and
the typed retry is free to reach the one that does. Re-measured on `canonical/tests`, same sentence:

| | before | after |
|---|---|---|
| capability | `code.index.tree_sitter.incremental.v1` | `python.source.symbols.index.ast` |
| verdict | PASS, `definition_count`, **no caller named** | PASS, `callers_of` map |
| coverage of the 22 oracle callers (Name calls) | **0 / 22** | **22 / 22** (61 entries; strict superset — the extras are dotted/attribute calls a Name-only oracle cannot see) |
| latency | 8.7 s | **6.4 s** |
| `Find the dead code in <dir>` | PASS over `definition_count` | **`FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED`, 68 ms** (0 of 419 registry rows declare dead/unused) |

The dead-code refusal is the honest answer, not a regression: the moment a capability declares
`dead`/`unused` it is admitted by the same declaration, with no code change. The same
substitution happens for **dead code**: on `canonical/runtime/bound_capabilities` the door returns
`code.index.tree_sitter.incremental.v1` with `definition_count` and PASS in 1.2 s, and names no dead
function.

This is the most serious problem in the repository. It is not a routing bug in one place: it is the
*acceptance* layer accepting a capability whose `expect` is `output_verified: True` on a file-write,
for a request that asked a question about one symbol. The acceptance gate re-derives the *artifact*,
never the *question*.

**Reuse:** `python.source.symbols.index.ast` already produces the caller map (`call_edge_count`,
`caller_index_size`) and already refuses when it cannot; it is used on the toy tree. The fix is to
prefer the answering capability regardless of scope, or to make the indexer's row declare that it
answers a *parse* request and not a *caller* request — the same declaration-based rule
`stated_answer_errors` already applies to security and coverage.

### S-2 · One question costs five minutes on a real repository

```
"Which tests are affected if I change canonical/runtime/declared_input_derivation_v1.py?"
   cold 324,727 ms   warm 313,732 ms   PASS   133 affected files, 15 candidate tests
   the same question on a 3-file tree: 36 ms
```

The cause is visible in the adapter (`code_tree_sitter_impact_v1.py:164-169`): every query rebuilds a
Python-level reverse map over **every identifier reference in the index** — 916,734 rows for
`canonical/runtime` alone — before doing any BFS. The index stores per-reference rows by design; the
query materialises all of them, per call, in dict-of-sets Python objects.

**Reuse:** the same file already accepts a stated `index_path`, and `code.index.tree_sitter.
incremental.v1` already maintains an incremental index (`reused_file_count: 2256`) — the missing piece
is a *persisted* reverse map (symbol → importing/using files) written once when the index is written,
instead of rebuilt on every question. That is a column in an artifact that already exists, not a new
subsystem.

### S-3 · The index representation costs hundreds of megabytes

```
one parse of canonical/runtime      -> spool artifact  103 MB
one symbol-index request            -> artifact        284 MB
canonical/astra_runtime/tmp after a handful of queries   494 MB
cold index of canonical/runtime (2,256 files)            18.1 s
warm index (all 2,256 reused)                             3.4 s
```

916,734 reference rows carry `start_byte`, `end_byte`, `start_line`, `end_line`, `name`, `node_type`
each, as JSON. Nothing prunes them, nothing compresses them, and nothing reuses the artifact across
queries (the warm run still rewrites it).

**Reuse:** the index is content-addressed (`row_sha256`, `source_sha256`) and already incremental.
Keeping reference rows in a compact columnar form (or holding only *definition* rows plus a
per-file identifier multiset) is a representation change inside an existing artifact.

### S-4 · Composition still does not happen

```
"Write a unit test for <calc.py>, run it, and save a report to <out.json>."  393 ms  FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
"Find the bug in <calc.py>, fix it, and run the tests."                       47 ms  FAIL__LIVE_CONTROLLER_EXECUTION
```

The second one is routed, in 47 ms, to a patch **search** — the capability this branch already proved
is not a repair. Real software work is a chain; the DAG planner that could express one
(`goal_front_compiler_v1._dag_steps`, F12 `_bind_produced_artifact`) only fires when a sentence states
a command line or a payload+destination.

### F-1 · Whole daily-verb classes still have no registry row

Census over all 419 rows (id + `provides` + `keywords`, SWE-prefixed only):

| verb | SWE rows | |
|---|---|---|
| `type hint` | **0** | |
| `pyproject` | **0** | |
| `flag` (CLI option) | **0** | |
| `logging` | **0** | |
| `retry` | **0** | |
| `docstring` | **0** | |
| `format` | 1 — and it is `python.refactor.test_scaffold.fusion.v1`, not a formatter | |
| `git commit` | 1 — `python.repo.pr_realize.v1`, which needs a diff and a PR intent | |
| file-shaped `lint` / `typecheck` | 1 each, both diff-shaped (this is why S-1's fix mattered) | |

That is the matrix's `feature` lane 0/7. These are declarations over tools that already exist or are
one `pip install` away — not new engines.

### T-1 · The declared toolchain is provisioned by nothing

Six SWE rows declare a pypi source: `bandit`, `coverage`, `mypy`, `ruff`, `pytest` (plus the
mutation/perf gates). On a fresh container **all five are absent**; only `git` is present. I installed
them to take these measurements. V2 already measured that installing them alone changes **no verdict**
(9/1/37/0 at the time) — it is necessary and not sufficient, because the shape blocks first.

### T-2 · The tests lane is 0/3

`write_unit_test` promises a test file and never writes it (`PROMISED_ARTIFACT_MISSING`);
`tests_from_docstrings` fails its own verification (`ACTION_EXPECTATION_FAILED: verified:OBSERVED=
False`) even with pytest installed; `add_case_test` produces no observed effect. Verified again this
round on the 8-file tree.

### H-1 · The one false answer is a contract conflict — an owner decision

`"Repair <calc.py> so that the unit test <test_calc.py> passes, and save the repair report to
<out.json>"` returns PASS with the source byte-identical and the test red. The repair family's own
oracle (`live_solver_families_v3.py:430`) demands exactly that: untouched source + one applicable
patch in the report. The sentence asks for the test to pass. Two oracles in this repository disagree;
one of them has to change.

---

## 3. The order I would work in

1. ~~**S-1 — stop accepting a parse as an answer.**~~ **Done** (two declaration rows + a
   pre-execution gate; 0/22 → 22/22 callers at 6.4 s on `canonical/tests`).
2. **S-2 — the persisted reverse map.** One change turns a 5-minute question into a lookup, and it
   reuses the incremental index that already exists.
3. **S-3 — prune the representation.** 103 MB for a parse is a resource bug that will bite every
   downstream capability; definition rows + per-file identifier multiset.
4. **F-1 — the missing verbs**, as declarations over installed tools (`ruff format`, `mypy`, `git
   commit -m`, `add dependency`), cheapest reach in the list.
5. **S-4 — let the existing DAG planner fire on SWE chains.**
6. **T-2, then H-1** (H-1 needs the owner's decision, not code).

---

## 4. Reproduce

```
python3 execution_guard/swe_capability_matrix_v1.py                 # 47 requests, 8-file trees
python3 execution_guard/swe_capability_matrix_v1.py --lane feature  # the 0/7 lane
```

The scale probes are quoted verbatim with their oracles in §2 (independent AST walk for call sites;
`time` around one `door.solve`; `du`/`ls` for artifacts). They read
`live_brain_route_admission_v1.load_verified_registry()` and the real repository tree, and none of
them trusts a producer-reported field.
