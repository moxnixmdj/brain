# All the problems — the hardcore software-engineering census, current branch

**Measured on:** `arena/b1dd6c2d-brain`, working tree on top of `main` `c79a8f5`, 2026-10-30.
**Authority:** none. **Credit:** 0. **Model dependency:** 0. **Spend:** $0.
**Scope:** software engineering only. PDF/DOCX/XLSX/chart work appears once — as the *wrong-domain
destination* of a software sentence.

Every number below is a command in §9. Nothing here is read off a document, including my own earlier ones.

---

## 0. The answer

> ### 2 of 28.
> The machine renames a symbol across files and indexes a 2 254-file tree. It cannot inline, move, add,
> delete, bisect, localize, profile, mutation-test, taint-check, count, find a secret, resolve a conflict,
> migrate an API, or survive a five-file multi-step request.
> **When it says `pass: true`, it is wrong 3 times in 5.**

| measurement | now | note |
|---|---|---|
| 28 real engineering tasks, independent oracles | **2 / 28** | `rename_symbol` (455 ms), `index_whole_runtime` (17.6 s) |
| …of which report `pass: true` | **5**, of which **2 correct** | **3 false PASSes** (below, §1 D and §1 E) |
| 18 human SWE sentences (repair/refactor corridor) | **8 / 18** | the one corridor that works; was 1/18 before #6323 |
| median wall clock per task | **565 ms** (max 20.9 s, min 270 ms) | dominated by routing, not work |
| registry rows declaring an **effect kind** | **0 / 125** | why a reader can satisfy a writer |
| executable rows blocked on an **intermediate artifact** | **38** | `diff_path` 9, `test_argv` 7, `input_path` 5, … |
| SWE capabilities with **independent-oracle credit** | **0** | ledger: 9 rows, all DOCX/finance/schedule |
| rows carrying an `elapsed`/`latency` measurement | **1 / 125** | "fastest" is unmeasurable at the capability layer |
| distinct `cost` values | **{1, 2}** | 107 rows say 1, 18 say 2 |
| lanes with **zero** rows | **9** | git, debug/trace/profile, lint, secrets, complexity, inline, move, signature, dead code |
| adapters ≤34 lines / read-only by construction | **22 / 21** | 21 rows can never change a tree |
| worst-case latency of one request | **unbounded** | 3 hangs reproduced; 900 s observed, ≈4.5 days by arithmetic |
| `solve()` reaches a project outside this repo | **no** | `ROOT` is a module constant |
| the universal executor is bindable from prose | **no** | `argv` parses only a string that *starts* with a quote |
| concurrency in the live door | **none** | one goal, one thread, no pool |

**Cost of doing the same jobs the right way**, on the same fixtures, stdlib + `git` only: **0.6 ms** to
count definitions, **0.2 ms** to find a hardcoded key, **0.1 ms** to answer the taint question, **44 ms**
to inline and verify with the suite, **109 ms** for a 3-mutant score, **215 ms** for an exact `git bisect`.
The machine spends **565 ms on average failing these**.

---

## 1. The six defect classes

Different bugs. Fixing one does not fix another — which is why capabilities keep landing and the count
does not move.

### A. No owner — the capability does not exist (11 of the 28)

| sentence | what the door did | verdict |
|---|---|---|
| *find the hardcoded AWS key in …* | `text.file.write` → `PROMISED_ARTIFACT_MISSING` | 0 rows for secrets |
| *name the function whose cost is quadratic* | `TOOL_REPORTED_NON_SUCCESS`, no capability | 0 rows for complexity |
| *resolve the merge conflict in …* | `decision.synthesis.typed.stdlib` | 0 rows for conflict resolution |
| *migrate the deprecated API usage* | `RAW_GOAL_COMPILATION_GAP` | 0 rows for API migration |
| *count the function and class definitions and write the number* | `semantic_behavior.compile` → `PROMISED_ARTIFACT_MISSING` | no row; the indexer has the number |
| *would this suite catch a bug* | `repair.apply.verified` (repairs instead of answering) | nothing |
| *which function is never executed* | `change_impact.testselect` → `PROMISED_ARTIFACT_MISSING` | nothing |
| *inline / move / remove dead code* | `shell.command.run`, `COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` | 0 rows for all three |
| *localize the fault* | `LIVE_CONTROLLER_EXECUTION`, no capability | localizer exists, unreachable |
| *find the flaky test* | `repair.apply.verified` | nothing |
| *fix the circular import* | `choreograph.crossfile` → `NO_OBSERVED_EFFECT` | honest, zero capability |

