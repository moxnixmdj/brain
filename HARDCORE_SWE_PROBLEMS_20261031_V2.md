# The hardcore-SWE gap, measured — 2026-10-31

**Tree:** `main` @ `c233580` (clean). **Method:** every number below was produced by running
this tree, today. Nothing is carried over from the 2026-10-29 report without re-measuring it,
and two claims from that report are **corrected** here (see §9).

**The question this answers:** what stands between this machine and being the most advanced,
fastest software engineer?

**The answer in one line:** 14 ordinary hardcore-SWE sentences, phrased the way a human would,
produce **3 correct answers, 1 confident wrong answer, 9 fail-closed refusals and 1 raised
exception** — and the machine already contains most of the machinery it failed to reach.

---

## §1. The one table that matters

Fourteen sentences. Each run through the real door
(`live_brain_route_admission_v1.solve({"task_id": ..., "goal": ...})`), in a fresh process,
on this tree. Verbatim goals, verbatim results.

| # | sentence | verdict | capability it routed to | time | diagnosis |
|---|---|---|---|---|---|
| 1 | `Show the last three git commits` | **PASS** | `git.repository.operate.v1` (op=log, limit=3) | 0.72 s | correct |
| 2 | `Who wrote line 3 of canonical/runtime/swe_typed_plan_v1.py` | **PASS** | `python.source.symbols.index.ast` | 0.48 s | **wrong answer, exact acceptance** (§2) |
| 3 | `Show me the diff` | **RAISED** `GoalCompilationFailure` | — | 0.28 s | the door refuses by exception (§3) |
| 4 | `List the branches` | **PASS** | `git.repository.operate.v1` | 0.47 s | correct |
| 5 | `Find every caller of build_plan in canonical/runtime/swe_typed_plan_v1.py` | FAIL | `python.refactor.inline_helper.v1` | **14.33 s** | wrong family: *inline* on a *caller* question (§5) |
| 6 | `Run the tests in canonical/tests/test_swe_typed_plan_v1.py and tell me which fail` | FAIL | `python.tests.mutation_score.v1` | **60.59 s** | `BOUND_CAPABILITY_UNKNOWN` (§5) |
| 7 | `Type-check canonical/runtime/swe_typed_plan_v1.py` | FAIL | `python.review.diff_type_gate.v1` | 0.34 s | only a **diff** gate exists (§4) |
| 8 | `Lint canonical/runtime/swe_typed_plan_v1.py` | FAIL | `python.review.diff_static_triage.v1` | 0.37 s | only a **diff** gate exists (§4) |
| 9 | `Profile the function build_plan in canonical/runtime/swe_typed_plan_v1.py` | FAIL | `python.source.dead_code.v1` | 0.28 s | no profiler route (§4) |
| 10 | `Build the project` | FAIL | none — `RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP` | 0.30 s | no build surface at all (§4) |
| 11 | `Find dead code in canonical/runtime/swe_typed_plan_v1.py` | FAIL | `python.source.dead_code.v1` | 0.22 s | **right capability, `SOURCE_ROOT_MISSING`** (§6) |
| 12 | `Debug the failing test test_breaking_the_derivation_breaks_the_selection in canonical/tests/test_declared_input_derivation_v1.py` | FAIL | `test.slice.never_miss.v1` | 0.36 s | a *test id* was parsed as a source file (§4) |
| 13 | `Which commit broke the tests` | **PASS** | `git.history.bisect_regression.v1` | 3.82 s | correct |
| 14 | `Measure the test coverage of canonical/runtime/swe_typed_plan_v1.py` | FAIL | `code.impact.tree_sitter.testselect.v1` | 1.57 s | `WRITE_AUTHORITY_REFUSED` (§6) |

**Tally: 4 PASS (one of them false), 9 FAIL, 1 exception. Correct end-to-end: 3 of 14.**

Reproduce any row with:

```bash
python3 /tmp/census/one.py "<the sentence>"
```

The distribution is the point. The machine is not failing because it lacks capabilities —
§4 shows it has them — it is failing because **a human sentence cannot reach them**, and
because when routing is ambiguous the door resolves the ambiguity with a guess that claims
success.

---

## §2. P0 — a wrong capability still returns PASS with "exact semantic acceptance"

Sentence 2 above, in full:

```
goal   : "Who wrote line 3 of canonical/runtime/swe_typed_plan_v1.py"
status : PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
pass   : True
capability : python.source.symbols.index.ast
artifact   : {"file_count": 1, "symbol_count": 54, "reference_count": 342,
              "call_edge_count": 118, "caller_index_size": 42,
              "output_verified": true, ...}
contains any of {author, committer, blame, commit} : False
```

