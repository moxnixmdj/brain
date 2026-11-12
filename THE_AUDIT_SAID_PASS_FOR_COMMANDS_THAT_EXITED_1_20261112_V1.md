# THE AUDIT SAID PASS FOR COMMANDS THAT EXITED 1

**Date:** 2026-11-12 · **Branch:** `arena/fa0079c8-brain` · **Base:** `4325dbfa`
**Authority: NONE.** Every number here is a sandbox measurement, not independent verification.
**Cost:** $0 · **Model dependency:** zero · **truth.achieved: false**

---

## 0. The one-sentence version

The instrument this repository built to answer *"how much of what we call verified can still be
shown true"* reported **495 PASS and 0 FAIL** out of 605 predicates — and **52 of those PASSes
were commands that exited non-zero**, including four that never ran at all because the file they
name does not exist on any machine but the one that wrote the receipt. `PASS` meant *"a process
started"*. It did not mean *"the claim held"*, and it could not: **595 of the 605 predicates
(98.3%) declared no expectation**, so nothing in them could be contradicted.

After the fix: **452 PASS / 58 FAIL / 95 UNRUNNABLE**, of the 452 passes only **10 were actually
checked** and **442 merely started**, and the report is red. The denominator did not move: 605
before, 605 after.

---

## 1. What was wrong, exactly

`canonical/tools/auditability_report_v1.py::run_predicate` executes a declared command and then
checks whatever expectation fields the record happens to carry:

```python
if "expect_exit" in spec and int(proc.returncode) != int(spec["expect_exit"]):
    return {"verdict": "FAIL", ...}
...
return {"verdict": "PASS", "reason": None, "stdout": proc.stdout[:200]}
```

If a record declared no `expect_exit`, no `expect_stdout_contains`, no digest — and 595 of 605
declared none — then **every exit code fell through to PASS**. The exit code was computed, held in
`proc.returncode`, and discarded.

That contradicts the module's own docstring, which promises:

> *"Exit status is 1 when any predicate that was run FAILED, so this can gate a pipeline. It is
> deliberately able to go red: a metric that cannot decrease is not a metric."*

The metric could not decrease. It had one reachable FAIL path and 1.7% of the corpus could reach it.

### The four receipts that never ran anything, recorded as PASS

Reproduced directly, not inferred:

| declared `argv` | exit | stderr | recorded |
|---|---|---|---|
| `python /home/sprite/verify_r2_v33_terminal_projection.py` | **2** | `can't open file '/home/sprite/…': No such file or directory` | **PASS** |
| `python full_ocr_integration.py` | **2** | `can't open file '/home/user/brain/full_ocr_integration.py'` | **PASS** |
| `python real_raster.py` | **2** | `can't open file …` | **PASS** |
| `python independent_invariant.py` | **2** | `can't open file …` | **PASS** |

A receipt in `canonical/verification/` asserts that a verification happened. The named program is
not in this tree and not on any path here. The command exits 2. The audit says PASS.

---

## 2. The measurement, before and after

Both runs are `python3 canonical/tools/auditability_report_v1.py --audit --json` on this tree.
The **before** run was on a bare sandbox; the **after** run on the same sandbox with the
repository's own pinned, hashed substrate installed
(`requirements/software_engineering_kernel_v1.txt` → pytest 8.4.2, tree_sitter, tree_sitter_languages).
The environments differ, and §4 attributes every transition by mechanism rather than by guess.

| | before | after |
|---|---|---|
| predicates run | 605 | **605** (denominator unchanged) |
| PASS | 495 | **452** |
| FAIL | **0** | **58** |
| UNRUNNABLE | 110 | 95 |
| declaring an expectation | 10 (1.7%) | 10 (1.7%) |
| PASS because it was **checked** | not reported | **10** |
| PASS because it only **started** | not reported (all 495) | **442** |
| report `red` | False | **True** |
| tool exit status | 0 | **1** |

FAIL exit codes: **39× exit 1, 18× exit 2, 1× exit 254** (`npm run gate`) — **43 distinct
contradicted commands**. 13 of the 58 carry stderr naming a missing file. 8 of the 58 name another
machine's filesystem outright (`/home/runner/work/brain/brain/…`, `/home/sprite/…`,
`/workspace/scratch/11a40f06e57e/…`, `/work`).

### UNRUNNABLE, before one string and after named by cause

