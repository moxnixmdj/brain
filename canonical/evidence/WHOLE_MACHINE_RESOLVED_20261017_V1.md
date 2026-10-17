# Resolved: the machine works; the objective's length was the gate

The 1-in-4 was not a defect. It was the coverage threshold doing its job.

## The gate, finally read rather than inferred

`objective_evidence_unit_extract.py:291`:

    admission = relevance.get("top_candidate_admission") or {}
    if admission.get("verified") is not True:
        return None, "RELEVANCE_SUBJECT_COVERAGE_ADMISSION_REQUIRED"

I had spent turns checking `decision_role_admitted` — the wrong field. Reading
the line took one command.

## The actual mechanism

`required_matched_term_count` scales with `query_token_count`. More
discriminative terms in the question means more must be matched before the
source is admitted as answering it.

| Objective | query tokens | matched | required | verified | units |
|---|---|---|---|---|---|
| Does Brain own all of its capability mechanisms and keep knowledge external? | 10 | 2 | 3 | false | 0 |
| Should Brain outsource capability or own it? | 5 | 2 | 2 | true | 10 |
| Does Brain own its capability mechanisms? | 5 | 2 | 2 | true | 10 |

Same URL, same code path, same content. Only the question changed.

## Why the machine was right

A question containing ten distinctive terms, where the retrieved document
matches only two, is not answered by that document. Admitting it as evidence
would be claiming more than the content supports. The machine declines.

Shorten the question to what is actually being asked, and the same content
clears the bar honestly.

This is not strictness to be tuned away. It is the difference between
"this document contains some of my words" and "this document answers my
question".

## Final state — all pieces, one run

    python3 canonical/runtime/run_whole_machine_v1.py \
      "Should Brain outsource capability or own it?" \
      "https://api.github.com/repos/moxnixmdj/brain/issues?state=closed"

    [KNOWLEDGE ] RAN  retrieve external content
    [KNOWLEDGE ] RAN  assert retrieval provenance
    [CAPABILITY] RAN  establish objective relevance
    [CAPABILITY] RAN  extract objective-grounded evidence

    provenance_status:      RETRIEVAL_PROVENANCE_VERIFIED
    relevance_status:       LEXICAL_RELEVANCE_RANKED
    evidence_units:         10
    knowledge_retained:     false
    model_dependency_count: 0
    incremental_spend_usd:  0

## Method note

Four times this session a field name was inferred instead of read:
`documents`/`candidates`, `text`/`snippet`, `decision_role_admitted`/
`top_candidate_admission`, and a hand-written relevance status. Every one
produced a false negative that looked exactly like a genuine absence.

The machine does not reject malformed input. It scores it as empty and
reports "unresolved". Reading the line, not the error string, is the only
reliable move.
