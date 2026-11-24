# Independent repair and one-shot carrier review request

**This template remains unsigned and is not an attestation.** The owner subsequently supplied a scoped approval statement, preserved in `SWE_REPAIR_OWNER_APPROVAL_20261124_V1.md`; it was not accompanied by a cryptographic signature or independent reproduction logs. The machine predicates described below are historical observations at the candidate revision, not evidence of independent review, and must not be satisfied by inventing a flag or receipt. The repair inspect gate is now explicitly fail-closed against these weak legacy encodings. Neither this request nor an approval statement alone qualifies the carrier or grants execution authority. The candidate revision was `9a6bb9c54696175e5a93530cdd11ba2010a3e62e`; later changes require review if they are in scope.

## Actual repair-capability machine contract at the candidate revision

`canonical/runtime/verified_bound_capability_execution_adapter_v1.py`, `_load_registry`, `_receipt_anchor_verified`, and `inspect`, load `canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` (schema `PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1`) and overlay non-null row fields from `canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json`. For `python.software.repair.apply.verified.v1`, the merged row must exist, have `status` exactly `VERIFIED_BOUND_CAPABILITY`, `incremental_spend_usd` convertible to zero, and a nonempty mapping `verification`. Then one of the following must hold:

* `verification.independent_verified is True`, `verification.independently_verified is True`, `verification.producer_independent is True`, or `verification.independently_verified_by` is **any string**, even an empty one; OR
* a string `verification.receipt_path` or any string member of `verification.additional_receipts` (a list or tuple) names a JSON file resolved using `ROOT / path`. That file must parse as a mapping with `status` exactly `COMPLETE` and strings `mission_path` and `mission_sha256`; the mission path is also resolved using `ROOT / path`, must be a file, and its SHA-256 hex digest must exactly equal `mission_sha256`.

The code does not require a particular receipt schema, reviewer identity, independent run, signature, result digest, task binding, or carrier evidence. Paths are joined by `pathlib`, which means an absolute path overrides `ROOT`; the predicate does not enforce repository containment. After this check `action_template` must be a mapping with type `invoke_capability` or one of the four allowed kernel-native types. These are observations about a weak machine predicate, **not instructions to set its fields**. The current row has `independent_sprite` and `independent_test_count`, which are not accepted marker names, and has no matching receipt; `inspect` emits `BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:python.software.repair.apply.verified.v1`.

Canonical registry SHA-256: `8b35d61e542273e308ae81f294d8ef38e67fde025a3569b79ea0c0c2ef3a6415`
Snapshot registry SHA-256: `3400a1a9b35f3642ade42dfc053ad9db315332d7879c12646fb6b4777382e482`
Merged row SHA-256 (UTF-8 JSON, sorted keys, separators `,` and `:`, `ensure_ascii=False`, `default=str`): `21273fac3564eee72846384f6fe7d5c4c6c01c556b0401f12f0e8195598916fc`.

The extended registry checks in `canonical/runtime/live_integrated_brain_v1.py` are a **different gate**, with different receipt and verification-record fields and a distinct verifier/run reference; their presence must not be confused with an accepted signature or the emitting `inspect` contract. The repair row uses `source.adapter_path`, not the extended gate's `source.path`.

## Carrier: no attestation acceptance schema exists

The one-shot namespace launcher and trusted-host fixture pipeline have **no implemented independent-review attestation schema, accepted attestation path, authenticated reviewer field, or attestation digest check** that qualifies the carrier. `canonical/runtime/brokered_workspace_execution_v1.py` reports `carrier_qualified=False`. This is distinct from the repair capability's weak registry predicate. An independent reviewer may document findings below, but a successful review by itself neither changes the code's status nor provides a safe integration/admission path.

Candidate file SHA-256 values at `9a6bb9c5`:

* `canonical/runtime/zero_ambient_namespace_launcher_v1.py`: `6a5c1d8d67667f2f77ca31ea5924c3260b13045347ee36633d6d0d7b274a1bb5`
* `canonical/runtime/worker_syscall_allowlist_v1.py`: `32f9366e0f773cbb2c73fbf8833df930beb9ed1ccdef14f20b481c5cb5942c40`
* `canonical/runtime/repair_candidate_broker_v1.py`: `e70cd6a989c426375c46b7216140cf265de604526779a0fbb0ef49a8b5218583`
* `canonical/tools/isolated_worktree_fixture_collector_v1.py`: `1da459085b0555abeefd98fdcb56fa216f0c95803eac0173e34dc91e502f962a`
* `canonical/tools/recompute_worktree_fixture_receipt_v1.py`: `c3ee61e439c1991977a331092d621c4cc73d3d16150de963bf15d05ea13508b1`
* `canonical/runtime/verified_bound_capability_execution_adapter_v1.py`: `fd96af03475835c7d87eac7281568c373e58a881cb3eac20389d8a57d29a0638`

The producer-run `qualification_results/namespace_recompute_20261124.{json,log}` reports 95 tests passed, zero skipped. It is not independent verification, packet capture, broad egress proof, or a qualification. Fixture recomputation is also producer-built and assumes trusted quiescence/no hostile host writer. The candidate shares the host kernel and libraries.

## Review checklist (for the human owner and an independent reviewer)

- [ ] Identify producer and distinct reviewer, authorize only the stated scope, verify revision/clean tree, hash the full reviewed file set, and preserve a distinct run reference and raw logs.
- [ ] Examine the repair registry, exact predicate and downstream invocation/refusals; determine independently what evidence should be accepted and how it is authenticated and bound to task, code, results and reviewed carrier. Do not self-promote or modify evidence merely to pass the existing weak predicate.
- [ ] Inspect one-shot isolation threat model, shared kernel/host runtime, namespace and syscall restrictions, environment, mount and path/symlink behavior, output and resource bounds, and all unconfined/fallback paths. Persistent worker and arbitrary host writes remain out of scope and closed.
- [ ] Independently exercise legitimate and negative tests on an appropriately controlled host, including host-observed network behavior, lifecycle/descendant cleanup on timeout, SIGTERM and supervisor SIGKILL, nested mounts and environment; preserve skips and failures. Capture packets only where authorized and technically available; the existing TEST-NET probe is not packet capture or proof of universal no-egress.
- [ ] Examine host collector, expected base identity, quiescence/worker termination before hashing, write-race and symlink handling, effect and patch-byte recomputation, tampering refusals, and trust assumptions. Two snapshots cannot exclude all transient or restored writes.
- [ ] Record results, uncovered threats, residual risks and an explicit scope-limited accept/reject/defer decision. Determine separately what implementation and independently authenticated evidence are needed for qualification/admission; no future repair or benchmark result is guaranteed.

## Unsigned human-review template

This proposed human document is **not an accepted machine schema** and contains no representation that review occurred. The human reviewer must supply actual information, not placeholders presented as evidence.

```text
STATUS: UNSIGNED — REVIEW NOT YET PERFORMED
Candidate revision: 9a6bb9c54696175e5a93530cdd11ba2010a3e62e
Reviewed revision / dirty diff and hashes: [reviewer to record]
Reviewed files and SHA-256 hashes: [reviewer to record and independently check]
Producer identity: [reviewer to record]
Independent reviewer identity and affiliation: [reviewer to record]
Distinct independent run reference: [reviewer to record]
Host / kernel / architecture / test environment: [reviewer to record]
Commands, raw log locations, numeric results including failures and skips: [reviewer to record]
Threat model and reviewed scope: [reviewer to record]
Repair-gate and evidence-authentication findings: [reviewer to record]
Carrier, lifecycle, network and effect/receipt findings: [reviewer to record]
Limitations, unresolved risks and assumptions: [reviewer to record]
Decision and exact scope (accept / reject / defer): [reviewer to decide]
Date and human owner acknowledgement: [not provided]
```

Await explicit owner sign-off. Any execution remains blocked pending a properly designed and admitted carrier and independently verified effects; a five-real-instance gate and official benchmark evaluation are subsequent conditional steps, not implied by this form.
