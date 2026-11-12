# The multiplier is not the multiplicand

**2026-11-12.** Branch `arena/0e568329-brain`. Authority **NONE**. `truth.achieved` stays
`false`. $0, zero model calls in every result-bearing path. This answers the owner's question
directly and prices it with the tree's own landed records; it does not claim a capability,
register one, or widen a gate.

> *Give our model the most advanced coding actions, let it experience each once, and it will
> have learned them permanently. Then we have solved anything on a computer, and we have the
> most advanced coding agent on the planet. Am I right or wrong?*

**Right about the direction. Wrong about the mechanism, the scope, the timeline, and the
score.** Experience *should* compound into capability; that is the correct target. But the
thing that makes it compound is not exposure. It is a trustworthy label on a real task, a
hypothesis space that contains the right rule, and enough instances to identify it. Experience
is a multiplier on those three. It cannot supply any of them.

The tree's own sharpest measurement of the owner's sentence: **teaching the published fixes of
all 39 other QuixBugs bugs bought exactly one bug (5 of 40 → 6 of 40).** If one experience were
the bottleneck, thirty-nine experiences would not buy one.

---

## 1. The sentence, already run as an experiment

No new benchmark was written for this note. The tree has four producer-run records on external
distributions — 100 held-out HumanEvalFix bugs and 40 QuixBugs bugs written by other people —
and `canonical/tools/the_exchange_rate_of_one_lesson_20261112_v1.py` re-reads them and prints
the arithmetic. Every number below is from those records, not from prose.

**HumanEvalFix, 100 bugs met once each, one pass, frozen learner:**

| arm | repaired | right as far as checked |
|---|---:|---:|
| solver alone (cold) | 53 | 36 |
| keeps its own repairs as lessons | **64** | **45** |
| the same lessons kept backwards (size-matched control) | 62 | 42 |
| the published fix shown after every bug | 65 | 45 |

The raw gain over cold is +11, and it looks like learning. It is mostly *candidate generation*:
the backwards control — same number of lessons, same programs, no fix — also gains +9. The
lessons' own directional contribution is **+2 repaired bugs and +3 right answers**. The tree's
own adjudicator, on the same record, returns **`NO_COMPOUNDING`**: cost ratio 1.0819 where it
requires 1.5, paired wins 31/98 where it requires 80/100.

**QuixBugs, 40 bugs by other authors:**

| what was done | result |
|---|---:|
| solver cold | 5 / 40 |
| all 39 other published fixes taught first | 6 / 40 (**+1**) |
| one fix, 22 lessons, 858 (lesson, target) pairs | **1** other bug repaired |
| the same bug again, from memory | **4 / 4**, ~1.9 s, no search (search: 5.5–228.6 s) |

Exact repetition is real, exact and cheap. Generalisation to the next bug is not.

**The one large positive, kept because it is real:** transfer the *shape* of an edit, not the
fix. A learner shown 164 HumanEvalFix fixes (no QuixBugs fix at all) repaired **20 of 40**
QuixBugs bugs, where the tree's own search repairs 5; with the QuixBugs fixes too, 21. On
HumanEvalFix, 203 lessons repair 62/100 against a 56/100 backwards control (+6). The record is
explicit that this QuixBugs arm is not an equal-budget control and that its 40 fixes had been
read earlier, so it is an exception to investigate — not an unseen score.

**What the four records jointly say:** memory is a cache (excellent), an operator prior is a
real transfer mechanism (promising), and *exposure as such* is neither.

## 2. First principles: why "once" cannot be the mechanism

1. **Learning is selection under evidence.** An experience is one constraint on which rule to
   keep. It identifies the rule only where the prior plus that constraint leave one survivor.
   Measured in this tree: one showing reaches 1 of 4 unseen sites; two *chosen*, adversarially
   different showings reach 4 of 4; one demonstration leaves 14 of 47 candidate rules standing.
   "Once" is sufficient exactly where the concept was already pinned — a word over a fixed
   algebra, an exact repair — and nowhere else.
