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

## Addendum 2026-11-11 — the launcher now has a syscall allowlist; it has not been reviewed

**Producer statement. No authority, no verifier, no change to `carrier_qualified` (still `False`).** The paragraph above says the launcher "lacks reviewed syscall filtering". Until this date it lacked filtering altogether. It now has filtering; the word *reviewed* is still missing, and it is the reviewer's to supply or withhold.

What changed, exactly:

1. `canonical/runtime/worker_syscall_allowlist_v1.py` declares one list (193 calls allowed, 5 allowed only in a harmless form, 63 refused by name with `EPERM`, every other call answered `ENOSYS`, a caller that switches instruction set killed) and assembles it into a classic-BPF seccomp program. No dependency; the bytes are the same on every x86_64 host, so one hash names one program. `describe()` returns the lists and the hash; `decide(number, args)` runs the shipped program in the open for any call.
2. `canonical/runtime/zero_ambient_namespace_launcher_v1.py` installs that program in the step that enters the worker's root (`_ENTER_ROOT_BEHIND_SYSCALL_FILTER`), before `env`, before `setpriv`, before the workload. If the program is absent, malformed or refused by the kernel, the step exits 126 and runs nothing. Every launch site that uses this launcher's setup script inherits it without a change of its own: `run_confined`, the persistent worker in `brokered_workspace_execution_v1`, and `root3_read_only_local_file_query_executor_v1`.
3. `canonical/tools/carrier_qualification_probe_v1.py` no longer searches the launcher's source for a word. It asks the worker: is a filter in force, and are calls refused that the unfiltered kernel answers? Producer-run result on this tree: 9 of 10 items observed satisfied, `no_host_libraries` not satisfied, verdict unchanged (`CARRIER_NOT_QUALIFIED`). Record: `canonical/verification/CARRIER_QUALIFICATION_PROBE_20261111_V1.json`.

What a reviewer should question, in the producer's own order of doubt:

- **The list.** It was measured (a tracer followed ordinary Python, shell, `make`, `pytest`, `gcc`, `g++`, `git`, `node`, `npm` and `perl` work: 147 distinct calls in 25 traces, 140 of which can pass and 7 of which are closed on purpose) and then widened by hand with 58 calls that were **not observed**: the older and newer spellings of the same requests. Hand-widening is where a wrong entry would hide; the module's docstring names all of this.
- **What is allowed whole.** `ioctl` and `prctl` are not filtered by argument. The worker has no device node beyond `/dev/null` and no terminal; that, not the filter, is what bounds them.
- **Loopback sockets.** `AF_INET` and `AF_INET6` are allowed because the launcher's declared authority is a private loopback (`PRIVATE_NAMESPACE_LOOPBACK_ONLY`) and an existing test requires it. Netlink, packet and every other family are refused. A reviewer who wants the network stack unreachable should say so; the list changes in one line and that test changes with it.
- **The other launchers.** `root3_bound_codec_child_executor_v1`, `root3_confined_shell_executor_v1` and `root3_pdf_raster_temp_executor_v1` carry their own copy of the setup script and are **not** behind this filter.
- **One machine type.** x86_64 only. Elsewhere there is no table, therefore no filter, therefore the launcher refuses to start a worker.

What this does not change: the worker still runs the host's libc and interpreter; no attack campaign has been run; no pinned minimal runtime exists. And the class of the boundary is unchanged: namespaces plus a syscall filter on a **shared kernel**. A kernel bug reachable through an allowed call still crosses it. A virtual machine boundary does not have that property, and nothing here claims to be one.
