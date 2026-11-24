# Preregistered effect-bound carrier gate — 2026-11-24

Status: **design only; no authority, no carrier qualification, no benchmark score, no §6 completion.** This document is written before the implementation and formal receipt. Its pass/fail criteria may not be tuned after the formal run. It is a local mechanism gate, not a hardest-open benchmark.

## Bound interpretation and §2 decision

The whole mission was reread as new. The system date 2026-11-24 UTC is used; `10/11/2026` is interpreted as Nov 2026. Runtime must use own model only, zero model calls, zero knowledge house, external inspectable/editable instant knowledge, derived mechanisms, full computer use, and single-experience learning verified under §6. Build-time research is not shipped or counted as capability.

§2 default is kept and refined: no memorized world facts in weights, no runtime dependency on another model; computed procedures and skills may live in an external store. This loop stores no new fact or raw experience in weights. It adds one external receipt file. Knowledge outside weights is necessary but not sufficient: without a trusted collector, exact-byte binding, an independent verifier, quiescence/cleanup evidence, and a reviewed isolation carrier, a receipt is only an integrity identifier. The current system is still code plus external stores, not a trained own-weights model.

## Single bottleneck selected

The live front door is closed because `confinement_v1` is a normal host subprocess: a controlled sentinel wrote outside the clone while `host_untouched=True` and `verified=True` were reported. `receipt_sha256` in that carrier hashes a pre-execution basis, not emitted bytes. The SWE adapter extracts a returned patch or worktree diff, not a trusted-collector effect. Merely wiring `open_model().solve()` through that substrate would manufacture false authority.

