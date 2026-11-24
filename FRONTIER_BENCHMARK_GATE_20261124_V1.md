# Frontier benchmark gate — 2026-11-24

## Current state

**Not qualified; do not execute task agents or claim a score.** The owner now
requests Harbor task containers as the isolation boundary for these evaluations,
without nested Linux namespaces. This supersedes the earlier restriction to the
one-shot carrier for the requested Harbor evaluations; it does not imply
approval for task-triggered effects on the unisolated host or production. The
fixture collector is not qualified
for arbitrary code; it cannot express all Git changes, and its own checks do not
constitute independent authenticated attestation. Its producer-side SHA-256
recomputation is not proof of origin, isolation, correctness, or test success.
The Harbor agent now refuses before constructing a solver or executing an
environment command. The legacy SWE adapter also refuses before solver or
checkout. Neither accepts any real benchmark yet; the historical SWE-bench
Verified dataset is out of scope. The requested import name
`HarborEpistemicAgent` aliases the same refusal-only class; it is not an
executable agent.

### Why the Harbor transition remains blocked

The former proposal helper called `solve()` on a host-side thread; it no longer
accepts a host model. A **test-only** transport seam now dispatches a worker
through `environment.exec()`; that worker calls `open_model().solve()` inside
whatever environment executes it. The production entry point still refuses
before dispatch. Mocked tests confirm command construction and refusal of a
host model, **not** execution in Docker or isolation. `solve()` can have side
effects before returning, and the command filter is not an egress boundary.

Harbor `upload_dir` copies data; it does not make the copy read-only. The
entry point does not yet stage Brain, validate mounts or privileges, verify
no-network egress, capture an effect/base-bound patch, or integrate any
verifier. A fake environment or a boolean opt-in cannot establish those
properties. Harbor may also bind-mount logs and artifacts to the host, so the
actual runtime configuration must be checked, not assumed. Nested namespaces
are not required by the owner's current decision.

Harbor's [verifier-mode source](https://github.com/harbor-framework/harbor/blob/39c2219a41b3caa7a689cef1882263b5a93ae93f/src/harbor/models/task/verifier_mode.py)
defaults to a shared agent/verifier environment if no separate verifier is
configured. [SWE-bench Pro V2](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)
requires capturing a patch and separately replaying it into a pristine image;
merely running `harbor run` does not automatically provide that. FrontierSWE v2
uses px-eval's separate verification. Each suite needs its own confirmed
protocol rather than assuming every Harbor verifier is fresh. No independent
reviewer has run this integration and no verified-integration credit is claimed.

## Container-worker transport increment

`canonical/runtime/harbor_container_solver_worker_v1.py` calls the existing
`open_model().solve()` from a worker script. The non-production transport loop
encodes the request and dispatches that script exclusively with Harbor
`environment.exec`; a supplied host model is rejected before dispatch. Request
and response validation rejects oversized, malformed or ambiguous envelopes;
uncertain execution is not retried. Its returned trajectory explicitly says
that no patch or external verifier was produced. The worker's isolated Python
invocation and cleared environment do not themselves prove model independence,
read-only staging or blocked egress.

The existing proposal protocol is still only a hypothesis: no real run has
shown that `solve` returns the expected action envelope or can solve a frontier
task. Mock response tests do not show that. On this machine Docker, Podman and
Harbor remain unavailable. No task was executed and no score was earned.

## Docker configuration diagnostic (not admission)

`canonical.runtime.harbor_docker_inspect_diagnostic_v1` conservatively filters
an externally supplied Docker inspect document for a running, non-privileged,
no-network container with all capabilities dropped, no devices, one read-only
`/opt/brain-ro` bind, and optionally exactly allowlisted Harbor log binds with
caller-supplied sources. The log mounts are writable host effects and may
include `/logs/verifier`; they are not independent verdicts. It rejects GPU
access and many otherwise legitimate configurations. Harbor's pinned CLI
exposes Docker Compose mounts via `--mounts` (a JSON array), but a writable
`upload_dir` or `chmod` is not equivalent to a read-only mount.

