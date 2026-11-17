# Why no mechanism can buy reach, and what that means for "solve everything on a computer"

This round asked a question with a shape: *we solved instant learning, and instant learning in a brand-new
environment. Doesn't that make this a solution to every problem and all computer use? Give the model the most
advanced coding actions, let it experience them once, it learns them permanently, apply them to anything —
so we solve everything on a computer, permanently? Is that revolutionary versus how agents learn today?*

The answer is not agreement and not disagreement. It is four propositions, each measured, and one mechanism
built to test the strongest version of the claim.

## The four propositions

| proposition | verdict | what settles it |
|---|---|---|
| one execution plus a sufficiency verdict settles an action whose survivors agree | **true** | verification is exact; 29 trials of environment adaptation converged at a 25.78-request crossover |
| instant learning of a new environment is a real law | **true, as a cost law** | the same 29 trials: a learned environment costs a fixed crossover and then nothing |
| experience eventually covers the actions that real fixes need | **false** | 75.2% of 2,178 real fix pieces from 500 SWE-bench Verified tasks are rebuilt by no operator any other task produced; with every other task as experience, coverage is 18.7% and flat across quartiles (0.15 / 0.18 / 0.16 / 0.18) |
| a perfect oracle at a localised site makes the remaining edits nameable | **false, and this round built the machine that shows why** | see below |
| permanence follows from repetition | **false** | permanence follows from *expression*: an action that has a name in the artifact stays usable; an action that does not have one is not made namable by one more demonstration |
| a retired benchmark measures the frontier | **false** | HumanEvalFix in-grammar repair is .74 and out-of-grammar is .32 — the code that matters is the code the alphabet cannot spell |

`P(correct action) = REACH × SEARCH × VERIFICATION`, and it is unchanged at **0.2978**. Search and
verification are solved. Experience moves only reach. Reach is the binding term, and reach is not a search
problem.

## The strongest version of the claim, built rather than argued

If anything could rescue the claim, it would be this: *don't enumerate a grammar — invert the failure.*
Localise the site from the failure, read the value the test demands out of the test's own assertion, and
solve for the expression that produces it. That is not enumeration, so the 75.2% out-of-vocabulary figure
would not apply to it.

So it was built: `canonical/swe_kernel/witness_inversion_v1.py`. It is a pytest plugin, not a harness,
because a real repository's test has fixtures, parametrisation and classes, and by the time the test fails
the library frame that returned the wrong value is already gone. The plugin therefore **records** every
return and every raise inside the files the fix touched while the test runs, and reads the witness from the
failing assertion itself — either the compared value of `assert <expr> == <value>`, or the required message
pattern of `with pytest.raises(E, match=...)`.

Localisation is by invertibility rather than by traceback depth: a recorded value is a candidate site only
if what it produced is what the test is complaining about, and the site survives only if some expression
over the site's own live frame reproduces the required value exactly. The alphabet is the frame's values,
their non-callable attributes, eighteen pure builtins, and binary arithmetic over them. Every proposal is
judged by the real test and nothing else, and the file is restored byte for byte whether the proposal wins or
loses. The control arm is the tree's own mutation families — operator swap, comparison swap, literal
replacement, dropped operand, call swap — re-expressed on the same span, with the same witness, the same
judge and the same budget. The only variable between the arms is the proposal set.

## What the corpus said

Real committed releases only: `pypa/packaging 21.0→24.0`, `pallets/itsdangerous 2.0.0→2.1.2`,
`pypa/pyproject-hooks 0.0.1→1.2.0`, `hukkin/tomli 1.0.0→2.0.2`. Each fix commit's parent is materialised with
`git archive`, the fix commit's own test files are overlaid, and the repository's own pytest names the real
failures. No synthetic defect is introduced anywhere.

- 55 commits materialised
- 13 carried a test that really fails at the parent state
- 16 attempts, **18 witnesses captured**, 0 verified, 16 refused with a named reason

Every single witness is a **message string the parent never produced**. The real fix in this corpus invents a
distinction — a new error message, a new branch — rather than selecting a different existing value. Not one
of the eighteen recorded sites admitted any expression over the live frame that reproduces the required
value, so **both** arms were silent, for the same reason. The refusal is correct, not incidental: an
inverter selects over existing content, and the answer is new content.

The closure check attacks it from the other side. Five real commits whose fix is exactly one changed return
expression were taken at their *fixed* state, the human's own line was put back the way it was before the
fix, and the loop was asked to find it again from the failing test alone. It recovered the human's answer in
**0 of 5**: on this corpus either the reverted line is not covered by any test of the fix, or the answer
needs a name the recorded frame does not have. A fix's meaning is distributed across its diff, and reverting
one expression usually restores no defect at all.

The mechanism does close where the answer *is* expressible, and the unit suite proves it end to end on a real
package and a real failing test: capture returns the required value, the site is the single return, the
alphabet contains the expression, synthesis verifies with the real test, and the file comes back byte for
byte. That is the honest boundary: **a perfect oracle at a localised site names an edit only when the edit is
a selection over what the artifact already contains.**

## So: is it revolutionary?

The expensive parts of an agent — search, execution, verification, and now experience of a new environment —
are solved or bought cheaply. That is real, and it is why the cost curves look revolutionary. But the thing
that decides whether an action exists at all was never on those curves. Reach is not bought by experience,
not by a better oracle, and not by a stronger model: 75.2% of what real fixes do has no expression in the
vocabulary any amount of experience produces, witness inversion refuses all eighteen real witnesses it could
capture, and the closure check recovers none of five human answers because the answer is a distinction the
artifact does not have.

What is real: instant knowledge, exact verification, one-shot environment adaptation, no parameters bloated
with a knowledge house, and a refusal machine that never claims an unverified edit. What is not: that any of
those compose into "everything on a computer, permanently".

## The smartest thing to do

Not another grammar, not a bigger alphabet, not more demonstrations. The next organ must **create the
distinction** the artifact lacks — synthesise the missing branch or the missing message from the test's own
demand, instead of selecting an existing value — because that is the only term in the product that is still
binding. That is where the next round goes, and it is named in the receipt's `next_step` rather than hidden
in prose.

Reproduce everything in this document with:

```
.venv/bin/python -m pytest canonical/tests/test_witness_inversion_v1.py -q
.venv/bin/python canonical/swe_kernel/witness_inversion_v1.py --corpus --limit 22 --closure-limit 8 \
    --json canonical/verification/WITNESS_INVERSION_20261116_V1.json
```
