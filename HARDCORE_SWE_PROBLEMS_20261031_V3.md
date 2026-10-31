# Every problem between this machine and a hardcore software engineer

**Tree:** `main` @ `59a593c` (clean at measurement start).
**Method:** 62 sentences, all run through the real door
(`live_brain_route_admission_v1.solve`), each in its own process, plus direct inspection of the
artifacts they returned. Every number below was produced by running this tree today. Nothing is
inherited from the 2026-10-29 or 2026-10-31 reports without re-measurement.

**Scope ruling honoured:** PDF/DOCX/XLSX and other document-format work is ignored except where
it is the destination a *software* request is wrongly routed to. One sentence in 62 hit a
document capability (`Extract the helper …` → `pdf.extract.ocr.tesseract`); the rest of the
document surface is not counted against the machine here.

---

## The headline

```
62 hardcore software-engineering sentences
   5 produce a correct answer                     8%
  12 return PASS — of which 7 are WRONG ANSWERS  58% of passes are wrong
   4 hang 180 s and return nothing, or raise
  14 ask the machine to CHANGE code
   0 of 14 change code correctly
```

A software engineer that answers 5 of 62 requests correctly, and none of the 14 that involve
changing a program, is not an advanced software engineer. It is a repository question-answerer
with a very convincing certificate format.

The full result table is in §1. The seven defects behind it are §2–§8. The fix order is §9.

---

## §1. The measurement

62 sentences across eight kinds of work a hardcore engineer does daily. Every row is verbatim;
reproduce any one with

```bash
python3 /tmp/c3/one.py "<the sentence>"
```

Legend: **✔** correct · **✘** wrong answer returned as PASS · **·** honest refusal · **!** hang
or exception.

### A — navigate and understand (10 sentences, 3 correct)

| # | sentence | verdict | capability | time |
|---|---|---|---|---|
| 0 | `Find every caller of build_plan in …/swe_typed_plan_v1.py` | ✘ PASS | `python.source.symbols.index.ast` | 37.5 s |
| 1 | `Who calls _resolve_family` | · FAIL | `symbols.index.ast` `STATED_SWE_EFFECT_UNSERVED` | 1.1 s |
| 2 | `Show the definition of _family_terms in …/swe_typed_plan_v1.py` | ✘ PASS | `python.source.definition_count.v1` | 1.5 s |
| 3 | `List the functions in …/swe_typed_plan_v1.py` | ✘ PASS | `python.source.audit.ast` | 1.5 s |
| 4 | `Show the imports of …/swe_typed_plan_v1.py` | ✘ PASS | `python.source.audit.ast` | 1.5 s |
| 5 | `What is the complexity of build_plan` | · FAIL | `python.source.complexity.v1` `R3_WEAK_EVIDENCE` | 1.2 s |
| 6 | `Are there any import cycles in canonical/runtime` | · FAIL | `crossfile.choreograph` `R12_…` | 1.4 s |
| 7 | `Find duplicated code in canonical/runtime` | ✘ PASS | `code.index.tree_sitter.incremental.v1` | 94.6 s |
| 8 | `Show me the class hierarchy of goal_compiler.py` | · FAIL | `grounding.verify.stdlib` not admitted | 1.1 s |
| 9 | `Which modules import …/swe_typed_plan_v1.py` | · FAIL | `move_symbol.v1` no candidate | 1.3 s |

**Every "show me X" that PASSed returned a COUNT of X.** Verbatim artifacts:

```
"Show the definition of _family_terms in …/swe_typed_plan_v1.py"
  -> {"answer": 10, "definition_count": 10, "function_count": 10, "class_count": 0,
      "files_scanned": 1}                                    ← the answer is the number 10

"List the functions in …/swe_typed_plan_v1.py"
  -> {"function_count": 10}                                  ← the list is a count

"Show the imports of …/swe_typed_plan_v1.py"
  -> {"distinct_imported_module_count": 5}                   ← the list is a count

"Find every caller of build_plan in …/swe_typed_plan_v1.py"
  -> {"file_count": 2285, "symbol_count": 92726, "reference_count": 619599,
      "call_edge_count": 236739, "caller_index_size": 8}     ← repo-wide index, not the callers

"Find duplicated code in canonical/runtime"
  -> {"definition_count": 16177, "reference_count": 957493,
      "parsed_file_count": 1, "reused_file_count": 2287}     ← an index; zero duplication analysis
```

Four of these five answers carry `EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`.

### B — change code (14 sentences, 0 correct)

| # | sentence | result | time |
|---|---|---|---|
| 10 | `Rename the function build_plan to construct_plan in …` | `CAPABILITY_EXITED_PROCESS` | 55.6 s |
| 11 | `Extract the helper from … into a new function` | routed to **`pdf.extract.ocr.tesseract`** | 2.1 s |
| 12 | `Inline the helper _request_goal in …` | `HELPER_AMBIGUOUS` | 62.5 s |
| 13 | `Add a parameter to the function build_plan in …` | `SyntaxError: invalid syntax, line 47` | 1.6 s |
| 14 | `Move the function _family_terms to a new module` | `module:value_not_parseable` | 2.2 s |
| 15 | `Remove the unused import from …/git_repository_operate.py` | `source_root:0_existing_directories` | 2.0 s |
| 16 | `Fix the ZeroDivisionError in app/utils.py` | `R3_WEAK_EVIDENCE` | 1.8 s |
| 17 | `Repair … so the unit test … passes` | **hang** | 180 s+ |
| 54 | `Write a test for build_plan` | `python.software.repair.apply…:source_root` | 1.5 s |
| 55 | `Generate tests for …/swe_typed_plan_v1.py` | **hang** | 180 s+ |
| 56 | `Fix the failing tests and report which ones you fixed` | `PATH_OUTSIDE_REPOSITORY` | 1.8 s |
| 57 | `Implement a function that parses git log output` | `STATED_SWE_EFFECT_UNSERVED` | 1.6 s |
| 58 | `Refactor …/goal_compiler.py into smaller modules` | `HELPER_AMBIGUOUS` | 52.0 s |
| 59 | `Make the test suite pass` | **hang** | 180 s+ |

**Zero of fourteen produced a correct change. The three highest-value sentences — repair to
green, generate tests, make the suite pass — are the three that never returned.**

### C — verify (10 sentences, 0 correct)

| # | sentence | result |
|---|---|---|
| 18 | `Run the tests in canonical/tests/test_swe_typed_plan_v1.py` | `mutation_score.v1` then `TimeoutExpired` after **124 s** |
| 19 | `Tell me which tests fail` | `bridge_enumeration.v1` not admitted |
| 20 | `Lint …/swe_typed_plan_v1.py` | `diff_static_triage.v1:diff_path` |
| 21 | `Type-check …/swe_typed_plan_v1.py` | `diff_type_gate.v1:diff_path` |
| 22 | `Measure the test coverage of …/swe_typed_plan_v1.py` | `WRITE_AUTHORITY_REFUSED` |
| 23 | `Run a mutation test on …` | `REFUSING_BROAD_REPO_MUTATION_SCAN` |
| 24 | `Scan canonical/runtime for SQL injection` | `REFUSING_BROAD_REPO_MUTATION` |
| 25 | `Check for security vulnerabilities in …` | `diff_security_gate.v1:diff_path` |
| 26 | `Measure the performance of build_plan` | `R3_WEAK_EVIDENCE` |
| 27 | `Which tests does … break` | `REFUSING_BROAD_REPO_MUTATION_SCAN` |

### D — history (10 sentences, **5 correct** — the only healthy area)

