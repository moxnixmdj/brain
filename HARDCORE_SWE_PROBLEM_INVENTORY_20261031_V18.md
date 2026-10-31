# Hardcore software-engineering problem inventory — V18

Measured 2026-10-31 on `75ea4ec` (branch `arena/42d647fc-brain`).
Supersedes V17. V17 named the next change and this document records it landing.

---

## §0 The answer in one paragraph

The 49-request advanced census serves **2**, and the 47 refusals are now classified with one
correction to V17: the magnets are not the first thing to fix, because deleting them makes the
machine answer wrongly. That experiment was re-run on this commit and reproduced exactly —
with the five magnet rows removed, served goes 2 → 6 and **four of the six are wrong**, all
`python.source.definition_count.v1`, answering *profile the hot spot*, *optimise; it is too
slow*, *release the GIL* and *fuzz this function* with PASS. The gate that stops this already
existed as a data table (`_STATED_EFFECTS`, 14 classes, consumed by `stated_answer_errors`);
profiling, optimisation, concurrency and fuzzing simply were not in it. They are now, and the
same experiment scores **2 served / 0 wrong**, with all four sentences refused by name. That is
the prerequisite V17 said it was: containment is now safe to attempt.

---

## §1 Measurements on `75ea4ec`

| instrument | before | after |
|---|---|---|
| advanced census (49 requests) | 2 served / 47 refused | **2 served / 47 refused** (unchanged by design) |
| census with magnets removed | 6 served, **4 wrong** | **2 served, 0 wrong** |
| capability matrix (54 cases) | 19 REAL / 0 FALSE / 0 DAMAGED | **19 REAL / 0 FALSE / 0 DAMAGED** |
| matrix latency | median 62 ms, p90 479 ms | median **68 ms**, p90 **387 ms**, max 505 ms |
| new pinning suite | — | **10/10** |

The four sentences, before and after (magnet rows removed so the counter is reachable):

| request | before | after |
|---|---|---|
| *Profile `<f>` and tell me which function is the hot spot* | PASS | `STATED_PROFILE_NOT_TAKEN_BY_CAPABILITY` |
| *Optimise the function total in `<f>`; it is too slow* | PASS | `STATED_OPTIMISATION_NOT_PERFORMED_BY_CAPABILITY` |
| *Make the function total in `<f>` release the GIL* | PASS | `STATED_CONCURRENCY_NOT_ADDRESSED_BY_CAPABILITY` |
| *Fuzz the function add in `<f>` for integer overflow* | PASS | `STATED_FUZZ_OR_PROPERTY_RUN_NOT_PERFORMED_BY_CAPABILITY` |

---

## §2 What the four rows say, and why each is a distinct effect

A profile is a **measurement over time** — `cProfile`, `py-spy`, `scalene`, a named hotspot.
An optimisation is a **change** — the rows that really perform one declare the transformation
(`performance.quadratic.linearithmic.optimize`), and a row that only *describes* performance
(a diff perf gate) is deliberately not matched, which is why the matrix case
*"Run a performance review of `<f>`"* still reaches the perf gate and stays REAL.
Concurrency is a statement about **concurrent execution** — GIL, thread pool, lock, race.
Fuzzing is **execution under generated inputs**, which the hypothesis/property row already
declares.

Each row is `(asked, supplied, code)`, exactly the shape the other 14 use, so nothing new was
built: the same table the answer gate and the declaration shortlist both read.

---

## §3 The neighbours the gate must not touch (pinned)

| sentence | row | expected |
|---|---|---|
| "Run a performance review of `<f>`" | `python.review.diff_perf_gate.v1` | **admitted** (matrix case stays REAL) |
| "Measure the mutation score of `<f>`" | `python.tests.mutation_score.v1` | **admitted** |
| "Which function in `<pkg>` is never called?" | `python.source.dead_code.v1` | **admitted** |
| "How many functions are defined in `<f>`?" | `python.source.dead_code.v1` | **admitted** |

And a capability that really does the work would be admitted by its own declaration — a
hypothetical profiler, threading change and fuzzer each pass the gate in the test. A refusal
that cannot be distinguished from a break is not worth having.

---

## §4 Still open, in the order the measurements now support

1. **Magnet containment** — 22 of 49 claims, 0 successes. Now *safe*, because the effect gate
   converts the wrong answers that containment would expose into named refusals. The honest
   target is not "delete the five rows" but "a row may not claim a sentence whose effect it does
   not declare".
2. **Chain wiring** — `capability_composer_v1.plan()` and `composer_route_v1.execute_chain()`
   exist and every `requires` in the 84 rows is satisfiable; 13 requests wait on the call.
3. **Derivation** — 22 of 85 declared slots have a producer; `symbol`, `to_module`, `edits`,
   `index_path`, `task_text` and the budget knobs have none.
4. **Nine requests with no row** — Go method, Java method, dependency add, pyproject creation,
   CI-YAML edit, thread pool, dependency audit, ADR, package split.
5. **`generate.scaffold`** still defaults its write root to a repo-root `generated_tests/<dir>`
   that its registry row never declares.
6. **Substrate identity** is proved from wheel metadata, so a vendored deployment refuses.

---

## §5 Pre-existing reds (verified by stashing this change)

* `test_a_deliverable_is_not_a_measurement_v1` — 2 failures (`test_setting_up_ci...`,
  `test_a_bisect_is_not_a_test_selection`), identical with and without this change.
* `test_git_sentence_routing_v1::test_the_registry_row_declares_the_operation_contract` —
  registry args drifted from the adapter's.
* `test_python_crossfile_edit_choreograph_v1::test_the_entry_is_a_verified_bound_capability` —
  a `provides` list mismatch.
* `test_crossfile_multiline_imports_v1` — errors on `import pytest`, which is not installed.

Authority: NONE.
