# Every hardcore software-engineering problem, measured — 2026-11-01

Measured on **`origin/main` = `6aa5dab`** (fetched this session; the branch `arena/3918bb60-brain`
is based on it) inside a clean worktree, with the repository's own instruments:

| instrument | what it measures |
|---|---|
| `swe_probe_20261029/swe_probe.py` | 18 ordinary software sentences, each with a **filesystem oracle** |
| `hardcore_swe_surface_probe_20261030.py` | 28 hard tasks; oracle **and** the door's own verdict, side by side |
| `execution_guard/swe_advanced_probe_v1.py` | 49 hardcore sentences across 11 axes (a census; **no per-request oracle**) |
| `execution_guard/swe_capability_matrix_v1.py` | 54 capability cases classified REAL / FALSE / DAMAGED |

Nothing below is a wish or a roadmap. Every number is from a run, and every failure is quoted with
the status and reason the runtime itself returned.

---

## §0 The answer in one paragraph

The machine is **not** short of theory, and it is not short of verification machinery: 443 live
rows, 2 249 test modules, a door that refuses rather than guesses, and one workhorse lane that does
really do memory-safe edits (equivalence-checked with `exec` on samples, suite run, rollback on red;
measured: `lru_cache` memoisation and type hints applied correctly, a package-rooted repair really
rewriting `return a - b` to `return a + b`). The problems are, in order of what an hour buys:

1. **The substrate is empty by default** — the image has `gcc`, `g++`, `node`, `make`, `git` and
   **none** of `pytest`, `ruff`, `mypy`, `hypothesis`, `tree_sitter`, `coverage`, `bandit`, `rustc`,
   `go`, `javac`, `tsc`. The repo already ships the one command that fixes it
   (`scripts/restore_substrate_v1.py`, 12 s, 10/10 modules). Measured on the *same commit*:
   **18-sentence probe 9/18 → 11/18**, capability matrix **42 → 44 REAL**.
2. **A served answer can be false, and the door certifies it** — measured: the dependency audit
   reported `requests==2.32.3`, `pyyaml==6.0.1`, `cryptography==43.0.0` as *vulnerable* (all three
   are past their fixes) with `PASS__…EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`. Cause: one line that
   tested membership in a dict instead of the version. Fixed on this branch.
3. **A refusal is reported as a crash** — 7 of the 13 census refusals came back
   `FAIL__LIVE_CONTROLLER_EXECUTION`, the status reserved for a broken adapter, with the cause
   discarded. Fixed on this branch.
4. **Routing cannot bind three slot shapes** — a directory-wide rename, a function whose body is
   never stated, and a dependency add. These are the `RAW_GOAL_COMPILATION_GAP` /
   `CONTRACT_NOT_STATED` class.
5. **Two of the 14 refusals were "nothing to do"** — the requested state already held, and the door
   had a status for exactly that it did not use. Fixed on this branch (census 35 → 37 served).
6. **Whole capability classes are absent**, and the census's *served* count hides it, because only
   **8 rows** answer all 36 served requests and **three of them answer 31**.

---

## §1 The boards, as they stand today

| board | bare image (`6aa5dab`) | same tree, substrate restored |
|---|---|---|
| 18 ordinary sentences (filesystem oracle) | **9 / 18**, mean 193 ms | **11 / 18**, mean 215 ms |
| 28-task surface ladder | 28/28 reached, **27 PASS**, 1 refused by design, 0 false PASS | 27 PASS |
| 49-sentence advanced census (no oracle) | 36 served / **13 refused** | 36 served / 13 refused |
| 54-case capability matrix | **42 REAL** / 0 FALSE / 0 DAMAGED, median 79 ms | **44 REAL** / 0 FALSE / 0 DAMAGED, median 73 ms |
| 2026-11-01 re-measure, bare venv vs restored, clean `origin/main` | 41 REAL, exit 0 | 43 REAL, exit 0 |

The two sentences the substrate buys are the two the registry advertises as *gates*:

```
type_check  FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT  gate='PASS_BASELINE_ONLY'   (mypy absent)
lint        FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT  gate='PASS_SYNTAX_ONLY'     (ruff absent)
   after `python3 scripts/restore_substrate_v1.py`:  both PASS
```

That is the whole "type-check my file" and "lint my file" capability, missing because a comment
told the operator to run a script.

---

## §2 What actually works (so the fixes below are aimed correctly)

Measured REAL, each with its own evidence:

