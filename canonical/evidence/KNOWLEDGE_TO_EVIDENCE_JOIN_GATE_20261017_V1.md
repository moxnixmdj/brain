# What the Knowledge→Evidence join actually requires — 2026-10-17

Attempted to join the Knowledge term to the evidence chain by feeding the
extractor real content fetched live from api.github.com. Each attempt got one
gate further. Recorded here because the sequence is the finding.

## The refusal ladder

| Input | Result |
|---|---|
| synthetic documents, no objective | `OBJECTIVE_REQUIRED` |
| real fetched content, no objective | `OBJECTIVE_REQUIRED` |
| objective, provenance block guessed | `LIVE_RETRIEVAL_PROVENANCE_REQUIRED` |
| objective + `status: RETRIEVAL_PROVENANCE_VERIFIED` | `PROVENANCE_CANDIDATE_MISMATCH` |

Not stuck at one wall. Four distinct gates, each passed in turn.

## The gate that matters

`objective_evidence_unit_extract.py`:

```python
if not objective:
    return {**base, "reason": "OBJECTIVE_REQUIRED"}
if provenance.get("status") != "RETRIEVAL_PROVENANCE_VERIFIED":
    return {**base, "reason": "LIVE_RETRIEVAL_PROVENANCE_REQUIRED"}
```

The extractor refuses to emit evidence units unless retrieval provenance
carries the status `RETRIEVAL_PROVENANCE_VERIFIED`.

**That status is exactly what `knowledge.status.assert` exists to produce**
(`knowledge.status.verified`). So the join between the Knowledge term and the
evidence chain is not a matter of plumbing — it is a specific, named
requirement, and it is the one thing the Knowledge term is for.

## Why the join has never worked

`knowledge.status.assert` is one of the four capabilities declaring
`runtime_native_action`, a module that does not exist
(`CAPABILITY_ADAPTER_AUDIT_20261017_V1.md`).

So the evidence chain has been demanding `RETRIEVAL_PROVENANCE_VERIFIED`
from a capability that cannot run. The machine has been blocked at a door
held by a capability that was never implemented — which is why
`knowledge.status.verified` also has zero consumers
(`KNOWLEDGE_TERM_IS_AN_ISLAND_20261017_V1.md`).

## Final state

Stopped at `PROVENANCE_CANDIDATE_MISMATCH`: the extractor compares the
provenance candidate URL against a URL on the document, after `_safe_url`
normalisation. The correct provenance shape is now narrow and known —
status, candidate_url, final_url, plus a matching document URL.

Not resolved here. The remaining work is to have `knowledge.status.assert`
emit this shape, since constructing it by hand is the wrong fix: it would
hand-fabricate the very provenance the machine demands be real.

## Consequence

The join is fully specified, not mysterious. It needs:

1. `knowledge.status.assert` implemented or repointed, emitting
   `RETRIEVAL_PROVENANCE_VERIFIED` provenance;
2. that provenance fed, with the objective, into
   `objective_evidence_unit_extract`;
3. `knowledge.status.verified` declared as consumed by the evidence chain, so
   the Knowledge term stops being an island.

Doing (2) by hand would fake the provenance and defeat the control. The
control is the point: this machine refuses to call anything evidence that was
not really retrieved.