| # | sentence | result | time |
|---|---|---|---|
| 28 | `Show the last three git commits` | ✔ `op=log limit=3` | 1.3 s |
| 29 | `Who wrote line 3 of …/swe_typed_plan_v1.py` | · `STATED_SWE_EFFECT_UNSERVED` | 1.2 s |
| 30 | `Show me the diff` | ! **raises** `GoalCompilationFailure: GOAL_INPUT_BINDING_REQUIRED:limit` | 1.5 s |
| 31 | `Show the diff of the last commit` | · `git.repository.operate.v1:limit:not_stated` | 1.8 s |
| 32 | `List the branches` | ✔ `op=branch` | 2.1 s |
| 33 | `Which commit broke the tests` | ✔ `git.history.bisect_regression.v1` | 15.4 s |
| 34 | `Revert the last commit` | ✘ **PASS with `op=log`** | 1.4 s |
| 35 | `Show the status of the working tree` | ✔ `op=status` | 1.6 s |
| 36 | `What changed in the last 5 commits` | ✔ `op=log limit=5` | 1.3 s |
| 37 | `Show me the staged changes` | · `limit:not_stated` | 1.2 s |

`Revert the last commit` is the most dangerous row in the document. The artifact:

```
op: "log"   row_count: 1   → the list of commits
verdict: PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED
```

The machine did not revert anything. It printed the log and certified it. A caller reading
`pass: true` believes the commit is gone.

### E — debug and profile (8 sentences, 0 correct)

| # | sentence | result |
|---|---|---|
| 38 | `Profile the function build_plan in …` | `python.source.dead_code.v1` → `SOURCE_ROOT_MISSING` |
| 39 | `Debug the failing test test_breaking_the_derivation_breaks_the_selection` | `test.slice.never_miss.v1` → `STATED_SWE_EFFECT_UNSERVED` |
| 40 | `Find the fault in … that makes the test fail` | `MEASURED_TREE_BYTE_LIMIT` after 16.9 s |
| 41 | `Trace the value of limit through build_plan` | `decision.synthesis.typed.stdlib` not admitted |
| 42 | `Set a breakpoint in build_plan` | `crossfile.choreograph` not admitted |
| 43 | `Show me the stack trace of the last failure` | `input_path:0_type_compatible_existing_files` |
| 44 | `Which line raises the ZeroDivisionError` | routed to `chart.read.legend_linear_intersection.v1` |
| 45 | `Find the slow function in …/goal_compiler.py` | `dead_code.v1` → `SOURCE_ROOT_MISSING` |

Meanwhile the repository **contains** `python_dynamic_fault_localizer_v1.py` (`sys.settrace` at
:67, :96) and `python_interprocedural_value_provenance_v1.py` (`settrace` at :76, Ochiai
ranking). Neither is reachable from any of the eight sentences that ask for exactly what they do.

### F/G/H — build, review, compose (10 sentences, 1 accidental PASS)

| # | sentence | result |
|---|---|---|
| 46 | `Build the project` | `RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP` |
| 47 | `Run the script …/goal_compilation_benchmark_v1.py` | routed to `external_benchmark_dominance_compiler_v1` |
| 48 | `Install the dependencies` | `testselect.v1:changed_paths` |
| 49 | `Package the project` | `archive.tar_gz.create_from_manifest` not admitted |
| 50 | `Run a static analysis pass on canonical/runtime` | `MEASURED_TREE_BYTE_LIMIT` |
| 51 | `Review the diff` | `diff_coverage_gate.v1:anchor_path` |
| 52 | `Review …/git_repository_operate.py for bugs` | `git.history.bisect_regression.v1` `STATED_SWE_EFFECT_UNSERVED` |
| 53 | `Check the type safety of the diff` | `diff_type_gate.v1:diff_path` |
| 60 | `Find every place that reads the registry` | `grounding.verify.stdlib` not admitted |
| 61 | `Design a cache for the capability registry` | ✘ **PASS** |

`Design a cache for the capability registry` was answered by
`plain_goal.bound_capability.grounding.verify.stdlib`, and the artifact it produced opens with:

```json
{"schema": "PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1",
 "clauses": [{"text": "Design a cache for the capability registry",
              "status": "UNBOUND_INPUTS_NOT_GROUNDED"}]}
```

**The artifact says the request was not grounded. The verdict says
`PASS__RAW_GOAL_COMPILED_CONTROLLER_EXECUTED_VERIFIED_AND_CHECKPOINTED`.** A pass over a
document whose own field reports failure.

---

## §2. P0 — "show me X" is answered with a count of X, and certified

Five wrong passes in §1 share one skeleton: an **inspector that counts** was chosen for a
request that asked to **extract**.

This is not five accidents. Measured over the bound registry's 77 software-engineering rows:

```
rows whose ONLY result fields are counts / sizes / verification flags : 23 of 77  (30%)
```

Twenty-three capabilities can report *how many* things are in a file and cannot report *which*
things. `python.source.audit.ast`, `python.source.definition_count.v1`,
`code.index.tree_sitter.incremental.v1` and twenty others are counters. When a sentence says
"list", "show", "find every", the selector matches on the noun (`function`, `import`,
`caller`) and picks the counter, because the counter's keywords contain the same noun.

**Root cause:** selection is lexical over `keywords + provides`, and no capability declares what
*shape* of answer it produces (list / count / location / diff / patch). A `result_fields` list
exists on every row, but nothing in selection reads it.

**The fix is in the repository already:** `result_fields` is declared per row. One predicate —
"does this row's `result_fields` contain an enumerating field when the sentence's verb is
enumerating" — removes this whole class. It is the same discipline the write-authority gate
applies to paths, applied to answer shape.

---

## §3. P0 — a revert is answered by a log, and the door says PASS

`Revert the last commit` → `op=log`, `PASS…EXECUTED_AND_VERIFIED` (§1 row 34).

The seven declared git operations are `log status diff show blame branch commit`. **`revert` is
not among them**, so nothing could have done what the sentence asked. But the derivation layer
matched the word `commit` (the noun in "the last commit") and produced `op=log`, and the
acceptance layer checked only that *a* git operation ran and its artifact verified.

Three separate holes, in the order they matter:

1. **`op=log` was derived from a sentence whose verb is `revert`.** The grammar in
   `declared_input_derivation_v1._GIT_OPERATION_GRAMMAR` reads nouns. A destructive
   imperative must be matched on its *verb*, and an unmatched verb must derive **no**
   operation.
2. **A destructive verb was satisfied by a read.** There is no check that the operation
   performed belongs to the same *verb class* as the sentence: read, write, or rewrite history.
3. **The acceptance layer cannot tell "ran" from "did what was asked".** `output_verified` is
   true, so the pass is exact — the artifact is a correctly written log of the wrong thing.

This is the most damaging signature in the project because it is the one that can lose a user's
work: a caller who believes `pass: true` after a revert will not look again.

---

## §4. P0 — the machine cannot change code at all (0 / 14)

Every one of the fourteen mutating sentences failed, hung, or produced a `SyntaxError`. Grouped
by cause:

| cause | sentences | evidence |
|---|---|---|
| the adapter chose an unrelated target and changed it, then died | 13 | `SyntaxError: invalid syntax (<unknown>, line 47)` from `python.source.add_parameter.v1` |
| ambiguity treated as failure rather than as a question | 12, 58 | `HELPER_AMBIGUOUS:_allowed_story_part, _alphabet_sentences, …` — the *file's other functions* became the ambiguity |
| a required input was never derivable | 14, 15, 54 | `move_function.v1:module:value_not_parseable`, `source_root:0_existing_directories` |
| routed to a document capability | 11 | `Extract the helper …` → `pdf.extract.ocr.tesseract` |
| no deadline | 17, 55, 59 | 180 s+, see §5 |