Frontier evidence agrees. SWE-bench Pro V2 re-grades every captured `model.patch` in a fresh container; forged dependencies outside the patch passed locally and failed the clean grade [1](https://arxiv.org/pdf/2610.24206). The pinned official README calls `patch_replay:PatchReplayAgent` on a pristine image the authoritative score. Harbor resolves to a shared verifier unless a separate environment is configured; Terminal-Bench's 2026 hardening issue catalogs overwrite, patch, reward, fail-open, sleeper, staging, forgery, disclosure, and exploit vectors [4](https://github.com/harbor-framework/terminal-bench/issues/2086). OSWorld issue #567 shows graders reading ground truth from an agent-controlled VM and recommends host-side immutable snapshots or a second independent channel [7](https://github.com/xlang-ai/OSWorld/issues/567). Benchmark-trojan research found near-perfect scores with zero real solutions when agent and evaluator were not isolated [4](https://blog.pebblous.ai/report/ai-agent-benchmark-trust/en/). The November frontier gap analysis ranks Terminal-Bench 4.0 first and calls SWE-bench Pro V2 nearly saturated, OSWorld-V2.1 heaviest, and exact run protocols mandatory [3](https://github.com/Exgentic/eval-containers/issues/733). None of those benchmarks is run here.

**Bottleneck:** trustworthy effect/receipt validation and independent verifier identity. It is a prerequisite for container-local `open_model().solve()` confinement and for any defensible §6 score.

## Post-draft project research amendment, before any formal receipt

After this document was drafted, but before any implementation or formal run, deeper project research found three existing tools that must be accounted for so their evidence is neither duplicated nor overstated:

- `canonical/tools/isolated_effect_receipt_verifier_v1.py` is a byte-integrity receipt verifier. It explicitly says that a worker-supplied digest proves nothing and that expected digest, base, and policy must come from an independent trusted source.
- `canonical/tools/isolated_effect_collector_v1.py` produces host-hashed broker bytes from a namespace worker and reports `carrier_qualified=False`, `independent_verification=False`, `publication_authority=False`.
- `canonical/tools/isolated_worktree_fixture_collector_v1.py` plus `canonical/tools/recompute_worktree_fixture_receipt_v1.py` already performs producer-built fixture snapshotting and a separate-process recomputation that replays the exact patch against a fresh base checkout. It still reports `independent_verification=False`, `independent_attestation=False`, `carrier_qualified=False`, `publication_authority=False`, and its docstring says it is not an independently verified receipt. Its namespace launcher is not adopted here because the owner asks for Harbor task containers without nested Linux namespaces.

Therefore the minimal increment is **not another byte-integrity verifier or another producer-built recomputation**. It is an independent, different-code, fresh-process verifier consuming immutable bytes from a trusted parent snapshot, with its own run reference, exact-patch binding, fresh-tree replay, explicit run-ref distinctness, no caller authority fields, and no automatic publication. The existing tools remain historical producer-side prerequisites, not authority. This amendment does not change the pass/fail criteria below.

## One minimal plan, with rejected ideas

Build only the missing carrier gate:

1. A trusted parent uses the existing bounded no-follow snapshotter `canonical/runtime/repair_candidate_broker_v1.py` to enumerate a sanitized input snapshot and a post-worker effect-channel snapshot. It refuses absolute paths, `..`, NUL, duplicate paths, symlinks, hard links, special files, oversized effects, unstable reads, missing declared effects, and any undeclared difference. This is a controlled in-process parent, not a qualified isolation carrier and not the existing namespace worker.
2. It reads each declared effect once, hashes those exact bytes, and passes the immutable bytes—not a mutable path—to a separate verifier process.
3. A versioned canonical receipt binds run ID, base-commit claim, input snapshot digest, runtime policy digest, isolation/resource policy identifiers, declared normalized effect paths, each effect's byte length and SHA-256, exit/timeout/cleanup claims, collector identity/version/run ref, solver run ref, verifier identity/version/script digest, and the exact `model.patch` bytes as a declared effect.
4. An independent `python3 -I` verifier script, with different code and its own run reference, recomputes the canonical receipt digest and every effect hash, checks patch format/path safety, rejects forbidden authority fields, and returns its own verdict. The parent checks that solver, collector, and verifier run references are distinct.
5. `git apply --check` is run against a fresh git tree built from the input snapshot; this checks patch applicability, not task correctness.
6. The gate can report `receipt_verified`, but `carrier_qualified` remains false until a separately reviewed isolation carrier supplies real setup, egress, filesystem, process-quiescence, cleanup, aggregate-limit, and independent-review evidence. No patch is published, no host worktree is adopted, `execution_authorized` is always false, and `truth.achieved` remains false.

Rejected first choices and reasons:

| Rejected idea | Reason |
|---|---|
| Re-wire `open_model().solve()` through `confinement_v1` now | Prior sentinel escaped the clone while the receipt claimed `host_untouched=True`; Phase A was reverted. |
| Accept `confinement_admitted`, `carrier_qualified`, `receipt_sha256`, or an env opt-in | Project and frontier evidence both say a flag/hash/boolean is not authority; no caller flag may grant execution. |
| Reuse `harbor_pro_patch_handoff_v1.store_candidate_patch` alone | It stores candidate bytes with a checksum but explicitly does not verify origin, quiescence, completeness, isolation, or verifier outcome. |
| Reuse `effect_broker_receipt_resolver_v2.resolve_receipt_bytes` alone | It proves byte identity/existence only and says semantic verification and carrier enforcement remain separate. |
| Reuse `effect_carrier_guard_v2` alone | It binds a carrier result to authorization but does not enumerate effects, prove no-follow collection, or independently verify emitted patch bytes. |
| Reuse `isolated_effect_receipt_verifier_v1.verify_patch` alone | It is producer-callable integrity code whose own docstring says a worker-supplied digest proves nothing and an independent trusted source is still required. |
| Reuse `isolated_worktree_fixture_collector_v1` / `recompute_worktree_fixture_receipt_v1` as independent verification | Their separate recomputation is explicitly producer-built and reports `independent_attestation=False`; it reads mutable source/worktree paths and does not supply a distinct attesting verifier identity or run reference. |
| Use `unshare` / `zero_ambient_namespace_launcher_v1` as the qualification boundary | The owner decision requests Harbor task containers without nested namespaces; the broker itself reports `carrier_qualified=False`; a working namespace is not an independently reviewed VM/container boundary. |
| Trust a shared Harbor verifier | Harbor defaults to shared unless separate is configured; reward-hacking vectors move into the grading phase. |
| Use a worker-returned `model_patch` or a host worktree diff | Worker output and host diffs are untrusted; the trusted collector must bind exact emitted bytes. |
| Add an LLM judge or another runtime model | Violates zero model calls and does not solve isolation. |
| Run Pro V2 / Terminal-Bench / OSWorld now | Docker, Podman, Harbor, Python 3.12, OSWorld VM, GPUs, and a disposable independent VM are unavailable; that blocker is logged once. |

## Smartest-approach kill attempt

The design is killed if any of the following fails before the formal receipt: default refusal remains, no caller authority field is accepted, no solver/collector/verifier run-reference collision is accepted, no forged or mutated effect/receipt is accepted, no escaping/symlink/duplicate/undeclared/special/oversized effect is accepted, the exact patch bytes are not recomputed by a separate process, patch applicability is not checked against a fresh input tree, any patch is published, or `carrier_qualified`/`execution_authorized` becomes true without reviewed isolation evidence. A green-looking receipt with no carrier qualification is a bounded mechanism result, not a capability gain.

## Frozen local protocol and pass/fail

- Formal run: five identified local fixtures built from real repository source files. Each fixture is explicitly **synthetic carrier material**, not a SWE-bench task or a hidden answer. A deterministic in-process trusted fixture changes, adds, or deletes copied source bytes and emits a real unified Git patch as `model.patch`; no model call, no nested namespace carrier, and no hand-solved task answer is used. The patch is checked for applicability by the independent verifier against a fresh tree built from the immutable input snapshot.
- At least one fixture must produce a non-empty `model.patch` whose exact bytes are independently recomputed and whose `git apply --check` succeeds. All five per-instance refusals, receipt digests, and verifier run refs remain visible.
- Negative cases are preregistered from the review design: missing, undeclared, duplicated, escaping, symlink, special, oversized, changed/forged effects; mutated patch/manifest/run ID/base/policy; caller authority fields; shared run references; patch path traversal; verifier script digest mismatch; and a sentinel outside the allocated workspace. Every one must refuse or remain unqualified.
- Pass: all negative cases refuse; benign receipt verification passes; solver/collector/verifier run refs are distinct; `receipt_verified=True` on at least one exact-byte patch; `carrier_qualified=False`, `execution_authorized=False`, `patch_published=False`, `acceptance_credit_delta=0`, and no §6 claim.
- Fail: any negative case is admitted, any authority flag is honored, any patch is published, any score or completion is claimed, or the verifier is not a different process/implementation with a distinct run ref.
- No threshold, case, target, or implementation may be changed after the formal receipt.

## §6 status regardless of result

**NOT DONE.** No hardest-open Nov-2026 coding/computer-use benchmark, no arbitrary unseen GUI/browser environment, no single-experience universal-learning qualification, no own-weights-only end-to-end qualification, no GUI/DOM oracle, no independent cloud verifier with a different run reference, and no completion claim. The next bottleneck remains a reviewed container-local `open_model().solve()` carrier with real isolation/quiescence/cleanup evidence, followed by the hardest-open benchmark battery and a GUI/DOM oracle.
