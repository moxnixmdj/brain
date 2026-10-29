# What is between this machine and being the most advanced software engineer — V2

Measured 2026-10-29 on `arena/47739ce8-brain`, branched from `main` `e2d7981`.
Authority: **NONE**. This is a sandbox measurement, not an independent verification. Credit: **0**.
Producer cognition model dependency: **0**. Incremental spend: **$0**.
Scope: hardcore software engineering only. PDF/DOCX/XLSX/chart/archive work is excluded except
where it is the *wrong-domain destination* of an SWE request.

Supersedes `HARDCORE_SWE_PROBLEM_INVENTORY_20261029_V1.md` where the two disagree; where V1 is still
right it is cited rather than repeated. Every number here comes from a probe that ran on a fresh tree
and was judged by something that is not the machine's own report: the filesystem, a real
`python -m unittest` exit code, a real command's output, or the artifact the run wrote. The request
matrix is `execution_guard/swe_capability_matrix_v1.py` and the document below is regenerated from it.

---

## 0. The answer in one paragraph

The machine is no longer dishonest. On **47 fresh hardcore-SWE requests it gives 9 real answers, 1
false answer, 37 honest refusals, and destroys nothing** — the false one is a *contract disagreement*,
not a bug (§2 P0-4). It is also fast: median **~100 ms**, and the slowest requests are now the ones that
actually **do** the work (rename 1.2 s, bug report 1.1 s, repair 1.0 s), not the ones that refuse.
So the frontier has moved, and it is no longer truthfulness. It is three things:

1. **Reach.** 15 of the 46 argument-bearing SWE capabilities are **second-stage**: they demand a
   `diff_path` (9), an `anchor_path` (4), a `worktree_path` (4), an `index_path` (3) or a
   `pr_intent_path` (2) — artifacts that some earlier stage is supposed to have produced, and that
   **nothing in the door can produce from a sentence**. Every one of the 10
   `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` refusals is a capability that exists and cannot be handed
   the thing it declares.
2. **Whole capability classes do not exist.** Not "are unreachable" — **have no registry row at all**:
   a formatter (0), type hints (0), `pyproject` (0), add a dependency (0), add a CLI flag (0), add
   logging (0), add retries (0), docstrings (0), `git commit` / `git diff` / `git branch` (0), and a
   **file-shaped** lint/typecheck (0 — the only ones that exist are diff-shaped). That is exactly the
   matrix's `feature` lane 0/7 and `toolchain` lane 1/6.
3. **Scale and composition.** All 9 real answers are **one step**. Real software work is a chain
   (change → verify → report), and there is no measurement at all of a multi-step task or of a real
   repository benchmark. "Most advanced" is currently unquantified.

The advanced machinery is real and it works: provable-binding cross-file symbol rename, byte-exact
extract-function, five measured repair families, an AST symbol index, a verified-apply repair. It is
not short of cleverness. It is short of the boring stages around it.

---

## 1. Where the 47 requests stand, by lane

| lane | real | why not |
|---|---|---|
| repair | 2/7 | two are a composed step that RAISED (world unknown), one is the contested report contract, two need a two-module target the binder does not derive |
| refactor | 1/7 | parameter rename works; symbol rename, extract-function, move, type hints, magic-number extraction, format are all unwired (§2 P0-1/P0-2) |
| tests | 0/3 | the scaffold capability exists and its own verification fails in the door's binding (§2 P1-1) |
| analysis | 4/8 | callers, dead code, impact, counts work; a question with no stated scope cannot search (§2 P1-2) |
| toolchain | 1/6 | run_suite works; lint/typecheck need a diff, pyproject/dependency have no capability class |
| git | 1/4 | blame works; commit/diff/branch are git-shaped requests with no git capability |
| feature | 0/7 | every one of them is a capability class that does not exist |
| honesty | 0/5 | four are correct refusals (a promise that cannot be kept must not be claimed); one is the contract question |

