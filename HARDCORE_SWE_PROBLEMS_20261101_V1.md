# Every hardcore software-engineering problem, measured — 2026-11-01

Measured today on `main` `34124aa` (PRs #6498 and #6504 merged), substrate restored
(`python3 scripts/restore_substrate_v1.py` → `SUBSTRATE_READY`, 10/10 modules,
parser 0.20.4 match), by `execution_guard/swe_capability_matrix_v1.py`,
`execution_guard/swe_advanced_probe_v1.py`, and two extra passes written for this
document that re-run the same fixtures and record what the census does not: **whether
an answer was handed to the caller**, and **which result fields each passing
execution produced** (`/tmp/audit_answers.py`, `/tmp/fields.py`).

Scope: hardcore software engineering only. PDF/DOCX/XLSX work is excluded, per standing
instruction, except where it is the wrong-domain destination of a real SWE request.

---

## §0 The answer in one paragraph

The machine is much stronger than the last inventory says and much weaker than its own
certificates imply. **The last document (`HARDCORE_SWE_ALL_PROBLEMS_20261031_V1.md`) reports 4 of 49
sentences served; the same instrument on today's tree reports 36 of 49, and the capability
matrix reports 44 of 54 REAL with 0 FALSE and 0 DAMAGE.** That headline is real: the machine
really does add a Rust function, split a module into one file per function, add type hints,
compile a C kernel and call it through `ctypes` to release the GIL.

The problem is somewhere else, and it is one problem with many faces: **a PASS carries
nothing.** Of the 34 census cases that pass, **33 return `answer: null`**; of the 42 matrix
cases that pass with the world changed, **37 return `answer: null`**. Seventy of 77 passing
executions wrote a report to `output_path` containing the answer — `hot_spot_function`,
`root_causes`, `adr_markdown`, `migration_steps`, `mutation_score`, `line_coverage_pct` —
and the door closed the run without reading a single one. So the machine *works* and
the caller *learns nothing*.

Ranked by capability bought per hour:

1. **Delivery** — 34 of 34 census PASSes and 42 of 42 matrix PASSes should hand back what the
   row produced. One projection step. (§1)
2. **A read-only question with no answer is a wrong certificate** — 8 census sentences pass
   with `answer: null` while asking a question. One predicate. (§2)
3. **The row declarations under-declare their own result** — so even a declaration-driven
   projection cannot find the answer. Derived mechanically from a run. (§3)
4. **Eleven absent capabilities**, and four rows that refuse *correctly* are counted as gaps.
   (§4)
5. **Substrate**: still a Python machine in its verification, not in its ambition. (§5)
6. **Unmeasured structural gaps** — no long-horizon loop on a real repository, no ranked
   cross-module navigation, no learning from the refusal corpus. (§6)

---

## §1 The measured surface

| instrument | today (`34124aa`) | last document (`b37f118`) |
|---|---|---|
| advanced census, 49 hardcore sentences | **36 served / 13 refused** | 4 served / 45 refused |
| … of the served, with an answer delivered | **1 / 34** | 0 |
| capability matrix, 54 cases with a world oracle | **44 REAL / 0 FALSE / 0 DAMAGE / 10 refused** | 23 REAL |
| … of the REAL, with an answer delivered | **5 / 42** | – |
| census latency | median **38 ms**, p90 250 ms, max 1 253 ms | median 102 ms |
| matrix latency | median **88 ms**, p90 529 ms, max 3 373 ms | median 102 ms |
| live verified registry | 443 rows, **87 software-engineering rows**, 110 declare `output_path` | 440 rows, 88 SWE |

**Retraction.** `HARDCORE_SWE_ALL_PROBLEMS_20261031_V1.md` §0 states the brain answers
"4 of 49" advanced sentences. That number is stale by the time it was read: the same
instrument on the merged tree says 36 of 49. The document's *conclusion* (the gap is
plumbing, not theory) survives; its *headline* does not.

**The one number that does not move:** 70 of the 77 passing executions across both corpora
write `output_path` + `output_sha256` and never deliver the contents.

---

## §2 The problems, ranked

### P1 — A PASS hands over nothing (reach: every question, 33 of 34 census, 37 of 42 matrix)

