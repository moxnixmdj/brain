# One demonstration leaves ten bits — identification cost measured in a real program space

**2026-11-16 · branch `arena/524c902a-brain` · 23 real published bugs · no model, no weights, no network**

Receipt: `canonical/verification/IDENTIFICATION_COST_IN_A_REAL_SPACE_20261116_V1.json`
Tool: `canonical/tools/identification_cost_in_a_real_space_v1.py` (8 tests)
Space: the merged generator's candidates for each bug (median **13,212**, max **25,346** programs)
Discriminator: the tree's own `canonical/runtime/finite_identifiability.py`, reused, not rewritten.

---

## The question, and the shape of a real answer

> *Instant learning and instant learning in new environments are solved perfectly. So give the model
> the most advanced actions, let it experience each once, and it knows them permanently — therefore
> all computer use and the most advanced software engineering are solved. Right?*

The direction is right. The word "therefore" is where it breaks, and it breaks in a place that can be
counted rather than argued. This note does three things the previous four did not:

1. It shows that the **three different "single bottlenecks" named in this repository on this very
   day** are not rival answers. They are the three factors of one equation, and each was reported as
   if it were the whole.
2. It measures identification cost **in the space real repairs actually live in**, which nobody here
   had done: every earlier identifiability number came from a hand-built space of about thirty toy
   rules.
3. It reports that the tree's own discriminator kernel is solving the **wrong objective** for this
   setting — never better, and up to **9×** worse — and that the correct objective is one line.

---

## 1. The claim is five steps, and four of them are not learning problems

| # | step | measured | receipt |
|---|---|---|---|
| 1 | an action can be taken at all | **55 of 92**, 56 after 2.5× compute | `MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json` |
| 2 | one success ⇒ a rule for the next instance | **60.0%** vs **15.0%** cache | `OPEN_BENCHMARK_ONE_SUCCESS_GENERALISATION_20261114_V1.json` |
| 3 | a stored rule is correct | ungated permanence **breaks a correct program** | `test_lesson_admission_gate_v1.py` |
| 4 | N verified skills ⇒ a verified sequence | two correct skills compose to a **no-op** | `SKILLS_DONT_COMPOSE_20261112_V1.md` |
| 5 | a learned procedure ⇒ any computer use | best 2026 agent **20.6%** binary, OSWorld 2.0 | arXiv:2606.29537 |

Step 2 is real and it is the good news: four times a cache, on pages nobody here wrote. Steps 1, 3,
4 and 5 are why "therefore everything" does not follow. A product of five factors with a zero in any
position is zero, however good the other four are.

## 2. Three bottlenecks were named today. They are one equation.

| note | named bottleneck | what it is, exactly |
|---|---|---|
| `THE_EDIT_SPACE_IS_THE_PROGRAM_NOT_A_LIST_20261116_V1.md` | the **unit of a hypothesis** | the space must contain the truth |
| `THE_VERIFIER_IS_KNOWLEDGE_NOT_LEARNING_20261116_V1.md` | the **verifier** | an oracle must read the outcome |
| `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md` | the **observable** (state merges) | the observation must distinguish |

Identifying which program is true in a space `H` given observations `O` requires, simultaneously:

```
   ∃ h* ∈ H   that is the truth          <- the space contains it      (vocabulary / unit of hypothesis)
 ∧ ∃ o ∈ O   that h* answers differently  <- the observation separates (the observable)
 ∧ o is computable and affordable        <- the oracle reads it        (the verifier)
```

**All three notes were describing one term of this equation and calling it the equation.** That is
not a failure of any of them — each measured its term correctly — but it is why the project has
produced three "the single bottleneck is X" statements in one day that cannot all be the answer.

The honest single bottleneck is **separation**: the *pair* (a space containing the truth, an
observation that splits it). The pair is why "one demonstration" cannot be enough, and it is also why
"get more experiences" cannot be enough — repetition of the same observation separates nothing. What
this turn adds is a measurement that says, **per task and in one question, which term is binding.**

## 3. The measurement: identification cost in the real space

Protocol, with nothing hand-written anywhere in it:

- **space**: every candidate the merged generator enumerates for the bug (`compile()`-checked)
- **one demonstration**: the corpus's *first* published input/output example, and nothing else
- **a question**: "does the true program agree with *this* input?" — answered by the corpus's
  published expected value, never by the answer-key source
- **repair**: a candidate that passes every published example
- **sufficient**: every surviving candidate is a repair — no *wrong* program is still alive

| measured | value |
|---|---|
| tasks measured | **23** of 31 (5 have <2 examples, 2 hit the budget, 1 instrument timeout) |
| median space size | **15,600** programs |
| survivors after **one** demonstration | median **1,037**, max **16,480** |
| bits left unresolved by one demonstration | median **10.018**, max **14.008** |
| questions to *sufficient*, where a repair is in the space (16 tasks) | **21 total**, mean **1.31** after the first demonstration, worst **3** |
| tasks where the space contained **no** repair (7) | **0** made sufficient by any number of questions |

Three things follow, none of them an opinion.