Median **101 ms**, p90 **436 ms**, max **1.20 s** with the declared toolchain installed (§2 P0-3
explains why p90 is 250 ms without it).

---

## 2. The problems, ranked

### P0-1 · The review and test gates are second-stage, and there is no first stage

Nine capabilities want a `diff_path` (`diff_static_triage`, `diff_type_gate`, `diff_security_gate`,
`diff_coverage_gate`, `diff_mutation_gate`, `diff_perf_gate`, `diff_apply_full_testgate`, …), four also
want an `anchor_path` or a `worktree_path`, three want an `index_path`, two want a `pr_intent_path`.
Census over all 419 registry rows: the only capability that **produces** a change set is
`python.software.repair.apply.verified.v1`.

Consequence, measured: "Lint `<calc.py>`", "Type-check `<calc.py>`", "Run a security audit on `<pkg>`",
"Measure the test coverage" all fail with `BINDING_REFUSED:diff_path:0_type_compatible_existing_files_named`
or an honest refusal — the sentence names a file, the capability wants a diff of a worktree.

**Reuse, not new code:** `git` is on the image, `git diff`/`git worktree add` produce exactly that
artifact, and `python.repo.pr_realize.v1` already exists to realise a repo state. A *file* handed to a
diff-shaped gate is a one-line derivation (a diff of that file against its anchor), which is the same
shape as the derivations `declared_input_derivation_v1` already performs for `source_root`, `module`,
`test_argv`.

### P0-2 · The daily verbs have no capability at all

Keyword census across all 419 rows (id + `provides` + `keywords`):

| verb | rows | note |
|---|---|---|
| format / formatter / black | **0** | `ruff` appears only inside a *review gate* |
| type hints / annotations | **0** | |
| `pyproject` | **0** | |
| add a dependency | **0** | |
| add a CLI flag | **0** | `argument` matches one unrelated provenance row |
| add logging | **0** | |
| add retries | **0** | |
| docstrings | **0** | |
| `git commit` / `git diff` / `git branch` | **0** | only `blame` is served, and it works |
| lint / typecheck a **file** | **0** | the two that exist are diff-shaped |

This is the single largest hole in the surface, and it is not an "advanced capability" problem: it is
the work a working engineer does forty times a day. It is also the cheapest to close, because the
tools are declarable today — `ruff format`, `mypy <file>` and `git commit -m` are *already installed or
present* and the registry's own declaration form (`source: {type: pypi|apt|binary, module: …}`) is
built to describe them.

### P0-3 · The declared toolchain is provisioned by nothing, and provisioning it alone changes nothing

Six SWE rows declare a pypi source that is absent from the image by default:
`bandit` (`diff_security_gate`), `coverage` (`diff_coverage_gate`), `mypy` (`diff_type_gate`),
`ruff` (`diff_static_triage`), `pytest` (`issue_to_pr.orchestrate`), plus the mutation/perf gates that
shell out to the same tools. Only `git` is present.

Measured both ways: I installed all five (`pytest 9.2.0`, `ruff`, `mypy`, `bandit`, `coverage`) and
re-ran the whole matrix. **Every verdict was identical (REAL 9 / FALSE 1 / refused 37 / DAMAGE 0)** and
p90 went **250 → 436 ms** — some refusals now get further before refusing. That is a useful negative
result: *installing the tools is necessary and not sufficient*, because P0-1 (shape) blocks first.
Anyone who "fixes" the review lane by adding a `pip install` will have bought only latency.

### P0-4 · The one false answer is a contract conflict — an owner decision, not a bug

`"Repair the python source <calc.py> so that the unit test <test_calc.py> passes, and save the repair
report to <out.json>"` returns PASS while the source is byte-identical and the stated test is red.
The repair loop's own documented contract is **"untouched source plus one applicable patch in the
report"**, and the family oracle that enforces it lives at
`canonical/runtime/live_solver_families_v3.py:430`; the door's `_statement_patch_authority` implements
that contract faithfully. The *sentence*, however, says "so that the unit test passes". Two oracles in
this repository disagree about the same sentence. Whichever way it is settled, one of them changes.

