# The extraction gate, located to a single line — 2026-10-17

Previous measurement: 1 of 4 cases produced evidence. This narrows the
failure to one gate inside one capability.

## Correction to the earlier reason

The zero-evidence cases were reported as `NO_OBJECTIVE_GROUNDED_EVIDENCE_UNITS`.
Inspected directly, the actual reason is:

    RELEVANCE_SUBJECT_COVERAGE_ADMISSION_REQUIRED

Different gate, different meaning. It is not "nothing was found in the
content" — it is "the source was never admitted for extraction".

## The extractor does not read the documents I pass it

`objective_evidence_unit_extract` fetches the admitted URL itself. The
`documents` field in the joined input is not the content path. So the
extractor's ability to find units depends on which URL it admits, which is
governed by `_qualified_relevance_source`.

## Every BM25 precondition passes

Checked against the live relevance output:

```
status                      LEXICAL_RELEVANCE_RANKED   required: same
verification_method         DETERMINISTIC_BM25         required: same
output_verified             True                       required: True
top_candidate_original_index 0                         required: not None
```

All four satisfied. The route is entered, the candidate is selected, and then
`objective_evidence_unit_extract.py:294` returns:

    RELEVANCE_SUBJECT_COVERAGE_ADMISSION_REQUIRED

## What the selected row does not carry

The ranked row produced by the BM25 ranker:

    candidate, lexical_relevance_score, matched_terms,
    original_index, term_contributions

The ranker only populates `decision_role_admitted` / `decision_role_coverage`
when `_decision_role_focus(objective)` yields a focus. With no focus, those
fields are absent, and the extractor's subject-coverage admission has nothing
to admit on.

## Consequence

The 1-in-4 hit rate is explained: the successful case was the one where the
objective happened to yield a decision-role focus. The other three produced a
valid BM25 ranking with no subject-coverage fields, so the source was never
admitted and nothing was extracted.

This is a gap between two capabilities that each work correctly alone. The
ranker is entitled to return a ranking without decision-role data. The
extractor is entitled to require subject coverage before admitting a source.
Neither is wrong; the composition between them is incomplete.

## Not resolved

Whether the fix is to (a) have the ranker always emit decision-role fields,
(b) have the extractor admit on plain lexical relevance when no role focus
exists, or (c) route these objectives through the first-party relevance
verifier instead. Each is a small change with different trust implications,
and choosing among them is a design decision rather than a debugging step.
