# What stands between this machine and being the most advanced software engineer — V5

Measured 2026-10-29 on `arena/47739ce8-brain` @ `0936404`, branched from `main` `e2d7981`.
Authority: **NONE**. Sandbox measurement, not independent verification. Credit: **0**.
Producer-cognition model dependency: **0**. Incremental spend: **$0**.
Scope: hardcore software engineering. PDF / DOCX / image / archive work is excluded *except* where it
appears as the **wrong-domain destination** of an SWE request — which turns out to be the main event.

V5 supersedes V4. Eight problems closed since V3; **two new fabrications found by probing** (both
closed in the same round, both now cases in the harness); and one **structural** finding that explains
most of the remaining refusals and is the thing to fix next.

---

## 0. The answer in one paragraph

The machine's verified core is real: 419 registry rows of which **125 are routable**, and the ones that
answer do so with evidence (a re-run command, a real `unittest` exit code, a caller map that covers
22/22 oracle callers, a formatter checked by the formatter). What is missing is **reach and judgment**.
The router has **no "none of these"**: it ranks 125 rows and always returns a top-1, so the only thing
standing between a wrong pick and a wrong answer is whether a downstream gate happens to apply. Measured
on twenty *advanced* requests: 18 refused, **7 refused while naming a capability from an unrelated
family**, and **2 PASSED on an unrelated capability** (CI setup answered by a repository measurement;
a bisect answered by a test selection). And the advanced capabilities that do exist — dynamic-dataflow
fault localization, mutation/coverage/security/perf gates, CEGIS patch synthesis, a Hypothesis oracle —
are **never reached**, because their inputs (`diff_path`, `anchor_path`) are never derived from a
sentence. That is the difference between "419 capabilities" and "an engineer".

---

## 1. Closed since V3, and the mechanism that closed each

| # | problem | closed by | before → after |
|---|---|---|---|
| S-1 | a **parse** accepted as the **answer** at directory scale | two rows in the door's existing `_STATED_EFFECTS`, applied **before** execution | `"Find every caller of X in canonical/tests"`: 8.7 s, PASS, **0 / 22** callers → **6.4 s, 22 / 22** |
| S-1b | dead code had no answer and passed anyway | same table | PASS over `definition_count` → `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` (63 ms) |
| S-2 | one question cost **five minutes** | `_name_indexes()`: a per-path question was recomputed per (row, import) — 54,722,085 calls | 324,727 → **21,756 ms** cold, 313,732 → **5,896 ms** warm |
| S-5 | **293 inventory rows were routable** and a script's exit code was certified as the answer | `is_verified_entry()` + "addressable by name, never by words" | `"Show the last 3 lines of <f>"` ran an unrelated `*_verify_v1.py` → real `tail -n 3` |
| S-5b | `"Who last changed line 2 of <f>?"` answered by `tail -n 1 <f>`, certified exact | `_PROVENANCE_RE` + one row | PASS (fabricated) → refusal in 63 ms |
| G-1a | `git` executed correctly and was then refused by the inspector | `_READ_ONLY_SUBCOMMANDS` — the mechanism the file already uses for **flags**, one level deeper | `git diff` / `git log` → **PASS**, re-run compared |
| S-2b | every new task id rebuilt a 2,256-file index | derived index keyed by **scope**, not output name | 21,404 ms cold *every time* → **7,269 ms** |
| S-3b | a **composed change** reported as *nothing happening* | the composed branch snapshots the world **before** the chain | `delete_file` refused → REAL; honesty lane 0/5 → 1/5 |
| F-1a | `format` had **0** rows | `_PROSE_COMMAND` row + `_post_ruff_format`, verified by `ruff format --check` | `NO_OBSERVED_EFFECT` → **PASS**, file rewritten and verified |
| **S-6** | **"Set up CI to run the tests in `<pkg>`" PASSED**, answered by `python.repository.acceptance.measure.v1` measuring the tree it stood in (`test_count 0`, `test_returncode 1`), no workflow written | one `_STATED_EFFECTS` row | PASS → `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` (99 ms) |
| **S-7** | **"Bisect the regression that broke `<test>`" PASSED**, answered by test *selection* (the test file treated as the change), no commit, no traversal | one `_STATED_EFFECTS` row | PASS → refusal (84 ms) |

Both S-6 and S-7 are now **cases in the harness** with typed oracles, and both were re-measured with
the fix reverted: `pass=True`, oracle `False`. They were invisible because no case asked for a
**deliverable the repo does not have** or a **fact about history**.

---

## 2. The structural finding: the router has no "none of these"

Twenty advanced requests, one fresh tree, filesystem as the oracle:

| request | verdict | capability it was handed to |
|---|---|---|
| `Find the bug in <f> and explain the root cause` | refused (composed chain unverified) | — |
| `Which function is responsible for the failing test <t>?` | refused `R3_WEAK_EVIDENCE` | `python.software.request.semantic_behavior.compile.v1` |
| `Refactor add into smaller functions` | refused `PROMISED_SOURCE_CHANGE_NOT_APPLIED` | `python.source.audit.ast` |
| `Move the function mul from A to B` | refused `NAMED_INPUT_REMOVED` | — |
| `Add property-based tests for add` | refused `R3_WEAK_EVIDENCE` | `…semantic_behavior.compile.v1` |
| `Measure the mutation score of <t>` | refused `R3_WEAK_EVIDENCE` | `python.patch.search.test_guided.ast.v1` |
| `Profile add and report the slowest line` | refused `R3_WEAK_EVIDENCE` | `…semantic_behavior.compile.v1` |
| `Report the cyclomatic complexity of <f>` | refused (compilation gap) | *(earlier: a **Pandoc PDF converter**)* |
| `Add a pyproject.toml declaring the dependencies` | refused (composed step raised) | — |
| `Create a Dockerfile for <pkg>` | refused (compilation gap) | — |
| **`Set up CI to run the tests in <pkg>`** | **PASS — fabricated (S-6)** | `python.repository.acceptance.measure.v1` |
| **`Bisect the regression that broke <t>`** | **PASS — fabricated (S-7)** | `code.impact.tree_sitter.testselect.v1` |
| `Add retry with exponential backoff to add` | refused `R3_WEAK_EVIDENCE` | `…semantic_behavior.compile.v1` |
| `Add structured logging to every function` | refused `R3_WEAK_EVIDENCE` | `structured.decision_evidence.locate.stdlib` |
| `Write a docstring for add` | refused `PROMISED_ARTIFACT_MISSING` | — |
| `Sort the imports in <f>` | refused `PROMISED_ARTIFACT_MISSING` | — |
| `Review the diff for security issues` | refused `R3_WEAK_EVIDENCE` | `software.review.gate.composer.v1` |
| `Explain the architecture of <pkg>` | refused (composed step raised) | — |
| `Generate tests from the docstrings in <f>` | refused `CAPABILITY_EXITED_PROCESS` | — |
| `Add a feature flag to <f>, add a test, run the suite and report` | refused `R3_WEAK_EVIDENCE` | `test.slice.never_miss.v1` |

**7 of the 18 refusals name a capability from an unrelated family, and 2 passed on one.** The refusal
message (`R3_WEAK_EVIDENCE`) is the gate noticing after the fact that a 419-row ranker returned a
top-1 it should not have. This is why the same sentence can route differently on an incidental token:
`Which tests are affected if I change <f>?` passes for three scopes and is refused
(`test.slice.never_miss.v1`) for a fourth whose path contains `tmp/`.

**What it needs** is a *coverage* answer before a *ranking* answer: does any routable row declare the
effect the sentence states? That is the declaration test the answer gate already implements
(`_STATED_EFFECTS`) — applied at **routing** time, it turns "best of 125" into "these 3 declare X, or
nothing here can do X". The alternative — 419 rows each with hand-written keywords — is the failure
mode this whole list is made of.

---

## 3. The advanced capabilities that exist and are never reached

The most capable code in this repository is unreachable. From the registry (125 routable rows):

| family | rows | what happens at the door |
|---|---|---|
| fault localization (`python.fault.localize.dynamic.dataflow.v1`, `…provenance.fusion.v1`, interprocedural value) | **7** | `"Localize the fault in <f> with the tests in <t>"` → **`software.hardcore.kernel.orchestrate.v1`**, `R3_WEAK_EVIDENCE`. Named directly by id it raises. |
| mutation / coverage / security / perf gates (`python.review.diff_*_gate.v1`) | 4 | named by id: `FAIL__RAW_GOAL_COMPILATION_GAP` — `diff_path:0_type_compatible_existing_files_named`, `anchor_path:0_...` |
| CEGIS patch synthesis (`software.patch.synthesize.cegis.z3.v1`) | 1 | named by id: composed step **raised** |
| Hypothesis property oracle (`evidence.oracle.hypothesis_property.v1`) | 1 | named by id: composed step **raised** |
| cross-file edit choreography | 1 | named by id: `EDIT_PLAN_INPUT_INVALID: output already exists: spool_0_output.json` |

Two distinct defects, both mechanical:

1. **`diff_path` / `anchor_path` are never derived.** `3fb8e01` built file → change set for the
   review-of-a-file case and it works there; these four rows still ask for a *named* file of the right
   type and get `0_type_compatible_existing_files_named`. The same derivation, applied to
   `anchor_path`, is a review gate that runs.
2. **The shared spool output collides between runs.** A capability that ran once writes
   `canonical/astra_runtime/tmp/spool_0_output.json`; the next run refuses `EDIT_PLAN_INPUT_INVALID`
   because that file already exists. An artifact path derived from a fixed name is a lock the machine
   sets on itself.

Also: `"Generate tests from the docstrings in <f>"` ends in `FAIL_CLOSED__CAPABILITY_EXITED_PROCESS` —
a capability that `raise SystemExit` is reported as a closed failure (correct) but with no reason the
caller can act on (T-2).

---

## 4. What does not exist at all

Census over the **125 routable** rows (id + `provides` + `keywords`):

