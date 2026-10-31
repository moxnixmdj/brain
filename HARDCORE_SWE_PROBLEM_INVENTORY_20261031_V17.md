# Hardcore software-engineering problem inventory — V17

Measured 2026-10-31 on `8679d55` (branch `arena/d64f2e25-brain`).
Supersedes V13–V16. V16 was right about the mechanism and **wrong about the order**, and this
document measures why. Document-format, image, chart and office rows are excluded throughout.

---

## §0 The answer in one paragraph

Of 49 advanced software requests the machine serves **2**. The 47 refusals split four ways:
**22** are claimed by five magnet rows and every one of them refuses, **9** have no row at all,
**16** reach some other row and refuse for a specific reason, and **2** are served correctly.
The obvious fix — delete the magnets — was measured and **makes the machine worse**: with the
five removed, `python.source.definition_count.v1` rises to take 9 requests and answers
"profile the hot spot", "release the GIL" and "fuzz this function" with `PASS`. The magnets are
currently acting as an accidental honesty layer, because a wrong row that fails is better than a
wrong row that succeeds. So the first change is not containment, it is an **effect gate**: a
served answer must name the effect the sentence stated. Only after that does containment pay, and
only after both does the chain wiring reach the 13 requests it can reach. Everything above is
measured in this document, not projected.

---

## §1 Measurements on `8679d55`

| instrument | result |
|---|---|
| `swe_capability_matrix_v1.py` (54 ordinary cases, per-case oracle) | **19 REAL / 0 FALSE / 35 REFUSED / 0 DAMAGED** |
| matrix latency | median **78 ms**, p90 479 ms, max 593 ms |
| `swe_advanced_probe_v1.py` (49 advanced requests, 11 axes) | **2 served / 47 refused** |
| write/imperative requests | 39 of 49 — **0 of 39 served** |
| registry anatomy | 440 rows = 293 `.auto.v1` law rows + 147 real; **84** reachable by the typed family resolver |

