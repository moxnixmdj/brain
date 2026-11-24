# Frontier benchmark gate — 2026-11-24

## Current state

**Not independently qualified; no benchmark score is claimed.** The owner
requests Harbor task containers as the isolation boundary, without nested Linux
namespaces, and explicitly accepts residual detached-process risk on a disposable
benchmark VM. The Harbor agent now has an **experimental opt-in path**, but it
has not run against real Docker, Harbor, tasks, or an external verifier here.
The opt-in is not approval for task effects on an unisolated host or production.
The fixture collector is not qualified for arbitrary code; producer-side SHA-256
recomputation is not proof of origin, isolation, correctness, or test success.
The legacy SWE adapter still refuses. The historical SWE-bench Verified dataset
is out of scope. `HarborEpistemicAgent` aliases the experimental opt-in class.

### Experimental opt-in and limits

The former proposal helper called `solve()` on a host-side thread; it no longer
accepts a host model. The current worker calls `open_model().solve()` inside
`environment.exec()`. With `BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL=1` and an
explicit `suite=pro-v2` or `suite=terminal-bench-4`, the entry point samples
Compose inspection before and after each exec, requires its strict static filter
to pass, and dispatches the worker. Otherwise it refuses. Mocked tests confirm
command construction and dispatch, **not** execution in Docker or isolation.
`solve()` can have side effects before returning, and the command filter is not
an egress boundary.

Harbor `upload_dir` is a copy, not a read-only mount: the operator must supply a
read-only bind at `/opt/brain-ro` and a no-network Compose configuration. The
experimental process cleanup snapshots the PID table and kills newly visible
processes before capture; it can kill unrelated new processes, can miss detached
processes, and is not a proof of quiescence. The agent refuses a writable host
agent-log mount because it writes the candidate patch on the host. A boolean,
inspection, SHA-256 and mock results cannot establish isolation or correctness.
Nested namespaces are not required by the owner's current decision.

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
`open_model().solve()` from a worker script. The transport loop
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
stays disabled, or establish process quiescence. **The standalone diagnostic
always returns a nonzero CLI status and `execution_authorized: false`.** The
experimental opt-in uses the live diagnostic's static-filter result as a filter,
not as proof. Tests are data-only negative controls, not a Docker test. The
previous mock smoke-script test installed a fake `docker` executable, contrary
to `AGENTS.md` rule 1; it was removed. A green guard did not make that test
compliant. A real VM and independent verifier remain necessary.

### Pro candidate capture and byte handoff (not grading)

`canonical.runtime.harbor_pro_git_capture_v1` captures nonignored worktree
changes with a temporary Git index, checks the expected `HEAD` before and after,
and includes binary changes without modifying the ordinary index. The
`harbor_pro_capture_transport_v1` helper dispatches this worker through Harbor's
`environment.exec` transport and feeds its claimed base, bytes and SHA-256 to
`harbor_pro_patch_handoff_v1.store_candidate_patch`, which publishes once as
`agent/model.patch` in a caller-trusted host log directory. Local tests exercise
real Git fixtures and a mocked exec receipt, including binary files and failed
receipts; they are not real Harbor or Docker tests.

The opt-in agent now calls this path for `suite=pro-v2`. It is **not** an
official Pro replay, authenticated base, proof that descendants stopped, or
complete capture: ignored untracked files, submodule contents and effects
outside the repository are not represented. A task-controlled Git configuration
can run clean filters, so do not run this worker on an untrusted repository on
the host. The task can also forge its Git and worker response; the checksum
only checks byte agreement. The handoff never overwrites an existing `model.patch`.

In the pinned Harbor version, `environment.exec` uses Docker Compose's `main`
service. Automatic host log mounts are **optional** (`auto_mounting` defaults to
false); task-defined mounts can also exist. A live, non-authorizing diagnostic
in `canonical.runtime.harbor_live_compose_diagnostic_v1` samples the ID of that
Compose service before and after `docker inspect`, checks its project/service
labels, and checks configured log source paths against trial paths. It accepts
only exact standard log binds plus Brain, and resolves host paths before comparison.
It has not been run with real Harbor or Docker here. The two ID samples do not
atomically bind a subsequent `environment.exec`, establish quiescence, or
independently prove egress isolation; the opt-in uses the diagnostic as a filter,
not as proof. A hostname is configurable, a private cgroup
namespace may hide the Docker ID, and neither in-container value authenticates
the earlier Docker inspection. A route check also does not exclude every egress
path, and an exited worker can leave detached descendants. Combining checks and
launch in one shell invocation narrows one race but does not make Docker policy,
mount state and process quiescence atomic. Writable verifier logs are not
independent evidence. For FrontierSWE, the pinned px-eval rollout and grade scripts transfer
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

## Owner-opted Ubuntu VM commands (unexecuted draft)

The following commands are derived from the pinned upstream CLIs and the
experimental wiring. They have **not been executed or proven working** here:
Docker, Harbor and Python 3.12 are unavailable. Run on a disposable Ubuntu VM
with Python 3.12, `venv`, Git, Docker and the Docker Compose plugin installed,
and a user permitted to use Docker. Installation and task execution access
registries, consume time and resources, and may incur VM or registry costs.
Inspect the code and resource settings first. The process cleanup can kill
newly visible processes inside each task container. The restrictive Compose
overlay may make tasks needing GPUs, capabilities or verifier network fail.

