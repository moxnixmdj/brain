# One try covers a fraction

**2026-11-12 · branch `arena/7aa1248a-brain` · authority NONE · measurement only**

The owner asks again, in four forms: *we already solved instant learning in arbitrary
environments; give the model the most advanced coding actions, let it experience each once, and
it learns them permanently; then it can do anything on a computer and become the most advanced
coding agent; isn't this a revolutionary way to learn?*

The honest answer is narrower than the claim and larger than "no":

> **One demonstration does transfer a real, precise piece of a change — and it transfers a
> fraction of it, not the skill.** On fifteen real pull requests where people repeated one kind
> of change, one changed file recovers **15.8% of the developers' other changes at 95.5%
> precision**; a second example raises coverage to **24.0%**. The learner is not guessing: it is
> right about almost everything it does. It is doing a small part of the job. The addressable missing part
> is named, refusal by refusal, in its own words — and every addressable name is an operator to
> buy in code, not an experience to add.

This note reads the record that was already on `main` as a **dose-response curve** instead of a
single score. It adds no organ and runs no model. The reader is
`canonical/tools/one_try_coverage_frontier_20261112_v1.py`; its eleven tests pin every figure
below.

---

## 1. The measurement nobody had read as a dosage

`REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json` took 15 merged pull requests (89 changed Python
files) in which the developers made one kind of change in many places — an old assertion name, a
logging method, an f-string conversion, a library removal. Each changed file in turn is *the*
demonstration; every other drawn file is a place to repeat it. The organ is
`canonical/swe_kernel/taught_actions/edit_by_example_v1.py`: no model, no weights, nothing taught
except the one example.

| organ, one example | coverage of the developers' changes | precision of what it changed | edited / asked |
|---|---:|---:|---:|
| older organ (run 1) | 23.18% (388/1674) | 96.82% (396/409) | 142/440 |
| **current organ (run 2)** | **15.83% (265/1674)** | **95.45% (273/286)** | **87/440** |
| current, leave-unshown-alone (run 3) | 17.50% (293/1674) | 95.86% (301/314) | 95/440 |
| ceiling, every try kept (run 6) | 23.30% (390/1674) | 96.84% (398/411) | 144/440 |

`coverage = right changes / the developers' changes`. `precision = right changes / the organ's
changes`. They are different fractions about different populations, and the earlier debate
quoted one while arguing about the other.

**What a second example buys.**

| organ | one example | two examples | second example buys |
|---|---:|---:|---:|
| older organ | 23.18% | 32.74% (1089/3326) | **+9.56 pp** |
| current organ | 15.83% | 23.96% (797/3326) | **+8.13 pp** |
| current, leave unshown | 17.50% | 26.97% (897/3326) | **+9.47 pp** |
| ceiling | 23.30% | 32.17% (1070/3326) | **+8.87 pp** |

The marginal value of a **second** demonstration is stable at **eight to ten points of
coverage**, with precision staying at 95–97%. That is a real learning curve, and it is shallow. It
is not a switch that turns a skill on.

## 2. One example is not one number

Per pull request, current organ, one example:

- recovers **nothing** on **5 of 15** pull requests;
- recovers **at most 1%** on **6 of 15**;
- median **9.09%**, mean **15.31%**, best **58.82%**.

A change kind either has a form the demonstration can express or it does not. When it does, the
example reaches a useful fraction of the other files. When it does not, the answer is zero, not
"a little." This is why a single average hid the shape: the average is mostly a mixture of good
kinds and kinds outside the algebra.

## 3. The refusals are the roadmap

Every refusal in the record is the learner's own sentence. Grouped over the 440 askings of the
current organ, one example:

| class | askings | share | what it means |
|---|---:|---:|---|
| `NO_FORM_IN_FILE` | 162 | 36.82% | the demonstrated change does not occur in this file — **not** an operator gap |
| `EDITED` | 87 | 19.77% | it did repeat the change |
| `IMPORT_ONLY_EXAMPLE` | 60 | 13.64% | the example differs only in import lines; the algebra learns only expression changes |
| `CALL_SHAPE_NOT_SHOWN` | 50 | 11.36% | the callee is shown with a different number of arguments or keywords |
| `BLOCK_SHAPE` | 34 | 7.73% | the change adds, removes or reshapes whole statements |
| `NAME_NOT_AVAILABLE` | 22 | 5.00% | the new code reads a name the file does not define, import or receive |
| `CONFLICTING_CONTEXT` | 15 | 3.41% | the same code was changed in one place and left alone in another |
| `PARSE_MISMATCH` | 10 | 2.27% | the written result did not parse to the intended tree |

**191 of 440 askings (43.41%) are ordinary refusals** — not "the change does not apply here,"
but "the algebra cannot say this yet." Ranked by frequency, the next operator classes are:
import-only (60), call-shape (50), block-shape (34), name availability (22), conflicting context
(15), parse mismatch (10).

