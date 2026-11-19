# Breadth buys what repetition cannot

**2026-12-01 · branch `arena/791f90af-brain` · receipt `canonical/verification/BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201_V1.json`**

---

## 1. First, a retraction of my own last number

Last round reported **79 statements** consistent with everything the user ever said on TARBALL, and called
that the residual. It was inflated: a conjunction whose second conjunct is true on every run — or repeats
its first — has the same behaviour as the smaller statement. Of the 79, **75 are redundant**. The user's
goal has **4 minimal statements** on TARBALL, not 79.

The correction belongs first because it makes the user's claim *stronger*: one machine already pins the
goal to four sentences, and the failure I claimed was partly an artifact of my own counting. A count that
flatters my argument is the same sin as a test on bugs known to pass.

## 2. The claim under test

*Experience once, in a new arbitrary environment, and it learns the goal permanently.*

If breadth of experience is what identifies a goal, then the class of statements carrying the goal must
shrink as environments are added — and the only question that decides the claim is whether it shrinks
**to one**.

So: one grammar over the union of every literal three machines can hold — a **tarball**, a **filesystem**,
a **SQLite database** — 244 terms, closed under conjunctions of two, **29 890 hypotheses**, each evaluated
once into a bitmask over **555 executed runs**. A statement's behaviour is its mask; a statement is
*minimal* for a behaviour if no conjunct of it alone already has that behaviour. All **seven subsets** of
the three machines are measured, so the marginal value of each environment is a count.

## 3. Results

**Resolving power** — how many behaviours the world can exhibit:

| | TARBALL (231 runs) | FILESYSTEM (196) | SQLITE (128) | **union (555)** |
|---|---|---|---|---|
| behaviours | 353 | 129 | 78 | **622** |
| behaviours with a unique minimal statement | 190 (54.1 %) | 82 (64.6 %) | 29 (38.2 %) | **354 (57.1 %)** |
| mean class | 2.06 | 1.71 | 4.04 | **2.09** |
| largest class | 20 | 10 | 20 | **38** |

**The goal's class, as environments are added:**

| environments | 1 (TARBALL) | 2 (best pair) | **3 (all)** |
|---|---|---|---|
| minimal statements for the user's goal | **4** | **2** | **2** |

The second machine removes two statements. **The third removes zero.**

**The residual, after 555 runs of three different kinds of machine:**

```
created_once[probe_new_content]
monotone[probe_new_content] ∧ final:count[probe_new_content]==1
```

Two sentences. The first says *exactly one increase and no decrease*; the second says *never decreasing and
exactly one copy at the end*. No run of any of the three machines tells them apart. **The price of the
residual is one question of the user** — `log2(2) = 1` — and the number of runs that can pay it is **zero**.

## 4. What is false, and what it costs

1. **False: "instant learning in new environments" identifies the goal.** It shrinks the class fast and
   then stops: 4 → 2 → 2 across three environments, with the third buying nothing. The residual is
   structural, not a budget.
2. **False: that the ambiguity is an artifact of too little experience.** It is an artifact of the *world's
   reach*: the two sentences differ only on runs no machine in this set can produce (a decrease after an
   increase that still ends at one copy).
3. **False: that most goals are even pinned by one sentence.** Only **57.1 %** of the union's 622
   behaviours have a unique minimal statement; the mean behaviour carries **2.09** sentences and the worst
   carries **38**. For the average goal, breadth does not finish the job either — it just moves the residual.
4. **False: that breadth keeps paying.** The second machine removed 2 of the 4 statements; the third
   removed 0. That is the saturation the previous round pre-registered as a falsifier, and it landed.
5. **False — my error, again, and the third kind of it:** that a count of statements is a count of
   intentions. 75 of the 79 were the same intention written redundantly. Behavioural minimality is the
   only counting rule that survives.
6. **False: that any of this is coding capability.** No edit is composed here. This prices what an edit
   would be *for*.

## 5. The criteria, as written before the receipt run

The tool was written after a prototype probe over the same three pools, and the receipt says so in
`criteria_were_declared_after_a_prototype_probe`. The criteria are therefore **confirmatory**, and they are
written as structural claims rather than as the numbers seen, so that an edited tool cannot pass them by
accident:

| | |
|---|---|
| B1 the union has strictly more behaviours than any single machine | **MET** — 622 vs 353 / 129 / 78 |
| B2 breadth strictly shrinks the goal's minimal class | **MET** — 4 → 2 |
| B3 the residual is still greater than one after every machine | **MET** — 2 |
| B4 the third machine removes fewer statements than the second | **MET** — 2 removed, then 0 |
| B5 the residual is log2(class) questions of the user, and no run pays one | **MET** — 1 question, 0 runs |
| B6 zero model calls, zero parameters | **MET** |

## 6. The law

> **Breadth buys what repetition cannot, and then stops.**
>
> Repetition saturates: the 231st run of a machine teaches nothing the 200th did not. Breadth does not
> saturate the same way — a second environment halves the goal's class (4 → 2) and adds 270 behaviours —
> but it saturates too, and at a residual that is a property of what the environments can exhibit, not of
> the learner. That residual, for any behaviour, is a class of minimal statements, and its size is a price
> in **words**: `log₂(class)` questions the user must answer, none of which any run can answer.

## 7. What is real and what is not

**Real.** The resolving power of a set of environments is countable and small (622 on 555 runs). The
goal's class is countable and it *moves* with breadth (4 → 2), which is the first direct evidence in this
project that new environments buy identification — the user's intuition is right about the direction, and
this is the round that measures the size of what it buys. Every number is a bitmask operation over
executed runs; 109 s, no model, no parameters.

**Not real.** "Permanently." After every run of three kinds of machine, two sentences remain, and the
difference between them is not something any of those machines can produce. "Mostly." Two thirds of
behaviours (354 of 622) are pinned by one statement — the other 268 are not, and the worst needs 38.
"Learn the goal from experience." You learn a class; the class ends in words.

**On sentience, one line.** The missing object is not a mechanism inside the learner — it is the sentence
the user meant, and the measurement says exactly how many bits of it are missing: `log₂(class)`.

## 8. The single bottleneck

**The residual class — and the fact that it can only be closed by language, not by experience.**

Everything else is now cheap and measured: the environment's model (229 of 231 decided, 0 errors at a
depth never measured), the statistic (3 cells), the questions to the ceiling (8 judgments for 8.46 bits),
the breadth (622 behaviours from 555 runs, 4 → 2 on the goal). What remains is one bit for this goal and
`log₂(class)` in general — and that bit is not in any trace. **The next capability is not a bigger learner.
It is an intake for the user's sentence**, with a known price: one question per bit, asked *after* the
world has been exhausted, never before.

## 9. Next step, pre-registered

**Build the intake and price it.** Take the residual class, put both sentences to a user, and measure two
things that can fail: (i) does one sentence of the user's reply collapse the class to one, at a cost of
`log₂(class)` questions or fewer; (ii) does the *chosen* sentence then predict verdicts on a machine it was
never fitted on — if it does not, the class was not the ambiguity and this round's residual is wrong.

Pre-registered falsifiers: more than `log₂(class)` questions to collapse the class, or a chosen sentence
that mispredicts on held-out runs of a fourth environment, kills the claim that the residual is exactly a
matter of words. Corpus, stated plainly: **not SWE-bench**. Three CLI machines, depths 5/4/4, no network at
run time, no model, no parameters. Depth 6 is out of reach here and named, never simulated.
