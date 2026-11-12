# Choose the demonstrations that apply

**2026-11-12 · branch `arena/c3653209-brain` · authority NONE · measurement only**

The owner's Problem 1 is exact recall: the same task again, answered instantly. It works — the
8.13× second call is real. **Problem 2 is the one that matters: a similar task, not the same
one.** On the tree's own repeated-change record, one demonstration recovers **15.8%** of the
developers' other changes at 95.5% precision. A second demonstration, averaged over every pair,
raises that to **23.1%**. The tree has been treating the second demonstration as the lever.

It is not. **Which two demonstrations you give is the lever.**

| policy for the two demonstrations | coverage of the developers' changes | precision | right changes |
|---|---:|---:|---:|
| all pairs — the record's average | **23.12%** | 92.87% | 769 / 3326 |
| first two by path | 18.35% | 93.02% | 40 / 218 |
| two largest files | 19.77% | 92.11% | 35 / 177 |
| **chosen by self-simulation** | **61.78%** | 87.42% | 139 / 225 |
| best pair (oracle, reads the answer) | 63.72% | 87.26% | 137 / 215 |

The chosen pair recovers **2.67×** the all-pair average, **3.9×** one demonstration, and
**96.95% of the oracle-best pooled coverage**. It is the oracle-best pair on **12 of 15** pull
requests. No model, no new operator, no target outcome. The mean per pull request is 25.76% for
all pairs, **49.79% chosen**, 54.94% oracle.

Those two numbers — 49.79% and 54.94% — are the honest pair to compare, because the pooled
denominators differ when the chosen pair changes which four files remain. The pooled 61.78% vs
63.72% is a ratio of two different denominators, not a paired win. Both are reported.

## 1. What "chosen" does, and why it is allowed

A demonstration is spent to teach a rule that will be applied somewhere. The agent can see the
files it will edit. It cannot see what the developers did to them. So before choosing, it runs
**its own learner** on each candidate pair and counts the places the resulting rules change in
those target files. It picks the pair that reaches the most places.

That is the whole mechanism:

```
for each candidate pair of demonstrations:
    rules = learn_all(pair)
    predicted = sum over target files of the places rewrite(rules, target.before) changes
pick the pair with the largest predicted
```

No target `after` is read. The selector's only inputs are the demonstration pair and the
target's before-text. The oracle column reads the after-text and is a ceiling.

This is the difference between **seeing more** and **seeing what applies**. The all-pairs
baseline is what "give it a try in every environment" means: every pair, including pairs whose
change has no form in the target. It is the **worst** policy in the table. The smartest move is
not more tries; it is **two tries that cover the target's use shapes**.

## 2. The mechanism, in nine lines

The learner refuses a target when the changed call is used a way the examples never showed:

```
line 87 of target has self.assertEquals called with 3 arguments;
the examples showed it called with 2 arguments. A use the examples did not show
may not work with the new code, so nothing was changed; show that use too.
```

That refusal is the generalization boundary. The learner's own documentation says it: a part of
the code becomes a blank **only where two changed places differ**. One example gives a literal
rule; a second, *different* use makes the rule wider. The synthetic minimal case:

| demonstrations | target with 2-arg call | target with 3-arg call |
|---|---|---|
| one 2-arg example | edited | **refused** |
| two 2-arg examples | edited | **refused** |
| 2-arg + 3-arg example | edited | **edited** |

So the second demonstration is not valuable because it is a second sample. It is valuable
**only when its use shape is one the target needs and the first did not show**. Picking two
demonstrations at random is mostly picking shapes the target already has, or no shape at all.

## 3. The trade-off, stated rather than hidden

The chosen pair's precision is **87.42%**, below the all-pair **92.87%**. A pair that applies in
more places also makes more changes, and some are not the developers'. The oracle's precision is
87.26% — the policy is at the oracle's precision, not worse than it. But precision is agreement
with the developers, not correctness: **no test of any of the 15 projects was run.** The right
reading is "more correct changes, more wrong ones too," not "better."

## 4. What this does not solve

- **Five of fifteen pull requests recover nothing under any pair.** The changed code has no form
  the algebra can repeat, or the change is a whole-statement reshape. That is an **operator
  gap**, not a selection failure. Selection cannot choose a rule that does not exist.
- **One pull request is mis-selected**: `testing-cabal/testtools#335` gets 0.333 where the best
  pair gets 1.000. Predicted places are not the same as correct places; a policy that counted
  *changed sites that survive a check* would do better, and that check is the next thing to add.
