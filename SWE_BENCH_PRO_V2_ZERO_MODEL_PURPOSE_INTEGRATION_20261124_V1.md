# SWE-bench Pro V2 / HARD-51 zero-model purpose-compiler integration — iteration 10

Date: 2026-11-24 UTC  
Branch: `arena/6f8ac9ce-brain`  
Status: producer-side finite mechanism and distinct OIDC runner carrier added; no capability credit, no aggregate score, §6 NOT MET.

## 1. What changed from iteration 9

Iteration 9 proved that a distinct OIDC runner can own a hard-benchmark attempt receipt, but three fresh Terminal-Bench 4.1 CPU reward vectors were all `{"reward":0.0}`. The smallest undecided relation class became whether a zero-model Brain-owned mechanism can turn fresh hard-environment evidence into task success without hidden-test leakage. Iteration 10 does **not** answer that with a model, learner, world model, task-specific solver, hidden tests, gold patches, borrowed outputs or authored repair content. It composes only a finite, fail-closed purpose compiler from computed parts already allowed by the §2/§3 boundary:

- `canonical/harbor/brain_zero_model_purpose_policy_v2.py` derives a bounded read-only file-name scan, an instruction fingerprint, quoted operands, fenced code/diff blocks and a small finite grammar of admissible transformations: instruction-supplied unified diff, replace a quoted literal, write quoted/fenced content, remove literal lines, copy, move/rename and chmod. Arbitrary natural-language bug reports fail closed with `UNRESOLVED_PURPOSE` and an empty patch.
- `canonical/harbor/brain_zero_model_purpose_agent_v2.py` is the external Harbor `BaseAgent` adapter. It makes zero model calls, forces `model_name=None`, opens no runtime network, reads no hidden tests/solutions/verifier outputs, executes only policy-generated safe commands and captures a visible-repository git diff as `model.patch` for fresh-container replay.
- `canonical/harbor/select_swe_pro_v2_hard51_tasks_v1.py` reads pinned release metadata and per-task `task.toml` only. It does not read problem statements, solutions, tests or model trajectories, saves no raw benchmark task in the Brain repository, and selects three run-id-seeded HARD-51 task IDs.
- `canonical/tests/test_brain_zero_model_swe_pro_v2_purpose_v1.py` pins the finite grammar, hidden-path refusals, natural-language fail-closed behavior, scan/patch boundaries, model-free agent source, metadata-only selector and deterministic selection.
- `.github/workflows/zero-model-swe-pro-v2-hard51-runner-v1.yml` is a distinct GitHub Actions OIDC runner carrier. It verifies exact Brain source SHA-256 bindings, pinned SWE-bench Pro V2 `v2.0.0` bytes, release asset digests, 6,436 file checksums, digest-pinned GHCR images, an offline agent phase, disabled initial verification, and upstream `PatchReplayAgent` fresh-container re-grading.

The external store boundary is unchanged: computed mechanisms live in parameters; relation texts and grammar descriptors may live externally but predicates, world facts and goal pointers are recomputed from each machine’s own executed runs/call log. No raw external web page, PDF, task, hidden test, solution or trajectory is saved under `/home/user/brain`.

## 2. Primary-source facts used as exact bindings

- SWE-bench Pro V2 release tag `v2.0.0`, commit `66f92766bba642462d4bbe5479e83f91f9211862`: 642 validated Harbor tasks, HARD-51 subset, `v2/SHA256SUMS`, `v2/GATE.md`, `v2/tooling/patch_replay.py`, offline `[agent] network_mode="no-network"`, public GHCR images. Release gate from upstream: oracle 642/642 resolved, empty patch 642/642 unresolved, 642 manifests verified. Those are upstream release facts, not our results.
- Repo `v2/SHA256SUMS` SHA-256 `9d84f8507c89241d42d8b3ef911600a1ec75dbbb32687ce9b45b93318502c0bd`, 6,436 checked files; `v2/hard51_ids.txt` SHA-256 `6e35e84708a26443e1746ae928940555a3188654c90f3a2eb691f4f699482bd1`; `v2/tooling/patch_replay.py` SHA-256 `5c8b344de37164e9723f1724c2573013957fb644c3913a64c12c1718c737d876`.
- Release asset `SHA256SUMS` digest `sha256:2377c1a2462a911cca428611494d2595a17bd9ddf5af2e476c77566b0b40ed9a`; `swe-bench-pro-v2.0.0-tasks.zip` digest `sha256:1b4e97502e7c73c6c96d86fd72ae3b67cb081af1796784157fe3097b34406947`. The runner uses API metadata and the pinned git tree; direct release-asset download is avoided because it redirects to a host that failed with an EOF in this sandbox.
- OSWorld 2.1 reproducible evaluation uses release tag `osworld-v2.1`, not `main`: pinned code base `325ab352e2ff7410854bf8e3324c391bc60e7526`, 108 long-horizon workflows, gated HF task classes/assets, self-hosted websites, Docker/KVM or AWS provider images, Python >=3.12 and `uv sync --frozen`. The local research clone from `main` is only a source-reading aid; it is not the reproducible release. OSWorld remains blocked by gated assets, VM/KVM/display, websites and pinned evaluators.

## 3. Runner protocol and boundaries

