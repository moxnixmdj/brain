# One run, three vocabularies, one judge — 24 of 40, measured

**2026-11-16 · branch `arena/68eb44a5-brain` · 41 task files, 40 real bugs · no model, no weights, no network**

Receipt: `canonical/verification/COMPOSED_REPAIR_ONE_RUN_20261116_V1.json`
Tool: `canonical/tools/composed_repair_one_run_v1.py` (4 tests)

---

## What was never done before today

Every number this project has quoted for repair came from a **different run of a different
mechanism**, and the best number it ever published — 24 of 40 — was a *projection*: take one arm's 18,
take another arm's 16 verified repairs, union them, and call it a capability. A union of two receipts
is arithmetic, not a system.

This is the first time the arms have run **together, in one command, under one judge**, ordered by
measured cost, first acceptance wins:

1. **synthesis from the failure** — build the expression the failure implies from the live scope at
   return (~2,000 evaluations, ~0.2 s), no vocabulary at all;
2. **the rewrite families** — grammar-closed rewrites seeded from the program's own atoms;
3. **a learned edit kind**, replayed from its own record's removed/put-in lines.

The judge, in every case, is the corpus's own `pytest` on a fresh copy with the answer key absent.

## The result

| | |
|---|---|
| tasks | 41 files (40 bugs; 9 ship no JSON examples) |
| **repaired, one run, one judge** | **24 of 40** |
| wall clock | **387.8 s** |

| arm | bugs it won | cost when it won |
|---|---|---|
| synthesized from the failure | **3** — bucketsort, is_valid_parenthesization, quicksort | 0.2–0.2 s |
| rewrite families | **15** | 0.4–25.8 s |
| recorded learned kind (replay) | **6** — hanoi, knapsack, levenshtein, longest_common_subsequence, minimum_spanning_tree, to_base | 0.2–40.5 s |

**The projection was right, and now it is a measurement.** 18 ∪ 16 with 10 shared = 24; the composed
run repaired exactly 24. That is the good kind of agreement — the arithmetic and the system land on the
same number for different reasons.

Two things the run makes visible that no receipt could:

- **The cheapest arm should always be tried first.** Synthesis won 3 bugs at
  ~0.2 s each; the families arm spent up to 25.8 s enumerating on the same bugs before it would
  have found them. Ordering by measured cost is free capability: same answers, a fraction of the work.
- **Six bugs exist only because a vocabulary learned elsewhere was kept.** Without the replayed arm the
  system is 18. The learned kinds are not decoration; they cover ground the hand-written families
  cannot reach from either side.

Remaining, and honestly counted: **9** files carry no JSON examples and were never searchable,
**6** produced no improving candidate, **2** improved every example they could see without closing the
task.

## What is real, what is not — the standing answer, with the best number this tree can currently show

**Real.** Permanent storage of a verified experience. One-demonstration generalisation on real code
(60.0% vs 15.0% cache). An admission gate that refuses a lesson which breaks a correct program. A
vocabulary-free synthesis that builds `(not depth)` from a failure in a fraction of a second.
Identification that settles in ~1.31 chosen questions once the space holds the repair. And now a
composition that repairs **24 of 40 in one run in 6.5 minutes.**

**Not real.** That one experience is a rule (~10 bits survive it). That more environments buy coverage
(2.5× compute bought 1 page in 37; 0/10 for a new kind). That making a missing observable present is
the fix (0 of 9). That the smartest actions ARE the answer: an action list repairs 0/20, a shape
learned from one showing 1–2/20, one learned vocabulary 16/40 — **each under half**, and the answer only
appears when three of them are run together. That any of this is sentience: the only proxy is measured
and small.

**The single bottleneck remains the hypothesis space — and today it is bounded from above as well as
below.** Below: no arm alone passes 18. Above: three arms together, judged only by the corpus's own
tests, reach 24 and stop. The gap between 24 and 40 is not budget, not
questions, not an oracle — it is vocabularies that do not exist yet, on bugs whose fixes are new kinds of
change.

## What is next, in the order it pays

1. **Nine bugs are still unsearchable.** They have no JSON examples; their cases are objects inside
   their own test file. That is the cheapest remaining +N and it is a plumbing problem, not a research one.
2. **Make the recorded arm a real arm.** Its lessons are not in this repository, so it is replayed. A
   learner that runs here converts a replay into a mechanism.
3. **Grow the vocabulary by reading refusals, never by guessing.** Four audits have now landed on the
   same conclusion; the fifth family will come from a specific bug, not from imagination.
4. **Kill list:** more demonstrations as coverage; more environments with the same vocabulary; any
   number quoted from a record instead of a run.

## Non-claims

- 40 single-function Python bugs. Not general repair, not SWE-bench, not computer use.
- The learned arm is a **replay from its own record**, not a re-learning; its lesson corpus is not here.
  This is the strongest number available in this sandbox, not the strongest available in principle.
- The 41st file is a helper module, not a bug; it is counted in `tasks` and not in `repaired`.
- Producer-run, one machine, authority **NONE**. No tolerance widened, `truth.achieved` unchanged.
