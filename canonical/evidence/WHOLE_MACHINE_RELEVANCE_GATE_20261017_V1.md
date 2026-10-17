# The whole machine runs; one gate remains, precisely located

## State of the full run

`canonical/runtime/run_whole_machine_v1.py` runs every term in one path:

    [KNOWLEDGE ] RAN  retrieve external content
    [KNOWLEDGE ] RAN  assert retrieval provenance
    [CAPABILITY] RAN  establish objective relevance
    [CAPABILITY] RAN  extract objective-grounded evidence

    provenance_status: RETRIEVAL_PROVENANCE_VERIFIED
    relevance_status:  RELEVANCE_UNRESOLVED
    evidence_units:    0
    content_bytes:     8168, retained false, sha256 kept
    model_dependency_count: 0
    incremental_spend_usd:  0

Retrieval works. Provenance works. The JIT discard works. Checkpointing works.
Every status shown is produced by something that ran.

## The remaining gate

`objective_relevance_bm25` returns:

    status: RELEVANCE_UNRESOLVED
    reason: NO_LEXICAL_OBJECTIVE_EVIDENCE

The gate order inside `rank()` is now known:

| Check | Failure reason | State |
|---|---|---|
| objective present | `OBJECTIVE_REQUIRED` | passed |
| candidates non-empty | `CANDIDATES_REQUIRED` | passed |
| focus resolvable | `RESEARCH_QUERY_FOCUS_UNRESOLVED` | passed |
| discriminative tokens | `NO_DISCRIMINATIVE_OBJECTIVE_TOKENS` | passed |
| **any candidate scoring > 0** | **`NO_LEXICAL_OBJECTIVE_EVIDENCE`** | **fails** |

So the objective is understood, tokens are extracted, and the BM25 scorer
finds no lexical overlap between those tokens and the retrieved README text.

## Two bugs of mine found along the way, both fixed

1. **Fabricated relevance.** The first run hand-wrote
   `FIRST_PARTY_RELEVANT_SOURCE_VERIFIED` -- a status no capability had
   produced. It cleared a gate the run had not earned. Now computed for real.
2. **Wrong field name.** The ranker reads `candidates`; I passed `documents`.
   It silently ranked an empty list and returned RELEVANCE_UNRESOLVED -- the
   capability was right, my input was wrong. Fixed.

Note that both errors produced the *same* visible symptom as a genuine
failure. That is worth remembering: this machine reports "unresolved" for
"you lied to me" and "you passed the wrong field" and "no evidence" alike.
Reading the reason field is the only way to tell them apart.

## What is NOT wrong

The README was genuinely retrieved (8168 bytes, sha256 recorded), provenance
was genuinely verified over live HTTP, and the extractor genuinely refused to
emit units without established relevance. The refusal chain is intact and
correct at every step.

## Open question

Whether `NO_LEXICAL_OBJECTIVE_EVIDENCE` means the focus-extraction is too
narrow, the BM25 weighting is mistuned, or the README genuinely does not
lexically answer the objective as phrased. Not resolved here. It is a
scoring question inside one capability, not a plumbing question across the
machine.