* `python.software.repair.apply.verified.v1` — repairs a one-operator defect **and runs the suite**
  in the package-rooted layout (`from pkg.calc import add`, the import that used to kill every
  candidate run). 4 of the 18 sentences.
* `python.swe.transform_and_synthesize.v1` (12 of the 36 served census requests) — memoisation,
  type hints, thread pool, GIL-releasing C kernel, module split, verified test authoring. Its
  verification is real for several ops: `exec` equivalence over samples, suite run, **rollback on
  red**.
* `code.polyglot.transform_and_verify.v1` (10 served) — Rust/Go/Java/TS/SQL/TOML/Make/YAML edits
  that honestly report `compiler_verified: false, cst_verified: true` when `rustc` is absent.
* `software.analysis.diagnose_and_architect.v1` (9 served) — a real `profile_hotspot` (loop depth,
  call counts), real failing-suite diagnosis (frames, break frame, cause), real API-design findings
  with line numbers.
* `python.source.symbols.index.ast`, `git.repository.operate.v1`, the four review gates
  (with tools), `python.refactor.rename_symbol/rename_parameter/extract_function`.

So the machine is not a shell. It is a machine whose **reachable surface is far smaller than its
written surface**, and whose **truth layer still has holes**.

---

## §3 The problems, ranked

### P1 — The substrate is empty, and the machine measures a smaller brain than it has
`pytest, ruff, mypy, hypothesis, tree_sitter, coverage, bandit, rustc, cargo, go, javac, tsc, cmake`
are all absent; `gcc, g++, node, make, git` are present. 38 modules mention pytest, 47 mention
hypothesis, 145 mention coverage, 13 mention ruff, 12 mypy, 12 tree_sitter. Rows sourced from a
package: `pypi` 12, `npm` 3, `apt` 11. Costs: two review gates degrade to `PASS_*_ONLY`; 12 rows
whose evidence is a third-party tool cannot be run; nothing in the image runs the restore.
**Fix (landed 2026-11-01):** the restore was already written and takes 12 s, so it is now the first
step of the census workflow and its verdict is a precondition both instruments read
(`execution_guard/substrate_precondition_v1.py`, one owner: `restore_substrate_v1.verify`). Measured
on a bare venv and on the restored image, same commit, same sentences:

```
bare venv (0 of 10 tools)   census 35 of 49 served   matrix 41 REAL   exit 0, board written
restored image              census 35 of 49 served   matrix 43 REAL
after this change, bare     census NOT_MEASURED      matrix NOT_MEASURED   exit 2, no board written
```

The census count does not move, which is why this stayed invisible for two weeks; the two matrix
cases that do are `lint` and `type_check`. A board printed on the bare image was 41 marks, 2 of
which were facts about the interpreter. It is now a refusal instead.

### P2 — A served answer can be false, and "exact semantic acceptance" certifies it
Measured, `6aa5dab`:

```
"Audit the dependency list in <p>/requirements.txt for known vulnerabilities."
  -> PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
  -> vulnerabilities: requests==2.32.3, pyyaml==6.0.1, cryptography==43.0.0   (all fixed already)
```

Cause: `if pkg in _KNOWN_ADVISORIES: flag(...)` — the finding was a function of the *name*. A
6-entry table was treated as an advisory database, and silence about the other packages read as
"safety". **Fixed on this branch**: the table now stores the fixed version, the pinned version is
compared to it, a package the table cannot judge is listed in `unchecked_dependencies`, and
`coverage_note: ADVISORY_TABLE_IS_A_PINNED_SUBSET:6` says what the audit cannot see. Measured after:
safe versions → 0 findings; `requests==2.19.0` → 1 finding (`fixed_in 2.31.0`); unknown/unpinned →
`unchecked`.
**Lesson to generalise:** every row whose answer comes from a *table* rather than from *the
artifact* is a candidate for this defect. The audit was the one the census happened to hit.

### P3 — A refusal is reported as a controller crash
Measured on the census: 13 refusals, **7** returned `FAIL__LIVE_CONTROLLER_EXECUTION` while the
exception held the answer (`POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM` ×2,
`SQL_UNSUPPORTED_DDL_EDIT`, `PYPROJECT_ALREADY_PINNED_OR_EMPTY`, `NO_DECLARED_DEPENDENCY_TO_VENDOR`,
`NO_FLAKY_TEST_DETECTED`, `TARGET_SYMBOL_COLLISION:add`). Same shape in the 18 sentences
(`DIAGNOSE_ARCHITECT_REFUSED:…`, `GIT_FAILED:…`). The door parsed only the
`SystemExit(json.dumps({error:true,…}))` spelling. **Fixed on this branch** (one predicate; served
count deliberately unchanged at 36/49 — a better failure name mints no pass).

