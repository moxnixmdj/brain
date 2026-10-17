# The Knowledge term is an island — 2026-10-17

Followed the knowledge.* subgraph by what each capability provides and who
consumes it.

## The whole subgraph

```
knowledge.json.fetch.external
   provides knowledge.observation.available
        └─> consumed by knowledge.consistency.assess
                provides knowledge.assessment.available
                     ├─> consumed by knowledge.status.assert
                     │      provides knowledge.status.verified
                     │           └─> consumed by NOTHING
                     └─> consumed by knowledge.support.materialize
                            provides knowledge.fact.materialized
                                 └─> consumed by NOTHING
```

## The finding

The four capabilities that make up the declared Knowledge term form a closed
chain that **terminates in two capabilities whose outputs nothing consumes**.

`knowledge.status.verified` and `knowledge.fact.materialized` have zero
consumers anywhere in the 68-capability graph.

So the Knowledge term is not connected to the rest of the machine. It is an
island: it computes, and nothing downstream reads the result.

## This is the same shape as the identity finding

`same_identity_supervisor` was found scored in two places and joined in none:
declared as the substrate by `frontier_intelligence_v1`, declared as the
primary mechanism of the long-horizon family, never wired to either.

The Knowledge term has the same defect at larger scale. It is declared as one
of the three terms of the Theory, it exists as owned machinery, and it is not
joined to the capability graph's outputs.

## Why it looked healthy until now

`knowledge.status.verified` was observed routing to OWNED with a four-step
chain, which read like a working capability. It is owned machinery — the user
correctly insisted it must never be outsourced — and it is. But being owned is
not the same as being connected. It runs, and its result goes nowhere.

## Interaction with the adapter audit

These are the same four capabilities found non-runnable
(`CAPABILITY_ADAPTER_AUDIT_20261017_V1.md`), all declaring
`runtime_native_action`, a module that does not exist.

So the Knowledge term is simultaneously:
- wired to a module that was never written, and
- terminated in outputs nothing consumes.

Fixing only the adapter would produce a Knowledge term that runs and still
feeds nothing. Both defects need addressing together.

## Consequence for the Theory

The three terms are currently:

  CAPABILITY  64 of 68 runnable, composed, executing
  KNOWLEDGE   declared, owned, and unconnected
  SUBSTRATE   present, checkpointing

The loop observed running earlier used `http.json.fetch_from_state` for live
retrieval — a capability *outside* the declared knowledge.* family. That is
why it worked: it is part of the connected graph.

## Under the canon

Acquisition order step 1 is "delete unnecessary capability demand", and the
governing rule is that the best part is no part. But the Knowledge term cannot
simply be deleted — it is one of the three terms. It must be *joined*, which
first requires deciding what in the machine is supposed to consume
`knowledge.status.verified`.

No code changed. This is a diagnosis, deliberately made before a fix, so the
fix is not applied to the wrong question.
