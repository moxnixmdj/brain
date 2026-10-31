# What stands between this machine and being the most advanced software engineer — V6

Measured 2026-10-29 on `arena/47739ce8-brain`, branched from `main` `e2d7981`.
Authority: **NONE**. Sandbox measurement, not independent verification. Credit: **0**.
Producer-cognition model dependency: **0**. Incremental spend: **$0**.
Scope: hardcore software engineering. PDF / DOCX / image / archive work is excluded *except* where it
appears as the **wrong-domain destination** of an SWE request.

V6 supersedes V5. §3 of V5 ("the advanced capabilities that exist and are never reached") was the
largest open item and the one with the clearest mechanism. **Six defects are closed this round, all in
the wiring between a sentence and a capability that already worked**, and every one of them was found
by asking a working capability to answer a request and following the failure down:

    FAIL__RAW_GOAL_COMPILATION_GAP          -> a review that had not been attempted
    software.review.gate.composer.v1        -> a composer that tags the tools it cannot run
    anchor_path:0_...                       -> a slot the sentence was never asked for, and never should be
    gate: PASS / diff_executable_lines: 0   -> a coverage verdict over nothing
    BOUND_PYPI_SOURCE_INCOMPLETE            -> a substrate that was importable
    BOUND_PYTHON_STDLIB_MODULE_MISSING      -> "the standard library" read as an import name

---

## 0. The answer in one paragraph

Four capabilities that exist, execute and report real verdicts — a **security review**, a **coverage
measurement**, a **mutation score**, a **performance review** — could not be reached from the sentence
that describes them. They are reached now, from ordinary phrasing, with the gates' own artifacts as
the evidence:

    "Measure the test coverage of <calc.py>."     PASS  PROJECT_BRAIN_DIFF_COVERAGE_GATE_V1 gate=PASS,
                                                        diff_executable_lines=5, ratio=1.0
    "Review <calc.py> for security issues."       PASS  PROJECT_BRAIN_DIFF_SECURITY_GATE_V1 gate=PASS
    "Measure the mutation score of <calc.py>."    PASS  PROJECT_BRAIN_DIFF_MUTATION_GATE_V1 gate=PASS
    "Run a performance review of <calc.py>."      PASS  PROJECT_BRAIN_DIFF_PERF_GATE_V1 gate=PASS,
                                                        both medians present

and the same request over a file with a planted vulnerability now answers
`FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT` (`gate: FAIL`, real finding) instead of claiming the
compiler could not turn the sentence into a contract. What is still missing is unchanged from V5: the
lanes that need a *change* (repair 1/7, refactor 1/7, tests 0/3, feature 0/7, git 0/5) and the
long-horizon work.

---

## 1. Closed this round, and the mechanism that closed each

| # | problem | closed by | before → after |
|---|---|---|---|
| R-1 | a **composer** that lists `bandit`, `coverage`, `mutation` as KEYWORDS outranked the row that *provides* the gate | `declared_effect_ids` now ranks `provides`+id above `keywords` (tags are not production) | `"Review <f> for security issues"` → `software.review.gate.composer.v1` **not_admitted:R3_WEAK_EVIDENCE` → shortlist = `['python.review.diff_security_gate.v1']` |
| R-2 | the declared-effect shortlist could **turn a routable sentence into a compile gap** | narrow the registry, and on `GoalCompilationFailure` compile exactly as before | `"Set up CI …"` stayed `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` instead of becoming a guessed chain |
| R-3 | the four review gates' effect families were never enumerated | four rows in `swe_typed_plan_v1._FAMILIES`, and the **effect token filters candidates before the oracle runs** (it was checked only after uniqueness, so a keyword-sharing row made the decision ambiguous) | coverage, security, mutation, perf → `DECISIVE_TYPED_PLAN`; `type-check` / caller-finding / bug-report families unchanged |
| R-4 | `anchor_path` had **no derivation row**; `min_coverage_ratio`-style thresholds were demanded from the sentence although the adapter defaults them | one derivation rule for directory slots; `adapter_defaulted_keys` recognises `args.get(k) if args.get(k) is not None else <default>` as an absence-provided default | `BINDING_REFUSED:anchor_path:0_…` → admitted, with the AST line as evidence |
| R-5 | a change set derived from a **file** was written as a NEW-file diff, which any gate that *applies* it must refuse; the coverage gate then reported **PASS over zero measured lines** | the change set rewrites the file in place (`--- a/x +++ b/x`), anchored at the same directory the gate runs tests in; the gate refuses `DIFF_FILES_NOT_IN_COVERAGE_REPORT` and reports `NOTHING_EXECUTABLE_CHANGED` instead of a vacuous 1.0 | `DIFF_DOES_NOT_APPLY … already exists` and `gate PASS / 0 lines` → real 5-line measurement |
| R-6 | acquisition gates blocked substrates that were **present** | `_pypi_module_already_present` (feature probe first, acquisition only for what is absent; a comparable-but-unsatisfied `version_family` is still a refusal) and `python_stdlib: "stdlib"` resolved as the interpreter itself | `BOUND_PYPI_SOURCE_INCOMPLETE` → `ALREADY_PRESENT_FEATURE_PROBED`; `BOUND_PYTHON_STDLIB_MODULE_MISSING:stdlib` → `LOCAL_VERIFIED` |
| R-7 | a **guessed chain** was composed before a decisive typed selection, and its raise (`side_effect_landed: UNKNOWN`) then forbade the retry | a decisive plan is consulted **before** composition; `STEP_RAISED_OUTCOME_UNKNOWN` is a not-verified class, judged on what *landed* (`created_paths`, `side_effect_landed`) rather than on whether a step raised | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` → the coverage gate ran |
| R-8 | the door reported `FAIL__RAW_GOAL_COMPILATION_GAP` for a retry that **executed**, and `CAPABILITY_EXITED_PROCESS` for a structured refusal | an executed retry's own verdict is returned; a `{"error": true, "reason": …}` SystemExit is reported as `FAIL_CLOSED__CAPABILITY_REFUSED_<reason>` | an empty reason → `NO_TESTS_DISCOVERED` |

