# Does the refusal name the missing word?

**Round 23. Receipt: `canonical/verification/DOES_THE_REFUSAL_NAME_THE_MISSING_WORD_20261119_V1.json`. Tool: `canonical/tools/does_the_refusal_name_the_missing_word_v1.py`. 13 tests. 87 real fixes, 73 real upstream suites executed in their refused state. Zero model calls, zero parameters.**

## The question, in your terms

> Instant learning and instant learning in new environments are solved. So give the system the most advanced coding and computer-use actions, let it experience each one once, and it learns them permanently — then anything on a computer is solved, including frontier software engineering. Am I right?

Right about operators. Wrong about edits. And the wrongness is now a number, not an opinion.

## What round 22 already established

87 shipped fixes: **72 of 87 (83%) add or remove a line**; the 15 that only change tokens are contained by 1/2/3/5 token edits in 8/9/11/13 cases; of the 8 that are one token, **0** draw their word from the file's own alphabet, **1** from the machine's, **7** change the content *inside a string literal*. Blind generate-and-verify costs a median of **4,581 executions** per one-token fix, with a perfect oracle. Verification is not scarce — 27 of 36 fixes are fully pinned by their own suites — so the scarcity is elsewhere.

## What this round adds: does the checker *speak*?

If a refusal names the missing word, the checker is not only a grader but a proposer, and the search collapses. If it only grades, then proposal is the bottleneck and no vocabulary, corpus, or one-shot experience can supply it.

Measured on the same 87 fixes, executing **real upstream suites**: the fix's own test, against the pre-fix source, reconstructed from the corpus (source at parent, test at fix — because the parent's own suite passes: 1,247 tests green, since the test that catches the bug does not exist yet). The refusal is read from the machine's own diagnostic lines only — never from the traceback source lines it echoes back.

| | count |
|---|---|
| tasks executed and failed in the refused state | **73 / 87** (12 could not run; each recorded with its reason) |
| fixes that introduce a new word (identifier or literal) | 57 |
| **the machine's refusal names one of those words** | **18 / 57 = 32%** |
| …names a new *identifier* | 15 / 57 = 26% |

By shape of the fix:

| shape of the fix | refused | named |
|---|---|---|
| adds or removes a line | 60 | 17 |
| multi-token change on the same lines | 7 | 1 |
| inside a string literal | 5 | **0** |
| from the machine's alphabet | 1 | 0 |

## What is real, and what is wrong

**Real.** An operator's effect is produced by the world, so one execution identifies it exactly and permanently, with no weights: the refusal surface (160/160 vs 123/160 for one-success-per-action), the provenance map (24/24 unexecuted trees exact), and composition. Genuinely faster than how agents learn today, and it needs no sentience — it needs a machine that answers.

**Wrong.** That the same mechanism reaches edits. Two numbers bracket why:

1. **Price.** Without a proposal mechanism, finding a real fix costs ~4,581 executions — and the oracle is perfect, so this is a floor, not a budget problem.
2. **Naming.** The checker's own statement names the word the fix adds only **32%** of the time, and **never** when the fix lives inside a literal (0/5).

So the environment can say **no**, and in two cases out of three it cannot say **what**. "Experience each action once" is exactly the procedure that converts a machine that answers into permanent capability; it cannot convert a machine that only refuses into one that proposes.

## The single bottleneck

**Checks that speak** — executable checks whose refusal names the thing to change — not checks that exist, not check density, not experience, not vocabulary, not parameters.

That is a sharper statement than last round's, and the two rounds together bound the value of fixing it: a *speaking* check turns a 4,581-way execution search into roughly one proposal, and the 68% of fixes where the refusal is silent are exactly the capability the current system cannot reach. Everything else this project has built is already past this bottleneck; nothing downstream moves until this one does.

## What that means for the model, and for "sentient"

Nothing in this answer requires sentience, and nothing requires weights. What looked like a creature is a loop with three parts: the world answers (operators — built), the machine refuses (checks — abundant), and the refusal says what is wrong (checks that speak — missing two times in three). The third part is the entire remaining gap, and it is not a property of the learner. It is a property of the checks.

## The next mechanism, named and not built

**Manufacture speaking checks from the repository's own assertions.** The expected and actual values a test asserts are already written down in the test source; they are the only vocabulary that (a) is produced by the machine, (b) is specific to the site, and (c) costs no parameters. Extract them, bind them to the localised site, and the proposal becomes "make the site produce the asserted value" — a derivation, not a guess. Measure it on the **68%** where the refusal was silent, never on the 32% where the word was already spoken, because grading a mechanism on the cases its shape already covers is the self-congratulation this project keeps refusing.

## Integrity: three fake signals this round had to remove

Each was caught by execution, and each would have produced a confident, wrong number:

1. `pytest` was absent; the harness read the missing module (`rc 1`) as "the test failed". Fixed: a harness failure is recorded as **could not run**, never as evidence.
2. A `--filter=blob:none` clone could not check out historical parents; the failure surfaced only later. Fixed: full clones, and the parent is not needed at all.
3. The parent's **own** suite passes (1,247 tests), because the failing test is added by the fix. Running it measured nothing. Fixed: the refused state is rebuilt from the corpus — source at parent, the fix's own test.

Also excluded: the traceback's source lines, which echo the test's own code and would let the specification masquerade as the machine's statement.

## Limits

- 87 fixes from three pure-Python libraries; real history, not all of software engineering.
- 12 tasks could not be executed here and are recorded, not scored; they are not evidence in either direction.
- Naming is necessary, not sufficient: a named word still has to be placed, and placement is not measured here.
- The refused state is reconstructed from the vendored pair rather than checked out from an unfetchable parent; that is the corpus rule exactly, and the fixed state was verified to pass.
- No independent verification.