1. Clone and verify `scaleapi/SWE-bench_Pro-os@v2.0.0` at the exact release commit; verify release asset digest metadata and `sha256sum -c v2/SHA256SUMS`.
2. Bind four exact Brain-owned source SHA-256s. AST-audit all four sources and the upstream replay agent for forbidden model/network/subprocess imports; check no known task-specific answers and no hidden-task-content readers.
3. Select three HARD-51 IDs deterministically from `sha256(run_id:task_id)`. Copy only those task directories into runner `/tmp`; never into the Brain repository.
4. Resolve each GHCR tag to an immutable `@sha256:` digest, replace only `task.toml`’s `docker_image` tag with that digest, and pull the digest-pinned image.
5. Run Harbor 0.27.0 with the Brain-owned zero-inference custom agent, `-e docker`, no model CLI argument, `--disable-verification`, `--no-export-traces`, and no verifier logs included. The agent sees only the Harbor instruction and bounded visible file-name scan; it does not read hidden tests, solutions, verifier code or borrowed outputs.
6. Re-run the same pinned task subset with upstream `patch_replay:PatchReplayAgent` and `--ak source_job=<initial job>`. The authoritative reward vectors come from the fresh-container replay `result.json`, not from the producer sandbox and not from the initial agent sandbox.
7. Emit a distinct GitHub Actions OIDC-attested receipt, SHA-256 sidecar and sanitized reward log; land only those three files on the active branch. Upload an explicit sanitized artifact list, not raw Harbor logs or raw benchmark tasks.

`PatchReplayAgent` is read-only with respect to benchmark hidden answers: its source applies the captured visible-repository git diff to a pristine image and writes a replay diagnostic; it contains no model/network client. The workflow’s static audit pins that fact.

## 4. What this mechanism is and is not

This is a finite **instruction-supplied transformation compiler**, not arbitrary natural-language purpose understanding and not authored repair content. If an instruction clearly supplies a safe quoted path, literal, fenced content or unified diff, the compiler can answer the one decision-relevant question with a bounded run. If a bug report asks for new behavior, edge-case correctness or an unspecified repair, the compiler refuses and captures an empty patch. That fail-closed refusal is a measured boundary, not a task solver and not a capability credit.

No aggregate benchmark score, §6 verification, capability/family/terminal credit, independent terminal verification, PR, merge or `truth.achieved=true` follows from this work. A three-task HARD-51 attempt is a fresh hard-environment contrast, not the full 642-task benchmark and not the full HARD-51 score. OSWorld 2.1, the remaining SWE-bench Pro V2 / HARD-51 tasks, remaining Terminal-Bench 4.1 CPU/GPU tasks, arbitrary purpose understanding, authored repair content and GUI/browser computer use remain unverified.

## 5. Runner-owned receipt status

The distinct OIDC runner workflow `45314632711` succeeded in 6m11s and landed its own receipt, SHA-256 sidecar and sanitized reward log at HEAD `d2bbd4e9`. Receipt SHA-256 `c24a1ea914d6bcccbd00d925fb2e7e1ba76f4f365a066d9842e627a935406e3a`; reward-log SHA-256 `bfb1b92dc130e81b85ecbdab544e563f44d2fe149a0a9c60b22dbbb3b0636382`; official fresh-container `result.json` SHA-256 `ade2d59609e566ac237b3c28dedc085f0d68d24abb8f3216c457412e7de1aab8`. The final full gate wrapper passed `ALL_GATES_OK True` with 26 checks after the receipt.

Three fresh run-id-seeded HARD-51 tasks produced three official reward vectors, all `{"reward":0.0}`, with `task_success_count=0` and no harness exceptions. The finite compiler planned zero action commands; one visible-state patch of 209 bytes and two empty patches were captured. This is measured evidence of fail-closed finite parsing, not task success, not authored repair content, not an aggregate benchmark score, not §6 verification and not terminal credit. Section 6 remains NOT MET.


## Producer-side gate record

The iteration-10 local gate wrapper passed `ALL_GATES_OK True` with 24 checks at `2026-11-24T02:43:57Z` on HEAD `227c3e1c`, including exact four-source binding, 11 finite-purpose tests, 15 combined zero-model Harbor tests, new workflow YAML/embedded-Python/source-binding checks, no raw benchmark task files, 200 selected regression tests and a clean tree after the ledger revert. The first wrapper run's route/OBS drift mismatch and copied assertion bug are preserved in the main report. This is local producer authority only; the distinct OIDC runner receipt is still the authority for any SWE-bench Pro V2 / HARD-51 attempt result.


## Runner receipt and final gates

The runner receipt is `canonical/verification/SWE_BENCH_PRO_V2_HARD51_ZERO_MODEL_PURPOSE_RUNNER_RECEIPT_20261124_V1.json`, its sidecar is the same path with `.sha256`, and the reward log is `canonical/verification/SWE_BENCH_PRO_V2_HARD51_REWARD_LOG_20261124_V1.json`. The local final gate wrapper `/tmp/run_iter10_runner_final_gates.py` passed 26 checks with `200 passed in 223.07s`, exact receipt/reward-log/workflow blob bindings, three OIDC run references, 29 instrument tests, 4 old zero-model Harbor tests, 11 finite-purpose tests and a clean tree after the ledger revert. No capability, family, terminal or truth credit was taken; no PR or merge was opened.