A symbol index cannot answer who wrote line 3. It has no authorship data at all. The door
nonetheless returned a **fully certified pass** — `semantic_acceptance_complete: true`,
`independent_reinspection: true` — which is precisely the defect the 2026-10-29 report filed
as §1.1, surviving in a new form: last time the wrong *file* answered a git question; now the
wrong *capability* does, and the certification machinery has nothing to say about it.

### Root cause: ambiguity in the right resolver is resolved by the wrong one

`git.repository.operate.v1` **does** bind this sentence. It derives `op=blame`, and
`select.admit()` returns `admitted: True`. So why did a symbol index answer?

```
family token                : git                       (correct)
typed family candidates     : 5
admitted + specific         : ['git.history.bisect_regression.v1',
                               'git.repository.operate.v1',
                               'python.repository.acceptance.measure.v1']
build_plan(...) is not None : False        <-- three candidates => "ambiguous" => fail closed
final verdict               : PASS via the PRIMARY lexical path
```

`swe_typed_plan_v1._resolve_family()` is right to refuse when three capabilities all bind —
that is its contract. The failure is what happens *next*: `solve()` then runs the primary
lexical path, which does not know it is picking up after a refusal, and that path returns a
PASS with exact acceptance for an unrelated capability.

**The fail-closed branch is consulted, says "ambiguous", and the answer that follows is the
loudest possible yes.** The rule that must exist here is asymmetric: when a sentence states a
software-engineering family and the typed resolver cannot decide, the door may fall back to a
*refusal*, never to a *certificate*.

### The second half: contracts too weak to be specific

`git.history.bisect_regression.v1` declares only `source_root` + `output_path`.
`python.repository.acceptance.measure.v1` declares only `source_root`. Both are "specific"
for a blame question because a blame sentence names a file, and a file yields a directory.
Specificity today is a property of *the inputs happening to be derivable*, not of the
capability being about the question. There is no negative binding: nothing in the registry
lets a row say "not me — this sentence has no bisect intent", so every derivation-compatible
row competes on equal footing and the tie-break is "refuse, then guess".

---

## §3. P0 — the door has two failure surfaces, and one of them is an exception

Sentence 3, verbatim:

```python
solve({"task_id": "DIFF", "goal": "Show me the diff"})
# raises GoalCompilationFailure: GOAL_INPUT_BINDING_REQUIRED:limit
#   at goal_compiler.py:1169  in _render_template
```

Every other failure in this document returns a dict with `pass: False` and a `status`. This
one throws. A caller that iterates over goals — a benchmark, a controller, an agent loop —
must wrap every call in `try/except` or lose the run, and the exception carries no
`capability_id`, no `execution`, and no acceptance verdict. One surface, two contracts.

**Root cause, measured:** `stated_family_token("Show me the diff")` returns **None**. The git
family triggers are

```python
('git', 'commit the', 'last commit', 'commits', 'blame', 'branches', 'who wrote',
 'working tree', 'staged changes')
```

— they contain `blame`, `commits`, `branches`, `who wrote`, but **not `diff`, `status`,
`show`, `log`, `history`**. So the one capability that declares `op=diff` is never consulted,
the sentence falls into the lexical compiler, and the compiler demands `limit` for a
capability (`git.repository.operate.v1` binds fine: `admit() -> True`) it should never have
been asked about.

This is a two-line fix with a large effect: the difference between *"which diff is this"*
raising and being answered is five words in a tuple.

---

## §4. P0 — the machine owns dynamic analysis and cannot reach it

The previous report said there are **zero** capabilities for a debugger, a profiler, an LSP, a
type checker, a linter or a build. **That is wrong on this tree, and the correction matters**,
because the real problem is worse than absence: the machinery exists and no sentence reaches
it.

What is actually in `canonical/runtime/bound_capabilities/` (163 adapters):

| surface | what exists | what a sentence reaches |
|---|---|---|
| dynamic tracing | `python_dynamic_fault_localizer_v1.py` — `sys.settrace()` at :67, :96, load-count tracing | **nothing** — sentence 9 routed to `dead_code` |
| value provenance | `python_interprocedural_value_provenance_v1.py` — `settrace` at :76, Ochiai scoring over argument/return fingerprints | **nothing** |
| coverage | `python_review_diff_coverage_gate.py` — `coverage run -m pytest` then `coverage json` | **nothing** — sentence 14 routed to `testselect`, then was blocked (§6) |
| lint / types | `python_review_diff_static_triage.py`, `python_review_diff_type_gate.py` | only as **diff** gates: both demand `diff_path`, so a whole-file question cannot bind |
| profiler | none | sentence 9 → `dead_code` |
| debugger / breakpoints | none | sentence 12 → `test.slice.never_miss.v1`, `NAMED_SOURCE_UNPARSEABLE` |
| LSP (definition / references / hover) | none | — |
| build / package | none | sentence 10 → `RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP` |