**3.1 One demonstration leaves about ten bits.** Median 1,037 programs survive it; max 16,480. That
is the quantified form of "one try buys a rule that is wrong": the rule is not one of two, it is one
of a thousand. This is the first time that number has been measured where repairs live rather than
among thirty toy rules, and it agrees with the toy measurement (13.05 of 32, ~2.76 chosen
experiences) rather than overturning it.

**3.2 When the space is right, one well-chosen question after the demonstration is enough.** In all
**16** tasks that contained a repair, "no wrong program survives" was reached in
**1.31** further questions on average, worst **3**. Not nine. Not one per
test. **The suite's size is not what identifies the fix; the choice of question is.** A published
suite of 6–12 examples is, for this purpose, redundant by roughly an order of magnitude.

**3.3 When the space is wrong, no question helps — and the instrument says so after one question.**
In all 7 tasks with no repair in the space, the live set went empty (`CONTRADICTION`) or
stayed wrong (`INSUFFICIENT`). No query strategy rescues them; that is the vocabulary wall, measured
as a *refutation* of the space rather than as a budget failure. This is exactly the split the repair
round measured from the other side (18 of 40 repaired): the binding term on those tasks is the space.

### 3.4 The tree's own kernel is optimising the wrong thing here

`select_discriminator` minimises the **worst case** remainder of a split. That is the right objective
when the answer to a question is unknown. Here it is never unknown: the question is *"does the true
program agree with this input?"*, and the true program agrees by definition, so every candidate
predicting disagreement is eliminated **with certainty**. The correct rule is therefore

```
next question = argmax |{h ∈ H_live : h predicts NO on this input}|      (maximum elimination)
```

Measured across the 23 tasks, same outcome tables, only the selection rule differing:

| selection rule | questions |
|---|---|
| **maximum elimination** (correct here) | **89** |
| corpus's own published order | 105 |
| random unused question (mean of 25 shuffles) | 99.76 |
| kernel's minimax balance (`select_discriminator`) | **112** |

Max-elimination is ≤ minimax on **all 23** tasks and strictly better on **8**,
worst case **8×** (`knapsack`: 1 question vs 9). The kernel is not wrong as
mathematics; it is being asked the wrong question. **A library is not an answer until the objective is
checked against the situation** — which is the most reusable lesson in this note.

## 4. What this does and does not say about the plan

**Real.** Instant storage. One-demonstration generalisation on real code (60.0% vs 15.0%). Admission
that refuses a harmful lesson. A generator with no model, no weights, no network, repairing **18 of
40** published bugs, and now a discriminator that reaches sufficiency in ~1 question after one
demonstration whenever the space is right.

**Not real, on the same evidence.** That one experience is a rule — it leaves ~10 bits. That more
environments buy coverage — 2.5× the compute bought 1 page in 37, and 0/10 for a new *kind* of task.
That "the smartest actions" are the missing piece — actions were never the binding term; **the pair
(space, observation) is**. That any of this is sentience: the only in-tree proxy for a creature,
*does experience change competence on a new problem*, is measured and negative.

**The single bottleneck, stated so that it can be tested rather than admired: separation.** Not the
learner (learning selects inside the space), not the budget (coverage is inelastic in budget), not the
oracle alone (an oracle that can only say yes/no cannot split a space that was never right). Two
factors, one equation, and now a one-question test for which factor binds a given task.

## 5. The smartest things to do, in the order they pay

1. **Choose the question instead of accepting the suite.** Free: 8× fewer
   questions at best, never worse, and it is 89 lines of arithmetic, not a project.
   This is the single highest return in the tree today.
2. **Spend on the space where the instrument says the space is wrong.** 7 of 23
   tasks here were refuted in one question — a cheap oracle for *where to spend*, which is what the
   repair round's family work should be steered by.
3. **Widen the observable only where the observation is provably insufficient** — the MiniWoB `STATE`
   pages (3 of 37), not everywhere. Everywhere else it is wasted work.
4. **Treat the verifier as the thing you are building, not the thing you have** (the 2026 field
   agrees: 80.2% of agent-written test patches carry weak or absent oracles).
5. **Kill list:** more demonstrations as a coverage mechanism; more environments with the same
   generator; quoting a saturated benchmark (SWE-bench Verified is retired and contaminated — OpenAI
   stopped reporting it in Feb 2026); any document that asserts a bottleneck without a per-task test
   of which factor binds.

## 6. Non-claims

- 23 of 31 tasks; 8 unmeasured (5 with fewer than two examples, 2 budget, 1 instrument timeout). The
  unmeasured ones are listed in the receipt and are **not** counted either way.
- The oracle here answers per input. Real work usually has no such oracle; this makes the numbers an
  **upper bound** on what identification can buy, not a promise about SWE-bench.
- Passing every published example is **not** correctness — it is consistency with the suite.
  Sufficiency means "no distinguishable wrong program survives", not "the program is right".
- Format and float comparisons follow the corpus's own `==`; where its data is internally
  inconsistent the instrument reports `CONTRADICTION` rather than smoothing it over.
- Producer-run, one machine, authority **NONE**. No tolerance widened, no capability registered,
  `truth.achieved` unchanged.