These are **askings, not changes**. Fixing a class does not recover every change in the files it
refused; the record does not keep the refused files' text. It tells you where to look, and the
same corpus can then measure the fix.

## 4. Why this is the answer to "the most advanced coding actions"

The owner's phrase is right about the goal and wrong about the mechanism. "Advanced coding
actions" are mostly:

- **block-shape** changes — add a guard, wrap a call, replace a loop, move a statement;
- **scope-aware** changes — rename a symbol, add an import, thread a parameter across files;
- **context-dependent** changes — the same call is migrated in one place and deliberately left
  in another.

Those are exactly the classes the one-example algebra refuses (34 + 22 + 15 askings here), and
exactly the ones a single before/after file does not pin down. A demonstration can only select
among operators the algebra already has. **One example cannot teach an operator the algebra
cannot express.** The tree measured the price of a new operator in round 9: one reducer for a
word problem cost **one lesson, two files, about ten lines of code**, and then answered **5 of 5**
held-out instances. The price is code. It has never been experience.

This is also why "just give it the most advanced actions" is not a shortcut. Giving it more
actions without the operator that composes them produces more candidates, not more skill; the
tree has already killed static catalogues and measured that adding environments buys **0 of 21**
on the confinement seam and **1525 = 1525** on a wider corpus.

## 5. The same law in three regimes