One `BINARY_ABSENT:<argv0>` string covered four different problems with four different fixes, which
is why 110 unrunnable claims were unactionable. Now:

| reason | count | what it means | the fix |
|---|---|---|---|
| `BINARY_ABSENT` | 55 | a bare tool name not on PATH (`qrencode` 28, `zint` 20, `pandoc`, `zbarimg`, `rename`, `py`) | provision the tool |
| `TIMEOUT_BUDGET_30s` | 19 | ran, exceeded the 30 s budget (5 distinct commands; two invoke the **whole** test suite) | raise the budget or narrow the command |
| `UNFILLED_TEMPLATE` | 10 | `argv: ["${input.argv}"]`, `zint -b CODE128 -o ${input.output_path}` | no command was ever declared |
| `DECLARED_PROGRAM_ABSENT` | 8 | a path-shaped program not in the tree (`.venv/bin/python`, `/usr/bin/pdftotext`, `/home/sprite/…`) | the receipt is machine-bound or stale |
| `DECLARED_PROGRAM_NOT_EXECUTABLE` | 3 | present in the tree at mode 644, so the declared direct invocation cannot run | `chmod +x`, or declare an interpreter |

Before the change, 10 of the `UNFILLED_TEMPLATE` cases and 8 of the `DECLARED_PROGRAM_ABSENT` cases
were all reported as `BINARY_ABSENT`, and 30 env-prefixed commands were reported as
`BINARY_ABSENT:PYTHONPATH=.` — the harness failing to read the declaration, not the declaration
being unrunnable.

---

## 3. What changed, and the test that can kill each change

Six behaviours, each pinned by a test in
`canonical/tests/test_auditability_predicate_exit_gate_v1.py` (26 tests). Every one is **two-sided**:
a gate that fails everything is as useless as one that passes everything, so each new behaviour is
pinned next to the behaviour that must *not* change because of it.

| # | change | pinned by | and the opposite arm |
|---|---|---|---|
| 1 | no `expect_exit` declared **and** exit ≠ 0 → `FAIL: EXIT n WITHOUT_EXPECTATION` | `test_a_command_that_exits_non_zero_with_no_expectation_FAILS` | `…_exits_zero_…_still_passes`, `test_a_declared_expect_exit_keeps_a_non_zero_exit_a_pass` |
| 2 | every result carries `exit`, `expectations`, `env_prefix` | `test_the_result_carries_the_exit_code_and_what_was_asserted` | — |
| 3 | PASS split into `pass_checked` / `pass_started` | `test_PASS_is_split_into_checked_and_only_started` | `test_the_split_sums_to_the_PASS_count` |
| 4 | leading `NAME=value` tokens parsed into the child env | `test_an_env_prefixed_command_line_is_run_and_the_env_reaches_the_child` | `…_with_the_wrong_value_FAILS`, `test_an_env_prefix_does_not_resurrect_an_absent_program`, `…_not_leaked_into_the_audit_process` |
| 5 | absence named by cause (template / not-executable / bare-name-not-on-PATH / path-absent / tool-absent) | `test_an_unfilled_template_is_not_reported_as_an_absent_binary` and 4 more | `test_an_absent_binary_is_still_unrunnable_after_the_env_fix`, `test_a_legitimate_argument_is_not_mistaken_for_a_shell_operator` |
| 6 | timeout named with its budget, not as an exception class | `test_a_timeout_is_named_with_its_budget_not_as_a_crash` | — |

**6/6 mutations killed.** Each behaviour was removed or inverted in the source and the suite was
required to notice:

```
KILLED  M1 drop the exit gate (revert to PASS-by-startup)
KILLED  M2 parse the env prefix but never give it to the child
KILLED  M3 count every PASS as a checked PASS
KILLED  M4 call a shell-operator argv a FAIL instead of unrunnable
KILLED  M5 borrow a PASS: run a non-executable declared script with this interpreter
KILLED  M6 leak the exception class instead of naming the budget
```

The suite was green before mutating, which is what makes a kill meaningful — a mutation harness run
against an already-red suite kills every mutant and reports a perfect score for nothing.

Also green: the 18 pre-existing tests in `canonical/tests/test_auditability_report_v1.py`
(**44 passed** together with the 26 new ones), and **101 passed** across the six suites touching
this code. `execution_guard/repo_integrity_guard_v1.py --static-only` → `rules=11 violations=0 PASS`.
`verify_brain_unified_model_v1.py` → **33/33 PASS** after recompiling the content-addressed artifact.

