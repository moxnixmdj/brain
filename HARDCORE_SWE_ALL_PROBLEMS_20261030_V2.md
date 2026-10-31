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
> **When it says `pass: true`, it is wrong once in three — and that one is a real deletion.**
> *(Was wrong three times in five until 2026-10-31; see §11. The fix converted two lies into
> honest refusals. The capability count did not move, which is the point.)*

| measurement | now | note |
|---|---|---|
| 28 real engineering tasks, independent oracles | **2 / 28** | `rename_symbol` (455 ms), `index_whole_runtime` (17.6 s) |
| …of which report `pass: true` | **3**, of which **2 correct** | **1 false PASS** (the deletion, §1 E); the two edit-lies are now refusals (§11) |
| 18 human SWE sentences (repair/refactor corridor) | **8 / 18** | the one corridor that works; was 1/18 before #6323 |
| median wall clock per task | **565 ms** (max 20.9 s, min 270 ms) | dominated by routing, not work |
| registry rows declaring an **effect kind** | **0 / 125** | why a reader can satisfy a writer |
| executable rows blocked on an **intermediate artifact** | **38** | `diff_path` 9, `test_argv` 7, `input_path` 5, … |
| SWE capabilities with **independent-oracle credit** | **0** | ledger: 9 rows, all DOCX/finance/schedule |
| rows carrying an `elapsed`/`latency` measurement | **1 / 125** | "fastest" is unmeasurable at the capability layer |
| distinct `cost` values | **{1, 2}** | 107 rows say 1, 18 say 2 |
| lanes with **zero** rows | **9** | git, debug/trace/profile, lint, secrets, complexity, inline, move, signature, dead code |
| adapters ≤34 lines / cannot write at all | **22 / 26** | 26 adapters contain no file write |
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

### D. False success — a read-shaped row satisfies a write-shaped sentence (**FIXED 2026-10-31, §11**; was 2 reproduced)

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
job, and 26 adapters contain no write at all (20 with no write and no `subprocess`, 6 that shell out
without writing).

**Root cause, one layer down (found and closed 2026-10-31):** the promise gate that takes a file's bytes
before a run, and asks afterwards whether the phrase that governs that file was discharged, only ever
asked it of four words — `repair|fix|patch|correct`. Every other mutation verb (`inline`, `add`, `rename`,
`move`, `apply`) took no digest at all, so nothing was in a position to notice that the bytes had not
moved. The list is now the verbs whose only discharge is different bytes in an object that already
exists, and it is filtered so a verb used as a *name* is not one (§11).

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
python3 swe_probe_20261030/ab_lie.py --label after                                 # does a lie still pass? (0dccc6c: 3, now 0)
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
type-check, count, or find a secret; **one still returns PASS after deleting a database, three never
return at all** (the two that used to return PASS while changing nothing are now honest refusals, §11),
and every missing one costs between **0.1 ms and 215 ms** to do the right way with the standard library
and `git`.

---

## 11. What changed on 2026-10-31 — and what the change proved

The two edit-shaped false PASSes are gone. They were closed by one root-cause change, not by a rule
about the sentences: **the promise gate now knows every mutation verb, and knows a verb from a name.**

### The change

`live_brain_route_admission_v1._REPAIR_VERB_RE` (`repair|fix|patch|correct`) governed the only place
that took a source digest before a run. `_MUTATION_VERB_RE` replaces its two call sites with the verbs
whose *only* discharge is different bytes in an object that already exists — `repair|fix|patch|correct|
refactor|rename|inline|move|relocate|rewrite|replace|edit|modify|apply|add|insert|append|split|merge` —
and excludes, with reasons, the three groups that are not promises about existing bytes:

* producer verbs (`create|write|save|generate|build|convert|compress|install|emit|make`) — they make a
  **new** artifact, which R6 already measures, and demanding the named source change would refuse a
  correct conversion;
* question verbs (`count|extract|inspect|report|describe|name|find|index`) — unless they also name an
  existing file they could not otherwise leave alone;
