# The guide is a test suite. 94% of it is prose, and that decides the question you asked.

*Round: `THE_GUIDE_IS_A_TEST_SUITE_20261204_V1` · 2026-12-04 · branch `arena/9be5cc43-brain`, base `8b3b0289`*
*Receipt: `canonical/verification/THE_GUIDE_IS_A_TEST_SUITE_20261204_V1.json`*
*Instrument: `canonical/tools/the_guide_is_a_test_suite_v1.py`*
**Model calls 0 · parameters stored 0 · network at run time 0**

---

## 0. Your idea, and what the machine says about it

> "All he should do is go into any new arbitrary environment, ask the right question, and know all
> the things he should know about from instant knowledge, from perfect research on the web — because
> in today's world anything on the computer already has a guide."

That is a real mechanism, and this round executed it. Two halves of it are now measured, and they
point in opposite directions:

| your claim | verdict | the measurement |
|---|---|---|
| **A guide already contains the actions** | **true, and executable** | 189 examples found in 9 real guides; **136 ran**; **128 matched the output the guide itself printed** (94%) |
| **The guide's printed output is a check** | **true** | 71 of 86 machine-made wrong inputs were separated by the guide's own stated answer; **0 real blind spots** |
| **A guide teaches something that transfers** | **true, narrowly** | 2 of 2 admitted rules reached inputs the guide never showed, 4 of 4 instances |
| **"He should learn everything in the environment"** | **false, and now arithmetically** | **5.96% of the documentation is checkable by running it. 339,648 of 361,161 bytes are prose that no run can confirm** |
| **"Ask the web what he doesn't know"** | **wrong target, measured** | the missing thing is not more text. 94% of what you would fetch is the part no run can decide |

**So: goal-directed, not exhaustive — but the reason is not the one in the question.** The reason is
not that learning everything is too expensive. It is that **almost everything in a guide is not
learnable by execution at all.** Fetching all of it would buy a system that has read a lot and can
check almost none of it.

## 1. What this round found that was already settled, so it did not rebuild it

Thirteen rounds of this project had already named this same seam, in these words:

* `THE_VERIFICATION_HALF_IS_FREE_THE_SYNTHESIS_HALF_IS_EMPTY_20261116` — 0 of 6 real fixes solved,
  and "not one of the six failures is a search failure";
* `THE_REPERTOIRE_IS_A_QUERY_20261129` — 437 programs, 4,621 options, 47 s, **0 of 80 accepted
  options changed a byte**, because *a printed option is a modifier, not an action*;
* `A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG_20261203` — a check that is not run
  cannot be wrong, and 281 of 370 citations were vacuous.

And the live defect this round started from: `perfect_algorithm_v1.run()` fetches instant knowledge
and then returns `OPEN__NO_PLAN_AFTER_SCAN` — **it stores documents and uses none.** §10 fixes that.

What none of them had done, and what your idea makes possible, is the synthesis half *from a real
document*. That is this round's work.

## 2. What was built: the guide read as a test suite

A documentation example is a test the author wrote by accident. It states a command and the output
that came back. So the instrument does three things and no more:

1. **Extract.** Every docstring in a source file, via `ast`; every fenced block in a README, via the
   fence; every `>>>`, `...` continuation, `$` prompt, and the answer after it.
2. **Replay.** The session in one interpreter, in the module's own namespace (the doctest rule), and
   the answer echoed the way the interpreter echoes it. Shell examples run with both streams kept.
3. **Score.** Line for line against what the guide printed, honouring the author's own `...`.

| what | number |
|---|---|
| guides read (6 stdlib modules + 3 READMEs) | 9 |
| examples extracted | **189** |
| examples that ran | **136** |
| **matched the guide's printed output** | **128 (94.1% of those that ran)** |
| refused by the interpreter | 53 |
| mismatched | 8 |

**Every one of the 53 refusals and 8 mismatches is this instrument's limit, not the guide's.** They
are counted, sampled in the receipt, and not repaired by hand: a guide line that needs a session
binding established elsewhere (`s = SequenceMatcher(...)` in a different docstring), a `pycon` block
that redefines a class, a `linear_regression(x, y)` whose `x`/`y` were set in a different example.
Naming them is the honest form of 94%.

## 3. Is the guide's output a *check*, or just decoration?

The last round's hardest lesson was that a check must be able to say **which** thing it is looking
at — 8 of 8 cited checks accepted a decoy. So every matched example was replayed with a
machine-made wrong input:

```
86 mutants · 71 separated by the guide's own printed answer · 15 equivalent by construction · 0 real blind
50 of 128 examples separate every non-equivalent mutant
```

The 15 "equivalent by construction" are the round's own correction. `median([1,3,5])` → `[1,3,5,7]`
is still `3`; no correct program separates those, and counting them as blindness would blame the
check for the mutant's degeneracy. **A decoy that cannot be separated is not a blind check.**