Nothing was widened. Every gate is still the pinned binder, the same execution path and the same
observation chain; `pass` is still `False` for a review that returned findings or for a measurement
that could not be taken.

---

## 2. The structural finding (V5 §2) still stands

The router still has **no "none of these"**: it ranks 125 rows and always returns a top-1, and the only
thing standing between a wrong pick and a wrong answer is whether a downstream gate happens to apply.
What changed is that the *declaration* data now shortlists before the ranking, and a decisive typed
selection now runs before a guess. Both are preference, not permission.

Remaining, measured this round, unchanged:

- `"Find the dead code in <f>."` → `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` (honest, nothing produces it).
- Fault localisation, `cegis.z3`, `hypothesis_property`, the cross-file choreographer: by-id invocation
  is not a path either — each raises at composed-step level (`EDIT_PLAN_INPUT_INVALID: output already
  exists: canonical/astra_runtime/tmp/spool_0_output.json`, a fixed spool name that self-locks).
- Seven refusals still name an unrelated family (fault-localize → `…semantic_behavior.compile.v1`,
  logging → `structured.decision_evidence.locate.stdlib`, feature-flag → `test.slice.never_miss.v1`).

---

## 3. What does not exist at all (unchanged from V5 §4)

A census over the 125 routable rows — `provides` + `keywords` per row — finds **zero** rows for: docker,
CI, lockfile, bisect, flaky tests, docstring, complexity, snapshot, checkpoint, resume, memory, learn.
Of those, three are the *stated* answer of ordinary sentences, and the answer gate now refuses them by
name (`STATED_CI_SETUP_NOT_PROVIDED_BY_CAPABILITY:UNNAMED`,
`STATED_BISECT_NOT_PROVIDED_BY_CAPABILITY:UNNAMED`), so the machine no longer fabricates them. It also
does not have them.

---

## 4. Scoreboard (generated, not typed)

`execution_guard/swe_capability_matrix_v1.py`, **53 requests**, one fresh tree per case, judged by
something outside the machine's report:

    REAL 13 · FALSE 1 · REFUSED 39 · DAMAGED 0
    median 95 ms · p90 489 ms · max 1127 ms
    repair 1/7 · refactor 1/7 · tests 0/3 · analysis 7/12 · toolchain 3/7 · git 0/5 · feature 0/7 · honesty 1/5

Four of the thirteen REALs are new this round (`measure_coverage`, `security_review`,
`mutation_score`, `perf_review`), each with an artifact-only oracle: the harness reads the gate's own
JSON and requires its own schema, its own verdict and its own numbers. The single FALSE
(`repair_with_report`) and the zero-DAMAGE result are unchanged.

---

## 5. The order I would work in next

1. **`diff_path` for a real change** — every repair/feature lane needs the change set that
   `_stated_change_set` cannot derive (it can only say "the whole file is new"). A stated *intent*
   ("make `add` return the sum") still has no path to a diff.
2. **T-2 `write_unit_test` (tests 0/3)** — the one lane where a capability exists and the sentence is
   unambiguous.
3. **Long-horizon checkpoint/resume** — the spool collision (`spool_0_output.json`, a fixed name that
   self-locks on the second run) is the first thing that breaks.
4. **S-3 (103 MB)** — the same spool/derived artifacts are written into the repository tree; the
   content-addressed names help, the location does not.

---

## 6. Reproduce

    python3 execution_guard/swe_capability_matrix_v1.py                # 53 requests
    python3 execution_guard/swe_capability_matrix_v1.py --markdown     # the document's matrix block
    python3 -m unittest canonical.tests.test_a_review_that_ran_is_not_a_compile_gap_v1
    python3 canonical/runtime/verify_brain_unified_model_v1.py
