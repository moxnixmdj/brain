# Review request: retained repair candidate and launcher defects

**Status: unadmitted draft; no execution authority or independent verification.** This request does not claim a verifier, a run reference, or an accepted security boundary. It is meant for a separate reviewer to use after the exact candidate bytes are fixed. Do not update the live registries or mark evidence independent based on this document.

## What needs review

1. `RETAINED_REPAIR_ACTION_TEMPLATE_CANDIDATE_20261102.json` proposes adding one optional input binding to the existing snapshot repair action. Its `basis_action_template_canonical_sha256` binds the exact canonical JSON of that template. It is not itself a registry entry and cannot grant authority.
2. `canonical/runtime/verified_bound_capability_execution_adapter_v1.py` prepares omitted optional repair arguments by removing only absent, direct `${input.name}` bindings from a copied template. It validates the explicit retention `enabled` flag, while preserving the existing inspection gate and unconfined-execution refusal. Preparation does not authorize execution. The separate kernel renderer does **not** implement this optional behavior; RAW_GOAL retention remains unsupported. Full contract/context/database validation and an end-to-end policy are separate work.
3. `canonical/runtime/confine_v1.py` now stops on failed required mounts and resource-limit installation, and does not report `confined=True` for setup failures or timeouts. `solve_v1.act` propagates that uncertainty instead of claiming success. These are local defect corrections, not carrier admission. The solve path still has an explicit unconfined fallback when the launcher is unavailable or raises, and other direct APIs remain outside the repair guard.
4. `canonical/runtime/repair_candidate_broker_v1.py` is an unadmitted, nonpublishing staging and byte-scope comparator described in `REPAIR_CANDIDATE_BROKER_DRAFT_20261102.md`. Review its selection, privacy, quiescence assumptions, resource bounds and races; do not equate its unsigned effect request or its controlled direct tests with permission to publish or execute untrusted code.

## Independent review

A verifier distinct from the producer should review the exact changes and independently run controlled tests against the same checked-out tree. Record the verifier identity, exact revision and dirty-tree patch/file hashes, environment, command, numeric result, and a distinct run reference. A hash of this request or of a producer receipt is not verification. Evaluate whether optional pruning can change required or mismatched bindings, whether the gate and refusal remain before execution, and whether every required setup failure stops the candidate launcher before invoking the program.

A focused producer-run reproduction on **trusted fixtures only** is:

```sh
python3 -m unittest -q \
  canonical.tests.test_retained_repair_boundary_v1 \
  canonical.tests.test_confine_mount_failure_v1
```

A producer-run, network-isolated disposable-copy suite including these tests passed 182 cases. A separate pytest subset passed 51 and failed 2: the known stale registry-count assertion and the receipt-backed CLI success assertion now blocked by the earlier confinement guard. These numbers are not an independent review. The tests include simulated setup failures, not an attack campaign. The real fabric checks intentionally stop at the existing independent-evidence gate. Run in a disposable checkout with isolated test state; a copy or network namespace alone is not a hostile-code sandbox. Review the changed tests and their mocks before trusting the results. Preserve failures rather than editing evidence to obtain a pass.

## Separate carrier qualification, still missing

The existing namespace launcher is a research candidate, not a qualified carrier: it uses host libraries, lacks reviewed syscall filtering and aggregate delegated CPU/memory/PID limits, captures subprocess output without a bound, and has no proven descendant cleanup on timeout. Its `available()` only probes a namespace/chroot, and its success result is not proof of hostile-code isolation. Its network-enabled path adds additional scope. Do not run hostile code in it.

A real carrier requires a separately reviewed threat model and controlled host, pinned minimal runtime, isolation and effect/publication broker, aggregate limits, bounded output, termination and cleanup verification, and independently witnessed negative and legitimate-work tests. Qualification must cover the exact transport, file/effect boundaries, runtime, and lifecycle being admitted—not merely a locally generated configuration or a self-report from the worker. None of that evidence is created here.

Only after appropriate review, admission, and carrier qualification should a new retained-repair action be integrated and a fabric-level teach/restart/reuse comparison be attempted. The enabled and disabled arms must share the same safety and independent acceptance checks. No capability, family, benchmark or terminal credit follows from this request.
