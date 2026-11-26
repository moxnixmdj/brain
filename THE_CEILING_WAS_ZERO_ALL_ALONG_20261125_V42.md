# The zero was never the vocabulary's fault until the vocabulary was measured

**Round V42. Branch `arena/11f5214b-brain`, base `6712850d`.** Model calls 0, stored parameters 0,
network at run time 0. Corpus: the same 28 mined fail-to-pass tasks, 23 from pypa/packaging and 5
from hukkin/tomli. **Not a benchmark row. 0 of 28 solves.**

---

## What I was asked, and what I actually did

The round began where V41 left off: the DEFER form solves exactly the task it was derived from and
nothing else, and the next lever I proposed was to detect "this value is computed too early" without
requiring the re-entrant failure shape to be visible.

Before building that, I did something the last six rounds did not do. I asked whether the generator's
zero is a **budget** problem or a **vocabulary** problem, and tried to measure the difference. Those
two have opposite repairs, and guessing which one we had is what produced six rounds of adding a form
and watching the rate stay at zero.

The answer is vocabulary — but not for the reason any previous round assumed, and the *first* thing
the measurement destroyed was my own planned next lever.

---

## The claim the prompt rests on, audited

`canonical/tools/audit_the_prompt_claims_v1.py` re-run against this tree:

| claim class | result |
|---|---|
| identifiers (19) | **6 exist as code files**; 13 appear only as strings inside my own code and reports |
| commit hashes (9: `209bbc6c`, `92b6db85`, `d6c1661a`, `ac0e297`, `c53d373`, `05f6fd0`, `884437ae`, `fc518e4`, `051fd663`) | **all 9 FAIL: not commits in this repository** |
| figures (75.2%, 344, 0.35s, 447, 226, 244) | appear elsewhere in the tree, none independently supported |

The prompt calls those hashes "our logged unsolved commits." They are not commits here. Nothing
downstream was built on them, and the branch names it cites (`aab1b545`, `b81b2217`, `06dc079e`, …)
do not resolve either. **This does not change any measured result in this report** — every number
below was produced by running code in this round — but it is the third consecutive round in which the
prompt's inventory has failed verification in the same way, and it is worth stating plainly rather
than repairing into a sentence.

---

## Channel 1 — the traceback: no input on 86% of the corpus

`canonical/tools/site_edit_space_measurement_v1.py`

Every operator family in this project is keyed to a traceback frame: parse the frames, pick the
innermost one inside the source tree, emit edits around it. So I counted the input.

| | |
|---|---|
| tasks that expose a source frame | **4 of 28** |
| tasks that expose none | **24 of 28 (85.7%)** |
| failure classes | `AssertionError` 17, `AttributeError` 5, `Failed` 5, `TypeError` 1 |

On 24 of 28 tasks the failure is raised inside the **test file**, so no line of the project's source
is ever named. The recorded outcome `NO_CANDIDATE_EMITTED` — read for six rounds as a defect of the
vocabulary — is on those tasks simply **no input**. That is an uncomfortable correction: V41's "the
engine emits 0 candidates from a correctly localised site" is true of *one* task, and was never the
general picture.

---

## Channel 2 — the assertion's expected value: empty

`canonical/tools/expected_value_channel_census_v1.py`

The only other thing in a test-only traceback is pytest's expected-vs-actual diff. Measured on the 24
no-frame tasks:

| | |
|---|---|
| expected value extracted | 24 of 24 |
| that value appears anywhere in the source | **1 of 24** |
| that value within 10 lines of a real fix line | **0 of 24** |
| value appears only in the test file | 3 |

So the idea I proposed at the end of V41 — route on expected-vs-actual and infer "computed too early"
from the test mutating an argument — **has no substrate on this corpus**. I killed it before building
it. The values are constants the test invents, or objects with no textual representation.

---

## Channel 3 — dynamic coverage: the one channel that works

`canonical/tools/coverage_selector_measurement_v1.py`

Run the failing test and record which lines of the source execute. An injected pytest plugin does the
tracing; the target repository is never modified.

| | |
|---|---|
| tasks measured | 28 |
| candidate budget — whole files | 21,288 lines |
| candidate budget — executed lines | **2,847 lines (86.6% reduction)** |
| tasks where a real fix line is inside that set | **25 of 28** |
| fix-line retention | 23.8% |

This is the first usable pointer to a *line* the project has had on the no-frame majority, and it
needs no exception to propagate. V41's standing result was line-level localisation 1 of 28; coverage
reaches a real fix line on 25 of 28, which is a different and much better starting point.

---

## The generation attempt — and the bound it hit

`canonical/tools/coverage_seeded_generation_v1.py`

Hypothesis, stated before running: *the edits that fix these bugs are mostly recombinations of tokens
already present in the same file.* If true, a small generator that recombines only what it can see
should solve a non-trivial fraction, and six rounds of zero were an artefact of where it was told to
look.

Three blind families — token swap, quantifier flip, guard/return rewrite — sites restricted to
covered lines, 40 candidates per task, interleaved, each run against the target node **and** the whole
module.

| | |
|---|---|
| candidates screened | **1,040 across 28 tasks** (median 40/task — every task ran a full budget) |
| solved | **0** |

The zero is a measured zero: the harness ran, emitted, applied and tested. It is not the failure to
launch that produced plausible zeros in three earlier rounds.

---

## Why it is zero — the site-level taxonomy

`canonical/tools/fix_vocabulary_taxonomy_v1.py`

Per changed line: does it execute at all, and is the change a substitution of tokens the file already
contains?

**667 changed sites across 28 tasks:**