`canonical/runtime/answer_shape_v1.py` decides what to deliver from a fixed table of **13
nouns** (`caller`, `function`, `class`, `import`, `definition`, `symbol`, `reference`,
`file`, `commit`, `branch`, `test`, `duplicate`, `dead`). Any sentence that does not name one
of those takes `asked() -> None` and delivers nothing, whatever the row produced.

Measured, all four PASS, all four `answer: null`, all four with the answer already on disk:

| sentence | row | what the row produced | delivered |
|---|---|---|---|
| Profile `pkg/util.py` and tell me which function is the hot spot | `software.analysis.diagnose_and_architect.v1` | `hot_spot_function`, `hot_spot_elapsed_ns`, `function_profiles` | **nothing** |
| The test in `tests/test_calc.py` fails; find the root cause | same | `root_causes`, `cause`, `failed_tests`, `frames` | **nothing** |
| Design the API for a rate limiter and write an ADR | same | `adr_markdown`, `api_types` | **nothing** |
| Plan the migration of `pkg` from Python 3.9 to 3.12 | same | `migration_steps`, `module_count` | **nothing** |

*The right fix.* Project the row's **declared** answer surface (its `result_fields`, and the
report at `output_path` when the declaration is incomplete), ranked by what the sentence asks
for — not by a hand-written noun table. The declaration already exists for 117 rows; the report
already exists for 110. One function, at the same single exit as today's projection.
The precedent is in this repository: PR #6504 added `deliver_observation`, which hands over
`observed_effect` for a state question and moved four sentences from `answer: null` to a real
answer without moving a single verdict.

### P2 — A question answered by silence is certified (reach: 8 census sentences)

