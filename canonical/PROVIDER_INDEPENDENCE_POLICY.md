# Provider-Independence Policy

1. Every consequential checkpoint gets a content hash and a canonical GitHub event/manifest.
2. Large or binary evidence is mirrored off-provider in immutable/versioned form.
3. No provider-local state self-promotes.
4. UNKNOWN state after provider loss remains UNKNOWN until recovered or re-proved.
5. Required independent verification remains independent of the submitter/controller.
6. SQLite is transactional working state, not the sole durable source.
7. Execution providers are replaceable.
8. Hard cost rule: $0 incremental spend; no automatic paid overage.
9. Val Town may be reconciled if access is legitimately restored, but must never again be the single canonical Brain.