The input document and expected ID are supplied by the caller. Even a complete
static match cannot authenticate Docker, prove the host source is sealed, bind
the inspected container to Harbor's `environment.exec`, prove future egress
stays disabled, or establish process quiescence. **It always returns a
nonzero CLI status and `execution_authorized: false`; the production agent does
not use it to bypass its refusal.** Its tests are data-only negative controls,
not a Docker test. The previous mock smoke-script test installed a fake `docker`
executable, contrary to `AGENTS.md` rule 1; it has been removed. A green guard
did not make that test compliant. More work is still needed for all four
requested wiring pieces and for the real VM and independent verifier.

### Pro candidate byte handoff (not capture or grading)

`canonical.runtime.harbor_pro_patch_handoff_v1.store_candidate_patch` can store
caller-supplied Git diff bytes once as `agent/model.patch`, after comparing
caller-supplied base values and rechecking SHA-256 over the stored bytes. Its
local Git fixture tests include modifications, deletions, and a binary addition,
then apply those bytes to a separate local Git fixture. This is **not** the
production path, an official Pro replay, an authenticated base, a proof that the
worker stopped, or complete patch capture. The production Harbor agent still
refuses, including when `BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL=1`; its trace
records that request as blocked. The helper only accepts a trusted host log
directory and never overwrites an existing `model.patch`.

In the pinned Harbor version, `environment.exec` uses Docker Compose's `main`
service. Automatic host log mounts are **optional** (`auto_mounting` defaults to
false); task-defined mounts can also exist. A live, non-authorizing diagnostic
in `canonical.runtime.harbor_live_compose_diagnostic_v1` samples the ID of that
Compose service before and after `docker inspect`, checks its project/service
labels, and checks configured log source paths against trial paths. It accepts
only exact standard log binds plus Brain, and resolves host paths before comparison.
It has not been run with real Harbor or Docker here. The two ID samples do not
atomically bind a subsequent `environment.exec`, establish quiescence, or
independently prove egress isolation; the production agent does not use the
diagnostic to authorize execution. Writable verifier logs are not independent
evidence. For FrontierSWE, the pinned px-eval rollout and grade scripts transfer
configured artifacts to a separate verifier image; a plain Harbor invocation is
not a substitute. Terminal-Bench verification is task-specific and the expected
non-Git effects cannot be inferred from the Pro patch format.

A standalone Docker smoke is provided for a disposable Linux VM with Docker
already installed and usable by the current user (this command performs no
benchmark and has not been run in this workspace):

```bash
git clone https://github.com/moxnixmdj/brain.git brain-harbor-smoke
cd brain-harbor-smoke
git checkout arena/d582a17b-brain
bash canonical/tools/harbor_docker_diagnostic_smoke_v1.sh
```

It pulls `python:3.11-alpine` if needed, prints its resolved image ID, launches
one disposable no-network container with a temporary fixture bind mounted
read-only, attempts a write as root and runs the static filter on Docker
inspect data. The container and fixture are removed on exit. It does not stage
Brain, send a solver to Harbor, prove ongoing egress isolation, or invoke a
benchmark verifier.

## Fixture-only effect expansion

The fixture collector now handles UTF-8, newline-terminated text additions,
modifications and deletions, including empty files, under its existing bounded
snapshot policy. Deleted effects carry baseline file bytes and their SHA-256;
new and modified effects carry resulting file bytes and their SHA-256. The
separate producer-built recomputation checks the effect set against a fresh
base checkout and replays the exact patch to compare file content, directories
and modes. The changed effect format is bound into its policy hash; old fixture
receipts were produced under the earlier policy and are not new-policy receipts.
Unsupported file types, paths, empty directories and mode changes are refused.
These are trusted-fixture tests, not admission for arbitrary tasks or an
independent authenticated receipt. The collector still has size limits and
unsupported Git effects; it must not be wired to execute real agents yet.

