# The edit space is the program, not a list — a hypothesis is a rewrite, and a comparison is part of the grammar

**2026-11-16 · branch `arena/b399b1d7-brain` · 40 real published bugs, no model, no weights, no network**

Receipts, every count folded from raw rows by `--consolidate`:
`COMPARISONS_CLOSE_THE_LAST_MILE_20261116_V1.json` (this run),
`REGION_REWRITES_AND_THE_REFUSAL_AUDIT_20261116_V1.json` (previous run),
`WHERE_THE_REFUSALS_ACTUALLY_WERE_20261116_V1.json` (the audit of the refusals),
`THE_EDIT_SPACE_IS_THE_PROGRAM_NOT_A_LIST_20261116_V1.json` (the run before that).

---

## The claim on trial

> Instant learning and instant learning in new environments are solved. So give the model the most
> advanced actions, show each one once, and it keeps them forever. Coverage plus the smartest actions
> is therefore the best coding agent on the planet.

**Right:** one demonstration really does compile into a rule, the rule really does travel to a
different module, and the admission gate really does refuse a lesson that breaks a program it was
never taught on. Measured here; not re-argued.

**Wrong:** the step from *learning* to *coverage*. Learning selects inside a space of hypotheses. It
cannot enlarge the space, it cannot make an expensive hypothesis cheap, and it cannot make a missing
observable appear. Everything the owner calls "coverage" is a property of the space.

## What four rounds of measurement did to that claim

| what the generator's hypothesis was | repaired (verified by the corpus's own test) | candidates | wall |
|---|---|---|---|
| a **hand-written list** of edits (what the tree had) | **0 / 20 held-out** — `^=`→`&=` was unreachable at any budget | 280 (then 0 accepted) | 83 s |
| a value **substituted** at one node, alphabet from the program | 14 / 40 | 204,783 | 449.7 s |
| a **rewrite of a region** (permutation, composition, atom shape, insertion) | 17 / 40 | 152,052 | 378.4 s |
| the same, with **comparisons** inside the atom family | **18 / 40** | 200,529 | 510.2 s |

Nothing in that table is a better learner, a bigger budget, or a stronger oracle. Every movement came
from changing **what counts as one hypothesis** — and one movement came from a plain hole in the
grammar (`is_valid_parenthesization`: `return True` → `return depth == 0`; the atom-combination family
built arithmetic only, so the comparison was outside the space while `True == 0` sat uselessly
inside it).

## Where the refusals were — measured, not guessed

The previous run refused 17. Guessing why would have wasted the turn, so each refusal was audited
against the corpus's own corrected programs, comparing the **target function** (several corrected
files ship extra implementations plus the task description as a string; a module-level comparison
misreads those as "the fix is missing" — that mistake was made, caught, and fixed).

| of the 26 refusals | count | what it means |
|---|---|---|
| `A_SEARCH_TOO_WEAK` — the fix **was** in the space | **6** | the hypothesis existed; the search never reached it |
| `B_SPACE_TOO_SMALL` — one edit, outside the space | **10** | the generator could not express it |
| `C_MULTI_EDIT` — more than one edit | **1** | a one-edit mechanism cannot express it |
| `NO_EXAMPLES` — no input/output example exists | **9** | one bit per test cannot direct a search |

**6 refusals were pure search failure.** The right hypothesis was already in
the enumerated space and the system did not find it. "Just enumerate more" is therefore not a
coherent strategy: expressiveness alone does not buy reachability.

## What was built and removed in the same turn

Mechanic 3 names *composing* new edits. So a two- and three-move composition pass was built:
best-first over the cheap rewrite families, seeded from the best single-edit foothold, each move
admitted by execution feedback, strict improvement required to expand a state.

**It repaired zero additional tasks** on this corpus across all seventeen refusals it was pointed at.
It was removed rather than shipped: "the best part is no part" applies to a part that pays nothing.
The finding stands on its own — **the refusals need families, not depth.** At this scale, a second
move almost never helps when the first move is the only improving one in a space that is missing the
family the bug actually needs.

## What is real, and what is not

**Real:** instant learning; single-demonstration transfer; admission that refuses a harmful lesson;
a generator with no list, no parameters, no model and no network, repairing **18 real published
bugs end to end** with the answer key provably absent — 15 of them local edits,
3 flagged as delegating to a builtin the program never used
(`kth` → `max(arr)`, `lis` → `len(ends)`), one of which is the coarse flag catching a genuine published
repair (`sieve`'s `any` → `all`).

**Not real:** that any of this is a route to "solve every computer task". The multiplier is still
`P(expressible) × P(found) × P(verified) × P(transfers)`, and this work moved the first two terms on
40 single-function programs. 9 of the 40 remain **unmeasurable** because their tests assert a
bare boolean: one bit cannot direct a search, and calling that a failure would be as dishonest as
calling it a success. Four more improved every example they could see but never closed the task
(4), and 9 produced no improving candidate at all.

**The single bottleneck, precise enough to act on: the UNIT of a hypothesis — what counts as one
move.** Not the learner, not the budget, not the oracle (the oracle only matters once a candidate
exists). Four rounds moved only when that unit changed: list → substitution → rewrite → rewrite plus
the comparison the grammar was missing.

**And the same lesson is the one that transfers to computer use**, which is why it is worth stating
generally: a canned list of actions is to a GUI what a canned list of edits was to this repairer. An
action should be a **rewrite of a region of the current state**, parameterised by what is actually in
front of the agent. Demonstrating an action once changes nothing about that — which is the precise
sense in which instant learning is real and yet not the solution.

## What this is not

- Not SWE-bench, not a frontier score: 40 single-function programs, one file, one edit, Python only.
- Not proof of correctness: a passing patch can be a plausible rewrite, and this note reports its own
  such patches rather than hiding them.
- Not independent verification. The producer ran it; no model was used at any point, so nothing here
  can be credited to one.
