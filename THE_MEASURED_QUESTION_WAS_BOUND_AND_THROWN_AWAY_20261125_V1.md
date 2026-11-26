# The measured question was bound and thrown away

**Date:** 2026-11-25 · **Base:** `c4f529eb` · **Branch:** `arena/90080b80-brain`
**Authority:** NONE (`MEASUREMENT_NOT_RECEIPT`). No capability registered, no family flipped,
no weight touched, `truth.achieved` unchanged, no model call, no network call, $0.

## 1. What this round measured, and why it matters

The system's only working generalization lane answered **sentences it had not understood** and
reported `PASS`. Measured on the untouched tree at `c4f529eb`, with the file
`alpha\nbeta\nalpha\ngamma\nbeta\n` (5 lines, 3 distinct, 2 repeated):

```
how many unique lines in items.txt          PASS  5     truth 3
count the blank lines in items.txt          PASS  5     truth 0
count the duplicate lines in items.txt      PASS  5     truth 2
count the top-level functions in x.py       PASS  4     truth 3   (the nested method was counted)
count the lines longer than 4 characters    PASS  28    truth 2   (it counted CHARACTERS)
list the lines in items.txt                 PASS  [...] the noun came from the FILE EXTENSION
```

Six sentences, six wrong answers, six `PASS` verdicts, and a causal-verification receipt attached
to each one claiming the program had been probed on interventions and found correct.

**This defect was already known in the repository, in the same words.** The CLI lane carries
`TestTheLinesThatRepeatAreNotAnsweredWithTheLinesThatDoNot`, whose docstring states that
"How many unique lines are in the file X?" must be *refused*, because `wc -l` answers it with the
total. That was written for one door. The neurosymbolic lane one tier over was doing the
forbidden thing — and `test_acquisition_to_execution_engine_v1::test_phase3...` was **red**
because of it, expecting `8` and being served `16`.

That is the shape of the failure this round names: **not a missing capability, but a verdict that
does not depend on the words it claims to have read.** It is the same failure family as the
repository's existing `FAIL_CLOSED__QUALIFIER_UNPARSED` gate, which already refused an
argument-count marker it could not ground. The gate existed. It covered one word.

## 2. Why the verifier could not catch it

The engine probes a synthesized program on a fixture before trusting it. The fixture was the
problem: it had no repeated line and no blank line, so **`distinct` and `blank` were no-ops on the
very source used to verify them.** The probe ran, both counts agreed, and the program passed — with
the modifier absent. A verifier whose fixture cannot distinguish "the filter ran" from "the filter
was dropped" certifies nothing about the filter.

This is the single most reusable lesson of the round, and it generalises past this engine:

> A probe is only as strong as the intervention that separates the hypothesis from its neighbour.

## 3. The repair

A **modifier ledger**. Every phrase that changes *which* items are meant must either be **grounded**
(a concrete predicate, executed, and verified against a fixture on which it is *visible*), or
**refused** with a reason that names it. Silence is not an exit.

The ledger is 12 keys, and each row is a concrete predicate with a refusal string, not a synonym
entry: `distinct`, `duplicate`, `blank`, `non_empty`, `longer_than`, `shorter_than`, `numbered`,
`comment`, `top_level`, `nested`, `has_call`, `has_parameter`. Grounded this round for the text
domain: `distinct`, `blank`, `non_empty`, `longer_than`, `shorter_than`. Everything else refuses.

Three supporting changes, each closing a distinct way the word could evaporate:

1. **Selection-time effect, not a label.** `FILTER_<KEY>` is a step in the plan the caller can read,
   and `_run_plan` applies it to the selection.
2. **The measurement unit is not the concept.** "longer than 4 characters" had made `character` the
   concept of a question about *lines*. Units of measure are consumed by the threshold, in the same
   span-blanking pass that stops a filename ("empty.py") from being read as the word *empty*, and a
   quoted payload ("write the word empty") from being read as a filter.
3. **Two derivations must agree.** The probes run on a fixture; a second, independent derivation
   over the caller's **real bytes** must produce the same count, or the run fails closed. One
   derivation is a claim; two that must agree are evidence.

Two new fail-closed statuses, both exercised by tests:

```
FAIL_CLOSED__UNBOUND_QUALIFIER              a word in the sentence bound to no predicate
FAIL_CLOSED__OPERATION_CONCEPT_INCOHERENT   the verb cannot answer the noun
FAIL_CLOSED__SECOND_DERIVATION_DISAGREES    the plan and the raw-bytes count differ
```

## 4. Honest before/after, same files, same machine

Two attempts were needed, and the first one was wrong in a way worth recording.

### 4a. The measurement that was wrong, and why

First attempt: 177 files that touch the front door, run against `c4f529eb` in a git worktree and
against this branch, `-n 2`, same interpreter. Before: **480 failed / 1967 passed**. After:
**487 failed / 1951 passed** — nine test ids newly failing. I treated them as regressions and went
looking.

They were not the code. The virtualenv I ran everything from was **inside the repository**
(`.venv-honest/`). One of those nine was
`test_jit_knowledge_v1::test_a_goal_that_compiles_does_not_go_looking`, whose goal
("Verify a tar.gz archive against its manifest") is served by a bound capability that checks the
archive's member set against a **manifest of this repository's own file listing**. Adding a
directory to the tree changed that listing, so the capability correctly refused with
`ARCHIVE_MEMBER_SET_MISMATCH` — on a tree I had perturbed. With the virtualenv moved outside the
repository, that goal returns `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`
again, exactly as on the before tree.

That is this project's own rule biting the measurement: **tests run against the tree as it is** —
so a harness artefact placed in the tree is part of the experiment. The fix is not to relax the
check; it is to keep the harness out of the tree.

### 4b. The measurement that stands

With `/home/user/venv-honest` outside the repository, the two files that the bad run accused:

| file | `c4f529eb` | this branch |
|---|---|---|
| `test_jit_knowledge_v1.py` | 42 passed | 42 passed |
| `test_a_capability_that_cannot_be_reinspected_can_never_be_accepted_v1.py` | 4 failed | 4 failed — **same four ids**, byte-identical set |

`test_an_ordinary_sentence_runs_the_command_it_states_v1.py`, the largest file in the blast radius,
measured whole-file on both trees: **232 failed / 113 passed** before and **232 failed / 113 passed**
after. The apparent movement inside it was scratch-directory pollution between tests that share
`canonical/astra_runtime/tmp/...` and rebuild it in `setUp` — not behaviour.

**What is claimed, exactly:** on the files where a whole-file before/after comparison was possible,
the failing sets are identical; the one difference found in favour of this branch is a test that
now passes. The claim made here is *no regression detected in the measured files*, not *no
regression anywhere*.

**Limits of this measurement, stated plainly.**

* The full suite is 16,361 cases. It did not finish on this 2-core sandbox: a whole-repo run was
  still at ~87% after 40 minutes and was abandoned twice. The numbers above come from the
  subset of files that touch the changed modules, compared file-by-file. **No whole-suite claim
  is made.**
* Single machine, producer-run, `authority: NONE`. It is not independent verification. The
  referee on `main` is the only independent judge.

### 4c. What the referee actually did

This section was written while the branch was still unmerged and it said the referee had not run.
It has now run, so that sentence is replaced rather than left standing.