**And one write landed where nothing had asked it to.** Two independent runs of the corpus, each
on a clean checkout, left this diff behind:

```
canonical/runtime/aa_briefcase_component_summary_noninversion_v1.py
-SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_COMPONENT_SUMMARY_NONINVERSION_V1"
+SCHEMA = 'add'                                                  (run 1)
+SCHEMA = 'Summarize the file %s into three sentences.'          (run 2)
```

Both payloads are fragments of *other* sentences' goals or derived names. It did not reproduce
from the write-only subset, from any single sentence I isolated, or from running the test file
that contains that string. **A write path exists that is not attributable to a request, not
isolated per solve, and not rolled back** — and it is silent: the run reports success while the
tree is corrupted. That is the exact failure mode the repository's own
`test_a_rename_never_leaves_a_dangling_reference_v1` was written to prevent, one layer lower.

### The repository is also mutated by *reading*

`Find every caller of build_plan …` is a read. It wrote:

```
canonical/runtime/typed_swe_report.json        ← a new file in the SOURCE tree
```

and every solve writes `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` plus a
`*__CONTROLLER_CHECKPOINT.json`. A run of 62 read-mostly sentences leaves the working tree
dirty in four places. There is no `solve(dry_run=…)`, no scratch root, and no separation between
"the tree being analysed" and "the tree the machine lives in".

---

## §5. P0 — the door has no wall-clock budget, and the highest-value verbs hit it

Three of the three "make it work" sentences hung past 180 s. Captured stack (`faulthandler`,
45 s in):

```
File ".../bound_capabilities/python_test_audit.py", line 136, in run
    proc = subprocess.run(..., timeout=timeout_s)
File ".../live_brain_route_admission_v1.py", line 906, in run_adapter_locally
```

`python_test_audit.py` takes `source_root` and **glob-matches `test_*.py`**, then runs each file
as a subprocess with `timeout_s` defaulting to **180 s**, **sequentially**, with **no overall
deadline**:

```python
files = sorted(p for p in source_root.glob(pattern) if p.is_file())   # 2,162 files here
for path in files:
    proc = subprocess.run(..., timeout=timeout_s)                     # 180 s each
```

Worst case 2162 × 180 s ≈ 108 hours inside one `solve()` call. Even at 0.5 s per file it is 18
minutes. There is no budget on `solve()`, no propagation of a deadline into the adapter, and no
way for the caller to say "you have 10 seconds".

The same class appears without hanging: `Run the tests in …` chose
`python.tests.mutation_score.v1`, which spent **124 s** before raising `TimeoutExpired`.

**Consequence for the mission:** the three verbs that constitute actual software engineering —
repair, generate tests, make the suite pass — are the three the machine cannot finish. Not
because they are hard, but because nothing bounds them.

---

## §6. P0 — verification gates only accept a *diff*, so ten file-level questions die outside them

Five sentences (`Lint`, `Type-check`, `Check type safety`, `Check for security
vulnerabilities`, `Review the diff`) died on one line of one rule:

```
python.review.diff_type_gate.v1      : diff_path:0_type_compatible_existing_files_named
python.review.diff_static_triage.v1  : diff_path:0_type_compatible_existing_files_named
python.review.diff_security_gate.v1  : diff_path:0_type_compatible_existing_files_named
python.review.diff_coverage_gate.v1  : anchor_path:0_type_compatible_existing_files_named
```

Every verification capability in the tree is **diff-scoped**. The underlying tools are not:
a lint pass, a type pass, a security pass and a coverage run are all meaningful on a *file* or a
*directory*. Because the declared input is `diff_path`, the derivation refuses and the sentence
has nowhere to go. Meanwhile the repository can do all four (`python_review_diff_static_triage.py`,
`python_review_diff_type_gate.py`, `python_review_diff_coverage_gate.py` — the latter literally
runs `coverage run -m pytest`).

Two further blocks in this family:

```
Measure the test coverage of …            → WRITE_AUTHORITY_REFUSED:
                                            OUTPUT_OVERWRITES_A_STATED_SOURCE
Run a mutation test on …                  → REFUSING_BROAD_REPO_MUTATION_SCAN
Which tests does … break                  → REFUSING_BROAD_REPO_MUTATION_SCAN
Find the fault in … that makes the test fail → MEASURED_TREE_BYTE_LIMIT
```

Each is a guard doing the right thing and making the capability unusable: the output path was
not derived so the default landed on the source file (the gate correctly refused); the mutation
scan refuses anything broader than one file; the measurement refuses trees over a byte limit,
and `canonical/runtime` is 2,285 files.

---

## §7. P1 — cold start dominates, and the cache that hides it is not addressable

The same sentence, run repeatedly on the same tree:

| sentence | run 1 | run 2 | run 3 |
|---|---|---|---|
| `Find every caller of build_plan …` | 37.1 s | 3.2 s | 3.0 s |
| `Find duplicated code in canonical/runtime` | 94.6 s | 29.5 s | 6.7 s |

A 15–30× difference between the first and the third run of an identical request. The first call
builds a repo-wide index (2,285 files, 92,726 symbols, 619,599 references); later calls reuse it
(`reused_file_count: 2287`). Nothing exposes that cache: no warm-up, no persistence the caller
can rely on, no statement in any result of how much of the time was index-building.

For the stated goal — *fastest* — this matters more than any other latency fact: the machine's
steady-state answer is acceptable (0.3–3 s) and its cold answer is not (37–95 s), and the
difference is invisible in every artifact.

Baseline fixed costs, measured:

```
import of the door module        : 542 ms
first solve after import         : 426 ms
subsequent solve, trivial goal   : 248 ms
```

---

## §8. P1 — "fastest" and "smartest" are still not expressible

Re-measured on this tree:

```
rows declaring latency_ms / p50_ms / peak_bytes : 0 of 437 admitted
declared `cost` values                          : {1: 419, 2: 18}
```

`cost` cannot separate a 0.4 s symbol count from a 95 s tree-sitter index. There is no measured
latency, no measured memory, and no per-capability success rate. Selection therefore cannot
prefer a cheap capability over an expensive one, and §1's evidence shows the cost of that:
**three sentences burned 460 s** (124 + 180 + 156) on capabilities that could not answer them.

---

## §9. What genuinely works, so the list is a gap list and not a dismissal

- **Git, after the repair landed earlier today.** Five of ten history sentences are correct,
  and they are the only five in the corpus. `log`, `status`, `branch`, `bisect` all answer
  properly, and `git.repository.operate.v1` re-derives every effect with a second plumbing
  command.
- **Determinism.** Five sentences run twice: identical status and identical capability both
  times, including the two failures and the exception. The machine is not random; it is
  consistently wrong in the same places.
- **The refusal vocabulary.** 46 of 62 refusals name exactly what was missing
  (`diff_path`, `source_root`, `limit`, `module`, `R3_WEAK_EVIDENCE`,
  `REFUSING_BROAD_REPO_MUTATION_SCAN`). A wrong answer is rare; a *silent* refusal is rarer.
- **Honesty about unsupported requests, sometimes.** `Who calls _resolve_family` and
  `Debug the failing test …` now fail closed with `STATED_SWE_EFFECT_UNSERVED` instead of
  answering with an unrelated capability — that gate is doing real work.
- **Dynamic-analysis substrate exists** (`settrace`, Ochiai provenance, coverage gate). It is
  unreachable, not absent (§E).

---

## §10. The fix order (damage per unit of work)

Each item names the mechanism that already exists in the repository, so none of this is new
substrate.