### P4 — Three slot shapes cannot be bound, so the sentence dies before any row runs
Measured on the 18 sentences / 54 matrix:

| sentence | status | detail |
|---|---|---|
| `Rename the function add to plus everywhere it is used in <dir>` | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | `rename_symbol.v1:contract_not_stated:module:not_stated` — a directory-wide rename has no single module |
| `Add a subtract(a,b) function to <f> and a matching passing test in <t>` | `FAIL__RAW_GOAL_COMPILATION_GAP` | `implement_function_spec.v1:body_expr:not_stated` — the sentence states no body and no test exercises the name yet |
| `Add requests as a dependency and pin its version` | `FAIL__RAW_GOAL_COMPILATION_GAP` | no row binds a dependency add without a stated manifest |
| `Where is the function mul defined?` (matrix) | `FAIL__RAW_GOAL_COMPILATION_GAP` | a definition lookup over an unstated tree |
| `fix canonical/…/missing.py` (matrix) | `FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED` | the file does not exist and nothing says so to the caller |

The first two are *shape* defects, not absence: the rows exist, and §3's ladder shows the same rows
passing when the sentence happens to fit.

### P5 — "Nothing to do" is not an answer the door can give
**Landed 2026-11-01 for two of the three** (`PYPROJECT_ALREADY_PINNED_OR_EMPTY`,
`NO_DECLARED_DEPENDENCY_TO_VENDOR`): the engine now reads the declared dependencies and reports
`PASS__REQUESTED_STATE_ALREADY_HOLDS` with the list it read (`edited: false`, manifest
byte-identical). Census **35 → 37 served / 14 → 12 refused**, the only two rows that move, and matrix
**43 REAL / 0 FALSE** unchanged. `NO_FLAKY_TEST_DETECTED` is **not** in that class after measurement:
the two CI fixtures do not have a flaky test, they have a failing import (`tests/test_calc.py` imports
`calc`, which lives in `pkg/`), so "so that CI is green" is false and the honest answer there is a
workflow repair, not an already-satisfied pass.

Remaining text of the finding (the vocabulary and the proof requirement): The door has `PASS__REQUESTED_STATE_ALREADY_HOLDS` (it uses it for
`BASELINE_ALREADY_PASSES`) but its vocabulary check is `BASELINE_ALREADY_PASSES|ALREADY_SATISFIED|
NOTHING_TO_DO`, which does not match any of these keys. **Fix:** extend the vocabulary **and verify
the state before claiming it** (read the pins, enumerate the deps, look for the flaky test), because a
claimed-already-satisfied is exactly the class of lie P2 punishes. Measured ceiling: 3 of 13 census
refusals become passes.

### P6 — Whole capability classes have no row
From the census, refused for want of a capability (not a bug):
`Benchmark <f> against the version in git HEAD~1` · `Add a regression test that reproduces the bug in
<f>` · `Cherry-pick the last commit onto a new branch` · `Write the changelog entry for the last three
commits` · `Find the race condition in <f>` (answered by a crossfile *editor* instead —
`FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED`) · `Fix the off-by-one bug in <f>.cpp` and
`Add a NOT NULL constraint … schema.sql` (the polyglot engine has no C++ repair and no DDL edit: the
only two real transform gaps, `CPP_NO_APPLICABLE_TRANSFORM`, `SQL_UNSUPPORTED_DDL_EDIT`).
Language reach: Rust/Go/Java/TS edits verify **by CST only** (`compiler_verified: false`), because
`rustc/go/javac/tsc` are absent — a PASS for a language the machine cannot compile.

### P7 — The served count is not a correctness count, and the reach is degenerate
36 served requests are answered by **8 rows**; three rows answer **31** of them
(`swe.transform_and_synthesize` 12, `polyglot.transform_and_verify` 10,
`diagnose_and_architect` 9). One row answers five different axes (debug, design, perf, review,
tests) and another five (git, perf, refactor, systems, tests). The workhorse rows are genuinely
capable — but the routing layer cannot tell them apart, so an unsupported request lands on one of
them and gets a *plausible* answer. That is exactly how P2 happened.

