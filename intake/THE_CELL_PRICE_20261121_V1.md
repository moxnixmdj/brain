# The cell price: wider conjunctions bought nothing

**2026-11-21 · branch `arena/67c67d7e-brain` · receipt `intake/RECEIPT_CELL_PRICE_20261121_V1.json` · authority NONE**

---

## 0. Requirements restated

Own model/agent and weights, zero runtime model calls, no knowledge house in parameters, external
deletable knowledge, every parameter computed, one-experience learning in unseen environments,
hardest open tests, no borrowed outputs, no questions to the owner, research first, ultimate minimal
design, kill bad ideas, honest evidence, no §6 claim early. §2: weights hold computed mechanisms;
typed knowledge lives outside and can be added or removed without retraining. `truth.achieved` stays
`false`.

## 1. Research and the question

The constructed-question round falsified four ways to aim a question at harm; cell labelling stayed
the cheapest sound policy. Its own next step was to make cells cheaper. This round asks the exact
question that decides whether the stated grammar allows that: does a conjunction of three generators
produce a coarser sufficient statistic than the best conjunction of two? The project's quotient
lattice supplies the mechanism; no new learning rule is introduced.

## 2. §3 verdict

- **Real:** a sufficient statistic transfers to unseen runs with zero false accepts, zero false
  rejects and zero abstentions (53 held-out runs here).
- **False:** that a wider conjunction in the same grammar buys a coarser statistic. It bought zero
  cells here.
- **Unproven:** that a different generator family, or a real repository's checker, changes this.
- **Missing:** a new observable that can split a cell without a paid judgment.

Why not "experience the actions once"? The table is cheap to check and expensive to identify. Four
question policies could not aim at the harmful pair, and widening the descriptive grammar did not
merge the cells. A parameter storing the missing judgment would be a lookup, not a mechanism.

## 3. Plan and killed ideas

**Plan:** split 231 real depth-5 TARBALL runs before fitting; enumerate all sufficient conjunctions
of size 2 and 3 over the same derived generators; fit on 178 runs; judge 53 untouched runs; report
cells and errors. Rejected: model-guided acquisition, more of the same generators, larger depth as a
substitute for evidence, and weakening the sufficiency criterion after seeing the result. Killed:
"wider conjunction makes the bill cheaper."

## 4. Evidence

All five criteria were declared before execution and are MET:

| | result |
|---|---|
| real split pool | 231 distinct runs = 178 train + 53 held-out |
| lattice | size 2: 4,465 conjunctions; size 3: 138,509 |
| coarsest size 2 | `decrements[probe_new_content] ∧ holders_ever[probe_new_content]`, **4 cells** |
| coarsest size 3 | the **same** statistic, **4 cells**, 0 saved |
| held-out verdicts | size 2 and size 3: **0 undecided, 0 false accepts, 0 false rejects** |
| zeros | 0 model calls, 0 parameters, 0 network calls |

Cost 82 s. The first implementation used the project's generic lattice evaluator and did not finish
in 30 minutes; it was replaced with an equivalent integer-partition computation that precomputes
each generator once. This is an engineering correction, not a change in criterion, and the receipt
records no result from the abandoned run.

## 5. Tests

`intake/tests/test_cell_price_measurement_v1.py` — **3 passed**: the wider search saved zero cells
and kept the receipt's criteria met; held-out verdicts are exact; the split was made before fitting.
Combined intake suites: **20 passed**. This pins the negative as well as the positive.

## 6. Non-claims and next bottleneck

Not claimed: OSWorld/SWE-bench performance, GUI/browser use, natural-language understanding, live
wiring, independent verification, or §6 completion. One CLI machine is not computer use; the goal
label is the project's own portable judge, not a new human judgment. `truth.achieved` stays `false`.

**Next bottleneck:** the generator family, not the conjunction width. The current four-cell table is
exact on 53 held-out runs, and no three-way conjunction within the family improves it. The next
falsifier is a *new computable observable*, derived from the machine's own reading, that splits one
of those four cells and remains exact on untouched runs — not a larger search over existing ones.