Five genuine SWE-bench Pro V2 HARD-51 task IDs were selected read-only at the
pinned commit in `qualification_results/frontier_five_discovery_20261124.json`.
The instruction and task configuration hashes enable identification, not
independent attestation. **0/5 executed; 0 patches collected or verified; no
scores.** During further preparation, the first selected task's public
`tests/config.json` verifier test names were displayed to the coding agent. No
gold patch was accessed, but that instance is no longer blind to this agent;
any later rollout must disclose this contamination. Neither the old Verified
refusals nor the Astropy trusted-fixture patches are frontier evaluations.
This machine has neither Docker nor Harbor,
no external VM, and no independent signing/verifier material has been supplied.

## Benchmark compatibility

* [SWE-bench Pro V2](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)
  supplies 642 Harbor tasks, including HARD-51. Its agent starts in an image
  with an existing base checkout, usually `/app`; grading replays the captured
  patch into a pristine image. The old Verified JSONL adapter does not implement
  this protocol. Locked runs have a 50-minute budget and no agent network except
  approved model endpoints. A Brain integration must capture and independently
  verify the exact patch before fresh-image regrading.
* [FrontierSWE v2](https://github.com/Proximal-Labs/frontier-swe-v2/tree/da83f84f8fbcec3cbf0f2b17c98ebc811355c2df)
  contains 34 diverse Harbor tasks, some requiring GPU resources; its artifacts
  and separate verifier are not generally representable as a Git diff against a
  known base. A worktree-patch carrier alone cannot implement that protocol.
  [px-eval](https://github.com/Proximal-Labs/px-eval/tree/ef9c4d1a6c69ce3e518bd11732dca109b1fc7919)
  orchestrates rollouts and separate grading. The reported benchmark uses a
  different, long-horizon protocol; a one-shot smoke run is not comparable.
* [Terminal-Bench 4.0](https://github.com/harbor-framework/terminal-bench/releases/tag/v4.0.0)
  uses the dataset `terminal-bench/terminal-bench@4.0.0`. It also needs a task
  environment and verifier integration beyond this worktree carrier.
* [FrontierCode](https://cognition.com/blog/frontier-code): Cognition describes
  its tasks as not publicly released and offers evaluation to model creators.
  Do not invent a public self-run dataset, task, harness, or score; request the
  relevant FrontierCode 2.0 evaluation access from Cognition.

## Read-only HARD-51 preflight

`canonical.tools.pro_hard51_preflight_v1` checks the pinned upstream checksum
manifest, the exact 51-task ID list, and each selected instruction and task
configuration. It records Task #1's test-name disclosure without reading test
files, checks declared network mode and image identifiers, and writes only JSON
metadata; it does not run containers, solver, task code or a verifier. The full
51-task metadata and five-task subset were checked read-only locally; results
are in `qualification_results/pro_hard51_full_metadata_preflight_20261124.json`
and `qualification_results/pro_hard51_metadata_preflight_20261124.json`.
Checksums establish agreement with the pinned bytes, not authenticated origin,
runtime isolation, or receipt provenance. Docker and Harbor executable presence
is reported for information only; even `--allow-isolated-vm-eval` cannot admit
execution. The legacy adapter similarly records that flag but never acts on it.
The Harbor refusal trace records the disclosure globally because it cannot bind
a trustworthy task identity.

## External Ubuntu VM preparation (not executed here)

These are **preparation and inspection only**, not evaluation commands. Use a
separate disposable VM with adequate disk, and have its operator review the
upstream code, resource requirements, license and costs. Network access to the
image registry and package registry would be necessary during setup. The requested
Brain runtime must not use a model endpoint; agent-phase egress must be denied.
Do not put credentials in commands, source files, logs, or agent-visible task
environments. No task code, container, oracle solution or agent is run here.

```bash
set -euo pipefail
mkdir -p "$HOME/frontier-eval-prep"
cd "$HOME/frontier-eval-prep"
# Clone the session branch after it has been pushed; record its actual HEAD.
git clone --branch arena/d582a17b-brain --single-branch https://github.com/moxnixmdj/brain.git brain
git -C brain rev-parse HEAD
git clone https://github.com/scaleapi/SWE-bench_Pro-os.git swe-pro
git -C swe-pro checkout --detach 66f92766bba642462d4bbe5479e83f91f9211862
git clone https://github.com/Proximal-Labs/frontier-swe-v2.git frontier-swe-v2
git -C frontier-swe-v2 checkout --detach da83f84f8fbcec3cbf0f2b17c98ebc811355c2df
git clone https://github.com/Proximal-Labs/px-eval.git px-eval
git -C px-eval checkout --detach ef9c4d1a6c69ce3e518bd11732dca109b1fc7919
(cd swe-pro/v2 && sha256sum -c SHA256SUMS)
python3 --version
command -v docker || echo 'Docker missing'
command -v uv || echo 'uv missing'
command -v harbor || echo 'Harbor missing'
mkdir -p reports
(cd brain && python3 -m canonical.tools.pro_hard51_preflight_v1 \
  --v2-root "$HOME/frontier-eval-prep/swe-pro/v2" --selection smoke5 \
  --allow-isolated-vm-eval) > reports/pro-smoke5-preflight.json
(cd brain && python3 -m canonical.tools.pro_hard51_preflight_v1 \
  --v2-root "$HOME/frontier-eval-prep/swe-pro/v2" --selection hard51 \
  --allow-isolated-vm-eval) > reports/pro-hard51-preflight.json
# Both reports intentionally say PREFLIGHT_ONLY_EXECUTION_BLOCKED.
```

px-eval specifies Python 3.12+, `uv`, an environment configuration and Modal
credentials; its example runtime uses Modal and may cost money. SWE-bench Pro V2
also documents Modal and public GHCR images. The owner has requested a Harbor
boundary, but the current Brain agent is not yet integrated with it. The above
clones are other repositories on the VM and do not alter this Arena branch.

**No executable Brain evaluation command is provided**: using the current
agent would only refuse, and claiming it is an integrated benchmark runner
would be misleading. After carrier qualification, authenticated verification,
protocol-specific integrations, the five-instance gate and any required scope
approval, follow the pinned upstream READMEs for image preflights, rollout and
separate grading. Terminal-Bench's upstream dataset selector is shown above;
FrontierCode access must be arranged separately. Before running other task
classes or harnesses, obtain explicit owner authorization for their actual
execution and effect model.

## Work remaining before admission

1. Integrate and test the container-local worker in a real Harbor environment.
   Establish genuinely read-only Brain staging; verify the actual runtime,
   network enforcement, configuration, mounts and lifecycle on a disposable
   Docker VM. The production entry point remains closed; the mock transport
   is not qualification. The owner no longer requires nested namespaces.
2. Implement each benchmark's artifact and verification protocol. Pro V2 must
   capture the complete patch, bind it to the actual base, hash its effects,
   and regrade in a pristine image. FrontierSWE and Terminal-Bench tasks may
   require non-Git artifacts and cannot be represented by a patch alone.
3. Arrange independent verification of the actual integration and retain raw
   evidence. A same-process flag, self-generated hash or mocked test is not
   reviewer authentication or proof of the container boundary.
4. Run the requested benchmark tasks only after the route is ready, disclose the
   Task #1 contamination, and report real outcomes and resource/cost data.

## Reference scores, not our results

Anthropic's [Fable page](https://www.anthropic.com/claude/fable) reports 69.9%
FrontierSWE v2, 49.1% FrontierCode 2.0, and 74.6% Terminal-Bench-**Science**
0.1 for Fable 5.2; its [system card](https://www.anthropic.com/claude-fable-5-2-mythos-5-2-system-card)
reports 93.0% on SWE-bench Pro. The 74.6% is not Terminal-Bench 4.0. Reported
scores need their version, agent, trials, test conditions and metric; they do
not validate or measure this repository.
