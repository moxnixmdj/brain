# The assertion is the demand — one point of demand is not a specification

Thirty fresh commits (click, jinja, attrs), none used by any earlier round, swept in 74.9 s with no oracle
questions spent: the failing assertion's demanded value is read out of a live run of the whole test file, and
each candidate is filtered by evaluating it inside the recorded frames (~10 µs) instead of running the suite.

**Funnel:** 15 structural edits (excluded, censused) · 1 site never ran in the failing test · 13 demand known and
no candidate produced it · **1 verified**, whole file green (47 tests), and the patch is the human's own fix.

**The round's sharpest result is against us.** The first receipt of this same round verified a *different*
patch: a literal string that reproduced the demanded value on the one name the test used — green in fact, wrong
in general. The suite, the only gate the tree permits, could not reject it, because the suite is also a point
set. One admission rule — a candidate that names nothing in the frame is a point fit — turned that wrong green
patch into the correct rule on the same row, with the demand and the space untouched.

**The completeness witness is negative and exact:** the human's own replacement is admissible by the table in
**1 of 14** in-class rows. Classified by AST, those fourteen need: attribute of another object (6), method call
on such an attribute (3), guard `is None` / `or` / ternary (4), a bare name already in the frame (2), an
f-string over a frame name (1).

**The law:** selection cost falls only to the degree the demand is selective, and a demand is selective only
when it names an object. A failing test supplies a predicate and a witness, almost never an identifier.

**Next, with acceptance declared first:** predicate reader from the assert's own AST and the crash entry's own
path; reference space over `dir()` of the frame's values; require the predicate to flip at the failing
occurrence. Acceptance: human fix admissible in ≥ 10/14 (now 1/14), verified generalising repairs ≥ 8/30 (now 1),
and no verified patch may name nothing in the frame.

Prose: `THE_ASSERTION_IS_THE_DEMAND_20261119_V1.md` · receipt:
`canonical/verification/THE_ASSERTION_IS_THE_DEMAND_20261119_V1.json` · authority NONE, producer-run,
0 parameters, 0 model calls.