`live_brain_route_admission_v1.stated_answer_payload_errors` returns `[]` unless the sentence
matches `_BISECT_ANSWER_RE`. Every other read-only question is never checked for an answer.
Measured PASS with `answer: null`: *hot spot* (#17), *root cause* (#30), *explain why it
returns None* (#31), *API design review* (#39), *security review* (#40), *dependency CVE
audit* (#41), *which tests fail and why* (#29), *migration plan* (#48).

*The right fix.* One predicate, already half-present: a sentence that **promises no change**
(`_READ_ONLY_REQUEST_RE` / `_asks_only_for_a_plan`, both in the same file) must carry an answer,
or the PASS becomes `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED`. The bisect rule is the special
case, not the model — generalise it, do not add a second classification.

### P3 — Rows under-declare their own result (reach: every projection, present and future)

`software.analysis.diagnose_and_architect.v1` declares
`result_fields = [adapter, verified, gate, operation, records, exit_code, tests, passed, failed,
functions, files, dead_symbols, output_path, output_sha256, output_verified]` and actually
returns `hot_spot_function`, `hot_spot_elapsed_ns`, `function_profiles`, `root_causes`, `cause`,
`adr_markdown`, `api_types`, `migration_steps`, `module_count`, `operation`.
Six answer-bearing fields are invisible to any consumer that reads the declaration.

*The right fix.* Derive `result_fields` from a run and check the derived set against the
declared set; a row whose declaration omits a field it returns is a declaration defect, the
same class `test_a_row_declares_only_what_it_implements_v1` already polices in the other
direction. No new mechanism.

### P4 — Eleven absences, and four refusals that are correct

The 13 census refusals and the 10 matrix refusals, classified by cause:

| cause | n | sentences | is it a defect? |
|---|---|---|---|
| `POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM` | 2 | fix an off-by-one in C++; repair C++ so it compiles | **absence**: the polyglot engine edits Rust/Go/Java/TS/YAML/TOML but has no C++ transform |
| `POLYGLOT_REFUSED:SQL_UNSUPPORTED_DDL_EDIT` | 1 | add a NOT NULL constraint in `schema.sql` | **absence**: no DDL transform |
| `POLYGLOT_REFUSED:PYPROJECT_ALREADY_PINNED_OR_EMPTY` | 1 | pin the dependency versions | **correct refusal** (the fixture is already pinned) |
| `POLYGLOT_REFUSED:NO_DECLARED_DEPENDENCY_TO_VENDOR` | 1 | vendor the single dependency | **absence** (vendoring) |
| `POLYGLOT_REFUSED:NO_FLAKY_TEST_DETECTED` | 1 | quarantine the flaky test | **correct refusal** (no flaky test exists in the fixture) |
| `NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT` | 3 | benchmark against `HEAD~1`; cherry-pick; changelog | **absence**: no row declares those effects |
| `FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED` (matrix) | 2 | `git_branch`; nonexistent source file | 1 absence (branch op), 1 **correct** |
| `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` (matrix) | 2 | ambiguous "fix it"; idempotent refusal | 1 **correct** (ambiguity), 1 plumbing |
| `FAIL_CLOSED__CAPABILITY_REFUSED_REGION_INVALID` | 1 | extract the body of `add` into a helper | **row contract too narrow** |
| `FAIL__LIVE_CONTROLLER_EXECUTION` | 1 | extract a constant | real failure |
| `FAIL__RAW_GOAL_COMPILATION_GAP` | 1 | `find_definition` | **compiler gap** for a family that has a row |
| `FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN` | 1 | delete a file | **absence**: no delete row, and the step died |
| `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` | 2 | race condition; bisect provenance | P2 / P-circular (below) |

Plus `TARGET_SYMBOL_COLLISION:add` (#33) — **correct**: both files define `add`, so the move is
genuinely ambiguous. A denominator that counts it against the machine overstates the gap.

**Absent capabilities, in the order a working engineer needs them**

1. **git operations that write**: cherry-pick, branch, changelog, rebase, tag. The only git row
   (`git.repository.operate.v1`) reads, and its own limitations say so.
2. **Benchmark against a parent commit** — needs a worktree at `HEAD~1`, two timed runs, and a
   ratio. The parts exist (`python.review.diff_perf_gate.v1` compares two trees); the row does not.
3. **C++ and SQL DDL editing**, and **vendoring/pinning** — the polyglot engine's transform table.
4. **Delete / rename a file** with the tree left consistent.
5. **Extract a named *body*** (the row accepts only a statement span).

### P5 — `FAIL__LIVE_CONTROLLER_EXECUTION` hides the row's own reason (reach: 7 census, 3 matrix)

`POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM`, `TARGET_SYMBOL_COLLISION:add`,
`NO_FLAKY_TEST_DETECTED`, `PYPROJECT_ALREADY_PINNED_OR_EMPTY` all surface to the caller as
`LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE`. Two of those are *principled* refusals, so
the class is over-broad: a correct "this is ambiguous" is indistinguishable from a broken run.

*The right fix.* Propagate the row's refusal code into `failure_class` under a
`CAPABILITY_REFUSED_<CODE>` prefix and keep `LIVE_CONTROLLER_EXECUTION` for runs that raised
without one. The row is already raising the right string; only the door is discarding it.

### P6 — "Make sure it compiles" without a compiler

`canonical/swe_kernel/polyglot_build_ci_engine_v1.java_transform_and_verify` sets
`compiler_verified = False` when `javac` is absent and still returns `verified: True`
(CST/delimiter check only). Measured on *"Add a second method to `src/Main.java` and make sure
it compiles"*: `verified: true`, `gate: PASS`, and the door stamped
`PASS__…_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`. No `javac`, `rustc`, `cargo`, `go` or `tsc` exists
in this image.

*The right fix.* The sentence states a verification clause; a row that can only discharge it at
CST level must report `EXECUTED_APPLIED_UNVERIFIED` (the door already has that status string and
already uses it for blind renames), or the substrate must supply the compiler.

### P7 — One effect's proof lives outside the repository

*"Make the function `total` release the GIL while summing"* is served by compiling a C kernel
and calling it through `ctypes`. The compiled object is written to
`tempfile.gettempdir()` (`/tmp/_gil_free_sum_22ee0301eda2575a.so`) and the emitted source
hard-codes that absolute path, with a silent `sum(items)` fallback when the file is absent
(`canonical/swe_kernel/egraph_and_deductive_synthesizer_v1.py:632`). The source that ships is
therefore *not* the source that proves the effect: on a fresh machine the effect silently
disappears and the code still passes.

*The right fix.* Emit the `.c` file into the package (with a build step, or a `ctypes` load that
fails loudly and is covered by a test), and make the fallback a named refusal, not a silent
one. The same pattern must be checked repo-wide: an artifact outside the repository is not a
capability, it is a caching accident.

### P8 — Substrate: the verification power is Python-only

After `scripts/restore_substrate_v1.py` (10/10 modules, `SUBSTRATE_READY`):

| present | absent (and what it costs) |
|---|---|
| python3, pip, gcc, g++, make, node, npm, git, pytest, hypothesis, coverage, mypy, ruff, bandit, crosshair, z3, tree-sitter | **rustc/cargo, go, javac/java, tsc** (5 of 7 polyglot sentences cannot be compiled), **gdb, valgrind, strace, perf** (no debugger, no race or memory checker, no profiler), **sqlite3** (SQL DDL unverifiable), **radon, libcst, rope, mutmut, pynguin** (in-house equivalents exist), **cmake, ninja, docker** |

The consequence is precise: 4 of the 49 census sentences turn on an absent binary, and every
"verified" claim in a language whose compiler is missing is a CST claim wearing a compiler's
name (P6).

---

## §3 Structural gaps neither instrument can see

1. **Both corpora are fixtures written by the same hand that writes the rows.** 103 sentences,
   all synthetic. Real software engineering is unbounded; a corpus that can be satisfied
   without being a good engineer is a weak oracle. Nothing here measures the machine on a real
   repository with an unfamiliar layout.
2. **No long-horizon loop on a real repository** — plan → edit → run → observe → repair, twice
   in a row, without a human re-stating the goal. Single-shot is measured; iteration is not.
3. **No ranked cross-module navigation.** "Where is this behaviour implemented" has no row and
   no ranked retrieval: the symbol index answers *where is this name*, not *where is this
   behaviour*.
4. **No learning from refusals.** The taxonomy in §2 was derived by hand again today. The
   refusal corpus is not mined into candidate rows.
5. **Latency is good and unbudgeted.** Median 38 ms (census) / 88 ms (matrix), max 3.4 s. There
   is no regression gate on it: nothing fails when a change makes the door ten times slower.
6. **Reproducibility under load.** `perf_review` measures 0.90–1.01 ratios against a 1.10 band
   on unchanged files; when contention pushes a run past the band the verdict is `UNCLEAR`.
   That is honest, but it means a refactor's performance cannot be *certified*, only refuted.

---

## §4 The order to fix it in

| # | move | reaches | why first |
|---|---|---|---|
| 1 | **Deliver what the row produced** (P1/P3): project the declared result surface and the `output_path` report at the door's single exit | 34/34 census + 42/42 matrix PASSes | the work is already done and already on disk; nothing else moves this many sentences |
| 2 | **A question with no answer is not a PASS** (P2): generalise the bisect rule to every read-only question | 8 | turns 8 silent certificates into refusals or answers; one predicate |
| 3 | **Propagate the row's refusal code** (P5) | 10 | a principled "ambiguous" and a crash stop looking identical |
| 4 | **A verification clause needs a verification** (P6/P7): no compiler → `APPLIED_UNVERIFIED`; no artifact in-repo → named refusal | 5 polyglot + 1 systems | the certificate is the product; this is where it lies |
| 5 | **Build the absent classes** (P4): git writes, benchmark-vs-parent, delete/rename, C++ and SQL DDL transforms, vendoring/pinning | 9 | each is mechanical and independently verifiable |
| 6 | **Extract a named body** (P4.5) and **`find_definition`'s compilation gap** | 2 | row contracts, no new capability |
| 7 | **Substrate for the verification** (P8): rustc/cargo, go, javac, tsc, gdb/valgrind, a profiler | unblocks P6 and every polyglot claim | an install, not a program |
| 8 | **A real-repository benchmark** (§3.1/3.2) | the measurement itself | without it, every number above is a fixture number |

---

## What this document is not

It is not a claim that 36 of 49 is a good score. Thirty-three of those 36 hand the caller
nothing, and eight of them are questions answered by silence. **The honest reading is: the
machine can already do the work and cannot yet tell anyone what it did.** That is a delivery
defect at one function, and it is the cheapest large win on this list.