The two served requests are request 29 (`python.repository.acceptance.measure.v1` for "run the
test suite and tell me which tests fail") and request 40
(`python.review.diff_security_gate.v1` for "review for security issues"). Both are faithful: a
stated-effect check over the served set finds **0 wrong rows served** in the current state.

---

## §2 Every one of the 49 requests, classified

| class | count | what it means |
|---|---|---|
| **SERVED** | **2** | pass, and the row's declared effect matches the sentence |
| **MAGNET_CLAIMED** | **22** | one of five rows took the sentence and then refused it |
| **OTHER_ROW_REFUSED** | **16** | some other row took it and refused for a specific named reason |
| **NO_ROW** | **9** | nothing reachable could produce an executable contract at all |

Magnet breakdown — **22 claims, 22 refusals, 0 successes**:

| row | claims | what actually refused it |
|---|---|---|
| `python.source.dead_code.v1` | 6 | `SOURCE_ROOT_MISSING` ×4 |
| `software.repair.choreograph.crossfile.v1` | 5 | `CHOREOGRAPHY_REPAIR_UNRESOLVED` ×2, `NO_PYTHON_SOURCE_FILES`, +2 admission refusals |
| `python.refactor.inline_helper.v1` | 4 | `HELPER_NAME_SURVIVED_IN` ×3 |
| `git.history.bisect_regression.v1` | 4 | `NAMED_TEST_NOT_IN_GIT_HISTORY` ×3 |
| `python.tests.mutation_score.v1` | 3 | `NO_MUTANTS_GENERATED`, `INPUT_FORMAT_MISMATCH` |

**Every one of the 14 execution failures in the census is a magnet row.** There is no
non-magnet execution failure in the set. That is the sharpest number here: the machine does not
have a broken-engine problem, it has a "the wrong engine picks up the phone" problem.

The 16 other refusals, by cause:

| cause | n | requests |
|---|---|---|
| admission refused the stated payload | 5 | 5 `INPUT_FORMAT_MISMATCH`, 24/25 `R11_STATED_PAYLOAD_SLOT_MISMATCH`, 35/42 `R3_WEAK_EVIDENCE` |
| answered, but not the stated effect | 3 | 5 symbols index, 26 patch search, 39 secret scan |
| capability refused on its own contract | 3 | 10 `WORKTREE_NOT_DIRECTORY`, 27 `NO_TESTS_DISCOVERED`, 38 `REGION_INVALID` |
| a read-only op with no observable effect | 2 | 45, 46 `NO_OBSERVED_EFFECT` (no cherry-pick/changelog op exists) |
| tool ran and reported failure | 1 | 30 `TOOL_REPORTED_NON_SUCCESS` |
| answered without the stated answer | 1 | 31 `STATED_ANSWER_NOT_PROVIDED` |
| process exited | 1 | 48 `CAPABILITY_EXITED_PROCESS:1` |

The 9 with no row: adding a method in Go, adding a method in Java, adding a dependency in
`pyproject.toml`, creating a `pyproject.toml` with a console script, editing a CI workflow,
adding a thread pool, auditing dependency vulnerabilities, writing an ADR, and splitting a
package. Go, Java, packaging, dependencies, CI-YAML and design are all absent as **rows**.

---

## §3 The experiment that inverted the order

I removed the five magnets from the registry *in memory* and re-ran the census. The first attempt
did not take (the typed path loads through `live_integrated_brain_v1`, not the door), and the
patch-check printed 440 rows — so it was re-run with the seam verified, 435 rows:

| | magnets present | magnets removed |
|---|---|---|
| served | 2 / 49 | **6 / 49** |
| of those served, faithful to the stated effect | 2 | **2** |
| of those served, **wrong row** | 0 | **4** |

The four new "successes" were all `python.source.definition_count.v1`:

* "Profile `util.py` and tell me which function is the hot spot" → `definition_count` → PASS
* "Optimise the function total; it is too slow" → `definition_count` → PASS
* "Make the function total release the GIL" → `definition_count` → PASS
* "Fuzz the function add for integer overflow" → `definition_count` → PASS

A function counter answering a profiling question, a concurrency question and a fuzzing question,
and reporting success. **Containment alone converts 22 honest refusals into up to 4 false
answers.** The blocking defect is that the door has no notion of *"the row I selected must state
the effect the sentence names"* — `implementation_effect_error` exists and is applied on the
composed path and on implementation imperatives, not to every served answer.

Order, corrected:

1. **effect gate** — a served answer must name the stated effect (converts wrong selections into
   honest refusals);
2. **magnet containment** — only now is it safe, and it removes 22 of 47 refusals from the
   misleading column;
3. **chain wiring** — `capability_composer_v1.plan()` and `composer_route_v1.execute_chain()`
   already exist and every `requires` is satisfiable, so this reaches the 13 chain-bound requests;
4. **derivation** — 22 of 85 declared slots have a producer;
5. **new domains** — the 9 no-row requests.

---

## §4 Landed this session

**#6479 — an empty diff is not an answer.** `git.repository.operate.v1` answered "show the diff
of `<file>`" with `git diff HEAD -- <target>`, which is empty for an untracked file, and reported
`PASS` over `row_count: 0`. It was the matrix's only FALSE. Fixed with git's own
`--no-index -- /dev/null` new-file patch plus a second independent plumbing check; 19 REAL /
0 FALSE / 0 DAMAGED, adapter suite 18/18.

**A structured refusal must carry its reason.** `python.source.crossfile_edit.choreograph.v1` and
`python.symbol.resolve` printed `{error, error_kind, message}` to stdout and then raised an
**empty** `SystemExit(1)`. A CLI reader saw the JSON; the in-process door parses `str(exc)`, got
the string `1`, and could only report `CAPABILITY_EXITED_PROCESS:1`. The reason now travels on
the exception in the shape the door already parses, so probe 48 reports
`CAPABILITY_REFUSED_EDIT_PLAN_INPUT_INVALID`. The stdout write is kept; the exception type is
unchanged.

---

## §5 Still open, with the measurement that sizes it

* **No effect gate on served answers** — the gate that would have caught all four
  `definition_count` answers, and the class the matrix caught once by accident.
* **Magnets** — 22 of 49 claims, 0 successes, and unsafe to remove until the gate exists.
* **9 requests with no row** — Go, Java, packaging, dependencies, CI-YAML, threading, ADR.
* **Derivation** — 22 of 85 declared slots have a producer; `symbol`, `to_module`, `edits`,
  `index_path`, `task_text` and the budget knobs still have none.
* **`generate.scaffold`** defaults its write root to a repo-root `generated_tests/<dir>` that its
  registry row never declares as an argument.
* **Substrate identity** is proved from wheel metadata, so a vendored deployment refuses.
* **Two reds that predate this branch**, verified by stashing: the registry-args drift assertion
  in `test_git_sentence_routing_v1` and `test_the_entry_is_a_verified_bound_capability`
  (a `provides` list mismatch). `test_crossfile_multiline_imports_v1` errors on `import pytest`,
  which is not installed here.

---

## §6 The ladder

| level | position |
|---|---|
| L0 report on a file it is given | **reached** — 7 engines, 0.5–80 ms |
| L1 edit one file | **partly** — 8 standalone refactor rows, 0 census hits |
| L2 edit several files coherently | **not reached** — planner exists, `edits_path` never binds |
| L3 repair and prove it | **not reached** — verifier chain-bound |
| L4 issue → patch → test → PR | **not reached** — three producers missing |
| L5 self-extend | **not attempted** |

Authority: NONE. One tree, one machine, one commit.