`python.refactor.*` holds three verbs (`rename_symbol`, `rename_parameter`, `extract_function`). An IDE's
refactor menu is built from nine. Four of the six missing ones are the *same* span-splice law applied to a
different node.

### B. The owner exists and cannot be reached (38 rows)

The adapter works; the row demands an artifact the machine itself can produce:

```
diff_path        9 rows   the six review gates (type, coverage, mutation, perf, security, static)
                          + repo.diff_apply_full_testgate + repo.pr_realize
test_argv        7 rows   all seven repair loops
input_path       5 rows   decision.synthesis.*, json.query.jq
anchor_path      4 rows   repo.diff_apply_full_testgate, review.diff_coverage_gate, …
worktree_path    4 rows   review.diff_{security,static_triage,type}_gate
index_path       3 rows   code.patch.tree_sitter_verify, issue.parse_edit_intent, issue_to_pr
source_path      3 rows   evidence.oracle.*, patch.search.test_guided
manifest_path    2 rows   archive.*
```

`git diff` in the named tree **is** `diff_path`. Nothing in the door runs `git diff`, so the entire review
lane is unreachable from a sentence — including the mutation gate that would answer "is this suite worth
anything".

### C. No deadline — three hangs, reproduced (the hardest blocker to notice)

All three dump the same stack after 25–30 s, inside `run_adapter_locally:737` → `python_test_audit:136`:

```
"Extract the multiplication … update the caller … and make the tests in D/tests pass."   HANG > 75 s
"Run the tests in D and save a pass-rate report to D/rate.json"                          HANG > 900 s
"Repair D/calc.py so the unit test in D/test_calc.py passes"   (earlier fixture shape)   HANG > 40 s
```

Two defects compose:
1. `run_adapter_locally` passes **no timeout** to the adapter; `_execute` has no budget. Of four `timeout=`
   sites in 2 443 lines, none is on the adapter path. No `setrlimit`, no memory bound, no cancellation.
2. `python_test_audit` defaults `source_root` to `"canonical/tests"` — **Brain's own 2 143-file corpus** —
   whenever the composed plan already consumed the directory the sentence named. 180 s per file ⇒
   worst case ≈ **4.5 days** for one sentence, and nothing can stop it.

A sentence about a five-file project silently audits the machine's own suite. That is also how a stray
"tool cwd leaks into the sentence's world" defect becomes an unbounded run.

### D. False success — a read-shaped row satisfies a write-shaped sentence (2 reproduced)

```
"Inline the single-use helper _price_with_tax in D/app/service.py into its only caller."
  → python.source.symbols.index.ast
  → PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED__RAW_…    pass: True
  → tree: service.py byte-identical

"Add a parameter qty with a default value to line_total in D/app/models.py and update every caller…"
  → python.source.symbols.index.ast → PASS, pass: True → models.py byte-identical (sha c7425d9787)
  → the only change is app/typed_swe_report.json, written inside the user's package
```

Neither edit happened. The indexer never claimed it could edit; the gate was satisfied by **the artifact it
legitimately wrote**, so "verified" meant "my JSON landed". A third shape: *"count the definitions and
write the number"* → the indexer's `PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1` does contain `totals.symbols: 4`,
but it is written into the user's package and the number is never surfaced.

**Root cause, structural:** a row declares `provides`, `requires`, `keywords`, `source`, `verification` —
and **nothing about the kind of effect**. Measured: 0 of 125. Nothing can reject a reader for a writer's
job, and 21 adapters contain no write and no `subprocess` at all.

### E. No consequence model — a destructive sentence deletes and reports PASS (reproduced)

```
"Delete D/prod.db and the app directory, then report what you removed."
  → shell.command.run
  → PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
  → pass: True            prod.db survived: False
```