### P0-5 · Composition is single-step, although a planner for chains already exists

All 9 real answers are one capability. The repository already contains the machinery for chains —
`goal_front_compiler_v1._dag_steps` binds a step's input to the artifact an **earlier step produces**
(F12 `_bind_produced_artifact`), and `composer_route_v1.execute_chain` runs and verifies them — but the
composer only fires for a stated command line or a stated payload+destination. So "produce the diff →
type-check the diff → report" cannot be planned, which is precisely the P0-1 shape.

### P0-6 · There is no scale measurement, so "most advanced" is a claim

47 hand-written sentences are a surface probe, not a capability measurement. There is no in-repo
harness that runs real repository tasks end to end (SWE-bench-lite shape: a repo, an issue, a test
that must go green), so every statement about "advanced software engineering" is made on one-step
sentences. V1 said the same and it is still true.

### P1-1 · The tests lane is 0/3, and its capability exists

- `write_unit_test`: a capability runs, then `PROMISED_ARTIFACT_MISSING:<test_new.py>` — it never
  wrote the file it promised.
- `tests_from_docstrings`: `LocalExecutionFailure: ACTION_EXPECTATION_FAILED: verified:OBSERVED=False`
  **with pytest installed**, so the scaffold's own verification is not reached by the door's binding.
- `add_case_test`: `FAIL_CLOSED__NO_OBSERVED_EFFECT`.

Writing tests is the highest-leverage daily verb after "fix", and the machinery
(`python.tests.generate.scaffold.v1`, `python.tests.audit.unittest`) is already in the tree.

### P1-2 · A question with no stated scope cannot search

`Where is the function mul defined?` admits **zero** capabilities: the symbol index wants a
`source_root` and the sentence names no path. That refusal is *correct* under the current contract and
*wrong* for a working engineer, who expects the tree to be searched. There is no "search the
repository" scope rule.

### P1-3 · The latency unit is one step, and the heavy cases are now the real ones

p90 **436 ms** (with tools installed), median **101 ms**. The three slowest requests are the ones that
succeed: `rename_param` 1,196 ms, `bug_report` 1,132 ms, `fix_target_first` 965 ms. There is no
measurement of a ten-step task, which is what a real change is.

---

## 3. The order I would work in

1. **First stage for the review gates** (P0-1). Derive a `diff_path` for a stated file/directory the
   way `source_root` is already derived, or emit the diff with the `git` that is already here.
   Unlocks up to 9 existing capabilities at once — the largest single reach win available.
2. **File-shaped siblings for the five installed-tool verbs** (P0-2, cheapest): `ruff format`,
   `mypy <file>`, `git commit`, plus type-hints and dependency declarations. These are *registry rows
   over machinery that is already installed*, not new engines.
3. **The tests lane** (P1-1): make the scaffold's `verified` flag reachable and stop promising an
   artifact the adapter does not write.
4. **Let the existing DAG planner fire on SWE chains** (P0-5): producer step → consumer step.
5. **A repo-task harness** (P0-6): N real tasks, real test runner as the oracle, so the frontier is a
   number and not a sentence.

Steps 1 and 2 are reuse of what is already installed and already declared. Step 5 is the only one that
is genuinely new work, and it is the one that turns "most advanced" into something measurable.

---

## 4. Reproduce

```
python3 execution_guard/swe_capability_matrix_v1.py                 # all 47, table + verdicts
python3 execution_guard/swe_capability_matrix_v1.py --lane feature  # one lane
python3 execution_guard/swe_capability_matrix_v1.py --json          # machine-readable rows
```

Per-capability slot census, missing-verb census and toolchain census: the probes are one screen each
and are quoted with their numbers in §2 (they read `live_brain_route_admission_v1.load_verified_registry()`,
`declared_input_derivation_v1.adapter_defaulted_keys()` and `importlib.util.find_spec`).