| class | sites |
|---|---|
| `UNDISCOVERED` — the line never executes under the failing test | **498 (74.7%)** |
| `NO_VOCABULARY` — executes, but the change is not a substitution | **144 (21.6%)** |
| `SITE_REACHED_SUBSTITUTABLE` — executes, and is a substitutable single-line edit | **25 (3.7%)** |

**Operations:** ADD 482, REPLACE 118, DELETE 67. The fixes are *additions*.

Per task, and this is the number that ends the argument:

| | |
|---|---|
| tasks reachable by a **single** substitution | **0 of 28** |
| tasks where **all** sites are substitutable (needs coordinated multi-edit) | 1 of 28 |
| tasks with at least one substitutable site | 13 of 28 |
| tasks whose only changed line never executes | 3 of 28 |

**The ceiling for the substitution family on this corpus is 1 of 28. For a single-edit version of it,
0 of 28.**

The generation run achieved 0, against a single-edit ceiling of 0 and a multi-edit ceiling of 1. It
did not underperform. **Six rounds of operator work have been measuring a family whose ceiling on its
own corpus was ~zero the whole time**, and no amount of ranking, budget, or another spelling of a
deferral could have changed that. That is the honest answer to "why zero, again."

Two concrete examples of the ceiling, both single-line fixes that a substitution form *should* reach:

- `2602dd07`: `re.compile(r"[^ \t]+")` → `r"\S+"`. This **is** substitutable — `\S` occurs elsewhere
  in the same file — but the line is a module-level constant in a dict, and the failing test never
  executes it. `UNDISCOVERED`.
- `2aada00b`: `[^\s;)]*` → `[^\s;)]+`. Quantifier flip, exactly what the form emits — but that line is
  inside a verbose regex that the failing test's path does not execute.

The channel and the grammar each have a hole, and the two holes barely overlap.

---

## What this says the next generator must be

Not another substitution form. The fixes are additions, and **194 of 600 added statements have a shape
that already occurs elsewhere in the same file** — `if not <I>:`, `raise <I>(<S>)`, `return <I>(<I>)`.
That is a template the repository supplies, which is a real thing to instantiate and is a different
claim from anything tested here. The 406 that match no existing shape have to be composed from
vocabulary the file does not contain, and that is a synthesis problem, not a search problem.

I am not claiming that addition generator works. I am recording that the substitution family is now
bounded at 0–1 of 28 by measurement, so that round seven does not spend itself re-measuring it.

---

## Leakage, checked rather than asserted

The two examples above quote the real fix lines (`r"\S+"`, `[^\s;)]+`). That is deliberate and it is
the reason those tasks are examples: they were read by a human (me) *after* the generator had already
been run and had already scored zero, to explain the zero. They are diagnostic evidence in a report,
not solver input, and no generator in this round ever read them.

Checked mechanically in this report for the previous round's fix content: `cached_property`, `super().__str__`,
`self.text` — **0 occurrences**. The DEFER form is not mentioned as a candidate anywhere here.

The standing contamination from V41 still applies and is unchanged: I had seen this corpus's
`f91ea793` fix before deriving DEFER, and that is recorded in
`canonical/corpus/defer_form_calibration_20261124_V1.json`. Nothing in this round depends on DEFER.

## Six instrument bugs, all of which produced a plausible wrong number

1. **`import_roots` put `src/packaging` on `PYTHONPATH` instead of `src`.** `packaging` resolved to a
   namespace package, the target test *passed on the parent commit*, and 22 of 28 tasks were
   misreported `NOT_FAIL_TO_PASS`. Caught only because a task I had already solved appeared in that
   list — the "harness cannot reproduce a known positive" rule, again.
2. **The coverage plugin dumped from `atexit`, after `os` was torn down**, and wrote an empty file.
   Empty is indistinguishable from "the test executed nothing"; eight rows carried a plausible
   `budget 0.0`.
3. **The coverage harness restored the parent commit and forgot to re-apply the added test file**, so
   it ran a node that did not exist and collected nothing.
4. **The coverage plugin discarded import-time hits**, deleting the module-level regex tables where one
   real fix lives. Retention 0.159 → 0.238 and reach 22 → 25 once import lines were kept. I nearly
   reported the lower number as a property of coverage.
5. **`failure_class` let `assert a == b` expressions through as exception names**, producing six fake
   classes.
6. **The first site classifier counted a two-line coordinated fix as one edit** by iterating per file
   rather than per task, which is why `tasks_reachable_by_a_single_substitution` is reported separately
   as 0 rather than being folded into the 1-of-28 figure.

Bug 1 and bug 4 both made the corpus look *worse* than it is, and bug 2 made it look *cleaner*. None
of them would have been caught by the tests failing; all were caught by checks on known values.

---

## What is verified, and what is not

**Verified by running this round:** everything in the tables above. Tests:
`canonical/tests/test_corpus_bounds_instruments_v1.py`, 13 passed. Receipts:
`canonical/corpus/{site_edit_space_measurement,expected_value_channel,coverage_selector,coverage_seeded_generation,fix_vocabulary_taxonomy,corpus_bounds}_*.json`.

**Not established:** any generalisation. All 28 tasks are the development corpus this project has been
mining; bounding the generator on them says nothing about unseen repositories. No benchmark row. §6
DONE is not met. Standing capability is unchanged: **0 of 28 solves, 17 of 28 file-level, 1 of 28
line-level**, and coverage now offers a better line pointer that has not yet been turned into a solve.

**Rejected this round, with the measurement that killed each:** expected-vs-actual routing (channel
empty, 0/24); another deferral spelling (family ceiling 0/28 single-edit); wider budgets (every task
already screened a full 40); more substitution families (482 of 667 sites are additions).
