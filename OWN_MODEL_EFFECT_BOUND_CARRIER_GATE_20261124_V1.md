# Own-model effect-bound carrier gate — 2026-11-24

**Progress only; mission unfinished.** §6 remains **NOT DONE**. No completion claim is made. `truth.achieved` remains `false`. Active branch `arena/e7a4ed58-brain`; formal base commit `23dabaf4fa28c8982aa444e056cd79db54a11cbb`; no merge.

## 1. Bound interpretation and §2 decision

The repeated Global Laws prompt was treated as a new mission. The system date **2026-11-24 UTC** is authoritative; `10/11/2026` is interpreted as Nov 2026. Runtime must use own model only, zero model calls, no knowledge house, external inspectable/editable instant knowledge, derived mechanisms, full computer use, and single-experience learning verified under §6. Build-time research is not shipped or counted as capability.

§2 default is kept and refined: no memorized world facts in weights, no runtime dependency on another model; computed procedures and skills may live in an external store. This loop writes no new fact or raw experience into weights and adds one external store pointer. Knowledge outside weights is necessary but not sufficient: without a trusted collector, exact-byte binding, a different verifier process with its own run reference, quiescence/cleanup evidence, and a reviewed isolation carrier, a receipt is only an integrity identifier. The current system remains code plus external stores, not a trained own-weights model.

## 2. Bottleneck selected

The live front door stays closed. `canonical/runtime/confinement_v1.py` is a normal host subprocess/clone; a controlled sentinel wrote outside the clone while the result reported `host_untouched=True` and `verified=True`. Its `receipt_sha256` hashes a pre-execution basis, not emitted bytes. Candidate Phase A wiring was reverted. The SWE adapter extracts a returned patch or worktree diff, not a trusted-collector effect.

Frontier evidence agrees that a hash, boolean, shared verifier, or worker-returned patch is not authority:

- SWE-bench Pro V2 re-grades every captured patch in a fresh container; forged dependencies outside the patch passed locally and failed the clean grade. Frontier agents nearly saturate the full V2 set, so exact protocol and clean regrade matter more than a self-reported local pass [1](https://arxiv.org/pdf/2610.24206). The pinned official README calls patch replay on a pristine image the authoritative score: `https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md`.
- Harbor resolves to a shared verifier unless a separate environment is configured: `https://github.com/harbor-framework/harbor/blob/39c2219a41b3caa7a689cef1882263b5a93ae93f/src/harbor/models/task/verifier_mode.py`. Terminal-Bench's 2026 hardening catalogs overwrite, patch, reward, fail-open, sleeper, staging, forgery, disclosure, and exploit vectors [4](https://github.com/harbor-framework/terminal-bench/issues/2086).
- OSWorld issue #567 shows graders reading ground truth from an agent-controlled VM and recommends host-side immutable snapshots or a second independent channel [7](https://github.com/xlang-ai/OSWorld/issues/567). Benchmark-trojan research found near-perfect scores with zero real solutions when agent and evaluator were not isolated [4](https://blog.pebblous.ai/report/ai-agent-benchmark-trust/en/).
- The November frontier gap analysis ranks Terminal-Bench 4.0 first, calls SWE-bench Pro V2 nearly saturated and OSWorld-V2.1 heaviest, and requires exact run protocols rather than as-is leaderboard claims [3](https://github.com/Exgentic/eval-containers/issues/733). A November coding-agent survey reports Terminal-Bench 4.1's top entry at 71.2%, but it is research context, not a score produced here [8](https://www.morphllm.com/best-ai-coding-agents-2026).

**Selected bottleneck:** trustworthy effect/receipt validation and independent verifier identity. This is a prerequisite for container-local `open_model().solve()` confinement and any defensible §6 score.

## 3. What existed, what was rejected, and what was built

Project research found existing partial mechanisms: `effect_carrier_guard_v1/v2`, `effect_broker_receipt_resolver_v1/v2`, `isolated_effect_receipt_verifier_v1.py`, `isolated_effect_collector_v1.py`, `isolated_worktree_fixture_collector_v1.py`, and `recompute_worktree_fixture_receipt_v1.py`. The last two already perform producer-built fixture snapshotting and a separate-process recomputation against a fresh base checkout, but explicitly report `independent_verification=False`, `independent_attestation=False`, `carrier_qualified=False`, and `publication_authority=False`. They were not reused as authority. `ISOLATED_REPAIR_CARRIER_REVIEW_DESIGN_20261124_V1.md` remains design-only/NOT APPROVED: effect adoption policy is owner authority, not an agent flag.

Rejected first choices: re-wiring `open_model().solve()` through the unisolated clone; accepting `confinement_admitted`, `carrier_qualified`, `receipt_sha256`, or an env opt-in; reusing patch handoff, receipt resolver, carrier guard, byte verifier, or producer recomputation alone; using `unshare`/`zero_ambient_namespace_launcher_v1` as qualification where owner docs request Harbor containers without nested namespaces; trusting a shared Harbor verifier; using worker-returned patches or host worktree diffs; adding an LLM judge; and running Pro V2/Terminal-Bench/OSWorld without the required containers, VM, assets, and budget.

Built only the missing gate:

| File | Purpose |
|---|---|
| `EFFECT_BOUND_CARRIER_PREREG_20261124_V1.md` | Frozen prereg; post-draft project-research amendment was recorded before any formal run. |
| `canonical/runtime/effect_bound_carrier_gate_v1.py` | Trusted parent: deny caller authority, bounded no-follow snapshots, canonical receipt, separate verifier invocation, run-ref distinctness, external-store/restart helpers. |
| `canonical/tools/effect_bound_carrier_independent_verifier_v1.py` | Different-code `python3 -I` verifier: recomputes receipt/effect hashes and own script digest, validates patch paths, builds a fresh tree from immutable baseline bytes, checks `git apply --check`, replays the patch, compares declared effect bytes, supplies its own run ref. |
| `canonical/tools/effect_bound_carrier_gate_v1.py` | Formal runner: five synthetic fixtures from real repository source files, 21 negative cases, store editability/restart, one canonical receipt. |
| `canonical/tests/test_effect_bound_carrier_gate_v1.py` | Real-fixture, negative-case, store, parser, authority and run-ref regression tests. |
| `canonical/astra_runtime/state/EFFECT_BOUND_CARRIER_GATE_V1.json` | External inspectable/editable/deletable store pointer; one procedure and provenance digests, no exact source binding, patch bytes, or target outcome. |
| `canonical/verification/EFFECT_BOUND_CARRIER_GATE_20261124_V1.json` | Canonical formal receipt, no patch bytes. |

No existing front-door dispatch, truth counter, protected path, declaration row, fail-closed record, or model route was changed.

## 4. Formal protocol and measured result

The prereg was frozen before the formal run. Its one amendment, recorded before implementation and any formal receipt, added the discovered producer-built collector/recomputer overlap and narrowed the increment to a different-code independent verifier with its own run reference. No threshold, arm, case, target, or implementation changed after the canonical formal receipt.

Formal command:

```bash
python3 -m canonical.tools.effect_bound_carrier_gate_v1
```

Output status: `EFFECT_BOUND_GATE_PASS__PROGRESS_ONLY`.

| Check | Result |
|---|---|
| Canonical receipt | `canonical/verification/EFFECT_BOUND_CARRIER_GATE_20261124_V1.json`, 12,765 bytes, SHA-256 `39e80076f53e961e6e012a33f6a09773532d237c6e3cbf28297a67657be14662` |
| External store | `canonical/astra_runtime/state/EFFECT_BOUND_CARRIER_GATE_V1.json`, 633 bytes, SHA-256 `c83401985ef38f9311ff3e5ee238bc7dba181eba3204f29e1de35a1c981a713a` |
| Prereg binding | SHA-256 `a2a63293298cb92f1e967240c48736121456481ec10c074dcd49232253797ce6`, matches receipt |
| Base / dirty tree | `23dabaf4fa28c8982aa444e056cd79db54a11cbb` / `582c81ed291875cebd30a912d5c3bb19269c52891e2731dcd647d5752ebb0ab9`, 6 porcelain lines at formal-run measurement |
| Synthetic fixtures | 5/5 verified; modify, add, delete, multi-modify, and mixed cases built from real repo source bytes; explicitly **not SWE-bench tasks** |
| Exact patches | 5/5 non-empty; exact `model.patch` bytes bound, independently rehashed, `git apply --check` passed, replay reproduced declared effect bytes |
| Independent processes | 5 distinct `python3 -I` verifier processes, 5 distinct verifier run refs; producer, collector, ticket, verifier, restart refs distinct |
| Negative cases | 21/21 refused or unqualified: caller authority, shared refs, missing/undeclared/duplicate/escaping effects, symlink/hardlink/special/oversized effects, outside sentinel, patch traversal, mutated receipt digest, forged patch/changed bytes, mutated patch/effect manifests, run ID, base, policy, and verifier script digest |
| External store | removal refused `STORE_MISSING__REFUSE`, restore verified, second-process restart digest matched; no patch bytes, fixture paths, or target outcome in store |
| Tests | New tests `5 passed in 0.75s`; affected regression set `81 passed, 37 subtests passed in 25.61s`. No claim about the full repository suite or honest baseline. |
| Integrity | `python3 -m py_compile` OK; `git diff --check` clean for tracked edits; no implementation changes after formal receipt |

Fixture verifier run refs: `3246c47f3971464c`, `0cd9dc49d2e79d51`, `f3b99de23aed38b3`, `c30a45c2758474d5`, `9f706a70d36f5a50`. Restart run ref: `1bc447f9a809dd1e`.

## 5. Verdict

**TRUE bounded:** a trusted parent can collect immutable declared effect bytes, bind a canonical receipt to those bytes, and have a different-code fresh verifier process recompute every digest, check patch applicability against a fresh tree built from immutable baseline bytes, replay the exact patch, compare declared effects, and return a distinct run reference. Caller-supplied authority fields can be denied. The external store can be inspected, removed, refused, restored, and restarted.

**FALSE universal:** this does not prove host isolation, untrusted-code containment, process quiescence for a real worker, aggregate CPU/memory/PID/storage limits, egress denial, task correctness, benchmark solve rate, arbitrary unseen environment learning, GUI/browser control, own trained weights, or a general GUI/DOM oracle. It does not qualify `open_model().solve()` or publish any patch.

**UNPROVEN:** hardest-open Nov 2026 SWE/computer-use score, arbitrary unseen GUI/browser qualification, own-weights-only end-to-end qualification, independent cloud verifier with a different run reference, GUI/DOM oracle, and §6. `carrier_qualified=false`, `execution_authorized=false`, `patch_published=false`, `no_automatic_adoption=true`, `independent_attestation=false`, `independent_cloud_verifier=false`, `acceptance_credit_delta=0`, `runtime_model_calls=0`, `runtime_network_calls=0`, `written_to_weights=false`, `own_weights=false`, `truth_achieved=false`, `completion_claim=false`. Zero parameter writes is not zero architecture bias.

## 6. Next bottleneck and §6 status

Physical/cost blocker logged once: Docker, Podman, Harbor, Python 3.12, a disposable independent VM, OSWorld assets, and GPUs are unavailable here; no 500-task VM run or cloud spend was attempted. All other work continues without pretending that blocker is a pass.

Next bottleneck: a reviewed container-local `open_model().solve()` carrier with real Harbor/VM isolation, egress, filesystem, process-quiescence, cleanup, aggregate-limit, and independent-review evidence; then a separate fresh cloud verifier/run reference; then the hardest-open Nov 2026 benchmark battery and GUI/DOM oracle. Until then, **§6 is NOT DONE and the mission is unfinished**.