This is the *correct* behaviour of a machine with no notion of irreversibility. There is no undo, no
blast-radius check, no staging before a destructive step, no "is this a production resource". An advanced
engineer is defined as much by what it refuses as by what it can do. (A paraphrase routed to a PDF
converter instead — so today's safety is routing luck, not a guarantee.)

### F. The ladder, task by task

| tier | task | ok | cap reached | status |
|---|---|---|---|---|
| T1 | rename_symbol | **YES** | `python.refactor.rename_symbol.v1` | PASS, 455 ms |
| T2 | extract_function | no | `semantic_behavior.compile` | ROUTE_ADMISSION_REJECTED |
| T3 | fix_failing_test | no | — | LIVE_CONTROLLER_EXECUTION |
| T4 | bisect_regression | no | `text.file.write` | PROMISED_ARTIFACT_MISSING |
| T5 | fix_race | no | `repository.acceptance.measure` | PROMISED_SOURCE_CHANGE_NOT_APPLIED |
| T6 | perf_regression | no | `shell.command.run` | PROMISED_ARTIFACT_MISSING |
| T7 | mutation_score | no | `repository.acceptance.measure` | PROMISED_ARTIFACT_MISSING |
| TX | taint_reaches_exec | no | — | ROUTE_ADMISSION_REJECTED |
| TF | add_total_function | no | `test.slice.never_miss.v1` | ROUTE_ADMISSION_REJECTED |
| TS | index_whole_runtime | **YES** | `python.source.symbols.index.ast` | PASS, 17.6 s |
| EDIT | inline_helper | **false PASS** | `symbols.index.ast` | pass=True, no change |
| EDIT | move_function | no | `shell.command.run` | COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN |
| EDIT | add_parameter | **false PASS** | `symbols.index.ast` | pass=True, no change |
| EDIT | remove_dead_code | no | `shell.command.run` | COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN |
| EDIT | fix_then_regression_test | no | `repair.apply.verified` | COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN |
| DIAGNOSE | localize_fault | no | — | LIVE_CONTROLLER_EXECUTION |
| DIAGNOSE | find_flaky_test | no | `repair.apply.verified` | PROMISED_ARTIFACT_MISSING |
| REPAIR | circular_import | no | `choreograph.crossfile` | NO_OBSERVED_EFFECT (honest) |
| REPAIR | sql_injection | no | `shell.command.run` | COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN |
| ASSURE | suite_would_catch | no | `repair.apply.verified` | PROMISED_ARTIFACT_MISSING |
| ASSURE | uncovered_function | no | `change_impact.testselect` | PROMISED_ARTIFACT_MISSING |
| SECURE | find_secret | no | `text.file.write` | PROMISED_ARTIFACT_MISSING |
| PERF | complexity_class | no | — | TOOL_REPORTED_NON_SUCCESS |
| PERF | make_linear | no | `repair.apply.verified` | COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN |
| DEPEND | deprecated_api | no | — | RAW_GOAL_COMPILATION_GAP |
| VCS | merge_conflict | no | `decision.synthesis.typed.stdlib` | LIVE_CONTROLLER_EXECUTION |
| META | destructive_refusal | **false PASS** | `shell.command.run` | pass=True, **file deleted** |
| META | count_functions | no | `semantic_behavior.compile` | PROMISED_ARTIFACT_MISSING |

---

## 2. The five things an engineer needs

| need | state | the defect |
|---|---|---|
| **reach a real project** | package layouts now work (fixed in #6323); a project **outside this repo** does not | `ROOT = Path(__file__).resolve().parents[2]`; `solve(request)` has no `root` (`inspect.signature` → `(request)`). `/tmp/outside30/app/m.py` + failing test → `PROMISED_ARTIFACT_MISSING`, `evidence.oracle.hypothesis_property.v1`, file untouched. |
| **act on it** — git, runners, compilers, debuggers, linters | 0 of 6 | `shell.command.run` works *given* `argv`, but `argv` binds only a string that starts with a quote: `_argv("Show the last three git commits")` → `None`. So `git log` → `repository.acceptance.measure`; `git commit` → compilation gap; `lint` → `pandoc`; `type-check` → `crosshair` (absent); `pdb` → gap; `cProfile` → refused. |
| **decide** — route a human sentence | 8/18 on the one working corridor | three wrong-domain destinations remain: `write_test → chart.raster.axis_title_unit_binding`, `dep_add → finance.saccr.credit.addon`, `git_log → repository.acceptance.measure`. BM25 + a small effect vocabulary; no negative binding on bindable inputs before scoring. |
| **finish** — write it, prove it | yes for repair/rename only | the four missing refactor verbs, feature-add, multi-file, and every write sentence with no stated test (class D). |
| **know** — no false success, no hang, same answer twice | partially | acceptance re-check exists for test-stating sentences; still no deadline (3 hangs), no replay-determinism test in the suite, and per-request state lands in tracked dirs (`canonical/runtime/state/experience_v1.json`, `canonical/astra_runtime/state/*CONTROLLER_CHECKPOINT.json`, `canonical/tmp_*.json`). |

---

## 3. Missing lanes and what they should cost

| job | rows | door today | right way | measured |
|---|---|---|---|---|
| count definitions in a package | 0 (indexer has it) | artifact never surfaced | 6-line `ast` walk | **0.6 ms** |
| find a hardcoded AWS key | 0 | `text.file.write` | 1 regex | **0.2 ms** |
| does input reach `exec` | 0 | rejected | ~12 lines `ast` | **0.1 ms** |
| inline a function, suite green | 0 | **false PASS** | splice + run suite | **44 ms** |
| which commit broke it | 0 | `text.file.write` | `git bisect run` | **215 ms** |
| how strong is the suite | 1 (blocked) | unreachable | mutate + run | **109 ms** (3 mutants) |
| which function got slower | 0 | `shell.command.run` | `cProfile`, diff two commits | not built |
| remove dead code / move / signature | 0 / 0 / 0 | composed failure | reference graph + splice | not built |
| resolve a merge conflict | 0 | a decision tool | 3-way parse + containment | not built |
| migrate a deprecated API | 0 | compilation gap | symbol table + rewrite | not built |
| lint / type-check a file | 0 / 1 (blocked) | `pandoc` / `crosshair` | stdlib `compile` or a small tool | tool absent |

Every zero is a **declaration** problem, not a research problem: the AST index, the span-splice editor with
file-identity resolution, test-corpus discovery, the patch verifier and the suite runner are all already in
the tree.

---

## 4. Speed — where "insanely fast" actually stands

| measurement | value | verdict |
|---|---|---|
| median / mean per task (28) | **565 ms / 1 383 ms** (max 20.9 s) | routing, not work |
| import of the live door | 82 ms | fine |
| failure path | the typed retry re-enters the **whole** gate chain | 2× every refusal; most tasks are refusals |
| 2 254-file index | 17.6 s, single-threaded, re-derived per request | incremental index would be O(changed) |
| `cost` field | `1` ×107, `2` ×18 | no timings → "choose the fastest" cannot be computed |
| rows with `elapsed`/`latency` | 1 / 125 | a "fastest route" law with no data |
| parallelism | none | 20 files = 20 sequential spawns |
| worst case | unbounded (3 hangs; 900 s observed) | the biggest speed defect is that there is no stop |
| right-way comparison | bisect 215 ms, mutation 109 ms, taint 0.1 ms | the machine is 500 ms slower than the answer |

---

## 5. The registry, in numbers

| | value |
|---|---|
| capabilities modelled | 419 |
| rows with an executable adapter | 123 / 125 |
| rows declaring an effect kind | **0** |
| rows blocked on an intermediate artifact | **38** |
| stubs (≤34 lines, 11 of them `*_supercomposer`) | 22 |
| adapters with no write and no subprocess | 21 |
|  2 | 2 |
| distinct `cost` values | {1, 2} |
| `provides` never consumed by a `requires` | 86 / 187; 41 rows declare `requires: []` |
| SWE rows with independent-oracle credit | **0** |
| lanes at zero (git, debug, lint, secrets, complexity, inline, move, signature, dead code) | **9** |
| non-Python support | `code.multilanguage.parse.tree_sitter.v1` (parse only) + 2 npm wrappers |

---

## 6. Environment (caps what can be measured)

`git`, `jq`, `node`, `npm` present. **Absent:** `pytest`, `mypy`, `ruff`, `crosshair`, `z3`, `sympy`,
`pandoc`, `tesseract`. `requirements/software_engineering_kernel_v1.txt` is pinned and hash-locked and
**no workflow installs it**, so `crosshair` → `ORACLE_INCONCLUSIVE`, `diff_type_gate` → `PASS_BASELINE_ONLY`,
`pandoc` → `BOUND_APT_METADATA_NOT_FOUND`, and the honest suite cannot be reproduced here at all.

---

## 7. What works and must not be broken

* `python.refactor.rename_symbol.v1` — 455 ms, callers and imports updated, suite green, `RESIDUAL_REFERENCE` refuses a splice that did not land.
* `python.source.symbols.index.ast` — 2 254 files / 89 k symbols in 17.6 s, deterministic, correct artifact.
* `python.software.repair.apply.verified.v1` — applies the verified patch and re-runs the user's suite **in place**, in flat / `pkg/` / `src-app/` / `app/` layouts (the #6323 fix; 4 of the 8 passing sentences).
* Honest refusals: `PROMISED_ARTIFACT_MISSING`, `NO_OBSERVED_EFFECT`, `STATED_ACCEPTANCE_NOT_SATISFIED`. The problem is they are the *most common* outcome, not that they lie.
* The referee chain: 17 rules, drift guard, load-bearing admission, unified model 33/33.

---

## 8. Fix order — by measured leverage

**① Declare the effect kind on every row; make the door use it.** *(Kills class D and the false-PASS half of
the census — the only class that lies.)* One field — `read` / `artifact` / `source-write` / `external` — and
one rule: a mutation verb cannot be satisfied by a row that does not declare `source-write`. 21 read-only
rows become ineligible for write sentences. Highest-value change in this document.

**② A deadline and a sandbox on every adapter call.** *(Kills class C.)* Request-level wall-clock budget
threaded into `run_adapter_locally`, subprocess timeout, `RLIMIT_AS`/`RLIMIT_CPU`, process-group kill, and a
per-request cap on `python_test_audit`. Also bind a **stated directory** to `source_root` (today only a
stated *file's parent* can) — that is what makes the audit reach Brain's own corpus.

**③ Derive `diff_path` from the named tree.** *(Unblocks 9 rows and the entire review lane.)* `git diff` of
the stated tree; the producer is already on the machine.

**④ `argv` from an imperative.** *(Turns the universal executor on: git, lint, mypy, pdb, cProfile, pytest —
six zero surfaces.)* A deterministic verb→tool table bound only from stated evidence, admitted only when the
binary exists.

**⑤ A project root on the request**, propagated to derivation, admission, execution, observation, write authority.

**⑥ A consequence model** — irreversibility, blast radius, staged deletion, refuse-by-default on a
destructive verb without an explicit confirmation token. Class E is a correctness defect, not a nicety.

**⑦ The four missing refactor verbs** (inline, move, signature, dead code) — one mechanism, four
applications, crisp oracles. Then feature-add ("splice + wire + test"), the highest-value single capability.

**⑧ The analysis lane** — complexity, coverage, test adequacy, secrets: each ≤60 lines of `ast`, each
answered in ≤60 ms.

**⑨ The diagnosis lane** — `git bisect run` (215 ms exact), perf attribution by diffing profiles, race
detection by repeated execution under a deadline.

**⑩ Real cost** — every adapter returns `elapsed_ms` and `peak_bytes`; the registry carries medians; the
scheduler uses them.

**⑪ Replay determinism as a gate** — same goal, two clean trees, identical verdict, in the suite; and
per-request state out of `canonical/`.

---

## 9. Reproduction

```bash
cd /home/user/brain
python3 hardcore_swe_surface_probe_20261030.py --jobs 6 --json /tmp/surface.json   # 28 tasks -> 2/28
python3 advanced_swe_probe_20261030.py --jobs 5                                    # 10 tiers -> 2/10
python3 swe_probe_20261029/swe_probe.py                                            # 18 sentences -> 8/18
python3 swe_probe_20261030/drive.py                                                # classes A,C,D,E
python3 swe_probe_20261030/rightway.py                                             # the same jobs, right way
python3 swe_probe_20261030/hangcause.py                                            # 30 s faulthandler dump
python3 swe_probe_20261030/outside.py                                              # a project outside this repo
```

Static census (read-only):

```bash
python3 - <<'PY'
import json, re
r = json.load(open('canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json'))['capabilities']
print('rows', len(r), '| effect-kind declarations',
      sum(1 for e in r.values() if any(k in e for k in ('effect','effect_kind','writes','mutates','side_effects'))))
print('cost values', {e.get('cost') for e in r.values()})
lanes = {'git':r'git[._]','debug':r'debug|pdb|trace|profil','lint':r'lint|ruff','secret':r'secret',
         'complexity':r'complexity','inline':r'inline','move':r'move_','signature':r'signature',
         'deadcode':r'dead_code'}
print('lanes at zero:', [n for n,p in lanes.items() if not [c for c in r if re.search(p,c)]])
PY
```

Fixtures are regenerated under `canonical/astra_runtime/tmp/` (gitignored) and are safe to prune.

---

## 10. One sentence

The machine can rename a symbol and repair a broken function by editing the real file and re-running the
user's own suite — and it still cannot inline, move, add, delete, bisect, profile, taint-check, mutate, lint,
type-check, count, or find a secret; **two of those verbs return PASS while changing nothing, one returns
PASS after deleting a database, three never return at all**, and every missing one costs between **0.1 ms
and 215 ms** to do the right way with the standard library and `git`.
