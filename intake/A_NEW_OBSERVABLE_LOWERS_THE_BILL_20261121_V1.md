# A new observable lowers the bill, but does not remove it

**2026-11-21 · branch `arena/67c67d7e-brain` · receipt `intake/RECEIPT_NEW_OBSERVABLE_20261121_V1.json` · authority NONE**

---

## 0. Requirements restated

Own model/agent and weights, zero runtime model calls, no knowledge house in parameters, external
deletable knowledge, every parameter computed, one-experience learning in unseen environments,
hardest available tests, no borrowed outputs or hand-solving, no questions to the owner, research
first, ultimate minimal design, kill bad ideas, honest evidence, no §6 claim early. §2: weights hold
computed mechanisms; typed knowledge lives outside and can be added or removed without retraining.
`truth.achieved` remains `false`.

## 1. Research and the exact question

The previous round found that the coarsest sufficient statistic at depth 5 already had **4 cells**,
and searching 138,509 conjunctions of three existing generators saved **zero** cells. Its next
falsifier was a new computable observable that splits a cell while remaining verdict-exact on
untouched runs. This round tests that falsifier directly. The observable family is derived from the
machine's own reading — arrival/departure steps, counts at arrival, holders, delta shapes, trace
length — and no candidate's value is computed from a label.

## 2. §3 verdict

- **Real:** a newly computed trace observable splits cells and keeps the refined table exact on
  runs it never fitted. The worst-case question bill falls.
- **False:** that this removes the bill. It falls from 174 to 154 labels on the training pool — a
  real but bounded improvement.
- **Unproven:** that the same observable family helps on a real repository or GUI/browser task.
- **Missing:** a mechanism that makes the remaining 154 labels unnecessary.

Why not "experience the actions once"? The machine's reading supplies a finite set of computable
distinctions. Some were unused, and finding one was worth 20 labels here. But the judgment that
lands in a cell still has to be supplied; no amount of replaying the same trace creates it, and a
parameter storing it would be a forbidden lookup.

## 3. Plan and killed ideas

**Plan:** reuse the depth-5 TARBALL pool and its 178/53 split; fit the existing four-cell statistic;
enumerate step-indexed observables from the reading; keep only refinements that split at least one
cell; judge each refined table on the 53 untouched runs; choose the best exact refinement. Rejected:
model guidance, answer storage in weights, weakening the exactness criterion, and adding more
conjunctions of the old generators (already measured to save zero cells). Killed: the claim that the
four-cell table was the last possible distinction.

## 4. Evidence

All five criteria were declared before execution and are MET:

| | result |
|---|---|
| candidate observables | 90 split at least one cell; **67** were verdict-exact on 53 held-out runs |
| best exact refinement | `delta_shape[probe_new_contentprobe_new_content]` added to the fitted table |
| base cells → refined cells | **4 → 24** |
| worst-case bill | **174 → 154** labels |
| held-out verdicts | **0 undecided, 0 false accepts, 0 false rejects** |
| zeros | 0 model calls, 0 parameters, 0 network calls |

Cost 80.9 s. Other exact refinements included `trace_length` (4 → 13 cells) and
`arrival_step[probe_new_content]` (4 → 9 cells). The best candidate is a delta-shape observable over
a literal the machine actually emitted; it is inspectable and deletable like every other knowledge
record here, and no parameter was changed.

## 5. Tests

`intake/tests/test_new_observable_measurement_v1.py` — **3 passed**: the best refinement splits a
cell, lowers the bill and stays exact on held-out runs; at least one exact candidate exists; no
candidate was named from a label. Combined intake suites: **23 passed**.

## 6. Non-claims and next bottleneck

Not claimed: OSWorld/SWE-bench performance, GUI/browser use, natural-language understanding, live
wiring, independent verification, or §6 completion. The goal label is the project's own portable
judge, not a new human judgment; one CLI machine is not computer use. `truth.achieved` stays `false`.

**Next bottleneck:** 154 labels is still the wrong order of magnitude. The next falsifier is a
*composition* of two or three of the 67 exact observables that reaches the same held-out exactness
with materially more cells — ideally a bill under 100 — without reading a held-out label to choose
the composition. If that fails, the honest result is that the question bill is structural here.
