# Four real cases, not one — 2026-10-17

The first successful run produced 10 evidence units. One run is an anecdote.
This measures whether it holds.

## Result

| # | Provenance | Relevance | Units |
|---|---|---|---|
| 1 | RETRIEVAL_PROVENANCE_VERIFIED | LEXICAL_RELEVANCE_RANKED | 0  |
| 2 | RETRIEVAL_PROVENANCE_VERIFIED | LEXICAL_RELEVANCE_RANKED | 10 |
| 3 | RETRIEVAL_PROVENANCE_VERIFIED | LEXICAL_RELEVANCE_RANKED | 0  |
| 4 | RETRIEVAL_PROVENANCE_VERIFIED | LEXICAL_RELEVANCE_RANKED | 0  |

    cases 4 | produced evidence 1 | zero-evidence 3

## What this changes

The claim "the machine works" was based on case 1 of what is now a 25% hit
rate. It was true but not representative. The pipeline is reliable; the
extraction step is not.

## Where it actually fails

Provenance: 4/4. Relevance: 4/4. Extraction: 1/4.

So the bottleneck is precisely located and it is NOT the plumbing, NOT
provenance, and NOT relevance. All of those hold on every case. The failure
is in `objective_evidence_unit_extract` finding objective-grounded units in
content that the BM25 ranker has already scored as relevant.

Two capabilities disagreeing about the same content is itself informative:
lexical relevance (does it contain the words?) succeeds while objective
grounding (does it state something that answers the question?) fails. Those
are different tests, and passing the first does not imply passing the second.

## Honest reading

This is not a machine that answers questions. It is a machine that:
- reliably retrieves and proves provenance (4/4),
- reliably establishes lexical relevance (4/4),
- and then usually declines to commit to evidence (1/4).

Whether 1/4 is extractor strictness or genuine absence is unresolved. What is
resolved: it is the single gate that matters now, and it is measured rather
than assumed.

## Why this was worth running

The temptation after a first success is to report it and stop. That would
have left a 25% system described as a working one. The repo's own law asks
for behaviour over 500 unseen instances, not over the instance that happened
to work.