---

## 4. Attribution: which transitions came from the code and which from the sandbox

341 distinct `argv` across the 605 instances. Transitions, same command in both runs:

| transition | distinct commands | caused by |
|---|---|---|
| PASS → PASS | 249 | nothing changed |
| UNRUNNABLE → UNRUNNABLE | 43 | reason now names the cause |
| **PASS → FAIL** | **34** | **the exit gate alone** — none of them declares `expect_exit`, so under the old code no exit value could contradict them |
| **UNRUNNABLE → FAIL** | **9** | env-prefix parsing made them runnable, and they fail |
| UNRUNNABLE → PASS | 6 | env-prefix parsing made them runnable, and they hold |

The 58 FAILs all carry reason `EXIT n WITHOUT_EXPECTATION`, a string that only exists because of
change 1, and none of them declares `expect_exit`. So under the old code, on this same provisioned
sandbox, all 58 would have been PASS. That inference needs no second 13-minute run.

### The 30 env-prefixed claims, instance by instance

All 30 were `UNRUNNABLE` before (reported as an absent binary named `PYTHONPATH=.`). Now:
**6 PASS, 9 FAIL, 15 UNRUNNABLE**. The 15 are five distinct commands that invoke the whole test
suite (`PYTHONPATH=. python3 -m pytest -q canonical/tests …`) and exceed the 30 s budget — honest
unmeasurability, named as such rather than silently dropped from the denominator.

Of the 15 that now produce a verdict, **9 are contradicted (60%)**. The class of claims the harness
could not read was not benign.

---

## 5. The discovery that is not about the harness

`python canonical/tests/test_astra_runtime_model_independence.py` exits **1**, and **five receipts**
cite it as their verification. All five were recorded PASS. All five are now FAIL.

Why it fails, measured:

```
Ran 16 tests — FAILED (failures=1)
AssertionError: "CAPABILITY_ACQUISITION_REQUIRED|BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_BLOCKED"
                does not match "GOAL_COMPILATION_FAILED:ModuleNotFoundError"
ModuleNotFoundError: No module named 'canonical'
```

Invoked as a **script**, `sys.path[0]` is `canonical/tests/`, so the runtime's goal compilation
cannot `import canonical`. The test expects a capability-acquisition `Blocker` and gets an import
error instead. Reproduced on a clean clone of `origin/main` at `d418ab52` — **pre-existing on main,
not caused by this branch**, and it fails for any machine using the declared invocation.

Two things follow, and they are different:

1. **The declaration is broken.** Those five receipts cite a command that has never worked as
   written. The working invocation is `python -m unittest canonical.tests.test_astra_runtime_model_independence`
   or `PYTHONPATH=. python …`. This branch does **not** edit the receipts: a receipt is a record of
   what was claimed, and quietly repairing it would destroy the evidence that it was wrong.
2. **The instrument was hiding it.** Before this change, a broken declaration and a working one
   were indistinguishable — both PASS. That is the whole cost of a verifier that cannot fail: it
   does not merely miss errors, it makes errors and successes the same symbol.

---

## 6. What I deliberately did NOT do

Each of these was considered and killed before implementation, because each would have manufactured
a number that looks like progress.

- **Did not run `python3 <script>` when the declared `script.py` is not executable.** That tests a
  *different command* than the receipt declared — a borrowed PASS. Named `DECLARED_PROGRAM_NOT_EXECUTABLE`
  instead. Mutation M5 inverts this and a test kills it.
- **Did not rewrite a bare filename to `./x`.** `execvp` and a shell both resolve a bare name via
  PATH, never via cwd, so the declared command genuinely does not run. Inventing `./x` would invent
  a command nobody claimed. → `BARE_FILENAME_NOT_ON_PATH`.
- **Did not substitute `python3` for `.venv/bin/python`, `py`, or `python`.** Different interpreter,
  different claim. → `DECLARED_PROGRAM_ABSENT` / `BINARY_ABSENT`.
- **Did not strip shell-script prefixes** (`set -euo pipefail …`). `test_a_shell_script_prefix_is_unrunnable_never_a_pass`
  pins that, and its intent — never fake a PASS — is the same principle as this round. My first
  design proposed stripping them; the pinned test killed the idea before I wrote it.