The gap is therefore **not capability count**:

```
registry rows: bound 138 | snapshot 142 | extended 2310 | LIVE (admitted) 437
SWE-prefixed admitted: 82 of 437
adapter file resolvable: 435 of 437   (the 2 misses are knowledge.* rows, not SWE)
bound_capabilities/*.py: 163
```

437 admitted capabilities, 82 software-engineering ones, 163 adapters on disk — and a human
asking to be *debugged* lands on a test-slicer, because "debug" appears in no row's keywords
and `test.slice` shares the word "test".

Two concrete, separate defects:

1. **Vocabulary hole.** No row declares the words `debug`, `breakpoint`, `profile`,
   `hot path`, `type-check a file`, `lint a file`, `build`, `coverage of a file`. Keyword
   matching is the router; a word that appears nowhere is a request that cannot be made.
2. **`diff_path`-only gates.** `python.review.diff_type_gate.v1` and
   `python.review.diff_static_triage.v1` are declared to take a diff. A file question
   (`type-check this file`) has no diff, so the derivation refuses
   (`diff_path:0_type_compatible_existing_files_named`) even though the underlying tools
   (pyflakes-class triage, type gate) would work on a file just as well.

---

## §5. P1 — selection picks capabilities that cannot run, and the cost is paid in wall-clock

Two of the fourteen sentences show selection choosing something the executor cannot execute,
and paying for it in seconds:

```
"Run the tests in canonical/tests/test_swe_typed_plan_v1.py and tell me which fail"
  -> python.tests.mutation_score.v1
  -> 60.59 s
  -> Blocker: BOUND_CAPABILITY_UNKNOWN: python.tests.mutation_score.v1
     (the row IS in the live registry: "mutation_score in live registry: True",
      live 437 | admissible 437 | dropped 0)
```

A benchmark-shaped capability was chosen for a *test-run* question, executed for a minute, and
then the executor said it does not know the capability that the selector just chose. The
selector and the executor disagree about what exists, and the disagreement is discovered after
the work.

```
"Find every caller of build_plan in canonical/runtime/swe_typed_plan_v1.py"
  -> python.refactor.inline_helper.v1          (a MUTATING refactor)
  -> 14.33 s
  -> RuntimeError: HELPER_AMBIGUOUS
```

"Find every caller" is a read. The chosen capability inlines helpers — a write. The run
failed only because the file has many small functions; on a file with one, the sentence
"find every caller" would have edited the tree.

**Cost of this class in this sample: 75 s of the 82 s spent on the three slowest failures was
spent on capabilities that were wrong before they started.**

---

## §6. P1 — the binding layer loses information the sentence already gave

Three of the fourteen failures bind the *right* capability and then fail on an input the
sentence supplied in plain English:

| sentence | capability | failure |
|---|---|---|
| `Find dead code in <path>` | `python.source.dead_code.v1` | `SOURCE_ROOT_MISSING` — the sentence names a **file**, and the row wants a **root** |
| `Measure the test coverage of <path>` | `code.impact.tree_sitter.testselect.v1` | `OUTPUT_OVERWRITES_A_STATED_SOURCE` — with no stated report path, the default sink landed on the source file |
| `Type-check <path>` / `Lint <path>` | `diff_type_gate` / `diff_static_triage` | `diff_path:0_type_compatible_existing_files_named` |

The first is a derivation rule that exists (`PATH_DIR_FROM_STATED_FILE_PARENT`,
`PATH_DIR_COMMON_TO_STATED_FILES`) but did not fire for `source_root` on a single stated file
in this sentence shape. The second is the write-authority gate doing exactly its job and
producing an unusable result: the honest fix is to derive a **report** path (the door already
relocates output paths, `_fresh_output_path`), not to weaken the gate. The third is §4.2.

---

## §7. P1 — "fastest" is unimplementable: no cost, latency or size model

```
rows declaring latency_ms / p50_ms / peak_bytes / cost_bytes : 0 of 437
declared `cost` values                                        : {1: 419, 2: 18}
```

`cost` is a *nominal* integer, not a measurement: it does not distinguish a 0.28 s symbol
index from a 60 s mutation run, and it is identical for 419 rows. Consequently:

- nothing can choose the cheaper of two bindable capabilities;
- nothing can refuse a 60 s plan for a question that should take 0.3 s;
- nothing can report "this took 14 s" as a defect, because no row knows what it should take.

Measured end-to-end on this tree: the three correct answers cost 0.47 s, 0.72 s and 3.82 s;
the two wrong-and-slow ones cost 14.33 s and 60.59 s. The distribution is not heavy-tailed,
it is **bimodal by capability choice**, which is exactly the signal a cost column would have
carried into selection.

---

## §8. P1 — the suite is not a gate