## 4. What is worth keeping, and what the three tests refused

The store is deliberately trivial — a JSON list — because the science is which rules earn a place:

| rule | example matched | decoys separated | transferred to held-out | verdict |
|---|---|---|---|---|
| `textwrap.shorten` | yes | yes | 2 of 2 | **admitted** |
| `statistics.median` (sort-invariance) | yes | yes | 2 of 2 | **admitted** |

`textwrap.shorten("Hello  world!", width=12)` → `'Hello world!'` is one example. The kept rule is
not that answer; it is the callable plus the property the guide states — *fits the width, ends in the
placeholder* — applied to `"Documentation is a test suite nobody grades"` at width 18, a sentence no
guide contains. That is the difference between a cache and a rule, and it is the only distinction
worth storing.

`stored_bytes: 603.` A store with no refusals is a store nobody tested; this one can refuse, and the
test that does the refusing is named next to each row.

## 5. The number that answers your question

**5.96%.** Of 361,161 bytes of real documentation, 21,513 are transcript — prompts, answers,
continuations — and 339,648 are prose. Per guide:

| guide | checkable |
|---|---|
| click README | 25.5% |
| requests README | 15.7% |
| statistics | 9.5% |
| difflib | 9.1% |
| httpx README | 7.9% |
| pickletools | 6.3% |
| fractions | 3.5% |
| enum | 1.3% |
| textwrap | 0.8% |

This is the arithmetic answer to *"should he learn everything in all the environments, or be
goal-directed?"* — **Be goal-directed, because exhaustive reading cannot be checked.** A system that
ingests 100% of a guide can verify 6% of it. The other 94% is not knowledge it can act on with any
confidence; it is context with no oracle. And the same ratio is why "ask the web" is a weak answer to
a gap: what comes back is 94% the kind of text no run can confirm.

## 6. The seam this round does **not** close

A transcript is checkable. A prose claim is not, and this round does not read it. It measures how
much there is and says so. That gap is the frontier's too: **VerifierBench** (arXiv 2610.28679,
Oct 2026) reports balanced accuracy of agent-generated verifiers at only 62.1% across 19 models,
with most false rejections coming from verifiers that accept no tested solution at all — and
**AutoTools** (2025) builds its entire pipeline on turning documentation into callable functions and
verifying them by execution, exactly the half built here. Neither is our system's capability; both
are the measured size of the problem.

## 7. The live defect this round fixed

`perfect_algorithm_v1.run()` reached the knowledge step, fetched documents, wrote them into the
receipt, and then **returned `OPEN__NO_PLAN_AFTER_SCAN`**. The loop was an open circuit: knowledge went
in, nothing came out. The next round's build target is the wire: a fetched example-shaped line is
compiled by the same extractor above, executed, and scored by the guide's own answer — so the circuit
closes on something the guide itself vouches for, and not on a summary.

## 8. What is real and what is not

**Real.** 128 real documentation examples executed and matched their own printed output with no
model. 71 of 86 wrong inputs separated by that output. 2 rules admitted by three tests and transferred
to inputs no guide contains. 5.96% checkable, measured over 361 KB of real docs. Every number above
comes from a command in this session.

**Not real.** That this solves computer use, or that it is a benchmark result — no OSWorld, no
FrontierSWE, no Terminal-Bench was run, and none was runnable here. That arbitrary documentation is
handled — the extractor handles `>>>`/`$` transcripts and nothing else. That the store is a memory
design — it is a 603-byte list proving three tests can refuse. That "learning from a guide" is
general: 2 rules from 189 examples is a lower bound on what is *admissible*, not a measure of
capability.

## 9. Where I was wrong in this round, kept as tests

Three mistakes, each now a regression test rather than a lesson:

1. **I read a `.py` file with the fence reader.** Six stdlib guides gave 0 transcripts and I nearly
   wrote "the guides contain no examples." Python uses `::` + indentation, not fences.
2. **I compared expected output against the *file's* indentation** and swallowed the prose and the
   closing `"""` after every module-level doctest. The fix was to stop guessing: `ast` knows where a
   docstring ends.
3. **I replayed doctests in a fresh namespace**, refusing 39 examples with `name 'mean' is not
   defined` — the guide was right and the replay was wrong. `testmod` runs a module's docstring in
   `vars(module)`; so does this now.

## 10. Reproduce

```bash
python3 canonical/tools/the_guide_is_a_test_suite_v1.py --receipt /tmp/r.json   # ~5 s
python3 -m pytest canonical/tests/test_the_guide_is_a_test_suite_v1.py
```

The guides are read from the interpreter's own standard library (version-matched, offline) and from
three READMEs fetched **once while building**. Nothing in the run touches the network.

---

*A guide is the only place where the author wrote down what happened. That makes it the cheapest
verifier on the machine — and the same fact makes it mostly unusable: 94% of it is the part the
author did not write an answer for. Read the 6%.*