- **Did not raise the 30 s timeout** to make the 19 timeouts disappear. That would trade an honest
  "unmeasurable in budget" for a 40-minute audit, and the budget is a declared property of the
  instrument, now carried in the reason string.
- **Did not delete or repair any receipt.** 58 FAILs stay 58 FAILs.
- **Did not touch a test to make a number move.** The one failing test in the tree
  (`test_a_seeded_rule_is_usable_not_just_counted`) fails only without the pinned tree-sitter
  substrate; installing the repo's own hashed manifest makes it pass. Documented, not edited.

---

## 7. What this does NOT prove

- **FAIL here means "the declared verification does not hold on this tree", not "the claim is
  false."** The instrument cannot tell a falsified capability from a stale path from an
  unprovisioned sandbox, and it does not pretend to: `exit`, `stdout` and `stderr` travel with every
  verdict so the cause can be triaged instead of guessed. 8 of the 58 name another machine's
  filesystem and are therefore *machine-bound receipts*, not refuted capabilities.
- **10 checked PASSes is not a verified tree.** It is 1.7% of the corpus. The other 442 passes are
  processes that started and exited 0 with nothing asserted about their output. They are not
  worthless — a command that exits 0 is weak evidence — but they are not checks, and the report now
  says so in two columns instead of one sum.
- **The audit is not in CI.** `grep -r auditability .github/workflows/` returns nothing, so going
  red gates no pipeline today. It can gate one; nothing currently asks it to. That is the largest
  remaining gap this round exposes and does not close.
- **Running `--audit` mutates the tree it measures.** Observed, not assumed: one 605-predicate run
  left 4 tracked files modified (`canonical/astra_runtime/evidence/live_audit.json` and `.html`,
  because a declared predicate is `capability_reality_auditor.py --json-out …/live_audit.json`;
  `canonical/astra_runtime/state/ANON_…__goal__CONTROLLER_CHECKPOINT.json`; and
  `canonical/runtime/state/experience_v1.json`) plus 3 new untracked `*_DIAGNOSTIC_*__RESULT.json`
  files. So the instrument is not side-effect-free and a re-run is not idempotent with respect to
  the repository. Pre-existing — those predicates ran and wrote before this branch too — and all of
  it was reverted before committing rather than smuggled into the change. Anyone gating CI on this
  audit has to decide first whether a gate may write to the working tree.
- **A high mutation score is sensitivity, not correctness.** 6/6 killed proves these behaviours are
  asserted. It cannot prove the *rule* is the right rule — a confidently-tested, confidently-wrong
  rule scores 100% under mutation. The rule's justification is §1 and §8, not the kill count.

---

## 8. The owner's question, answered with this round's evidence

> *"Why can't we just give our model the most advanced coding actions and let him experience them
> once, and then he will learn them?"*

Because of what was sitting in this repository's own audit file. The model *did* experience those
actions. It wrote them down. 605 records said "this was verified". When the tree was asked to
re-run its own evidence, **58 of those verifications failed and 95 could not run at all**, and until
today the instrument reported **0 failures** — because the one field that could have disagreed with
a receipt, the exit code of the receipt's own command, was computed and thrown away.

That is the mechanism, in one line: **an experience recorded without a check that can fail is not a
lesson, it is a sentence.** It cannot be lost, so it cannot be corrected, so it is permanent in the
only sense that matters — permanently unexamined. This is not a hypothetical about future
environments; it is what happened to 495 records already in the tree, and the four in §1 named
programs that do not exist.

The 2026 literature has converged on the same object from three directions:

- **"Vacuous pass" is now a named defect with a named cure.** arXiv **2610.20344** (Long-Horizon
  Harness Engineering, 19 frontier models × 3 builds × 328 cases; best **53.05%**, worst 27.44%)
  scores every case over four observable channels — requests, files on disk, **the process exit
  code**, and command output — and adds *positive controls* so that "a test case may pass even
  though the feature under test never ran" is recorded as **FAIL regardless of its own status**.
  That is change 1 above, published three weeks ago.
- **The verifier–deployment gap.** arXiv **2607.24300** (SEAL) measures self-authored scores staying
  near-perfect while deployment truth falls, names **vacuous tests** as a distinct design condition,
  and concludes: *"Reliable self-improvement need not abandon self-verification, but it requires at
  least one deployment-acceptance signal outside the agent's control."* An exit code is exactly such
  a signal: the receipt's author does not get to choose it.