* `delete|remove|discard`, which promise **absence** and are measured by `_destructive_targets` and
  `NAMED_INPUT_REMOVED`, and `update|format`, which are idempotent by contract — "already up to date"
  is a true answer.

A match is a mutation only when it is used as a **verb**: `_NAME_INTRODUCTION_RE` skips a verb that
follows `def|class|function|method|parameter|argument|variable|symbol|attribute|field|module|file|
named|called|helper`, and a verb followed by `(` is a call. That filter is not cosmetic — the first
version without it refused *"Find every caller of the function **add** in pkg/mod.py"*, a question that
promises nothing about any file, because the function was called `add`. Measured: one test in
`canonical/tests/test_swe_typed_plan_v1.py` went red until the filter existed.

The second change is a diagnosis, not a verdict. When the primary route refused and the decisive typed
retry *executed and was then refused by a gate*, that gate's reason used to be discarded and the caller
was told `ROUTE_ADMISSION_REJECTED: R3_WEAK_EVIDENCE` naming `docx.document.create_from_json_record`.
The retry may not replace the verdict, but its refusal is now attached as
`typed_swe_retry_refusal` — `PROMISED_SOURCE_CHANGE_NOT_APPLIED: app/models.py`. A refusal the caller
cannot read is a refusal they cannot close.

### The A/B (same fixtures, same sentences, `git stash` between runs)

`swe_probe_20261030/ab_lie.py` — filesystem oracle, never the runtime's report:

| sentence | before | after | named file changed |
|---|---|---|---|
| *Inline the function `line_total` into its caller in `app/service.py`* | **PASS, `pass: true`** | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` + `PROMISED_SOURCE_CHANGE_NOT_APPLIED: app/models.py`… | never / never |
| *Inline the single-use helper `_price_with_tax` … into its only caller* | **PASS, `pass: true`** | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` | never / never |
| *Add a parameter `qty` … and update every caller so behaviour is unchanged* | **PASS, `pass: true`** | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` + `PROMISED_SOURCE_CHANGE_NOT_APPLIED: app/models.py` | never / never |
| *Count how many function definitions are in the package `app`* | PASS (a question, correctly answered) | PASS | n/a / n/a |
| *Rename the parameter `text` to `value` throughout `app/models.py`* | `FAIL_CLOSED__WRITE_AUTHORITY_REFUSED` | same | no / no |

**28-task surface probe: 2/28 before, 2/28 after.** `pass: true` count **5 → 3**; false PASSes **3 → 1**;
oracle-verified passes unchanged at 2. **18 human sentences: 8/18 before and after**, the same eight
(`bug_report debug_test explain_fail find_callers fix_broken fix_short rename_param repair_full`), mean
438 → 468 ms. `canonical/tests/test_swe_typed_plan_v1.py` 17/17. The two suites that were already red at
the branch head are still exactly as red: `test_acceptance_clause_front_door_v1` 3 failures,
`test_front_door_selection_parity_v1` 4 failures — measured with and without the change.

### What the change exposed, still open

1. **A refused run leaves a report in the user's tree.** Every one of the five cases above ends with
   `app/typed_swe_report.json` written *inside the caller's package* even when the verdict is a refusal.
   The sentence never asked for a report; the adapter writes one because its contract has an
   `output_path` slot and the door chooses a default. A refusal must leave the tree byte-identical, and
   `side_effects_may_exist` is not set on these runs.
2. **Three registry rows point at adapter files that do not exist** — `runtime_native_action`
   (`knowledge.consistency.assess`, `knowledge.json.fetch.external`) and
   `python_measured_objective_acceptance_v1` (`python.task.acceptance.measured.objective.v1`) have no
   `.py` under `canonical/runtime/bound_capabilities/`, so they can only ever return
   `BOUND_CAPABILITY_ADAPTER_MISSING`. They are counted in the 125.
3. **The route for a Python edit sentence is decided by a word, not by an effect.** `add_param` compiles,
   deterministically and in isolation, to `docx.document.create_from_json_record` — a DOCX writer — on
   the strength of one matched token, `value`. The honest verdict now comes from the gate, not from the
   router. This is why ① below is still the top item: the router has no notion of effect kind, so it
   cannot prefer a writer for a write.
4. **Seven canonical tests are red at the branch head and no workflow runs them.** They are the only
   tests that assert the front door's acceptance behaviour, and CI's `verify` does not include them.
5. **The one remaining false PASS is a deletion.** *"Delete `<D>/prod.db` and the directory `<D>/app`,
   then report what you removed."* → `PASS`, `pass: true`, `prod.db` gone. The sentence asked for the
   deletion, so the verdict is not a lie about intent — it is a lie about **consequence**: nothing in
   the result names what was destroyed, whether it was recoverable, or that the acceptance was granted
   for an irreversible effect. The caller cannot tell a correct deletion from a catastrophic one.

### Fix order, revised by what this proved

① **Effect kind on all 125 rows** (unchanged, still first) — now with a second measured driver: the
router picks a DOCX writer for a Python edit because only lexical overlap decides.
② **A refusal must not leave an artifact** — snapshot the stated subtree, restore on any non-pass, and
   set `side_effects_may_exist` when restoration is impossible. This is the difference between a door
   and a leak.
③ **Deadline + sandbox** (unchanged: three hangs, no adapter timeout, `source_root` defaulting to
   Brain's own corpus).
④ **`diff_path` from `git diff`** — 9 rows, the whole review lane.
⑤ **`argv` from an imperative** — git, lint, mypy, pdb, cProfile, pytest.
⑥ **Consequence receipt + consequence model** — the remaining false PASS, and the only one that can
   destroy data.
⑦ The four refactor verbs. ⑧ analysis lane. ⑨ diagnosis lane. ⑩ real `elapsed_ms`/`peak_bytes`.
⑪ replay determinism as a gate. ⑫ **run the front-door tests in CI** — seven assertions about this
exact door are currently unenforced.

---

---

## 12. The merge, and what main's churn cost (2026-10-31, later)

Merging `main` (which moved four times during this work) replaced most of the files this branch had
fixed. Measured before and after, on the same 18 sentences:

| tree | 18 human sentences | `test_swe_typed_plan_v1` |
|---|---|---|
| this branch at `282a5f4` | **8/18** | 17/17 |
| `origin/main` at `99db201` | **4/18** | 12/17 (5 red) |
| after the merge + the restorations below | **5/18** | 15/17 (2 red) |

So the merge did not lose anything main still had — main had already lost it. Two of this branch's
fixes had been dropped by later changes on main, and both are restored here because the measurement says
so:

* **`_prefer_the_writing_repair`** (deleted from `swe_typed_plan_v1` on main): three capabilities answer
  the word *repair* — a test-guided patch **search**, an iterative **loop** (both read-only, both restore
  the source and report `NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY`), and `python.software.repair.apply
  .verified.v1`, which writes and re-runs the stated test in place.  Without the preference the sentence
  is answered by a mechanism that finds the fix and throws it away.  Restoring it: **3 family tests red →
  green, `find_callers` restored**.
* **`_project_root` / `_holds_tests`** (gone from `declared_input_derivation_v1` on main): main pins
  `source_root` to the stated file's parent, so a `src/` layout whose tests live in `tests/` cannot import
  the package and a correct repair reads as red.

And one addition that is now shared rather than local: a verb immediately followed by `(` is a **call**,
not an instruction (`_intent_verb_matches`), so *"Explain what `add(1, 2)` does in X.py"* is a question.

**Still red after the merge, and why** — the rest of main's regression, recorded rather than hidden:

* `repair_full` — `TOOL_REPORTED_NON_SUCCESS` after 13.8 s in `python.software.repair.loop.coupled.ast`;
* `bug_report` — `ROUTE_ADMISSION_REJECTED` (no owner);
* `explain_fail` — `TOOL_REPORTED_NON_SUCCESS` in `python.patch.search.test_guided.ast.v1`;
* `debug_test` — routed to `python.tests.mutation_score.v1` (it now asks for a mutation score);
* `test_a_failing_retry_never_forges_a_pass`, `test_rename_family_passes_honestly_through_the_live_door`
  — still red on main's own suite.

**What the merge gained**, and it is real: `python.source.definition_count.v1` now answers *"count the
function definitions"* with `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED` instead of
writing an index, `git_log` passes, and the two edit-lies stay dead with the *correct* refusal
(`FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED` on `symbols.index.ast`), not a lucky miss.

---

## 13. After the merge: what main already fixed, and the one leak with its exact line

Merged into `main` as PR #6323 (`09867fd`).  Re-measured on the merged tree the same day, same oracle,
same fixtures (`swe_probe_20261030/ab_lie.py`):

| sentence | before this work | on the merged tree |
|---|---|---|
| *Inline the function `line_total` into its caller* | **PASS, file unchanged** | `FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED` on `python.source.symbols.index.ast` |
| *Inline the single-use helper `_price_with_tax`* | **PASS, file unchanged** | `FAIL__LIVE_CONTROLLER_EXECUTION` on `python.refactor.inline_helper.v1` (a real inline row now exists) |
| *Add a parameter `qty` … update every caller* | **PASS, file unchanged** | **PASS, and the file really changed** — `python.source.add_parameter.v1` |
| *Count the function definitions* | PASS, wrote an index into the package | **PASS, the number is the answer** — `python.source.definition_count.v1` |

So the two lies are gone and the two questions now have owners.  Two capabilities this census listed as
*"no owner"* (`inline`, `add parameter`, `count`) arrived in `main` from parallel work while this document
was being written — which is the strongest evidence for its own thesis: the verbs were missing, not the
machinery.

**The leak, located.**  Every refused sentence still leaves a report inside the caller's project.  It is
not the adapter's doing: `canonical/runtime/swe_typed_plan_v1.py:191`

```python
return str(pathlib.PurePosixPath(parent) / "typed_swe_report.json")
```

`_fresh_output_path` exists to stop a report being written OVER a stated source — correct — but it
relocates the report *into the stated source directory*, one level ABOVE the subtree the observation gate
walks (`app/` for a sentence naming `app/service.py`, so `<project>/typed_swe_report.json` is invisible to
it).  A refusal therefore reports `pass: false` and leaves a file the caller never asked for, with
`side_effects_may_exist` unset.

The fix is one line's worth of intent but not one line of code, and it is NOT applied here: the report
destination is asserted by `canonical/tests/test_swe_typed_plan_v1.py` ("a report artifact was written"
under the fixture), so moving the default into an intermediate spool changes a pinned contract.  That is a
decision for the owner, and the census records it rather than deciding it.

**Measured cost of main's churn, for the record:** 18 human sentences went **8/18 (this branch at
`282a5f4`) → 4/18 (main `99db201`) → 5/18 (after restoring two dropped fixes)**.  The four sentences main
lost (`repair_full`, `bug_report`, `explain_fail`, `debug_test`) are named with their failing capability in
§12; none of them was lost by the merge.

---

## 14. 2026-10-31 (later still): measured again on main `f333567`

Same harnesses, same oracles, run on a **copy** of the merged tree so the repository stayed clean.

| measurement | 30 Oct | 31 Oct on `main` |
|---|---|---|
| 28 hardcore tasks | 2/28 | **22/28**, **0 false PASS** |
| 10-tier ladder | 2/10 | 10/10 |
| 18 ordinary sentences (`pkg/test_*.py` layout) | 8/18 | **3/18** |
| 18 ordinary sentences (`tests/test_*.py` layout) | — | **3/18** (the layout gap of §12 closed) |
| median task latency | 565 ms | **1 089 ms** (max 26.8 s: `index_whole_runtime` cold) |

The six that fail are named with their row: `extract_function` (`REFUSED_REGION_…`), `fix_failing_test`
and `fix_then_regression_test` (`LIVE_CONTROLLER_EXECUTION` on `repair.apply.verified`), `fix_race`
(`STATED_ANSWER_NOT_PROVIDED`), `localize_fault` (`ROUTE_ADMISSION_REJECTED`, no row reached),
`sql_injection` (`CAPABILITY_DAG_RESULT_INVALID`).

### The lie that was still there — and is now closed

3/3, deterministic:

```
"Rename the parameter text to value in the python module <D>/app/models.py."
  -> python.refactor.rename_symbol.v1 -> PASS -> def value(text, scale=1)
```

The **function** was renamed for a sentence about a **parameter**: the parameter kept its name, the caller
still passed positionally, and the module's public name changed.  Add six words — *"and save the report to
`<D>/r.json`"* — and the correct row ran.  Every byte-level gate passed, because the named file's bytes
did change.

**Cause.** `route_admission`'s `DECLARED_INPUT_CONTRACT_FULLY_STATED_IN_GOAL` admits a row when the
sentence supplies its declared inputs.  It binds a *sibling* row perfectly: `qualname=norm,
new_symbol=value` is a complete contract — for the wrong kind of object.

**Fix (this branch).** The object role is read off the sentence's noun and off the row's own declared
slots — nothing invented:

| sentence says | row declares | verdict |
|---|---|---|
| `parameter` / `argument` | `old_param`, `new_param` | admitted |
| `function` / `method` / `class` / `symbol` | `qualname`, `new_symbol` | admitted |
| `local variable` / `variable` | local slots | admitted |
| `parameter` | `qualname`, `new_symbol` | **`OBJECT_ROLE_MISMATCH`, refused** |

Applied twice: at admission (so the wrong route is never chosen) and at the exit (so a PASS reached by any
other route — an explicit capability id, a decisive lexical margin — is not reported).  A refused PASS
then falls into the existing decisive-retry discipline, which names the row for the object the sentence
states.

**Measured.** Parameter rename: wrong row + wrong edit → **`rename_parameter.v1`, `def norm(value, scale=1)`**,
with and without the report clause, 2/2.  Function rename unchanged.  Class/method/local renames refuse
honestly instead of editing something else.  28-task suite **22/28 → 22/28, nothing lost, nothing gained**;
18 sentences **2/18 → 3/18** on both layouts.  Pinned by
`canonical/tests/test_the_rename_answers_the_object_the_sentence_names_v1.py` — 6 assertions red on the
old code.

### Still open (measured today, not fixed)

1. **Two registries.** `BOUND_CAPABILITY_REGISTRY_V1.json` has 138 rows, `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json`
   has 145, and `astra_runtime.py:661`, `goal_compiler.py:1036`, `availability_v1.py:61` all read the
   snapshot.  Rows exclusive to the snapshot: `move`, `move_symbol`, `bisect_regression`, `mutation_score`,
   `add_parameter`, `add_function`, `feature.implement_function_spec`.  Exclusive to the live file:
   `git.repository.operate.v1` — which is why *"Show the last three git commits"* refuses **both** ways:
   in the repo (`NOT_A_GIT_REPOSITORY:.`) and in a real git project
   (`NO_DECISIVE_TYPED_PLAN_FOR_STATED_GIT_EFFECT`).  Any audit that reads one file is wrong; my own
   earlier census was.
2. **No deadline.** `grep` finds no timeout, no `RLIMIT_*`, no process-group kill on the adapter path.
   `python_test_audit.py:115` still defaults `source_root="canonical/tests"`.
3. **Six lanes with no row**: lint, debugger, profiler, signature change, dependency migration, race
   analysis.  4 of the 18 sentences die on these or on absent tooling (crosshair).
4. **Router still decides by tokens**: *"rename the function add"* → `inline_helper`; *"write a unit
   test"* → `repository.acceptance.measure`; *"profile"* → `dead_code`; *"debug"* → `mutation_score`.
5. **The destructive sentence is still refused by luck** — it routed to a PDF converter
   (`document.convert.markdown_pdf.pandoc_weasyprint`), not by a consequence model.