### P8 — Measurement debt
`execution_guard/swe_advanced_probe_v1.py` has **no per-request oracle**: `SERVED` means "came back
pass and edited nothing unnamed". A wrong answer in the right shape is invisible except in the
`selected` column — and one such answer (P2) sat in the tree certified as exactly accepted. The
census also exits 0 without `--floor`, so CI can be green with any number in it.

### P9 — Deadlines and cost discipline
`canonical/runtime`: **213** `subprocess.run` call sites, **31** without a `timeout`. Any one of them
can hang a request with no ceiling.

### P10 — Two registries
`canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` carries **141** rows; the live verified
registry has **443** (302 live rows absent from the snapshot, 0 snapshot rows absent from live). And
**0 of 443 rows declare `target_effects`**: the effect a row produces is inferred from its id /
`provides` / `keywords` at every call site, which is the P2 failure mode one layer up.

### P11 — Write authority on an unstated repository
`Commit the staged changes with the message 'wip'` resolved its repository to **the runtime's own
tree** and ran `git commit` there (`GIT_FAILED:commit -m wip --no-verify --quiet:Not currently on any
branch` — that is this worktree's state). The refusal saved it; nothing in the design did.

---

## §4 Fix order, with the delta each one is expected to buy

| # | action | measured/expected delta | cost |
|---|---|---|---|
| 1 | run `scripts/restore_substrate_v1.py` at boot; make `SUBSTRATE_READY` a census precondition | **9/18 → 11/18**, matrix **41 → 43** on a bare image; a bare board is now a refusal | done 2026-11-01 |
| 2 | land this branch: refusal taxonomy + version-correct audit | 7 misreported crashes → refusals; audit false positives → 0 | done, unmerged |
| 3 | bind the three slot shapes (P4): directory-wide rename, unstated body, dependency add | up to +3 on the 18-sentence board, +2 matrix | one binding rule each |
| 4 | "nothing to do" as verified already-satisfied (P5) | **+2 census (35 → 37)**, done 2026-11-01; `NO_FLAKY_TEST_DETECTED` is not in this class (the fixture's CI is red, not flaky) | 2 state checks |
| 5 | C++ repair and SQL DDL edit (P6) — the only two real polyglot transform gaps | +2 census | transform per language |
| 6 | benchmark-vs-revision, regression-test authoring, cherry-pick, changelog, race detection | +5 census | 5 rows |
| 7 | give the census an oracle and a `--floor` in CI (P8) | no pass gained; **the ability to see a P2-class lie** | 1 assertion per case |
| 8 | effect declarations in the registry (P10), one registry file | removes the P2 failure mode structurally | 443 rows, mechanical |
| 9 | deadlines on the 31 timeout-less call sites (P9) | no pass gained; no request can hang | 31 edits |
| 10 | split the 3 catch-all rows by operation (P7) | no pass gained; routing failures become visible | mechanical |

Items 1–4 are worth more capability than items 6–10: 1 and 4 are pure measurement/protocol
wins, 2 and 3 are already-written code.

---

## §5 What this branch already changes (unmerged)

`arena/3918bb60-brain` (PR #6497) is based on `6aa5dab` and carries two changes, each with its own
paired test that is red on main and green here:

1. `canonical/runtime/live_brain_route_admission_v1.py` — classify an adapter refusal by the key it
   names (`RuntimeError("GUARD_KEY:detail")`), not by the exception class. Census: 7 of 13 refusals
   change from `FAIL__LIVE_CONTROLLER_EXECUTION` to `FAIL_CLOSED__CAPABILITY_REFUSED_<KEY>` with
   `refusal_payload` carrying the adapter's own reason. Served count unchanged, by design.
2. `canonical/swe_kernel/diagnostics_perf_and_design_engine_v1.py` — the dependency audit compares
   the pinned version against the fixed version, reports `fixed_in`, and names every dependency it
   could not judge in `unchecked_dependencies` (`ADVISORY_TABLE_IS_A_PINNED_SUBSET:6`).

Tests: `canonical/tests/test_a_refusal_already_named_is_not_a_crash_v1.py` (3) and
`canonical/tests/test_a_dependency_finding_requires_a_vulnerable_version_v1.py` (4, including the
two-sided boundary `2.30.9` vulnerable / `2.31.0` clean).

Guard, unified-model compile/verify (33/33) and `repo_integrity_guard_v1` (0 violations) pass
locally; the boards are quoted above for both sides.