- **Official verifiers are themselves unsound.** arXiv **2611.13336** (Veritas, ByteDance, 9 Nov
  2026) reports an exploit that **solved no task yet scored 100% on SWE-bench Verified, SWE-bench
  Pro and Terminal-Bench** because the verifier ran tests in a container the patch could modify; an
  audit found **26 of 500** SWE-bench Verified tasks still accepted wrong patches; and the curated
  oracle **fails its own tests on 22 of 66 Terminal-Bench tasks** in their environment — the same
  shape as §5. Their artifact contract is the same rule: *"exit code 0 = PASS, non-zero = FAIL."*
- arXiv **2611.05590** (*Verified but Vacuous*, 5 Nov 2026): high verifier acceptance with weak
  specification binding. arXiv **2610.11464**: removing two anchor guards collapses an evolved
  verifier into an **always-pass grader (0.97–1.00)** that still trains skills just as well, so
  *"downstream task score cannot certify a self-evolved verifier."*

And the ceiling, so the answer is not mistaken for pessimism: OSWorld V2 best **21.3%** (Agent S4,
from *evolved interfaces*, 3.8× a fixed one), Terminal-Bench 4.0 **64.85%**, SWE-bench Pro public
**61.5%**, ARC-AGI-3 semi-private **30.2%** — where the arcade jump to 96.42% came from *transferred
donor manuals*, not from one-shot learning.

**So: am I right or wrong?** The bounded claim is real — a lesson can survive teach → bundle →
fresh machine → re-check, and last round made the shipped memory falsifiable (0/5 → 5/5). The
universal claim is not, and this round found the specific reason inside our own tree: **we have been
counting receipts, and the counter could not say no.** Corrected sentence, unchanged from last round
and now measured: *one try is enough exactly when the interface and the verifier already do the
generalising.* Today 1.7% of our evidence has a verifier. That fraction — not the number of
environments — is the limiting factor.

---

## 9. Receipts

| what | where |
|---|---|
| the fix (6 behaviours) | `canonical/tools/auditability_report_v1.py` — `run_predicate`, `_split_env_prefix`, `_program_absence`, `SHELL_OPERATOR_TOKENS`, `ENV_ASSIGNMENT`, `audit` aggregates, `main` printing |
| 26 new two-sided tests | `canonical/tests/test_auditability_predicate_exit_gate_v1.py` |
| mutation harness (6/6 killed) | run of the day; source restored byte-identical afterwards |
| this document | `THE_AUDIT_SAID_PASS_FOR_COMMANDS_THAT_EXITED_1_20261112_V1.md` |
| recompiled artifact | `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` |

Reproduce:

```bash
python3 canonical/tools/auditability_report_v1.py --audit        # exit 1, red, 58 FAIL named
python3 -m pytest -q canonical/tests/test_auditability_predicate_exit_gate_v1.py \
                   canonical/tests/test_auditability_report_v1.py
python3 canonical/runtime/verify_brain_unified_model_v1.py       # TOTAL 33/33 PASS
python3 execution_guard/repo_integrity_guard_v1.py --static-only  # violations=0 PASS
```

---

## 10. Next, ranked by what raises the ceiling

1. **Wire this audit into CI as a gate with a ratcheting floor.** 58 FAIL is a measured baseline;
   the floor belongs at 58 so the number can only fall, and lowering it becomes a deliberate act
   needing a reason. This is the cheapest move that converts a measurement into a constraint. It
   needs a decision first: gate on *new* FAILs, or accept a red main until the 58 are triaged.
2. **Triage the 58 into three buckets** — refuted claim / machine-bound receipt / unprovisioned
   sandbox — using the `exit` and `stderr` now carried on each. The 8 machine-bound ones are a
   schema defect worth its own round: a receipt that can only be re-run on the machine that wrote it
   is history with extra steps.
3. **Fix the five declarations in §5** in a *new* record that supersedes the old one, never by
   editing the old one, so the evidence that they were wrong survives.
4. **Give the 442 started-but-unchecked passes an expectation.** Each is one line: `expect_exit: 0`
   at minimum, a stdout needle where the claim has one. That moves `pass_checked` from 10 toward 452
   and is the single largest checkability gain available without writing new predicates.
5. Then, and only then, the 29 typed-but-unchecked capabilities from the census — two-sided, per
   last round's self-witness design.