- `canonical/tests/`: **2,162 test files**; there is no sharding, no `pytest-timeout`, no
  `pyproject.toml`, and no per-directory target.
- Known-red on a clean `main` today, measured by worktree A/B (same test ids on pristine and
  on the branch): **6** in `test_swe_typed_plan_v1.py` / `test_declared_input_derivation_v1.py`
  and **4** in `test_python_refactor_rename_symbol_v1.py`. They are *known* red, which is
  worse than red: a suite with permanent failures cannot tell a new regression from the
  background.
- One whole-file test (`test_a_provisional_pass_...`) drives **all 437** registry rows and
  takes ~26 s; several others drive the door end-to-end. That is the right *shape* of test —
  it measures the machine, not a function — but at this size it needs a shard key.

---

## §9. What is fixed, and what the previous report got wrong

Verified fixed on this tree (all three landed today, `#6428`, `#6432`, `#6434`):

| repair | evidence on today's `main` |
|---|---|
| a path-keyed inventory row is not a capability | prose goals against `.py.auto.v1` rows are refused unless they name the path or the id |
| a tool that printed `pass:false` is not a pass | 21 capabilities that printed "no" with exit 0 now fail `TOOL_REPORTED_NON_SUCCESS`; blast radius measured 174/9 → 153/30, PASS→FAIL 21, FAIL→PASS 0 |
| the git object model exists | sentences 1, 4, 13 above; 7 declared ops; `git.history.bisect_regression.v1` from the ladder also passes |
| a commit message is copied, never invented | `Commit the staged changes with the message 'wip'` runs `git commit -m wip`; `Commit the staged changes` binds nothing and refuses |
| the cross-file rename follows dotted receivers | `import a.b` + `a.b.s`, `from a import b` + `b.s`; unresolvable chains reported, `DANGLING_REFERENCE_AFTER_EDIT` before a byte is written |

Two claims in the 2026-10-29 report are **wrong on today's tree and are retracted here**:

1. *"20 of the 64 SWE capabilities are self-certifying stubs."* On this registry **435 of 437**
   rows resolve to an adapter file that exists. The count moved because the ladder added rows
   and because the earlier check keyed on `source.adapter_path` while most rows resolve their
   module by convention (`bound_capabilities/<adapter_module>.py`). The problem is not stubs;
   it is §4 — reachability.
2. *"Zero capabilities for debugger, profiler, lint, typecheck, build, LSP."* `settrace`-based
   dynamic analysis, a coverage gate and diff-scoped lint/type gates all exist as adapters.
   What does not exist is a **file-level** entry point or a **route** from a human sentence.

Everything else in that report still holds and was re-measured where cheap: `cost` model
absent (§7), TRUE ledger **9 rows, 0 SWE, 4 of the 9 DOCX** (the document-format work the
scope ruling deprioritises, still occupying the only "true capability" ledger in the tree).

---

## §10. The fix order (damage per unit of work)

1. **Make ambiguity end in a refusal, never a certificate** (§2). One rule in `solve()`: if a
   stated SWE family was detected and the typed resolver returned `None`, the primary lexical
   verdict may not be returned as PASS-with-exact-acceptance. Cost: a few lines. Effect: the
   single highest-severity class in this document stops producing confident wrong answers.
2. **Widen the git family triggers** (§3): add `diff`, `status`, `show`, `log`, `history`.
   Cost: five words. Effect: turns a raised exception into an answered question, and closes
   the `limit` crash path.
3. **One failure surface** (§3): `solve()` returns a verdict dict for every input; the
   compiler's `GoalCompilationFailure` is converted at the boundary, carrying the same
   status/reason fields every other refusal carries.
4. **Reachability pass over the adapters that already exist** (§4): register the
   `settrace` localizer, the provenance tracer, the coverage gate and the file-level lint/type
   checks with the words a human uses (`debug`, `profile`, `hot path`, `coverage of`,
   `lint`, `type-check`), and give the diff gates a `source_path` fallback. No new substrate.
5. **Derive `source_root` from a single stated file** (§6), and give output-less capabilities a
   derived report path instead of letting the write-authority gate make them unusable.
6. **Kill the 60 s/14 s class** (§5): the selector must not pick a capability the executor
   cannot resolve, and a mutating capability must not be reachable from a read-only sentence.
7. **Measure every adapter once** (§7): `latency_ms` and `peak_bytes` per adapter, recorded by
   the door. Then "fastest" becomes a statement the machine can make, and selection can prefer
   it.
8. **Then** the substrate work: shard the 2,162-file suite, fix the 10 known-red tests, split
   `goal_compiler.py`, add `pyproject.toml`.

Until (1) is done, no benchmark number this project produces can be trusted, because the
machine can still answer a question it did not understand and call it verified.
