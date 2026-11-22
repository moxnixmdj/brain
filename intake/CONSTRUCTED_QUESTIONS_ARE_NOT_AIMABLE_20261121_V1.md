# Constructed questions are not aimable: the bill stands

**2026-11-21 · branch `arena/67c67d7e-brain` · four receipts `intake/RECEIPT_CONSTRUCTED_QUESTION_*_20261121_V1.json` · authority NONE**

---

## 0. Requirements restated

Own model/agent and weights, zero runtime model calls, no knowledge house in parameters, external
deletable knowledge, every parameter computed, one-experience learning in unseen environments,
hardest open tests, no borrowed outputs or hand-solving, no questions to the owner, research first,
ultimate minimal design, kill bad ideas, honest evidence, no §6 claim early. §2: weights hold computed
mechanisms; typed knowledge lives outside and can be added or removed without retraining.
`truth.achieved` remains `false`.

## 1. Research and the question this round asked

`THE_COUNTEREXAMPLE_IS_THE_NEXT_EXPERIMENT_20261129_V1.md` found that harmful counterexamples were
not locatable by computable search orders (best harmful pair ranked 130th and 136th of 321, worse
than chance), while one harmful answer made the statistic exact. It pre-registered the next step:
**construct** a run to separate the surviving statistics, instead of selecting one from an existing
pool, and test at depth 5. Web evidence points the same way: STAIR turns past repairs into reusable
plans [1](https://arxiv.org/pdf/2607.29658), BIGBAG into reusable AST transformations with a known
single-project bias [3](https://www.alphaxiv.org/abs/2606.24446), and DeepSWE shows verifier quality
dominates measured coding capability [2](https://arxiv.org/pdf/2607.07946). Constructing the run is
the expensive half.

## 2. §3 verdict

- **Real:** one harmful judgment refits to an exact statistic; cell labelling is a guaranteed sound
  policy at `n − cells`; the previous round's three-cell table was verdict-exact on 87 depth-4 runs.
- **False:** that a computable construction policy can aim at harm. Four distinct policies all failed
  to beat the two-question cell-labelling control on the depth-5 TARBALL pool.
- **Unproven:** that a different construction objective would aim better; that any of this is
  software engineering capability or GUI/browser computer use.
- **Missing:** a run producer for real repositories whose checker can judge the constructed run.

Why not "experience the actions once"? The action vocabulary is not the scarce object; a judgment
about a constructed contrast is. The system can enumerate what it cannot distinguish, but four
computable objectives for choosing what to try next were anti-correlated with harm or indifferent to
it. A parameter that stored the answer would be an unfalsifiable lookup, and a model call is forbidden.

## 3. Ultimate minimal plan, and the kill

**Plan:** reuse the quotient lattice and real CLI machines; construct a run by executing atom
extensions of known traces; ask for one label; refit; compare against the cell-labelling control;
declare falsifiers before the run. Rejected: model-guided acquisition, random search, more atoms,
storing the harmful pair as a skill. Killed by measurement below: construction as a cheaper
acquisition policy. The best part is no part, so the constructor does not ship as a capability; it
ships as a negative result and a test pinning that negative result.

## 4. Build and hard evidence

`canonical/tools/a_constructed_question_is_a_run_v1.py` executes 231 distinct TARBALL depth-5 runs
and constructs questions by appending 1–3 real atoms to known traces. Four declared policies:
`max_moved`, `min_moved`, `cell_split`, `survivor_collapse`. Criteria Q1–Q5 were declared in the
tool before execution. Results:

| policy | questions | harmful answers | exact after | false accepts | undecided | cell-labelling control |
|---|---:|---:|---:|---:|---:|---:|
| `max_moved` | 5 | 1 | 5 | 0 | 2 | 2 |
| `min_moved` | 6 | 0 | never | 70 | 0 | 2 |
| `cell_split` | 6 | 0 | never | 70 | 0 | 2 |
| `survivor_collapse` | 6 | 0 | never | 70 | 0 | 2 |

`max_moved` found the harmful run at question 5 — `TAR_A2, TAR_A1, TAR_A1`, a delete followed by
two writes — but paid 5 questions for it and still left 2 runs undecided. The other three policies
never found harm and learned a table that falsely accepts 70 of 231 runs. The control reaches
exactness in **2 questions with 1 harmful answer**. All four receipts record `all_criteria_met:
false`; no criterion was relaxed after seeing the numbers. Total producer time 728 s; 0 model calls,
0 parameters, 0 network calls.

## 5. Tests

`intake/tests/test_a_constructed_question_is_a_run_v1.py` — **3 passed**: all four receipts are
present, keep the pre-registered criteria and keep Q2/Q4 as failures; no policy produced more than
one harmful answer; image projection is a pure lookup. Combined with the round's earlier suites:
**17 passed**. This is a regression guard against overclaiming the constructor, not a capability
claim.

## 6. Non-claims and next bottleneck

Not claimed: OSWorld/SWE-bench performance, GUI/browser use, natural-language understanding, live
wiring, independent verification, or §6 completion. The goal label came from the project's own
`portable_judge`, not a human; one CLI machine is not computer use. `truth.achieved` stays `false`.

**Next bottleneck:** given that construction cannot aim, reduce the price of the judgment the agent
cannot aim at. The sound policy is `n − cells` cell labels; the only honest improvement is to make
cells cheaper — a coarser sufficient statistic that still has zero false accepts — not to hunt
counterexamples. Falsifier: any policy that reaches verdict-exactness on unseen depth-5 runs in
fewer than 2 labels without reading their verdicts.