2. **The label is the scarce input, not the trajectory.** A run without a task-level oracle
   teaches *what I did*, not *what was right*. Measured: 5 of 30 ordinary tasks report
   `VERIFIED_ACTION` and **1 of those 5 is actually correct** (probe run on the tree today,
   open PR #6762; not yet merged); 9 of 62 test-passing repairs
   are wrong on an input the tests did not contain; three published skills *reduce* agent
   performance. More experience on a wrong label makes the system more confidently wrong.
3. **Local success does not compose.** Two individually correct rules, applied in sequence,
   can return the text to where it started; each step passes its own check. Sequence
   admission now exists in the store (`skill_sequence_verify_v1`), but it is a *guard*, not a
   source of capability.
4. **Permanence is validity under drift, not bytes on disk.** A lesson is permanent only if it
   still fits the tree when replayed next month. The honest metric is a published fit rate, not
   "stored".
5. **Memory cannot exceed the hypothesis space.** No amount of demonstration teaches `median`
   while the algebra has no median operator; the lesson was *refused* until the reducer was
   added in code (~10 lines). Success alone does not teach applicability: 0 of 200 requirements
   identified; the survivor says "always" in 68% of failing states.
6. **A frozen model plus memory recombines; it does not add capability.** 0 of 145 registered
   capabilities update weights. The same 40 QuixBugs bugs that this tree's solver repairs 5/40
   are repaired 31–40/40 by language models. When the base capability is 5/40 and 39
   demonstrations buy one bug, the gap is not a memory-format problem.

The owner's plan invests in the multiplier and hopes it becomes the multiplicand. It will not.

## 3. What 2026 actually measured about this exact idea

| study | what it tested | result | what it kills |
|---|---|---|---|
| **SWE-Skills-Bench** (arXiv:2603.15401) | 49 public SWE skills × 565 real repo tasks | **39/49 zero** pass-rate change; average **+1.2%**; 3 *harmful* up to −10%; token cost up to +451% | "give it a library of advanced actions/skills" |
| **SkillsBench** (arXiv:2602.12670) | 86 expert tasks, 7 model–harness configs, 7,308 trajectories | curated skills **+16.2pp**, but software engineering only **+4.5pp**; **self-generated skills −1.3pp**; 16/84 tasks worse | "let it write its own skills from its own experience" |
| **CL-Bench** (arXiv:2606.05661) | continual learning across six stateful domains | **naive full-context ICL outperforms dedicated memory systems**; best normalised gain ≈25% | "build a better memory store and the agent will learn" |
| **Continual-ARC** (arXiv:2611.14505, 10 Nov 2026) | lifelong stream, same tasks returning with fresh instances | **no harness-based method gains on unseen tasks**; harness persistence usually loses to a cache; **weight-based learning does gain** | "one pass in a new environment, kept in the harness" |
| **SkillTTA** (arXiv:2605.16986) | retrieve a few traces, synthesise a *temporary task-specific* skill, fixed solver | **+10.8** SpreadsheetBench (0.397→0.505), **+13.4** BigCodeBench (0.517→0.651) | the *working* form of the idea: synthesis for this task, not a permanent global library |
| **Darwin Gödel Machine / SICA** (ICLR 2026; arXiv:2504.15228) | the agent edits its own harness under a frozen evaluator | SWE-bench **20→50** on its 200-task evaluation in 80 iterations (~$22k, ~2 weeks); SICA **17→53** on a 50-problem subset (~$7k) | the *other* working form: evolution against an external evaluator — expensive, not one-shot |

The pattern is not subtle. **The static-library, one-exposure form of the idea is the form 2026
measured as inert or harmful. The forms that work are narrower and costlier:** synthesis
conditioned on the target task (SkillTTA), or harness evolution against a real evaluator
(DGM/SICA), or weight updates (Continual-ARC). None of them is "do it once and keep it."

For computer use specifically, the frontier is bifurcated. Short-horizon OSWorld-Verified is
near or above the human baseline (~86% vs 72.36%, leaderboard, secondary); long-horizon
**OSWorld 2.0/2.1** is **44–49% binary** (2.1 best: 48.7% binary / 81.8% partial). The named failure modes
are losing constraints, missing mid-task information, guessing instead of asking, and **skipping
verification** — not "the agent lacked an action." That is the same defect this tree found in
its own front door: `VERIFIED` means "met the postcondition I declared", not "answered you."

## 4. Real vs not — the scorecard

| the sentence | verdict |
|---|---|
| "We solved instant learning perfectly." | **No as stated.** Real for exact repetition (4/4 at 1.9 s), for a word over a fixed algebra (5/5 held out), and for edit-shape transfer (20/40, 62/100). Not general. |
| "Give it the actions once and it learns them permanently." | **No.** 39 demonstrations → +1 bug; 203 lessons → +2 over a size-matched control; one fix → 0/39 targets, 1 repair in 858 pairs. |
| "This solves anything on a computer." | **No, and not one problem.** Interface-defined code/CLI is the regime where one-shot transfer is real. Long-horizon GUI is ~44–49%; open-ended tasks have no oracle at all. |
| "Most advanced coding agent on the planet." | **No.** This tree's best external repair is 20/40 with an operator learner (5/40 cold); the same benchmark is repaired 31–40/40 by models. The frontier is defined by weights and compute this project's law forbids renting. |
| "Revolutionary vs how agents learn now." | **Partly.** The verification discipline, content-addressed receipts, and refusal behaviour are genuinely differentiated. The memory thesis is convergent with the field and, in its static form, measured inert. |
| "We already built it under non-obvious names." | **The names are not the problem; the state is.** The mechanisms exist and are listed below. The permanent store holds 1 episode, 3 macros, 7 lessons (3 procedures), 0 settled resolutions. |
| "It is becoming a sentient creature." | **Not measured, not required, and currently contradicted by calibration.** It reports success on 5 ordinary tasks and is right on 1. Nothing compares what was asked with what was answered. |

**What is real, keep it:** exact-repetition memory; one-lesson words over a fixed algebra;
edit-operator transfer with tests as the selector; within-family compression (41% and 30%
fewer description bytes); fail-closed verification; sequence admission; receipts that can be
re-run. These are assets. They are not "everything."

**What is not real:** that exposure alone generalises; that a static skill library is a
capability multiplier; that more environments make the next kind cheaper (0/5, 1525 = 1525);
that wiring the confinement seam unlocks advanced coding (a counterfactual run today lifting the
boundary decision bought **0 of 21**; the wall was compile/binding, and two capabilities then
worked end to end — open PR #6763, not yet merged); that
`VERIFIED` is `ANSWERED`; that "sentient" is a measurable target.

## 5. The mechanisms, under their non-obvious names, with their actual state

| name | what it really does | measured state |
|---|---|---|
| `solve_or_learn` | four-tier escalation; recall a compiled skill, else act, else learn | exists; the front door admits 8 sentences of 149, so it rarely gets to act |
| `VerifiedSkillStore` / `edit_by_example_v1` | crystallise an exact code repair and replay it | exact repairs work; one showing is one literal instance |
| `transfer_learning_v1` | recall a plan by environment fingerprint | 1 episode; no cross-kind transfer |
| `CompoundingConceptLibrary` / `MetaCircularOrganGraph` | compress a family of organs into a shared abstraction | 41% / 30% fewer bytes; two families; not cross-kind |
| `taught_words_v1` | one lesson → a word over a fixed algebra, re-verified at recall | 5/5 held out, reload-safe; cannot add an operator |
| `confinement_v1` | a disposable `git clone` worktree, restricted env, budget, hashed effects | mechanically 9/9; **not a kernel sandbox**, and consulted by nothing |
| `skill_sequence_verify_v1` | refuse a lesson sequence that no-ops or reverts | now called by the store |
| `what_the_machine_kept` | the permanent store census | 1 episode / 3 macros / 7 lessons / 0 resolutions |

## 6. The smartest things to do, in order

The fastest path is not more mechanisms. It is to stop scaling a learning loop whose reward
signal is wrong, then scale the one mechanism that is measured to work.

1. **Gate everything on oracle honesty — do this first.** On the 30-task ordinary set, claimed
   success is right **1 time in 5**. Do not add experience to a loop that rewards the wrong
   answer. Pass condition: claimed-success precision ≥ 0.9 against an independent check;
   fail below 0.7. Until this passes, every other number is noise.
2. **Choose the regime where one-shot transfer is real.** Interface-defined code and CLI tasks
   with executable oracles. Expand along declared interfaces. Stop treating GUI/open-ended
   breadth as the same problem; the field's long-horizon ceiling is ~44–49%, and its failures
   are constraints and verification, not missing actions.
3. **Build the instance corpus from real work.** A corpus entry is the inputs of a real task
   with an attestation. 2,000 instances means 2,000 real executions; fixtures fail 0/56 for a
   reason. The corpus — not the skill catalogue — is the asset.
4. **Use task-specific synthesis, not a permanent global library.** Retrieve k≈4 similar
   traces, synthesise a temporary procedure for *this* task, discard it after. Pre-register an
   A/B on a held-out local suite: **+10 points pass@1 or it is discarded**, per the external
   SkillTTA shape. A static library is measured at +1.2% and sometimes negative.
5. **Buy operators in code, and treat lessons as scoped hypotheses.** A new operator is ~10
   lines plus an independent recomputation plus a re-pin; experience cannot add it. Admit
   sequences only if no step no-ops or reverts. Publish a **replay fit rate** as the definition
   of permanence.
6. **Decide the weights/compute question with open eyes.** If the target is frontier coding,
   the only lever with published large gains is weights or harness evolution under a frozen
   evaluator: ~$7k–$22k per run and weeks, with an external evaluator. Under the current $0,
   zero-donor law that route is closed. Then the honest ceiling is a narrow, verified,
   interface-bound agent — valuable and differentiated, but not "most advanced on the planet."
7. **Get a real sandbox before arbitrary execution.** A disposable clone bounds `git status`,
   not the filesystem or the network. If "anything on a computer" is the goal, the execution
   substrate is a VM/OS sandbox with syscall and network policy, not a worktree. This is a
   precondition, not a feature.

**The one next experiment, pre-registered:** on the existing 30-task ordinary set, attach to
every success an independent check of *what was asked*, and measure claimed-success precision.
Pass ≥ 0.9, fail < 0.7; today it is 0.2. If it passes, run the 100-bug HumanEvalFix A/B above
(current learner vs current learner + task-specific synthesis, equal budget). Do not run
anything else in parallel.

## 7. Kill these, now

1. "One exposure → a permanent general skill." Measured: +1 bug for 39 demonstrations.
2. A static action/skill catalogue as the bet. Measured: 39/49 inert, average +1.2%, some harmful.
3. Self-authored skills from experience as a general bet. Measured: −1.3pp; no harness method
   gains on unseen tasks.
4. More environments as breadth. Measured: 0/5; 1525 = 1525; Continual-ARC.
5. Wiring the confinement seam as "the unlock." Measured: 0 of 21; the wall was binding.
6. Calling `VERIFIED` "answered." Measured: 1 of 5.
7. "Most advanced on the planet" without one external benchmark and a fixed split. The internal
   registry measures the registry.
8. Sentience as a target. It measures nothing here and it licenses exactly the overclaim
   ("the system already works") that the record refutes.

## 8. On the sentient creature

Keep the measurable half: **experience should change competence on new problems, and the system
should know when it does not know.** Today the first half is true within a kind and within a
family, and false across kinds; the second half is the actual defect — a system that reports
`VERIFIED` while answering a neighbouring question has no self-model to contradict. The word
"sentient" adds nothing to either half. The operational target is calibrated competence:
confidence tracks accuracy, refusal is available, and coverage rises on a measured
distribution. That is buildable. "Sentient" is not a test.

## 9. Receipts and non-claims

```bash
python3 canonical/tools/the_exchange_rate_of_one_lesson_20261112_v1.py          # the table above
python3 -m pytest -q canonical/tests/test_exchange_rate_of_one_lesson_v1.py     # 6 passed
```

The four source records are named in the tool's docstring. They are producer-run, one machine,
and nobody else has re-run them; that limitation is inherited here, not waived. The QuixBugs
operator arm is not an equal-budget control for the tree's solver, and the "1,365
demonstrations" figure is arithmetic illustration, never a forecast.

External sources were read, not reproduced: SWE-Skills-Bench (arXiv:2603.15401), SkillsBench
(arXiv:2602.12670), CL-Bench (arXiv:2606.05661), Continual-ARC (arXiv:2611.14505), SkillTTA
(arXiv:2605.16986), DGM (ICLR 2026; arXiv:2505.22954), SICA (arXiv:2504.15228). The OSWorld
leaderboard figures are secondary reporting, not a run performed here.

No capability, family, ownership, benchmark, acceptance, real-task, terminal or sentience claim.
No tolerance widened, no gate opened, no guard touched. `truth.achieved` remains `false`. $0.
Zero model dependency in every result-bearing path.