The merge (`68ade705`, PR #7093) went through `gh pr merge --auto`, which is the only merge this
repository permits: GitHub completes it only when the check the branch ruleset requires is green.
That required check is `referee/repo-integrity-guard`, and it passed. The ruleset requires exactly
one check — measured from the ruleset itself, not assumed.

Four things went red on the way there, and none of them was a defect this round introduced. They
are recorded because each one is a way a green branch can be believed for a wrong reason:

* **`verify-brain-unified-model-v1` failed at `recompilation_is_byte_identical`.** This one *was*
  mine, and it was the artifact working correctly. The compiled model indexes root `*.md`, so
  adding this document changed the tree the artifact records, and the artifact was stale.
  Regenerated with the compiler — never by hand — and the branch went to 33/33, later 38/38 after
  main admitted two hidden surfaces. **A content-addressed artifact is a function of the tree; the
  fix for a changed tree is a recompile, not a hand-edit.**
* **`declaration-floor` failed, and fails on `main` too.** Measured directly: base `c4f529eb` 596,
  `main` 607, this branch after merging main **607 — identical to main, adding zero**. The
  +1 that appeared at one point came from an *untracked* 119 MB test-scratch file under
  `canonical/astra_runtime/tmp/`, which the floor scans because it walks JSON on disk while the
  ignore rules only govern git. Deleting the scratch returned the count to main's. The floor's
  steady rise is a real repo-wide condition and is not this round's to claim.
* **`Drift Immunity Guard` and `Load-bearing primary admission` failed on the merge commit
  itself** — `ACTION_INTENT_MISSING` and `EXACTLY_ONE_ACTION_INTENT_REQUIRED`. The merge had
  carried nine runtime state files written by verification runs, and `canonical/runtime/state/` is
  under the sensitive prefix, so the guards fired on a state file rather than on the work. Both
  pass once the merge carries only what it changes. **A merge that carries a run's side effects
  cannot be read for what it changed** — which is why they were stripped.

Both guards and the model verifier were reproduced locally against the exact commits, not inferred
from a check name. On `main` after the merge: 21/21 modifier tests, 38/38 model verifier.
* 480 failures pre-exist at `c4f529eb` in these files. They are **not** this round's work to claim.
  They are the backlog.
* One earlier, in-repo-harness run produced a false regression signal (4a). It is recorded because
  the next measurement of this kind must keep the interpreter out of the tree.

## 5. What this round does *not* fix

Named, not hidden:

* `top_level`, `nested`, `has_call`, `has_parameter`, `duplicate`, `numbered`, `comment` are
  **refused**, not computed. Each needs a fixture that makes it visible and a predicate that
  composes with the selection. Refusing is honest; computing them without such a fixture would
  rebuild the defect this round removed.
* The second derivation is implemented for the **text** domain only. A filter on Python, JSON, CSV
  or Markdown is grounded by its fixture but has no independent second derivation yet.
* ~~Concept binding picks one concept and drops the other.~~ **Closed this round** — see §8.
* Nothing here was tested on a benchmark. This is a correctness repair to the front door, not a
  capability result.

## 6. The next bottleneck this exposes

The ledger makes the *front door* refuse sentences it cannot ground. It does not make the system
able to *understand more sentences* — it makes failure visible instead of silent. The chain from
"the sentence is understood" to "the answer is right on a task nobody wrote for us" still runs
through the bottleneck named in `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md` §5: the
**verifier**. This round supplies one concrete, reusable instance of the fix: give the verifier a
fixture on which the hypothesis and its neighbour disagree, and make the run fail closed when they
don't. That pattern — not the 12 keys — is what should be applied next, to the code domain, where
an oracle exists and can be made adversarial.

## 7. Files

* `canonical/swe_kernel/semantic_generalization_engine_v1.py` — the ledger, the filters, the
  measurement-unit fix, the concept-binding fix, the two new refusals, the second derivation.
* `canonical/tests/test_a_modifier_that_changes_which_items_are_meant_is_grounded_or_refused_v1.py`
  — 18 tests, including the **control** that proves the probe fails when the filter is neutered,
  so the probe's passing cannot be vacuous.
* this document.


## 8. The same defect one level up: two concepts, one answer

Having named the modifier defect, the next instance was found by asking the same question of the
next slot: *which word in this sentence narrows or selects, and was it bound?* The concept slot
failed it too.

```
count functions and classes in code.py     PASS  4   the class was never counted
list functions and methods in code.py      PASS ['m']  the functions were never listed
count the function call sites in code.py   PASS  0   the site count, not the function count
```

Three different sentences, one shape: the binder keeps the highest-priority concept and the other
named thing disappears. The engine serves **one** selection, so a sentence naming two is a request
for two answers — and answering half of it as if it were the whole is exactly the modifier defect
with the words swapped.

`FAIL_CLOSED__MULTIPLE_CONCEPTS_NAMED` closes it, and the refusal names *both* concepts.

The control matters as much as the gate: `"Count functions with a docstring in sample.py"` names
`docstring` too, but a concept inside a **qualifier** is a property of the thing being counted, not
a second count. The first version of this gate refused that question — so the gate tests spans
against the qualifier patterns before it decides a second concept is being requested, and
`test_a_qualifier_word_is_not_a_second_concept` is the test that fails if that is ever removed.

The notice also had to agree with the binder about *labels*. Each concept span is given the label
the binder would give that phrase, so `methods` is one span labelled `method` (the lexicon maps it
to `function` and the binder re-binds it), and `function calls` is one span labelled `call`. The
first version double-counted both and refused `count the methods in code.py`, which has an answer.
