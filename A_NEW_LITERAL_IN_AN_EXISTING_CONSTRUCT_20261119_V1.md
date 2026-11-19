# A new literal in an existing construct: it occurs three times, and the check never says the word

**Round 27. Receipt: `canonical/verification/A_NEW_LITERAL_IN_AN_EXISTING_CONSTRUCT_20261119_V1.json`. Tool: `canonical/tools/a_new_literal_in_an_existing_construct_v1.py`. Zero model calls, zero parameters.**

## The correction first

Round 26 ended by calling shape-level anti-unification "the only untried route". **That was wrong, and the project said so before I did.** `canonical/swe_kernel/change_shape_census_v1.py` classifies real changes and states what each one demands:

| shape | what the census says it demands |
|---|---|
| `GUARD_ADDED` | "a predicate and a seat. This is the only shape rounds 11-12 address" |
| `VALUE_OR_OPERATOR_SUBSTITUTION` | "the memorisable shape" |
| `VALUE_ADDED` | "a new literal in an existing construct: memorisable, literal unseen" |
| `FEATURE_NEW_DEFINITION` | "needs NEW CODE, which no learned action and no predicate supplies" |
| `STRUCTURAL_OTHER` | "needs synthesis" |

So the project had already (a) measured guards, (b) named the two memorisable shapes, and (c) stated the boundary for the rest. What had *not* been done is measure the second memorisable shape — and round 26's tests could not have, because they excluded multi-line constructs by construction.

## What this round measured

For all 87 real fixes, decided exactly from the diff and the pre-fix AST — no generation, no cap:

| | count |
|---|---|
| one element added to one line (insert, or appended before the closing bracket) | **18 / 87 = 20.7%** |
| **`VALUE_ADDED`: one element added to a construct that already spans lines** (list, set, tuple, dict or call) | **3 / 87 = 3.4%** (2 calls, 1 dict) |
| of those, a literal the check already names | **0 / 3** |

Both the insert form and the append form were accepted — appending an element to a construct's last line replaces that line rather than adding one, and the tool reads both as the same act.

**The shape the project calls memorisable does not occur in this corpus at all.** Not "occurs and is hard": absent. The 87 real fixes add two or more lines, replace a block, or restructure — which is exactly the set the census marks as needing new code or synthesis.

## What this closes, and what it fixes in the record

The line of work that asked *"can a fix be reached without generating anything?"* now has an answer bounded from both sides:

- eight selectors over machine-produced observables: **≤ 2.4%**, and the best one subtracts answers (round 26);
- the one shape that would be reachable by copying the check's own word: **3 instances, and in none of them does the check contain the literal**;
- the shapes that do occur: **new code and synthesis**, in the census's own words.

So the answer to "is one experience enough to learn any coding action?" is: **yes for operators, no for edits** — and not because the learner is weak, but because the corpus of real fixes contains almost nothing that a selector can pick. The mean reachable share across everything measured here is under three percent.

## The single bottleneck, in its final and usable form

**Generation.** Not localisation, not vocabulary, not checks, not values, not paths, not shapes-that-exist. Every route this project tried *selects among things the machine has already shown*. A real fix raises a predicate that was never in the file, or adds an element that was never in the construct, or defines a function that never existed. Selection cannot produce what is absent, at any price.

And this is not a defeat of the project's law — it is the law's exact boundary. **"The best part is no part" is why the operator layer is perfect**: an operator's effect is observation-bound, so one execution pins it forever with zero parameters. An edit is generation-bound, and generation is the part that must be *produced*. The frontier buys production with weights. This project has now measured, nine ways, that nothing cheaper buys it.

## The smartest thing to do next

Not another selector. The next build must be a **generator whose every bit is calculated** — the user's own condition — which means it cannot be a knowledge house and must be a *rule* that produces structure from the site. The honest candidate, and the only one the measurements leave standing: a **constraint-solver over the site**, where the check's asserted value is the constraint, the site's own names are the variables, and the expression that satisfies it is *solved* rather than retrieved. That is CEGIS with the sketch taken from the failing site instead of from a human — and it is the only route here that produces something absent rather than selecting something present.

It should be measured the way every route here was measured: containment on the same 87 fixes, then execution. If it also returns zero, the conclusion is final and should be stated without hedging: **parameter-free repair reaches a few percent of real fixes, and the rest requires a generator trained on structure — the one part of this system whose parameters must be calculated rather than borrowed.**

## Limits

- `VALUE_ADDED` is defined strictly: one element, one construct, decidable from two texts. A fix that adds an element while also changing a call elsewhere is not counted, so 3 is a lower bound.
- The first run of this tool reported 1 and 0 because the detector missed elements inserted *before* a closing bracket; that defect was found by a test and fixed, and the numbers here are from the fixed detector (18 and 3).
- The check's text is the test file at the fix commit; a literal that appears there for an unrelated reason counts, which errs toward optimism — and the class was empty anyway.
- 87 fixes from three pure-Python libraries. Real history, not all of software engineering.
- Execution confirmation was available for zero instances because the class is empty; nothing was scored without execution.
- No independent verification.
