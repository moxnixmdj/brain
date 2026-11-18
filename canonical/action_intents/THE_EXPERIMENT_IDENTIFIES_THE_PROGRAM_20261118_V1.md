# The experiment identifies the program

*1–4 chosen queries collapse 399–400 candidates. Not memory. Experiment.*

## The question, restated correctly

The standing thesis: give the model the most advanced actions, let it experience each once, and it
owns them permanently -- which would then cover any computer use. The previous build measured one
observation identifying one bug in six and invited the obvious conclusion: experience is weak.

That conclusion is wrong, and the correction is the whole result. **An observation identifies a
hypothesis exactly as far as the candidates are behaviourally distinguishable on it** -- log2 of the
number of behavioural classes it induces among the live candidates:

| bug | the corpus case that fails it | candidates before | after | bits |
|-----|------------------------------|------------------:|------:|-----:|
| `lis` | one list | 399 | **1** | 8.64 |
| `kth` | one list and one index | 400 | 400 | **0.00** |

Same instrument, same corpus, same size of hypothesis space. One case carried 8.64 bits; the other
carried none, because every one of the 400 candidates behaves identically on that input. The
observation was not weak. It was **uninformative**.

So the design question this project has been asking -- *how do we store what we experienced* -- is the
wrong question. The right one is: **which experiment identifies the program fastest.**

## The measurement

Object: a **behaviour table**, candidates x probes -> output. Identification is set arithmetic: split
the survivors on the observed output, keep the class the oracle names. The next experiment is the
probe that splits the survivors hardest. Nothing is stored. Nothing is trained. Every part is computed
from the program and the oracle.

| bug | candidates | chosen queries | survivors | held-out agreement |
|-----|-----------:|---------------:|----------:|--------------------|
| `lis` | 399 | **3** | 1 | **26/26** |
| `get_factors` | 399 | **2** | 1 | 22/23 |
| `kth` | 400 | **2** | 1 | 7/14 |
| `mergesort` | 399 | 2 | 3 | -- |
| `next_permutation` | 399 | 4 | 2 | -- |
| `possible_change` | 399 | 1 | 0 | -- |

Three queries identify a fix that is right on every one of 26 probes it never saw. Against that, the
corpus's *given* cases needed more than it had for five of six bugs (previous build).

## What the failures are, exactly

None of the three failures is an identification failure, and saying so precisely is the point:

- **`possible_change`** loses every candidate on the first probe: the fix is **not in the pool** at the
  chosen site. No number of queries can find a program the material cannot build. Evidence cannot
  substitute for expressiveness.
- **`mergesort`, `next_permutation`** stop with 3 and 2 survivors that **no probe in the pool
  separates**. The probes are not discriminative enough -- a property of the material, not the evidence.
- **`kth`** converges to one candidate that is wrong on 7 of 14 held-out probes, at a site where the
  pool cannot express the fix at all (`kth(above, k)` is replaced whole; the fix is to its argument).

So the bottleneck decomposes exactly, and this is the answer to "what is the single bottleneck":

> **Two things, in this order: (1) can the material build the fix at all, and (2) does the experiment
> separate the candidates that the material admits.**
>
> Memory is not on the list. Speed is not on the list. Vocabulary -- as a *size* of a store -- is not
> on the list either; *expressiveness at the site* is a different thing and it is first.

## What this says about the thesis

- **"Once and permanent" is a claim about the prior, not about experience.** Experience can only
  eliminate hypotheses whose behaviour differs on what was observed. Everything left standing is
  chosen by the prior. With a bad prior, one observation leaves 400 hypotheses; with a good one, one.
- **The revolutionary move is not faster learning; it is choosing the lesson.** A system that picks
  its own probes reaches identification in 3 queries where a system fed by a corpus does not reach it
  at all. That is not an incremental gain over passive experience -- it inverts who decides what is
  learned.
- **Nothing needs to be stored for this to work.** The behaviour table is derived on demand, discarded,
  and re-derived. "The best part is no part" is not a slogan here: the memory this project has been
  building for a year is what you get when you cannot choose your experiments.
- **"Any computer use" inherits the same two obstacles and nothing worse.** In an environment, the
  "pool" is the action vocabulary at the current state and the "probe" is a chosen action; the oracle
  is the goal state. Identifiability and expressiveness bind there for the same reasons and in the
  same order.
- **Sentience remains the wrong target.** It has no falsifier. What the table above describes is a
  machine that converts chosen interactions into identified programs, verified on interactions it
  never used. That is the whole of what is real here.

## Ship list

- `canonical/tools/the_experiment_that_identifies_v1.py` -- behaviour table, greedy experiment design,
  held-out verification against the corpus's own reference program.
- `canonical/verification/THE_EXPERIMENT_IDENTIFIES_THE_PROGRAM_20261118_V1.json` -- every number,
  and the diagnosis of all three failure modes.
- A prior-measurement tool was built during this work and **deleted**: its headline metric ("bits one
  observation can give" = log2|Y|) was wrong -- an observation gives log2 of the number of behavioural
  classes it induces, not log2 of the output space. Publishing it would have been a false theorem.
  The correct statement is the one above, and it is measured.