```bash
set -euo pipefail
export VMROOT="$HOME/brain-harbor-eval"
mkdir -p "$VMROOT"
cd "$VMROOT"
git clone --branch arena/d582a17b-brain --single-branch https://github.com/moxnixmdj/brain.git brain
git clone https://github.com/scaleapi/SWE-bench_Pro-os.git swe-pro
git -C swe-pro checkout --detach 66f92766bba642462d4bbe5479e83f91f9211862
python3.12 -m venv "$VMROOT/venv"
. "$VMROOT/venv/bin/activate"
python -m pip install 'git+https://github.com/harbor-framework/harbor.git@39c2219a41b3caa7a689cef1882263b5a93ae93f'
export BRAIN="$(cd "$VMROOT/brain" && pwd -P)"
export PYTHONPATH="$BRAIN:$VMROOT/swe-pro/v2/tooling${PYTHONPATH:+:$PYTHONPATH}"
python -c 'import canonical.runtime.harbor_epistemic_agent_v1 as a; print(a.HarborEpistemicAgent.name())'
docker info >/dev/null
docker compose version
(cd "$VMROOT/swe-pro/v2" && sha256sum -c SHA256SUMS)
python "$VMROOT/swe-pro/v2/tooling/make_subset.py" \
  "$VMROOT/swe-pro/v2/tasks" "$VMROOT/swe-pro/v2/hard51_ids.txt" "$VMROOT/hard51"
cat > "$VMROOT/brain-no-network-compose.yaml" <<'YAML'
services:
  main:
    network_mode: none
    ipc: private
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
YAML
export BRAIN_MOUNTS="$(python -c 'import json,os; print(json.dumps([{"type":"bind","source":os.environ["BRAIN"],"target":"/opt/brain-ro","read_only":True}]))')"
mkdir -p "$VMROOT/runs"
cd "$VMROOT/runs"

# Terminal-Bench agent effects stay in the task container; Harbor runs its
# task verifier. This is NOT generally a pristine-image regrade.
BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL=1 harbor run \
  -d terminal-bench/terminal-bench@4.0.0 -e docker -n 1 \
  -a canonical.runtime.harbor_epistemic_agent_v1:HarborEpistemicAgent \
  --ak suite=terminal-bench-4 --ak "brain_source=$BRAIN" \
  --mounts "$BRAIN_MOUNTS" --extra-docker-compose "$VMROOT/brain-no-network-compose.yaml" \
  --job-name brain-tb4

# SWE-bench Pro HARD-51 producer phase. No shared-container verification score.
BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL=1 harbor run \
  -p "$VMROOT/hard51" -e docker -n 1 \
  -a canonical.runtime.harbor_epistemic_agent_v1:HarborEpistemicAgent \
  --ak suite=pro-v2 --ak repo_root=/app --ak "brain_source=$BRAIN" \
  --mounts "$BRAIN_MOUNTS" --extra-docker-compose "$VMROOT/brain-no-network-compose.yaml" \
  --disable-verification --job-name brain-pro-hard51

# Official patch-replay agent; separate Harbor job creates fresh task containers.
# It reads each prior trial's agent/model.patch, then runs the task verifier.
harbor run -p "$VMROOT/hard51" -e docker -n 1 \
  -a patch_replay:PatchReplayAgent -m replay \
  --ak "source_job=$VMROOT/runs/jobs/brain-pro-hard51" \
  --job-name brain-pro-hard51-regrade
```

Do not infer success from command completion: inspect every trial's exceptions,
`agent/brain_epistemic_trace.json`, candidate patch and replay `replay.json`,
and the official verifier results. A refused trial or missing/empty patch is not
a solve. The `repo_root=/app` setting follows the pinned Pro reference's main
path; tasks that actually need `/testbed` must be configured separately rather
than silently assuming the patch replay applies it. Task #1's public verifier
test-name disclosure must accompany any report. The production-VM setup and
task images may be expensive; no result or zero-cost claim is made here.

## Work remaining for qualification

1. Independently run a disposable Docker VM and validate the actual Compose
   config, mount, network behavior, container lifecycle, cleanup and task output.
2. Check Pro capture completeness and regrade every candidate in a pristine
   image. Terminal-Bench's usual shared container is not automatically a fresh
   verifier, and its tasks may require non-Git artifacts.
3. Independently validate ATIF and task-specific verifier outputs. FrontierSWE
   remains closed until its px-eval transfer and separate grader are integrated.
4. Report actual outcomes, contamination, exceptions and resource/cost data;
   a mocked result or self-generated digest is not a score or independent review.

## Reference scores, not our results

Anthropic's [Fable page](https://www.anthropic.com/claude/fable) reports 69.9%
FrontierSWE v2, 49.1% FrontierCode 2.0, and 74.6% Terminal-Bench-**Science**
0.1 for Fable 5.2; its [system card](https://www.anthropic.com/claude-fable-5-2-mythos-5-2-system-card)
reports 93.0% on SWE-bench Pro. The 74.6% is not Terminal-Bench 4.0. Reported
scores need their version, agent, trials, test conditions and metric; they do
not validate or measure this repository.
