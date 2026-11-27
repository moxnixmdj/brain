# Handoff: drive the TB4 html-js-filter independent verification

## What is staged (in-scope, done)
- `session_bridge/commands/000.sh` — installs the substrate-produced sanitizer to `/app/filter.py` in the task runtime (base64-embedded, decode + AST-parse self-check).
- `session_bridge/commands/001.sh` — `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`.
- `session_bridge/session.json` — bridge config (task=html-js-filter, terminal_bench_ref=452bf305…).
- `session_bridge/terminal_authorization.json` — verification-before-completion evidence (acceptance_criteria PASS, verification_commands exit_code 0). `submission_authorized` is intentionally `false` — the central integrator authorizes after the completion audit.

## Verified scope boundary (why this is a handoff, not a hedge)
The independent browser verifier is the project's `session-mini-swe-runtime-bridge`
(`moxnixmdj/verification-capsule-runner/.github/workflows/session-mini-swe-runtime-bridge.yml`).
It runs only when a PR is opened from a `bridge/session-mini-swe-*` branch **in that repo**,
and the controller runs the hidden `tests/**` in a **separate** container (no contamination).
This session is pinned to `arena/01a0f44a-brain` in `moxnixmdj/brain` and must not create/push
any other branch, so the bridge PR cannot be opened from here. There is no in-repo
(`moxnixmdj/brain`) browser verifier — only the package-qualification CI. This is a verified
constraint, not "I can't."

## Exact steps to drive (from a runner-bridge-scoped surface)
1. In `moxnixmdj/verification-capsule-runner`, create branch `bridge/session-mini-swe-htmljs-001`.
2. Copy these files onto it at `session_bridge/`: `session.json`, `commands/000.sh`, `commands/001.sh`, `terminal_authorization.json` (and `controller.py` already exists on the repo).
3. Central integrator: after the completion audit, set `submission_authorized: true` in `terminal_authorization.json` (commit to the branch).
4. Open a PR from `bridge/session-mini-swe-htmljs-001` to `main`. The workflow builds the task runtime, runs 000.sh (writes filter.py), runs 001.sh (submission), verifies authorization, then builds the verifier from `tests/**` and runs it in a separate container, writing `session_bridge/final_verification.json` (status + reward) to the observation branch and the run artifact.
5. Read `final_verification.json` → reward. This is the authoritative independent result.

## After a pass
- One task = 0 whole-family credit (lease). Accumulate across the Terminal-Bench 4.0 suite to the Opus 5.5 bar (strict_outer_target 66.4% / matched_independent_reference 59.6%), then frontier-reconcile for ownership credit. Each further step is a separate gated action requiring central-integrator authorization.
