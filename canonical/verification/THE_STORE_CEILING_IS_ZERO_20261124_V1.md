# Why the store changes nothing: it is not the store, it is what the engine generates

**Measured 2026-11-24.** Receipts: `THE_STORE_CEILING_RECEIPT_20261124_V1.json`,
`canonical/tools/the_human_fix_is_the_oracle_for_the_relation_v1.py`.

## What was in doubt

Three independent measurements said the knowledge store changes no outcome:
full-corpus `+0`, `--limit 8` `+0`, and packaging `EMPTY 4/9 vs GENERAL 4/9`,
row-for-row identical. Every one of those is consistent with two very different
explanations:

1. the store is implemented badly, and a better one would transfer;
2. no row in this corpus can be helped by re-ordering, so no store of this kind can win.

Those demand opposite next actions, so the difference had to be measured rather than
argued. It was.

## The measurement

Take every one of the 45 rows and ask a question that needs no test run and no
sampling: **is the human's own repaired line among the hypotheses this engine produced
for that row** — and if so, was it attempted?

The answer across all 37 unsolved rows:

| bucket | rows | meaning |
|---|---|---|
| `IN_ATTEMPTS_UNSOLVED` | **0** | generated, attempted, and still did not fix the suite |
| `GENERATED_NOT_ATTEMPTED` | **0** | generated but lost to the ranking / the 8-attempt cap |
| `NEVER_GENERATED` | **37** | the engine never proposed anything shaped like the human's fix |

**The second bucket is empty. That is the whole result.** A store, by construction,
can only re-order hypotheses that already exist. There is no candidate anywhere in this
corpus for it to promote. Its measured `+0` is therefore structural, not a defect —
and the same argument kills any future re-ranking mechanism applied to this corpus.

This also re-derives the sweep's stage counts as a single fact: the build's problem is
**generation**, and the stage histogram was always telling us that. 26 of the 37 never
generated anything at all (`NO_RELATION_READ_FROM_THE_RUN` 17, plus harness/absent-test/
never-executed), and the other 11 generated 2–15 hypotheses, none of which was the fix.

## The bound that follows, and its honest limits

With no sampled evidence at all, the relation language can write the human's line for
**3/45** rows — and all three are the packaging `END_ANCHOR` family
(`8af75907`, `0625596e`, `189a76d5`), plus one row (`258202ed`) expressible only at a
different site. That number is a **floor, not a measurement of the lexicon**: most
relations are gated on a sampled value, and withholding all samples withholds those
relations too. The tool is honest about which question it answers; it does not answer
"how good is the lexicon" in general.

So the defensible claims are:

- **PROVEN:** no re-ranking mechanism can improve this corpus. The store's ceiling here
  is zero. (Empty bucket, 37/37.)
- **MEASURED:** 3/45 rows are reachable from the failing run with no sample, all regex.
- **NOT MEASURED:** the lexicon's reach on sample-gated relations. Doing that needs
  per-row samples replayed from the receipts, which are not stored; it must be
  re-instrumented.

## What this does to the immediate plan

It settles the design question the fourth ablation was built to answer, and it removes
the store from the critical path:

- Stop spending time on store admission, prior weighting and transfer harnesses. Those
  are all re-ranking machinery and the ceiling is zero. The single transfer test stays
  committed as the negative result it is.
- Spend it on generation breadth instead, which is now the only thing in the way.
  Concretely, from the 37: 17 rows read *no relation at all* from a run that did fail.
  That is the largest single bucket and the cheapest to attack, because a run that
  produced a failing assertion always contains evidence we failed to read.

## The one thing this does NOT say

It does not say the store idea is wrong in general — a corpus where the right answer
appears at rank 9 would reward re-ranking, and one verified row here
(`1b0e19f5`, click) was solved only after a relation ranker was introduced. It says that
**on this corpus, at this moment, generation is the binding constraint**, and building
ranking machinery ahead of it was the wrong order. That ordering mistake is the finding.