1. **Never certify a wrong answer** (§2, §3). Two predicates, both reading data that is already
   declared on every row:
   - *answer shape*: if the sentence's verb is enumerating (`list`, `show`, `find every`,
     `which`) the chosen row's `result_fields` must contain an enumerating field, not only
     counts and flags. Kills the five wrong passes in §1-A.
   - *verb class*: a read operation may not satisfy a rewrite verb. `revert`/`reset`/`rebase`
     are not in the declared operation set, so they must derive **no** operation and refuse.
     Kills §3.
2. **Give the door a deadline** (§5). One parameter, threaded into `run_adapter_locally`, with
   `python_test_audit.py`'s per-file loop checking it between files. Turns three 180 s hangs
   into three named refusals; also caps the 124 s mutation run.
3. **Stop the machine writing into the tree it analyses** (§4). `solve()` gets a scratch root
   for every artifact, and every adapter's output path is resolved against it. Removes
   `typed_swe_report.json` from the source tree and makes the untraced write in §4
   impossible by construction.
4. **File-level verification** (§6). Let the four review gates take `source_path` as an
   alternative to `diff_path` — the tools behind them already work on files. Instantly makes
   `Lint`, `Type-check`, `Check security`, `Measure coverage` answerable.
5. **Answer shape for the write verbs** (§4). `add_parameter` produced a `SyntaxError` after
   writing; `inline_helper` reported the file's other functions as its ambiguity. Both need the
   pre-write syntax check that `python_refactor_rename_symbol.py` already implements
   (`SYNTAX_ERROR_AFTER_EDIT`) and a candidate rule that reads the *sentence*, not the file.
6. **Expose the index cache** (§7): one persisted, checksummed index per root, with the build
   cost reported in the artifact. Turns 37 s into 3 s on the first call.
7. **Measure every adapter once** (§8): `latency_ms` and `peak_bytes` per row, written by the
   door. Then selection can be fast on purpose instead of fast by luck.
8. **Then** reach the dynamic analyzers (§E): register `python_dynamic_fault_localizer_v1` and
   `python_interprocedural_value_provenance_v1` with the words a human uses — `debug`,
   `profile`, `hot path`, `trace the value of`, `which line raises`. They are the difference
   between a machine that reads code and one that can find out why it fails.

**Until (1) and (3) land, no number this project reports about itself can be trusted**: it can
still answer a question it did not understand and call it verified (seven times in 62), and a
benchmark run can still corrupt the tree it is measuring.

---

## §11. Second pass, same day, `main @ b68f7c7` — the two boards, and four seams this report does not name

Everything below was re-measured after this report was written, on a copy of `main @ b68f7c7`
(clean at start), with the same filesystem oracle. It does not contradict §1; it explains it.

### 11.1 There are two boards and both are true

| board | sentences | correct |
|---|---|---|
| this report's prose corpus | 62 | **5** |
| curated fixture ladder (`hardcore_swe_surface_probe_20261030.py`) | 28 | **26** |
| ordinary sentences, `pkg/test_*.py` layout (`swe_probe_20261029/swe_probe.py`) | 18 | **3** |
| same sentences, sibling `tests/` layout | 18 | **3** |

The same machine scores 93 % when the sentence names a fixture it was built for and 17 % when a
human writes the sentence. That gap is the headline, and it is a **routing and admission** gap,
not a capability gap: `extract_function`, `rename_parameter`, `fix_race`, `git log`, `find_callers`
all execute correctly when they are reached. The machine's depth is real; its *interface* is not.

### 11.2 A three-clause request is answered by one capability, and certified

Measured, deterministic, filesystem oracle:

```
"The test in <D>/tests fails.  Fix the bug in <D>/app and add a regression test that would
 have caught it, then make the whole suite pass."
  -> python.software.repair.apply.verified.v1
  -> PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS…
  -> tree: app fixed, suite green, **no new test file**   (new_test_files: [])
```

The fix landed; the second clause was silently dropped; the report says PASS. Note the doors this
sentence passes through:

* `goal_compiler.compile_goal` **refuses it correctly**:
  `GOAL_COMPILATION_SUBGOAL_UNRESOLVED:{clauses:[…3…], index:2, cause:GOAL_COMPILATION_AMBIGUOUS}`;
* `goal_front_compiler_v1.compile_goal` — the compiler the door actually calls through
  `compile_against_live_registry` — answers it with one capability and no clause accounting.

**This repository has two compilers with different laws, and the door uses the one without the
clause-coverage law.** Clause coverage exists (`_validate_compiled_clause_coverage`,
`_attribute_chained_parts_to_clauses`) and is applied only on the compound path.

### 11.3 The answer gate asks the whole row, so "test-guided" reads as "writes tests"

`stated_answer_errors` decides whether a row may answer a stated effect by running the supplied
regex over `str(entry)`. `python.software.repair.apply.verified.v1` is a **test-guided** repair: the
word "test" occurs throughout its row. So:

* adding an honest `STATED_TEST_AUTHORING_NOT_PROVIDED_BY_CAPABILITY` rule to `_STATED_EFFECTS`
  (measured, 2026-10-31) **does not stop §11.2** — the gate matches the word "test" in the repair
  row's own text and admits it;
* the same addition *did* change which rows the shortlist narrows to, moving `write_test` from a
  chart capability to `test.slice.never_miss.v1` — still wrong, differently.

Any fix here must read what the row **provides** (`provides` / `target_effects` / `result_fields`),
not the row's prose. `declared_effect_ids` already states this law — "what it produces outranks what
it is tagged with" — and the answer gate has not adopted it.

### 11.4 `pass: true` is a weaker claim than its name

Measured on a PASS:

```
status  PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED
pass    True
raw_goal_acceptance.status                  RAW_GOAL_ACCEPTANCE_UNRESOLVED
raw_goal_acceptance.semantic_acceptance_complete  False
```

The status string is honest and the boolean is not. Every consumer that reads `pass` — including
every probe in this report — is reading "executed and locally verified", never "accepted". Either
the boolean becomes `pass and semantic_acceptance_complete`, or the field is renamed; a certificate
that says PASS in one field and UNRESOLVED in the next is a certificate no referee can trust.

### 11.5 No wall-clock authority anywhere, quantified

`canonical/runtime`: **194** `subprocess.run(...)` call sites without a `timeout=`, against **9**
mentions of `RLIMIT_*` in the whole tree. §5 measured the symptom (4 sentences hanging 180 s); this
is the cause: the budget is not missing from one path, it is absent from the layer.

### 11.6 Two registries, and nothing declares what it does

* live `BOUND_CAPABILITY_REGISTRY_V1.json`: **138** rows; snapshot: **145**;
* snapshot-only: `git.history.bisect_regression`, `python.feature.implement_function_spec`,
  `python.refactor.add_parameter`, `python.refactor.move_function`, `python.refactor.move_symbol`,
  `python.source.add_function`, `python.source.add_parameter`, `python.tests.mutation_score`;
  live-only: `git.repository.operate`;
* **0 of 145** rows declare an effect kind.

With no effect vocabulary a router can only count words, which is why `write_test` reached a chart
row, `profile` reaches `python.source.dead_code`, `debug_test` reaches `python.tests.mutation_score`,
and a destructive sentence was refused by luck.

### 11.7 Fix order, revised

1. **One compiler, or a coverage gate on the door** (§11.2) — a dropped clause must never be a PASS.
2. **The answer gate reads `provides`, not the row blob** (§11.3) — this is the seam that lets a
   wrong family answer with authority.
3. **`pass` means accepted** (§11.4) — one boolean, honestly computed.
4. **One registry, generated and verified** (§11.6) — plus a declared effect kind per row, which is
   the only vocabulary that lets routing stop counting words.
5. **A deadline at the process layer** (§11.5) — 194 call sites; a default timeout is one edit.

Items 1–3 are small and reduce certified wrong answers directly. Items 4–5 are the structural work.