- **The average is 49.79%, not 100%.** Problem 2 is **partially solved**: the selection step is
  now free and doubles what the same learner gives, but the remaining half is operator coverage
  and an oracle. "Perfect" is not a word this record supports.

## 5. What is real and what is not

| claim | verdict |
|---|---|
| exact recall is solved | **TRUE for exact repeats** — 8.13× on the second call; the tree's own proof is a cached refusal, so read the receipt, not the title |
| one demonstration generalizes to a similar task | **PARTLY** — 15.8% of the repeated change, 95.5% precision |
| a second demonstration is the lever | **FALSE as stated** — all pairs buy 23.1%; the pair choice buys 61.8% |
| "give it a try in every environment" | **DOMINATED** — that is the all-pairs baseline, the worst policy measured |
| the choice can be made without the answer | **TRUE** — self-simulation on target before-text, 12/15 oracle-best |
| a similar task is solved permanently | **FALSE** — 5/15 zero, average 49.8%; the lesson is tied to the code's shape |
| this is generalization in general | **FALSE** — one repeated change kind, 15 PRs, no project tests |

## 6. The smartest path, in order

1. **Ship the selection step.** It is free, deterministic, and already measured: 2.67× the
   all-pair coverage on the same learner. Use it wherever more than one demonstration is
   available: code edits, GUI traces, tool calls.
2. **Add the check to the prediction.** Count predicted places that survive the project's own
   tests, not places the writer changes. This should fix `testtools` and raise precision toward
   the all-pair level without losing coverage.
3. **Buy the missing operators, ranked by the refusal counts** (import-only 60, call shape 50,
   block shape 34, name 22, context 15, parse 10). This is the other half. A new operator costs
   code — round 9: one lesson, two files, ~10 lines, 5/5 held out — never more experience.
4. **Put the oracle in front of every stored lesson.** The tree's `VERIFIED_ACTION` is right
   **1 of 5** times. A learner fed a false success learns the wrong rule.
5. **Only then weights or search**, where the algebra cannot reach. Continual-ARC and
   SkillEvolBench both find harness/state methods fail on unseen tasks while weights learn;
   DGM and SICA buy their gains with archive + selection, which is this step at scale.

The order is the answer to "fastest": selection is a multiplier on what already exists, the
check is what keeps it honest, the operators are the remaining coverage, and weights are the
expensive fallback.

## 7. The 2026 literature says the same thing

- **SkillEvolBench** (arXiv:2605.24117, 180 tasks, 6 environments, 10 configurations): agents
  "adapt locally but rarely form robust reusable skills"; raw-trajectory reuse often beats
  distilled skills. Selection and abstraction are the bottleneck, not exposure.
- **ContinualSkillBench** (arXiv:2608.03874): the 16.9% sequential gain comes mostly from
  retained context, not skill abstraction.
- **SkillLearnBench** (arXiv:2604.20087): no continual method leads; more instances does **not**
  raise coverage (1→3→5 instances: 36.05→34.09→31.35). This is the external twin of the
  all-pairs baseline.
- **SkillsBench** (arXiv:2602.12670): curated skills +16.2 pp, self-generated −1.3 pp. Curation
  is selection, done by a person; this PR is selection done by the learner's own simulation.

## 8. Receipts

- Corpus: the 15 pull requests, 89 files, re-fetched from GitHub at the recorded commits and
  every file checked against its recorded SHA-256 (`/tmp/pulls.json`, 2.9 MB, not committed).
  Collection command is in the tool: `--collect /tmp/pulls.json --as-recorded-in
  canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json`.
- Tool: `canonical/tools/demonstration_pair_selection_20261112_v1.py` — 15 PRs, 220 pairs,
  870 target askings in the all-pair arm, no model, no network; `--json` writes the full record.
- Record: `canonical/tests/fixtures/demonstration_pair_selection_summary_v1.json` — per-pair
  counts, per-PR rows, organ hash, corpus hash, limits (113 KB, pinned by the tests; the tool
  writes the same record anywhere with `--json`). Baseline record: 23.96% two-example; this
  re-run reproduces 23.12% with the same learner, so the 61.78% is on the same scale.
- Tests: `canonical/tests/test_demonstration_pair_selection_v1.py` — **11 passed**: the
  2-arg/3-arg mechanism, the outcome-blind selector, every pooled number, and the row/summary
  recomputation.
- Not claimed: correctness, arbitrary coding tasks, GUI tasks, sentience. Authority NONE,
  `truth.achieved` false, $0, model calls 0.
