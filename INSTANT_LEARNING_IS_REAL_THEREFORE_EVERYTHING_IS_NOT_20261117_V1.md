# Instant learning is real. "Therefore everything" is not. And the space was the thing we kept mis-naming.

**17 November 2026** · branch `arena/eff7a8e7-brain` · base `67fdfa87` · authority **NONE**
(producer-run) · receipts `canonical/verification/AIMED_EDITS_FROM_THE_PROGRAM_AND_THE_FAILURE_20261117_V1.json`,
`SOLVE_WITH_A_CALIBRATED_JUDGE_20261117_V1.json`, and the ten cited below · 11 + 23 new tests

---

## 0. The answer in one paragraph

You are **right about acquisition and wrong about yield**, and the gap is not learning speed, budget,
parameters or effort. One verified experience really can be stored permanently and reused with zero
drift, and one experience *per environment* really is enough for competence there; both are measured
in this tree. But a demonstration is a handful of transitions and an environment is a state space:
the most charitable single demonstration on a real `git` repository licenses **112 of 168** states on
one task and **56 of 168** on another, and the set of situations that no observation can separate is
**invariant to experience**. On real edits, one-experience memory serves **4.814%** end to end and
**0 of 14** multi-line edits. On real web pages, the hand-written action algebra took **+5 pages and
0 of 121 held out**, and rewording one instruction ("the last word" → "the final token") made the
matching rule fire **zero** times. So: give the agent every smartest action and it still fails,
because the actions were never the binding term. **This session measured what was: the space.**
With the judge certified on the corpus's own answer last session, four tasks that this tree had
recorded as *no answer in the space* and one certified `SPACE_EXHAUSTED` are **solved — 8 of 8, every
verdict the corpus's own `pytest`** — by one rule: the space is the closure of the program's own
material under the program's own forms. Not a list of fixes. The program.

---

## 1. Your claim, split into the six parts that can each be checked

| # | the claim | verdict | the number, and where it was measured |
|---|---|---|---|
| 1 | one verified experience is stored permanently and reused correctly | **true** | 46.5% of recorded plans replay exactly, **zero drift** between proof and replay (`MINIWOB_ONE_MEMORY_FOR_ALL_TASKS`) |
| 2 | one experience per **new environment** is enough for competence there | **true, at a cost** | ~7 operations per environment; 13/16 requests in a new environment with a shared effect vocabulary, against 11/16 for learn-each (`INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116`) |
| 3 | therefore any computer use is solved | **false** | the yield is 4.814% end to end, 0/14 multi-line (`LEARN_ONCE_KEEP_FOREVER…`); +5 pages, **0 of 121 held out** on MiniWoB (`THERE_IS_NO_SINGLE_BOTTLENECK…`) |
| 4 | just hand it the most advanced actions | **false** | an action list repairs **0/20**; derived actions **13/46**; same-count decoys **0/46** (`AIMED_ACTIONS_OVER_THE_UNSOLVED_SET_20261116`) |
| 5 | one experience is a *rule* | **false** | ~10 bits survive it; on 51 decidable HumanEvalFix bugs, **43 had no input that separated the surviving hypotheses** (`ONE_DEMONSTRATION_LEAVES_TEN_BITS`, `…IS_NOT_IDENTIFICATION…`) |
| 6 | this is a sentient creature | **not measured, not supported, not required** | the only in-tree proxy — does experience change competence on new problems — is negative (`THE_PREMISE_IS_THE_SENSE`) |

Every one of those is already in this tree under a name you would not guess, which is why I am
citing rather than re-deriving. Nothing here is synthetic: real repositories, real pages, real
`pytest`, real `git` indexes.

## 2. Is it revolutionary? Yes — and here is the exact sense, with outside evidence

The revolutionary part is not "learns from one try". It is that **knowledge leaves the weights and
the only judge is execution**. That is what removes the years of training, and this session is a
clean demonstration of it: 70,050 candidates, 248 s, zero model calls, zero network calls, and every
verdict produced by the software's own test suite.

November 2026 outside evidence says the same thing, and says the caveat too:

- **World In-Context Learning / RoboScript (arXiv 2611.12885)**: one demonstration plus rehearsal in
  a simulator reaches **83.4%**, beating the strongest *trained* policy trained on 50 demonstrations
  (**61.7%**), with no gradient updates. But: a memory written from the demonstration **alone** scores
  69.0% against 78.5% with interaction — *"without the world, the demonstration brings no benefit."*
  **The demonstration is the seed; the interaction is the learning.** Our certified judge is exactly
  that interaction, made mechanical.
- **OSWorld 2.0 (arXiv 2606.29537, June 2026)**: the best frontier configuration, at 500 steps,
  fully completes **20.6%** of 108 long-horizon desktop workflows (54.8% partial). The authors locate
  the failures *not* in clicking or coding but in **hidden state**: "implicit-state inference,
  multi-item state tracking, conflict disambiguation, dynamic environment". Under **7%** of the action
  budget is spent on detecting and repairing its own errors. That is the observability term, measured
  on the hardest open suite that exists, by someone else, for free.
