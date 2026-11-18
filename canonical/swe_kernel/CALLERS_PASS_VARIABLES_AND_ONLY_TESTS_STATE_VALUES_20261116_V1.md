# Callers pass variables, and only tests state values

Seven sources have now been spent looking for the one object that decides whether a change can be checked: the
**discriminating input** — one input and the outcome it must produce, that separates the new behaviour from the old.

| round | source asked | residual parts pinned beyond the change's own test |
| --- | --- | --- |
| 16 | the tests themselves as probe | 0 of 8 |
| 17 | input **shape** (mutation) | 2 of 8 |
| 18 | the **value** a condition wants | 0 more |
| 19 | the repository's **documents** (5,949 of them) | 0 more, one lost |
| 20 | the language's **protocol operations** | 0 more |
| 21 | the author's **statement** (commit message) | 0 of 19 (names 50–55%, specifies none) |
| 22 | the repository's **callers** | 0 of 8 |

## This round's question, and why it was the last untested one

Every previous source was either the artifact's data or the author talking about the change. One was never asked:
**the code that calls the changed function.** Callers are real usage, they sit outside both the changed module and
the test that failed to pin it, and a caller exists only because someone believed that argument was correct against
the *old* behaviour — exactly the tension a behaviour change creates.

So the round harvested every literal argument the repositories pass to the callables a change touches: parse every
`.py` file except the change and its test, find calls of the changed module's own defined names or of the names the
failing test uses, and keep only calls whose arguments are literals. Each harvested call is then probed at the fixed
state and at the state with the part reverted; a pin counts only if it passes at fixed and **fails** at the revert.

## Measured

```
17 real fixes, 8 parts the suite accepts without
168 literal call sites harvested  (90 in a test, 78 in source code)
  3 candidate calls land on a residual part
  0 of them separate the two states
  0 parts pinned by a caller
```

Two of the residual fixes had any caller shape at all — `itsdangerous 7f4dcf83` (2 sites) and `packaging d5fedc90`
(1 site) — and neither separated. The three `tomli` fixes, which define 27 to 30 functions each, produced **zero**
literal call sites for the functions the change touched.

## Why the zero is structural, and what it says about programs

Not a harvesting bug — the harvest is bounded and the bound is the finding:

- **Where a caller exists, it passes a variable.** A parser's internal functions are called with a `state` object
  and a position, not with a literal. `suffix_location(state, ...)` has no caller that states a string, because the
  string arrived from the user's document ten frames earlier.
- **Where a value is written down, it is written down in a test.** 90 of the 168 literal call sites are in test
  files. Outside tests, a program does not state values; it computes them.

That is why the seventh source returns zero like the sixth, the fifth and the fourth: the repositories contain
exactly one place where an input and its required outcome are written together, and it is the test.

## What is now established, and what it means for the goal

Eleven of the seventeen fixes in this sample are **fully pinned by their own suites**. That is the honest positive
result of seven rounds: **a demonstration is checkable exactly to the extent it ships its discriminating input**,
and when it does, the check is free, exact, and needs no model, no parameters and no knowledge stored anywhere.

So the strategy you are asking about is real — with its boundary stated precisely:

- "Show it once and it learns permanently" is **true** for the work that arrives with a discriminating input, and
  true *because* of that input: the demonstration supplies the separation, the verifier makes it permanent.
- It is **false as a claim about all computer use**, because most unattested work contains no separation to learn
  from. Seven independent sources — data, values, corpus, operations, prose, callers — cannot manufacture one.
- Nothing in this refutes the architecture. It defines the **coverage** of the architecture, which is the number
  that decides where the remaining effort goes.

Which leaves exactly three levers, in order of measured leverage:

1. **Select or elicit the discriminating input.** Selection is free where work ships a test (11 of 17 here).
   Elicitation is the contract round 21 made executable: state the smallest question, convert the answer into the
   verified pin. That lever covers the residual, but only by involving the author.
2. **Raise the generator, not the oracle.** With a discriminating input in hand, the number that matters is: can the
   system produce the patch? The tree measures its own grammar at 18.7% coverage of real fix pieces with all other
   tasks as experience, and 75.2% of fix pieces are named by no other task's fixes. *That* is where the remaining
   capability sits, and it is untouched by every round in this table.
3. **Keep the knowledge instant.** Nothing in this round stored a parameter: the corpus, the prover, the operations
   and the call sites are all read at run time, and the only persistent artifact is a verified pin — a test, not a
   weight.

**Single bottleneck, stated for the seventh time and now measured from every side available: the discriminating
input is authored knowledge.** It is not in the data, not in the documents, not in the operations, not in the prose
about the change, and not in the code that calls the changed function. What can be built is the machinery that
recognises its absence, asks the smallest question that supplies it, and — once it exists — uses it exactly.
