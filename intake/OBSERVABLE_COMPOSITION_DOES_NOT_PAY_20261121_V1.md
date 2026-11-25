# Observable composition does not pay the bill

**2026-11-21 · branch `arena/67c67d7e-brain` · receipts `intake/RECEIPT_OBSERVABLE_COMPOSITION_*_20261121_V1.json` · authority NONE**

---

## 0. Requirements restated

Own model/agent and weights, zero runtime model calls, no knowledge house in parameters, external
deletable knowledge, every parameter computed, one-experience learning in unseen environments,
hardest available tests, no borrowed outputs or hand-solving, no questions to the owner, research
first, ultimate minimal design, kill bad ideas, honest evidence, no §6 claim early. §2: weights hold
computed mechanisms; typed knowledge lives outside and can be added or removed without retraining.
`truth.achieved` remains `false`.

## 1. Research and question

The single-observable round lowered the worst-case cell bill from 174 to 154 while staying exact on
53 untouched runs. Its next falsifier was a composition of several exact observables that reached a
bill below 100 without reading a held-out label to choose the composition. This round tests that
falsifier, and includes an uncorrected run as a control so the effect of an inner validation split
is visible rather than assumed.

## 2. §3 verdict

- **Real:** a fine-grained trace observable can lower the bill; a train-internal validation split
  prevents a large overfit.
- **False:** that greedy composition pays the bill. The best pre-registered run reached only 150,
  with 2 undecided held-out runs; the six-observable diagnostic reached 148 with the same 2
  undecided. Neither met the declared criteria.
- **Unproven:** that a different selection rule, or a real repository's checker, changes this.
- **Missing:** a mechanism that supplies the remaining labels without reading held-out verdicts.

Why not "experience the actions once"? Composition adds distinctions but not judgments. When the
selection maximised training cells alone it produced 125 cells and 26 held-out abstentions: a
larger table that had memorised the fit set. Inner validation restored honesty and reduced the gain
to 28 cells. The bill is a property of what the world can distinguish, not of table size alone.

## 3. Plan and killed ideas

**Plan:** split the 231 real depth-5 runs into 178 fit and 53 untouched; inside the 178, use a
128/50 fit/validation split; greedily add observables that increase cells while remaining exact on
the inner validation; evaluate once on the 53 untouched runs. Rejected: model guidance, answer
storage in weights, weakening M3/M4, and selecting observables from outer held-out labels. Killed:
"more observables means fewer questions." The uncorrected run is kept as a receipt, not hidden.

## 4. Evidence

| run | selected observables | train cells | worst-case bill | held-out undecided | false accepts |
|---|---|---:|---:|---:|---:|
| uncorrected (control) | 3 | 125 | 53 | **26** | 0 |
| pre-registered, inner validation | 3 | 28 | 150 | 2 | 0 |
| diagnostic, 6 allowed, 4 chosen | 4 | 30 | 148 | 2 | 0 |

All three receipts keep criteria M1–M5 as declared; `all_criteria_met` is `false` in each case.
The pre-registered M3 and M4 both fail. Total producer time 245 s; 0 model calls, 0 parameters,
0 network calls. No criterion was relaxed after the result.

## 5. Tests

`intake/tests/test_observable_composition_measurement_v1.py` — **3 passed**: all composition runs
keep the declared failure; inner validation reduced 26 abstentions to 2; allowing more observables
did not reach the bill target. Combined intake suites: **26 passed**.

## 6. Non-claims and next bottleneck

Not claimed: OSWorld/SWE-bench performance, GUI/browser use, natural-language understanding, live
wiring, independent verification, or §6 completion. One CLI machine is not computer use; the goal
label is the project's own portable judge, not a new human judgment. `truth.achieved` stays `false`.

**Next bottleneck:** the remaining 2 held-out abstentions are now the sharpest target — they are
runs whose observable image was never seen in the fit set. The next falsifier is a *constructed*
run that lands in one of those unseen images and is labelled once, with the rule that it must also
remove at least one abstention on untouched runs without creating a false accept. If that fails,
the honest next claim is that a finite fit set cannot cover this machine's observations.
