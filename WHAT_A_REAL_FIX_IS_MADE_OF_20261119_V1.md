# What a real fix is made of, and what that costs

**Round of 2026-11-19. Receipt: `canonical/verification/WHAT_A_REAL_FIX_IS_MADE_OF_20261119_V1.json`. Tool: `canonical/tools/the_edit_is_in_the_files_own_alphabet_v1.py`. Corpus: `canonical/corpus/real_fix_pairs_20261119_V1.json`. 21 tests. Zero model calls, zero parameters, zero network.**

## The claim this round answers

> Instant learning is solved, and instant learning in a new environment is solved, so give the system the most advanced coding and computer-use actions, let it experience each one **once**, and it learns them permanently. Then everything on a computer is solved, including frontier software engineering.

Two rounds ago I answered "genuine for operators, not for edits". That was an argument. This is the number.

## What was measured

The repository already holds 87 admitted real fixes — three libraries, one source file and one test file each, each verified at mine time to **fail at the parent and pass at the fix**. Until this round every measurement in the repair line took the changed hunk as given; the price of *finding* the hunk had never been counted. Both source states are now vendored next to the corpus, so the measurement runs offline.

Each fix is classified by the minimum number of tokens that separate the two states (true Levenshtein over token streams — a greedy alignment over-counts, and over-counting would understate what any vocabulary can reach).

| | count | share |
|---|---|---|
| the fix **adds or removes a line** | 72 | 83% |
| the fix changes tokens on lines of the same count | 15 | 17% |
| …contained by **1** token | 8 | 9% |
| …contained by 2 / 3 / 5 tokens | 9 / 11 / 13 | — |

And of the eight fixes that are exactly one token, where could that word have come from?

| origin of the replacement word | count |
|---|---|
| the file's own alphabet (the file already says it somewhere) | **0** |
| the machine's own alphabet — `dir()` of the interpreter's builtins and of its own types, asked at run time | **1** (`split` → `rsplit`) |
| inside a string literal (the token is a string and its *content* changed: regex bodies, format text) | **7** |
| nowhere in the environment | 0 |

Price of blind generate-and-verify for those one-token fixes: **median 4,581 candidate programs**, max 5,664 — because each candidate must be executed and the corpus rule guarantees the suite is the oracle.

## What is real in the claim

The operator layers stand, and they stand because the observable is produced by the machine:

- **when may I act** — the refusal surface: 160/160 exact, where one success per action got 123/160 wrong.
- **what acting does** — the effect is the provenance of the output's bytes: one execution, 24/24 unexecuted whole trees exact including modes.
- **chaining** — composition verified by execution (`mkdir` then `cp`, predicted before running).

All three are *identification*: the hypothesis is pinned by a machine-checkable observable, so one experience is enough and nothing needs to be stored in weights. That is genuinely faster than how agents learn today, and it is why the two vocabularies could be derived instead of designed.

## What is wrong in the claim

An edit is not an effect of an action. It is a **choice in a space of programs**, and the measurement says the space is not a vocabulary:

1. **83% of real fixes add or remove a line.** No alphabet — learned from one experience, read off the machine, or distilled from five thousand documents (round 21: 0 gained, 1 lost) — produces a line the environment never showed. A new statement is not a word to be recognised; it is a structure to be chosen.
2. **When the fix is one word, the word is almost never available.** Zero of eight came from the file's own alphabet. Seven of eight were changes *inside a string literal*: `r"(\d+)(.*)"` → `r"(\d+)(.*)\Z"`. That is not a token substitution in any meaningful sense — the information is the meaning of a pattern, and token substitution has nothing to substitute, because both states are one `STRING` token.
3. **Verification cannot pay for the search.** The suite is a perfect oracle for these 87 tasks (that is how they were mined), and it still costs 4,581 executions to find one fix blindly. Cheap verification does not make expensive search affordable; it only makes each step decisive.

So "experience each action once" buys exactly what it can identify — machine-readable effects — and it buys nothing where the thing to produce is a new line or the meaning of a literal. The failure is not a shortage of experience. **It is a shortage of the observable**: an action's effect is produced by the machine whether or not anyone is watching; an edit's correctness is produced by a checker, and only there.

## The single bottleneck

Restated with these numbers: **the supply of executable checks that localise a site and grade a choice.**

Not checks in the repository — 27 of 36 fixes were already fully pinned by their own suites (round 20), so verification is not the scarce good. The scarce good is *localisation and grading at the site*: the failing assertion that says "line N, expected this, got that". With it the 4,581-candidate space collapses to the tokens on one line, and a machine with no knowledge can choose among them by executing. Without it, no amount of experience, vocabulary, corpus, or model closes the gap — because the machine has nothing to be wrong against.

That also explains why the four failure classes order themselves the way they do: 72 structural fixes need a *statement* proposal (the checker grades but does not propose), 7 literal fixes need the *meaning* of a pattern (the checker states the observable, never the means), and 1 needed a word the interpreter already had — the only case where search alone suffices.

## The next mechanism, named and not yet built

**The goal is a refusal at a site.** Read the site from the refusal, read the acceptable values from the assertion's own literals, and propose only there — then let the same execution that was going to run anyway grade the proposal. It is the third instance of the same law this branch has now applied twice: *do not design the vocabulary, derive it from the machine that says no.* The refusal surface derived *when* an action may run; provenance derived *what* it does; this would derive *what the edit must satisfy*.

It must be measured on the 72 structural cases — where the current machinery is silent — and not on the 8 that are already substitutions, because a mechanism graded on cases its shape already covers is self-congratulation.

## Limits

- 87 fixes from three pure-Python libraries, filtered upstream to one source file plus one test file. Real history, not all of software engineering.
- k is reported to five; the per-task distance stored in the receipt is exact and admits any k.
- A literal-content change is counted as one token because at the token level it is one: the class is honest about where the information is, not about how hard it is.
- The tests are not vendored; the corpus rule already established fail-at-parent and pass-at-fix, so the price is a count of executions, not a re-measured pass rate.
- No independent verification.