| verb / noun | rows | verb / noun | rows |
|---|---|---|---|
| `docker` | **0** | `docstring` | **0** |
| `ci` / `continuous integration` / `workflow` | **0** | `complexity` / `cyclomatic` | **0** |
| `lockfile` | **0** | `bisect` | **0** |
| `flaky` | **0** | `snapshot` | **0** |
| `memory` / `learn` | **0** | `checkpoint` / `resume` | **0** |
| `parallel` / `concurrency` | **0** | `cache` | **0** |
| `profile` | 1 (a diff *perf gate*) | `mutation` | 4 (gates, unreachable) |
| `dependenc` | 2 (neither is dependency management) | `architect` | 1 (a CEGIS row) |

The absence of `checkpoint` / `resume` / `memory` / `learn` is the one that matters most for "most
advanced": there is **no long-horizon capability**. `flywheel_v1` memory exists and is consulted
(`_recall_for`), but 0 rows declare it and nothing in the solve path is conditioned on it. An engineer
that cannot resume, checkpoint or learn from a failed attempt is a function call, not an engineer.

---

## 5. Cost, still

```
one symbol-index request over canonical/runtime   103.36 MB artifact
"Which tests are affected if I change <f>?"       cold 30,485 ms · warm 7,269 ms  (was 324,727)
"Find every caller of <f> in canonical/tests"      6,400 ms
canonical/astra_runtime/tmp after one session     488 MB
```

7 seconds for a question about one file is not "insanely fast" when the tree is already indexed. The
remaining cost is: reading a 103 MB JSON, rebuilding the reverse map per query, and a Python-level BFS
over 916,734 references. The fix is representation (S-3), not another index: definition rows + a
per-file identifier multiset, memory-mapped or in SQLite, and the reverse map persisted as the column
it is.

---

## 6. Verification infrastructure — the referee is red

Ten SWE/front-door suites: **31 red** with these changes, 54 red on the baseline (the snapshot-order
fix closed 23). A green referee is a precondition for everything above being trustworthy, and today a
change can only be judged "no new red" — which is exactly the tolerance this repository forbids
widening.

Three blob-substring oracles have been found and fixed so far (`unused_helper`, `"bisect" in blob`,
`"author" in blob`). Each was written in good faith and each certified a fabrication. The class
recurs because a string search over a run's own report is the natural way to write a quick check; the
harness now has typed helpers (`_artifacts`, `_fields`, `_typed`, `_number`) and the two newest cases
read the **artifact** only.

The model verifier (33/33) fails whenever a capability's source changes, because it records source
hashes — a recompile is mandatory after any adapter edit. That is correct, and it is also a step a
human will forget.

---

## 7. Scoreboard

49 requests, fresh 8-file trees, typed oracles, filesystem and a real runner as the only judges:

```
REAL 10 · FALSE 1 · REFUSED 38 · DAMAGED 0 · median 71 ms · p90 569 ms
repair 2/7  refactor 1/7  tests 0/3  analysis 3/8
toolchain 3/7  git 0/5  feature 0/7  honesty 1/5
```

The one remaining FALSE is `repair_with_report` (H-1): the repair family's own oracle demands
untouched source + an applicable patch while the sentence asks for the test to pass. Two oracles in
this repository disagree; one has to change. **An owner decision, not code.**

---

## 8. The order I would work in

1. **Routing coverage before ranking** (§2). One function: for the sentence's stated effect, which
   routable rows declare it? If the top-1 does not, say so instead of letting a gate find out after
   execution. This is the single change that converts 18 refusals-with-a-wrong-name into either the
   right capability or an honest "nothing here does X", and it is the same declaration data the answer
   gate already uses.
2. **`diff_path` / `anchor_path` derivation** (§3.1). It unlocks four of the most advanced rows in the
   tree — mutation, coverage, security and performance gates — from sentences an engineer actually
   writes. `3fb8e01` is the template.
3. **Fault localization reachable** (§3). Seven rows, dynamic dataflow, sharper than anything else
   here for "why is this test failing", currently shadowed by a generic orchestrator.
4. **T-2, the tests lane (0/3).** `write_unit_test` promises a file and never writes it. It is the most
   requested verb in software engineering.
5. **Long-horizon**: checkpoint / resume / move memory into the solve path (§4). Composition fires for
   commands, not for plans; `"add a flag, test it, run the suite, report"` is refused today.
6. **S-3 representation** (103 MB, 7 s warm) and the **spool collision** (§3.2).
7. **The referee** (§6): 31 red suites, and no more blob oracles.
8. **H-1** — needs an owner decision.

---

## 9. Reproduce

```
python3 execution_guard/swe_capability_matrix_v1.py --markdown     # 49 requests, 8-file trees
python3 -m pytest -q canonical/tests/test_a_deliverable_is_not_a_measurement_v1.py
python3 -m pytest -q canonical/tests/test_a_pending_inventory_row_is_not_an_answer_v1.py
python3 -m pytest -q canonical/tests/test_a_formatter_is_verified_by_its_own_check_v1.py
python3 -m pytest -q canonical/tests/test_a_program_is_judged_by_its_subcommand_v1.py
```
