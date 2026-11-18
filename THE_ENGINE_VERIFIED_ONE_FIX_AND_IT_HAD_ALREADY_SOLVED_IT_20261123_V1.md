# 134 real fixes, one verified repair, and it was one this engine had already solved

*2026-11-23 · `canonical/tools/the_corpus_that_can_answer_the_question_v1.py` · 8 tests ·
corpora `canonical/corpus/single_line_fix_{candidates,commits}_20261123_V1.json` ·
receipts `THE_CORPUS_THAT_CAN_ANSWER_THE_QUESTION_{SHAPE,GATE}_20261123_V1`,
`THE_ENGINE_ON_EIGHTY_NINE_REAL_FIXES_20261123_V1`,
`THE_ENGINE_ON_FORTY_FIVE_UNSEEN_FIXES_20261123_V1` · 0 parameters · 0 model calls · 0 network calls
at measurement time*

---

## The claim, and why the last corpus could not test it

> "Give the model the most advanced actions, let it experience each once, and it owns them for ever.
> So all we have to do is take it through every coding environment and every computer task once."

The previous round answered a narrower version of this and had to admit its own ceiling: of its 30
real commits, **two** were the class the engine claims, so "admissibility ≥ 6" was unreachable, and it
said so — *"the corpus is the limit, not the reader. Any future acceptance has to be measured against a
corpus where more than 2 rows are in class."*

This round builds that corpus out of real history and then runs the unchanged engine on it. The engine
is not touched. That is the point: the only variable is the population.

## The population, built blind

**15,115 commits** across 15 real Python projects. A commit is a *shape* candidate by structure alone —
one source file, at least one test file, and a diff of exactly one removed and one added line — before
anything is executed and before anyone knows whether the engine can solve it.

```
15,115 commits scanned
   181 one-line fixes        (1.2% of commits)
    80 of them expression replacements, not statement changes   (44.2%)
    45 admitted by the project's own verdict                    (24.9% of 181)
    26 of the 45 expression replacements
```

Admission is pytest's verdict on the project's unmodified tests: the commit's test file fails on the
parent and the same tests pass at the commit, with no test the parent passed going red. Nothing here is
labelled by me, and no row is kept because the engine solved it — the engine is not run during mining at
all.

## Two instrument defects, both of which looked like laws of nature

Both were caught by the miner's own tests before a single receipt was written, and both are the failure
mode this project keeps repeating: **a generator defect is indistinguishable from a fact about the world
until you test the generator.**

1. **The gate put the parent's test on the parent.** It asked whether the old test passes on the old
   code — it always does. Measured: `PARENT_PASSES` for **75 of 181** candidates, i.e. three quarters of
   real one-line fixes "not checkable", which would have been reported as the ceiling of the whole
   approach. With the commit's test placed on the parent, the number is 24 of 181.
2. **`ast.parse(line, mode="eval")` cannot read `    return x * x`.** Reading the changed *line* as an
   expression classified **163 of 181** expression replacements as "not an expression", because a
   changed line is almost always a statement whose payload is the expression. Reading the payload, 80 of
   181 are expression pairs.

## The result, on two corpora, both real, neither chosen by the engine

| population | fixes | reaches the demand reader | demand binds to the site | **verified** |
|---|---|---|---|---|
| packaging / tomli / itsdangerous, machine-gated | 89 | 33 | 10 | **0** |
| 11 projects, gated this round, never used by any prior sweep | 45 | 35 | 15 | **1** |
| **total** | **134** | **68** | **25** | **1** |

The one verified repair is `attrs 1c962d15a7` — a message string becoming an f-string. It is the same
commit the previous sweep solved, the row the current binding law was derived on. **On the 45 fixes this
engine had never run on, it derived and exactly verified nothing.**

The 89-fix sweep's refusals are named, not summarised: 50 are not single-expression replacements at all;
23 have no assertion that binds to the site; 5 bind a demand no candidate in the closure produces; 5
have no comparable assertion (an exception, a timeout); 4 are sites that never ran in the failing test;
2 have no failing test under the project's own command.

## What that decomposition means

Each stage is a measured pass rate, and they multiply:

```
in the engine's class            80 / 181  =  0.44
    checkable by its own tests   45 / 181  =  0.25      (68% of checkable commits' tests
    demand binds to the site     25 /  68  =  0.37       discriminate their own change at all)
    closure produces the demand   1 /  25  =  0.04
    ------------------------------------------------------------------
    verified repair              1 / 134  ≈  0.007
```

No stage is near 1 except the first, and the last is 4%. This is not a tuning problem: the engine
already spends zero oracle calls on reading the demand, ~10 µs per candidate inside the recorded
frames, and one exact run of the project's own suite to verify. **Verification is free. What is not
free is knowing what to write.**

Seven earlier rounds spent the *oracle* — tests, input shape, wanted value, documents, protocol verbs,
the author's statement, the repository's callers — and every one of them returned 0 new pins. This round
spends the *proposer* with the corpus problem removed, and returns 1, on a row it had already been given.
The two halves of the answer now line up:

- the environment does not state the value a fix must produce (oracle, 7 sources, 0);
- the environment does not contain the shape a fix must take (proposer, 134 fixes, 1).

Both sentences say the same thing: **the content of a repair is authored, and the author left only the
check.**

## What is real, and what is not

**Real.** Instant learning, exactly and for free, wherever a check exists. A demonstration plus one
contrast produces a pin; a pin costs no parameters, no training, no storage beyond the assertion; a
verified pin passes at the fixed state and fails at the reverted part. A quarter of real one-line fixes
carry exactly such a check in their own commit, and this round admits them mechanically, at 45 of 181.
Adaptation to a new environment is a measured cost (29 trials, repaid at the 26th request), not a hope.

**Not real.** That this constitutes coding capability, or that repetition converts it into one. The
agent that "experiences" these 134 fixes and keeps what it sees keeps nothing that would let it write
the next one: the assertion names a value the site never produced, or the fix is not an expression at
all. **The failure is not slow learning. It is missing content**, and no schedule of exposure supplies
content that is not in the environment.

**The single bottleneck, stated in one sentence.** *Everything the environment can give — the check, the
localisation, the verification, the memory — this tree already extracts exactly and for free; the one
thing it cannot extract is what the program should do next, because that is the author's decision and it
is written nowhere.*

## The smartest three moves, in the order the numbers support them

1. **Buy content where it is cheapest: ask, instead of reading.** The commit message names the change
   50–55% of the time and specifies it **0 of 19**; the repository's 5,949 documents changed nothing;
   the callers pass variables. So the content has to be *elicited* — one question, phrased so that the
   answer is executable, which is what `the_smallest_question_that_makes_this_checkable` built. This is
   the only route that is both free of parameters and guaranteed to produce content.
2. **Spend parameters on exactly one thing, and only where they are measured to pay.** Every number above
   says the same: the proposer is the only term that is not already optimal. A generator whose *only*
   job is `(site, demand) → edit`, trained on **verified** triples and nothing else, is the one
   place where parameters are not a knowledge house — every bit carries a repair that passed an exact
   check. Everything else stays instant: localisation, verification, memory, adaptation.
3. **Stop buying oracle, and stop re-measuring it.** Seven sources, 134 fixes, two corpora: the
   marginal value of another oracle round is zero, and the tree has the receipts to prove it. Any round
   that returns to the oracle question has to answer this table first.

## What this does not claim

- **Not that the engine is the best possible proposer.** It is the tree's demand-driven closure, run
  unchanged. A different proposer could do better on the same 45; that is exactly the argument for
  move 2, and it is not evidence against the corpus.
- **Not that 45 of 181 is a rate for all software.** 81 of the 181 candidates could not be executed at
  all in this sandbox — old commits against modern dependencies (`soft_unicode`, `SNIMissingWarning`,
  `trustme`, `httpx2`). That is an environment fact with a named cause, not a law about code, and it is
  reported as a rejection with its message.
- **Not that "0 verified" means no repair is possible.** It means no repair was *derived and verified* by
  this engine on this material. The strongest honest form is the class-level one: **0.7% of 134 real
  fixes, with the single hit rehearsed.**
- **Not that a human would do worse.** A human reading these diffs knows what `_SkipClose` must do
  because a human decides what the program is for. That is the content the machine does not have, and
  the measurements above are a price list for obtaining it.
