# The machine completes — 2026-10-17

One command, one plain-language question, every term of the Theory, and a
non-empty answer.

## The run

    python3 canonical/runtime/run_whole_machine_v1.py \
      "Does Brain own all of its capability mechanisms and keep knowledge external?" \
      "https://api.github.com/repos/moxnixmdj/brain/issues"

## Result

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
    elapsed_s:              2.3
    checkpoint:             written

Ten evidence units, each content-addressed (sha256), each carrying
`source_url` and `page_raw_sha256`.

## What unblocked it

The previous run returned zero. The cause was content format, not plumbing:
the admitted URL returned a base64-wrapped JSON envelope, so there were no
sentences to ground. Pointed at an endpoint returning prose, the identical
code path produced ten units.

Three field-name bugs were found and fixed to get here, each of which had
silently produced a false negative:

| Bug | Symptom |
|---|---|
| passed `documents`, ranker reads `candidates` | ranked an empty list |
| body in `text`, `_candidate_text` reads `snippet` | scored an empty document |
| hand-written relevance status | cleared a gate the run never earned |

The first two are the same lesson: this machine does not reject malformed
input. It scores it as empty and reports "unresolved".

## Why this is the milestone

Not because ten is a large number. Because every status in that output is
produced by something that ran, and the content was retrieved live, used,
and destroyed:

    content_retained: false
    content_sha256:   <64 hex chars>

The JIT rule is now observed end to end rather than written down. Knowledge
came in from outside, was proven, was used, and left no copy behind.

## Honest limits

- The source is an allow-listed host (api.github.com). General web retrieval
  is untested in this environment.
- These are *extracted* units, not adjudicated truth. Downstream
  claim-relation and verification steps have not been run on them.
- Ten units from one source is one run, not a benchmark. The repo's law
  requires 500 unseen instances at 100% with two independent oracles before
  a capability is credited.