| regime | one example / one success | what limits it |
|---|---:|---|
| **repeated change in real code** (this record) | 15.8–23.3% coverage, 95–97% precision | operator algebra; 5/15 kinds recover nothing |
| **GUI task with a page reward** (MiniWoB, open PR #6770, producer-run, 50 pages, fresh seeds) | **68.8%** mean reward for one success + version space; replay 15.2%, random 12.0% | 17 of 50 pages had no first success; the version space is small and the reward is the oracle |
| **short code repair with tests** (QuixBugs / HumanEvalFix) | 20/40 QuixBugs from HumanEvalFix edit kinds; 62/100 HumanEvalFix vs 56/100 backwards control | tests are a strong oracle; the edit kind is narrow; all 40 QuixBugs fixes had been read earlier, so the 20/40 is not an unseen-bug score |
| **ordinary computer tasks** (this tree's 30-task probe) | 15 expressible, 5 `VERIFIED_ACTION`, **1 of 5 an answer** | the front door and the postcondition oracle, not the learner |

The pattern is the same in all four: **one example identifies a program only when the hypothesis
space is structured and the demonstration is informative; the oracle then decides whether the
identified program is right.** MiniWoB's 68.8% is real and is the strongest one-success result in
the tree — but it is 50 pages of a benchmark with the page's own reward, not "any computer."

External 2026 work says the same from the other side:

- **Continual-ARC** (arXiv:2611.14505): across a lifelong ARC stream, most harness methods score
  **below a floor that simply caches each task's demonstrations**, and **no harness-based method
  gains on unseen tasks**; weight training does (DAgger held-out 0.29 vs seen 0.57). Weights learn
  from ~200 instances where in-context state does not.
- **SkillsBench** (arXiv:2602.12670): **curated** skills +16.2 pp; **self-generated** skills
  **−1.3 pp**; 16 of 84 tasks negative. Curation is the operator algebra, not exposure.
- **SWE-Skills-Bench** (arXiv:2603.15401): 39 of 49 skills zero delta, mean +1.2%.
- **DGM** (arXiv:2505.22954) and **SICA**: 20→50 and 17→53 on SWE-bench by archive + selection,
  not by one-shot exposure; the cost was ~$22k of search.

## 6. What is real, what is not

| claim | verdict | the number |
|---|---|---|
| one demonstration carries more than a lookup | **TRUE** | 15.8–23.3% of other changes, 95–97% precision; 10 of 15 kinds recover something |
| one demonstration carries the skill | **FALSE** | 77–84% of the developers' changes are not recovered; 5 of 15 kinds recover nothing |
| a second demonstration helps | **TRUE, shallow** | +8.1 to +9.6 pp coverage, precision flat |
| "instant learning in arbitrary environments is already perfect" | **FALSE** | 30-task probe: 15 expressible, 5 `VERIFIED_ACTION`, 1 of 5 an answer; OSWorld 2.1 best binary 48.7% |
| "do anything on a computer once → permanent" | **FALSE as stated** | within-family GUI version space works (68.8%); transfer to arbitrary software, and persistence without replay, are unmeasured or fail |
| "most advanced coding agent on the planet" | **NOT FROM THIS** | a 15.8–24% coverage component is not a frontier agent; frontier systems combine weights, harness evolution, curated operators and selection |
| "revolutionary way to learn faster" | **PARTLY** | precise one-example transfer at ~zero model cost is a good building block; the published frontier already evolves harnesses; the revolution is choosing demonstrations and structuring operators, which is engineering |
| "we were trying to make our model a sentient creature" | **NOT WHAT THIS IS** | see §7 |

## 7. The sentient-creature question, directly

No. This architecture has memory, selection and verification. It has no persistent self, no
interoception, no valence, no continuity of identity across sessions, and no mechanism whose
function is to represent its own condition. Calling it a creature is a metaphor, and the
metaphor has a cost: it makes "it learned" sound like a fact when the measurable claim is "a
rule was stored and a test passed."

If the goal is a system that *behaves* as if it has a persistent self, the measurable proxies
are continuity of memory, accuracy of its self-model, stability of its preferences under
intervention, and surprise when its predictions fail. None of those are measured here. The tree
should not claim the word until at least one of them is. This does not make the engineering
worse; it makes the next experiment possible.

## 8. The smartest path, in order

1. **Oracle-honesty gate before any learning claim.** The 30-task probe's `VERIFIED_ACTION` is
   right **1 of 5** times. A learner fed a false success learns the wrong rule. Require an
   answer-level check (not a declared postcondition) on the tasks that matter; pass ≥0.9, fail
   <0.7. This is the precondition for everything below.
2. **Buy the import-only operator (60 askings).** The example differs only in import lines; apply
   the same import rewrite. Cheapest class, mechanically checkable (the module resolves), no new
   search.
3. **Buy the call-shape operator (50 askings), with a signature check.** A pure callee rename
   (`logger.warn` → `logger.warning`, `assertRaisesRegexp` → `assertRaisesRegex`) leaves the
   arguments untouched, so arity should not block it — but the new callee must accept the call.
   Resolve the signature from the AST or run the project's tests; do **not** widen blindly. This
   is the highest-yield cheap fix and the easiest place to lose precision.
4. **Buy the block-shape operator (34 askings).** Add/remove/wrap a statement. This is the
   `median` gap and the real "advanced coding action"; it needs a new algebra and a test oracle,
   not another demonstration.
5. **Buy scope-aware name/import handling (22 askings).** A rename that spans files is a project
   graph operation; one file cannot show it.
6. **Make the second demonstration a decision, not a default.** The conflicting-context class
   (15) and the tied version spaces are where a second example is worth +8–10 points. Choose the
   file that settles the most unresolved uses; do not spend a second example where the first is
   already unambiguous.
7. **Only then add exposure or weights.** Where the algebra cannot reach and the oracle is
   strong, train or search (DGM, DAgger). Do not use exposure to compensate for a missing
   operator; the record says that buys nothing.

The order matters: 1 makes the signal true; 2–5 raise coverage where the mechanism already
works; 6 spends the second example where it pays; 7 is the expensive fallback, not the first
move.

## 9. Receipts

- Record: `canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json`
  (15 PRs, 89 files, 440 one-example askings, 870 two-example askings; generated
  2026-11-12T17:19:18Z; authority `NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT`).
- Reader: `canonical/tools/one_try_coverage_frontier_20261112_v1.py` (`--json` writes the whole
  report; no network, no model, no organ import).
- Tests: `canonical/tests/test_one_try_coverage_frontier_v1.py` — 11 tests, pinning coverage,
  precision, the second-example marginal, the 5/15 zero spread, all eight refusal classes, and
  the 191/440 ordinary-refusal total.
- Prior work reused: `THE_MULTIPLIER_IS_NOT_THE_MULTIPLICAND_20261112_V1.md` (the exchange rate),
  `A_NEW_PART_COSTS_CODE_ONE_LESSON_BUYS_THE_WORD_20261112_V1.md` (the operator price),
  `ONE_PUBLISHED_FIX_IS_A_SKILL_NOT_ALL_CODING_20261112_V1.md` (one fix is not all coding),
  `expressibility_of_ordinary_computer_tasks_v1.py` (the 30-task probe).
- Open, not merged, producer-run: PR #6770 (MiniWoB 68.8% fresh), PR #6775 (demonstration choice;
  reach r=0.88 when unique, silent on 7 of 10).
- **PR #6772 merged while this note was in review** (`816dabaa`), titled "Proof: Instant learning
  system works on real coding tasks". It was read, and its Task 2 is a cached refusal — the
  second call is faster because the first learned the confinement requirement, not because a
  coding skill was learned. Task 1 counts functions in one file. Neither is the claim in its
  title. Do not adopt it without reading the receipts.
- External: arXiv:2611.14505, arXiv:2602.12670, arXiv:2603.15401, arXiv:2505.22954.
- Authority NONE. `truth.achieved` false. $0. Model calls 0. No capability registered. No family
  flipped. No test of any of the 15 projects run: **precision is agreement with the developers,
  not correctness.**