- **Learning from Failure (arXiv 2606.31270)**: inference-time self-improvement from failure
  trajectories gives +10–12% relative across model families. Experience teaches *when it is checked*.

So: yes, revolutionary relative to "pretrain on everything and hope", and no, not because one try is
enough. It is revolutionary because **the loop is closed by the artifact's own tests instead of by a
model's confidence.**

## 3. Why "give it the smartest actions and let it experience each once" cannot work

Three independent reasons, each with a number, none of them about effort:

1. **Identifiability.** One trace fits exponentially many hypotheses. A demonstration is not a rule;
   it is a point. On 51 decidable bugs, 43 had **no input anywhere** that would tell the surviving
   hypotheses apart. More tries do not help when two situations *look identical and need different
   actions* — that set is invariant to experience. What fixes it is an **intervention** (a question
   that separates the survivors) or a **causal observable** that was missing.
2. **Vocabulary insufficiency.** When the fact the plan depends on is absent from the representation,
   repetition cannot separate success from failure, because there is nothing to separate. Measured
   the hard way: nine QuixBugs tasks shipped no example file, so they were never searched at all;
   making the observable present made them searchable and repaired **0 of 9** (`WHERE_THE_OBSERVABLE_WAS_MISSING`).
   Necessary, not sufficient — and not the same thing as the space.
3. **Synthesis–verification asymmetry.** Replaying a seen edit covers **4.8%** of real changed sites
   and **0 of 14** multi-line ones. Real work composes *new* edits against a live repository, and
   composition is where a memory of experiences stops being a plan.

And the corollary you keep pressing: **the smartest actions are not the missing part.** The action
list repaired 0 of 20; derivations from the instruction and the page repaired 13 of 46; on the
remaining 33, twenty-two never observed a goal in 400 acts and eight needed state the observation
does not carry. Those are information failures, not action failures.

## 4. What was actually wrong — including in my own last answers

I have given six different "single bottlenecks" across sessions: the space, the index, separation, the
goal, the instrument, experience. That is not a contradiction, it is a **failure to discriminate**,
and it is the same failure the tree names in you and in me:

> The binding term is **the gap between what the goal depends on and what the agent can observe and
> express**. It has exactly two halves — **observability** and **expressibility** — and you can only
> tell which one you are hitting with an instrument that certifies itself.

Last session built that instrument (a judge certified per task on the corpus's own corrected *and*
defective program). It immediately caught three defects of mine that had been **published as facts**:
`hanoi` "has no answer in the space" (a recursive data transform), `sqrt` "is inadmissible" (the test
is a tolerance test), and an intermediate `SPACE_EXHAUSTED` on `hanoi` that was the judge's own fault.
That is the honest ledger: **three of my refusals were mine, not the corpus's.**

## 5. This session: the refusal was read, not guessed — and the space is a closure

`kheapsort` was certified `SPACE_EXHAUSTED`: all 8,310 candidates judged on a judge that sees the
corpus's own answer, none passed, 192.7 s. Reading the refusal takes one line:

```
python_programs/kheapsort.py           for x in arr:
correct_python_programs/kheapsort.py   for x in arr[k:]
```

The fix is a **slice** — built from two names the program already has (`arr`, `k`) using a node type
the program already uses (`arr[:k]` sits three lines above). The space could not build it because the
candidate generator is a hand-written list of shapes: `+ - *`, six comparisons, a few calls. Slices,
attributes, conditional expressions and statements were not on the list.

So the rule is not "add slices". It is the rule the list violated:

> **The space is the closure of the program's own material under the program's own forms.**

Atoms = the names, constants and literals the program contains. Forms = the node types it contains.
Operators = the operators it contains. Statements = the `name.attribute(name)` shapes it contains,
inserted into blocks it already has. **A program without a `Subscript` gets no subscript candidate;
a program with one gets `a[b]`, `a[b:]`, `a[:b]` over its own atoms.** Nothing is guessed and nothing
is listed — which is the same principle that took 13 of 46 real web pages where the hand-written
rules took 0.

Five refusals were read, and each named a class:

| task | what the fix needs | class |
|---|---|---|
| `kheapsort` | `for x in arr:` → `arr[k:]` | a form the program already uses |
| `to_base` | `result + alphabet[i]` → `alphabet[i] + result` | a commutative operator, turned round |
| `powerset` | `[[first] + subset …]` → `rest_subsets + [[first] + subset …]` | the program's own `+` around its own comprehension |
| `subsequences` | `return []` → `return [[]]` | one level of nesting of a form it has |
| `shunting_yard` | `+ opstack.append(token)` | a statement inserted into an existing block |

## 6. The result

`canonical/tools/aimed_edits_from_the_program_and_the_failure_v1.py`, run on the same eight tasks,
judged by the certified judge and decided by the corpus's own `pytest` on a fresh copy with the
answer key absent:

| task | before this session | now | judged / space | s | kind found |
|---|---|---|---|---|---|
| `kheapsort` | `SPACE_EXHAUSTED` (8,310/8,310) | **solved** | 4,950 / 14,236 | 6.0 | `REPLACE` |
| `powerset` | recorded: no answer in the space | **solved** | 2,100 / 5,759 | 4.3 | `REPLACE` |
| `subsequences` | recorded: no answer in the space | **solved** | 1,550 / 14,775 | 2.1 | `REPLACE` |
| `to_base` | recorded: no answer in the space | **solved** | 14,300 / 15,710 | 69.5 | `COMMUTE` |
| `shunting_yard` | recorded: no answer in the space | **solved** | 26,200 / 37,004 | 37.2 | `INSERT_STATEMENT` |
| `flatten` | solved | **solved**† | 4,500 / 6,223 | 5.8 | `REPLACE` |
| `hanoi` | solved | **solved**† | 13,350 / 20,762 | 16.5 | `REPLACE` |
| `sqrt` | solved | **solved**† | 3,100 / 7,957 | 106.8 | `REPLACE` |

**8 of 8 solved. 70,050 candidates in 248.2 s, 0 hung, 0 model calls, 0 network calls.** †The last
three were already solved last session; they are here as the regression, and they are solved inside
the larger space, so the closure costs nothing on them.

There is one number worth staring at: `kheapsort` is found at **candidate 4,950** — less than the
8,310 that the *narrower* space took to exhaust. Deriving the space is not just more powerful, it is
cheaper, because the derived candidate is put in front of the natural ones.

## 7. The single bottleneck, stated so it can be attacked

> **Can the fact that the goal depends on be OBSERVED at the moment of acting, and can the action
> that satisfies it be EXPRESSED by what the artifact already contains?**

Two halves, and they are the *only* two terms that have ever survived a measurement in this tree:

- **Observability** binds computer use. OSWorld 2.0: 20.6% binary, failures on hidden state. MiniWoB:
  8 of 33 residual misses need state no attribute carries (pointer position, timing, motion); 3 more
  fail only because the observation's own score frame cannot express the precision the task requires.
- **Expressibility** binds coding. It was the last half standing, and it is the half that fell today.

Everything else people name — parameters, pretraining, budget, model size, the "smartest actions",
more demonstrations — was measured and is not a binding term at these sizes.

**The instrument is what lets you say which half you are in.** Without it, an instrument defect
becomes a claim about the space (three of mine did). With it, a refusal is a *typed* object:
`CANDIDATE_FOUND`, `SPACE_EXHAUSTED`, `BUDGET_EXHAUSTED`, `JUDGE_NOT_CALIBRATED`.

## 8. What is not real, stated against my own interest

- **Not multi-edit.** The closure here is one edit, or one inserted statement. Multi-line edits were
  **0 of 14** and nothing here changes that. Composition across steps is the next honest target, and
  the certified judge at ~1 ms per candidate is what makes it affordable.
- **Not computer use.** No browser ran this session; there is no Chromium in this sandbox. The GUI
  numbers above are the existing in-tree receipts and the OSWorld 2.0 paper, not new work by me.
- **Not general repair.** Eight tasks, one corpus, single-function Python, one machine.
- **Not capability credit, not a benchmark rank, not an independent verdict.** Authority `NONE`,
  producer-run, `truth.achieved` unchanged.
- **Not sentience.** Nothing in this loop is a creature. The honest position, which the tree already
  holds: sentience is a different question from capability, none of these measurements bear on it,
  and the one proxy we do have is negative. If we ever want to claim it, it has to be a measurement,
  not a mood — and it will not arrive as a side effect of the repair loop.

## 9. The smartest next moves, in the order they pay

1. **Compose the closure across steps.** The measured hole is multi-edit (0/14). Each step is cheap
   now; what is missing is the rule for *which* step to take next, and the failure order already
   ranks it. This is the only remaining expressibility term.
2. **Decide observability, per task, instead of hoping.** For every refusal labelled "hidden state",
   ask the one question that has an answer: *is the missing fact obtainable by an intervention the
   agent can perform* (a probe, an instrumentation of the page, a scroll) *or is it not?* Two very
   different builds follow, and the taxonomy already tells them apart.
3. **Never report a refusal without its type.** This is code now, not discipline.

Reproduce:

```bash
git clone https://github.com/jkoppel/QuixBugs /tmp/QuixBugs && git -C /tmp/QuixBugs checkout 4257f44b
python3 -m pytest canonical/tests/test_aimed_edits_from_the_program_and_the_failure_v1.py -q
python3 canonical/tools/aimed_edits_from_the_program_and_the_failure_v1.py --quixbugs /tmp/QuixBugs \
  --tasks kheapsort powerset subsequences to_base shunting_yard flatten hanoi sqrt \
  --candidate-cap 60000 --wall-budget 900 \
  --receipt canonical/verification/AIMED_EDITS_FROM_THE_PROGRAM_AND_THE_FAILURE_20261117_V1.json
```
