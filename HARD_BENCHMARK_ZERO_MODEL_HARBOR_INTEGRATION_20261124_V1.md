# Hard-benchmark zero-model Harbor integration — 2026-11-24 UTC

## Scope

This iteration does **not** claim §6, terminal truth, a benchmark score, a capability registration, a merge, or a completed system. It adds the smallest honest next substrate: a Brain-owned external Harbor `BaseAgent`, a pure stdlib no-inference policy, a runner-side fresh CPU-only Terminal-Bench 4.1 selector, and a distinct GitHub Actions OIDC workflow that runs fresh unseen tasks under the official harness and lands its own sanitized reward-log receipt.

The project artifacts remain dated `2026-11-23`; this document uses the authoritative current date `2026-11-24 UTC` for current-Nov-2026 sources.

## Boundary preserved

- Parameters hold computed mechanisms only. No model calls, no model endpoints, no model name, no model token/cost credit, no learned weights and no runtime network dependency are added to producer cognition.
- The external inspectable store remains relation texts/grammar descriptors, not executable predicates, world facts, benchmark answers, hidden tests or reward labels.
- The new agent receives a task instruction from Harbor. It may use the instruction's own quoted operands to perform a small, generic, reversible file transformation. It refuses when purpose or repair content is not admissibly stated.
- Hidden `tests/`, `solution/`, `verifier/`, `.git/`, `node_modules/` and `__pycache__/` paths are pruned from the read-only scan and rejected from generated commands. No hidden-test reading, no oracle, no borrowed output and no fetched leaderboard score is used.
- Benchmark task files, tests, solutions, instructions and trajectories are not saved in this repository. They exist only in the ephemeral GitHub runner under `/tmp`.
- The GitHub Actions runner is a distinct verifier authority for the exact workflow run. Its OIDC claims, receipt and reward diagnostics are infrastructure evidence, never runtime cognition.

## Pinned current substrates

- Harbor `0.27.0`, published `2026-11-21`, Python >=3.12, custom-agent import path `module.path:ClassName`, `BaseAgent.setup/run`, `BaseEnvironment.exec`, `AgentConfig.kwargs/env`, `TrialResult.verifier_result.rewards`, and `VerifierResult.rewards`.
- Terminal-Bench `v4.1.0`, published `2026-11-03`, source commit `4070d6cef56a7d20cb5dc98d5e10ada88a6b9440`, 66 tasks and a 63-task CPU-only dataset.
- Release asset `prebuilt-images.json`, size `151060`, digest `sha256:49a2b9ce70dbbb957f3eaf74c737ccb8c6d68b3167d4ccfb5c58762a9726b289`, schema v1, `image_count=157`, `task_count=66`.
- Release asset `terminal-bench-prebuilt-v4.1.0.tar.gz`, size `456508604`, digest `sha256:c8bc0fea10af116061069248595c820d6da927652df1049ec834c6d98a6c12aa`. The workflow pulls selected digest-pinned images by `pinned_ref`; it does not need to load the full tar.
- OSWorld 2.1 and SWE-bench Pro V2 / HARD-51 are addressed as the next blocked hard-verifier frontiers, not run here.

## What the runner does

1. Binds exact SHA-256 hashes of the four Brain-owned source files and audits their imports for model/network/subprocess/producer-cognition dependencies.
2. Checks out Terminal-Bench `v4.1.0`, verifies the source commit, downloads and verifies `prebuilt-images.json` by digest.
3. Selects three CPU-only tasks using `sha256(run_id:task_name)`, excluding GPU tasks, compose-sidecar tasks, and six task names whose instruction text was already seen as build-time research. No selected task id is hardcoded and no instruction text is read by the selector.
4. Copies only the selected task directories into `/tmp`, rewrites only `task.toml` to use digest-pinned prebuilt environment and verifier images, and pulls those exact image references.
5. Runs `harbor==0.27.0` with `canonical.harbor.brain_zero_model_agent_v1:ZeroModelBrainAgent`, no `-m` model argument, one concurrent trial, and no oracle/solution.
6. Parses Harbor `result.json` reward fields into a sanitized reward log: trial ids, reward validity, per-trial reward vectors, exception types and log hashes. It records no aggregate benchmark score and no raw task text.
7. Obtains a GitHub Actions OIDC token, binds issuer/audience/repository/run id/attempt/ref/sha/workflow ref/runner environment, and emits a runner-owned receipt with a verified / unverified / failed split.
8. On push, commits only the runner-owned receipt, its `.sha256` sidecar and the sanitized reward log to the active branch. The local producer pulls that commit; it never writes the authoritative receipt.

## Honest expected outcome

The policy is deliberately finite and zero-model. Most hard tasks should fail or remain unresolved; the runner receipt must say so. A successful workflow run means the harness boundary and reward-log authority were exercised, not that the system achieved §6. `truth.achieved` remains `false`; `section_6` remains `NOT_MET`; no capability, family, terminal or truth credit is taken.

## Next hard-verifier frontiers

- **OSWorld 2.1:** needs gated HF task classes/assets, self-hosted websites, VM/KVM/display, pinned evaluator images and a maintainer-style verifier. None exists in this sandbox or the current runner workflow.
- **SWE-bench Pro V2 / HARD-51:** needs 642 locked Harbor tasks, GHCR images, an offline agent phase and fresh-container patch re-grading. No such run or score is claimed.
- **Terminal-Bench 4.1:** this iteration tests only a fresh, seeded, CPU-only three-task subset under pinned images and RewardKit-style separate verifiers. The other CPU tasks, GPU tasks, OSWorld and SWE-bench Pro remain unverified.
- The loop continues only with zero-model Brain-owned cognition, fresh unseen tasks, distinct verifier logs, and explicit failed/unverified splits. It must not merge or claim done until §6 is genuinely met.
