# Container-local Brain evaluation runbook

Date: 2026-11-24 UTC. Branch: `arena/c889ffa2-brain`.

**Status: transport implementation and producer-run regressions, not benchmark qualification.**
No HARD-51, FrontierSWE v2, or Terminal-Bench 4.0 trial has run in this session.
The Arena checkout has no Docker executable. Cloud capacity, image-registry access,
GPU access, and billing have not been established. Do not interpret the commands
below as completed runs, guaranteed image compatibility, or permission to spend.

## Contract and limits

- Agent import: `canonical.runtime.harbor_epistemic_agent_v1:EpistemicBrainAgent`
  (`HarborEpistemicAgent` is an alias).
- The Harbor host exports source/request bytes and downloads artifacts. It never
  imports or invokes Brain's solver. The single dispatch is `environment.exec()`.
- Inside the task container, a root supervisor prepares `/opt/brain-ro-<run-id>`
  as root-owned, non-writable source. Only a non-root, capability-free child calls
  `open_model().solve()`. Python starts with `-I -S -B`; `.pth` and `sitecustomize`
  cannot execute before the filter. A narrow allowlist of image toolchain variables
  (for example PATH/CUDA/GOROOT) is restored only after filtering, not inherited
  from the Harbor host. Installed dependency directories become
  importable **after** the boundary; `.pth` files are not executed.
- The child inherits Linux no-new-privileges and the existing syscall allowlist,
  tightened to deny socket creation/connect/send and process-group escape.
  Credentials and inherited network descriptors are not passed to it. All
  descendants are killed **and reaped** before patch capture, including on normal
  exit. The task container remains the outer boundary; this is not an independently
  reviewed hostile-code sandbox or a qualified end-to-end container boundary.
- This deliberately also blocks loopback/Unix-socket clients and daemonization.
  Tasks needing those operations, root administration, a writable Brain source,
  or unavailable image dependencies can fail. Do not weaken the boundary or omit
  such failures to improve a score. A clean image, trusted image interpreter,
  root staging access, Linux x86-64, Python >=3.10 with ctypes, and Git for Git
  workspaces are prerequisites. Pre-filter interpreter/import paths must be root-owned,
  non-replaceable by the worker and outside the task workspace; setup rejects an
  in-workspace Python installation (use a trusted image interpreter via `python_bin`,
  not a host interpreter). Root tasks use uid/gid 65534 and their workspace is
  re-owned without following symlinks; hardlinked files are rejected to avoid
  changing ownership outside that tree. This may be incompatible with some tasks.
- `READ_ONLY` memory policy, immutable source, and a fresh scratch directory per
  trial prevent shared learned-state updates. Host caches/state, virtualenvs,
  weights, `.git`, benchmark datasets, tests/fixtures, oracle and solution
  directories are not exported. Existing source, registries, laws and their
  historical evidence **are** exported and hashed; that is provenance, not a
  certification that the pre-existing Brain has never seen a public benchmark.
  Empty immutable legacy state/cache directories permit read-only initialization.
  Missing dynamic/third-party dependencies still fail closed; none is installed
  or fetched during solve. No model API key is needed or should be supplied.
- `model_calls=0` and `parameters_stored=0` are the run contract; reported nonzero
  or unknown counters are rejected. Those fields alone are not proof. Real local
  syscall-denial tests support the network mechanism; **no official task execution
  has measured these claims yet**. Harbor itself installs model-provider libraries
  as harness dependencies; they are not staged as Brain runtime dependencies or
  invoked for cognition by this adapter.
- Git workspaces must start at their repository root with clean tracked files and
  no nonignored untracked files. Capture uses a private index and the frozen
  initial commit, includes binary/new/deleted/staged/committed changes, and does
  not change the real index. Ignored files and non-Git effects are not Git patches.
  Non-Git tasks retain their filesystem effects for Harbor's verifier and explicitly
  label the empty patch as non-Git, rather than initializing a repository.
- Artifacts: `agent/model.patch`, `agent/trajectory.json` (ATIF-v1.6),
  `agent/brain_result.json`, and `agent/solver.log`. Request/source/patch hashes
  bind the bytes. Reports never claim task completion or external verification.
  The trajectory records one deterministic dispatch and the returned evidence,
  **not** a fabricated shell-action history. Solver errors/timeouts are not passes.
  An uncertain transport outcome is not replayed; Harbor owns container teardown.
- Standard Harbor log paths are used. Root publications are kept out of the task
  workspace; symlink/hardlink/FIFO worker outputs are refused. Host publication
  atomically replaces files so Docker bind-mount ownership cannot force writing
  through an untrusted link. Patch/log limits are 64 MiB; JSON limits are 8 MiB.
  Exceeding a limit fails transport, never silently truncates a successful result.

## Revisions and evidence

| Component | Revision used by this runbook |
|---|---|
| Brain | The active branch above; freeze and record its exact commit before running |
| SWE-bench Pro V2 | `66f92766bba642462d4bbe5479e83f91f9211862` (v2.0.0) |
| FrontierSWE v2 | `da83f84f8fbcec3cbf0f2b17c98ebc811355c2df` |
| px-eval | `ef9c4d1a6c69ce3e518bd11732dca109b1fc7919` |
| Harbor for px-eval | `0.23.0`, as pinned by px-eval |
| Harbor for SWE / TB4 | `0.27.0` |
| Terminal-Bench | **`terminal-bench/terminal-bench@4.0.0`**, not 4.1; upstream tag commit `452bf305c6daa62fc59061d22133a7cbc7c1572e` |

The host adapter tests have run against actual Harbor 0.23.0 and 0.27.0 on
Python 3.12.16. They do not launch containers. Real Git/process/syscall tests run
on Linux/Python 3.11.2. See
`canonical/verification/HARBOR_CONTAINER_TRANSPORT_20261124_V1.json` for exact
commands, counts, limitations and the unrelated historical orientation failure.

### Contamination notice (do not erase)

An earlier session exposed public fail/pass **test names**, not a gold patch, for:

`instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e`

Run all 51 for the official HARD-51 denominator, but disclose this exposure and
report its outcome separately. Do not call all 51 untouched or count that task as
unseen-transfer evidence. Prior preflight manifest SHA256:
`9d84f8507c89241d42d8b3ef911600a1ec75dbbb32687ce9b45b93318502c0bd`;
IDs SHA256: `6e35e84708a26443e1746ae928940555a3188654c90f3a2eb691f4f699482bd1`.
No gold patches/reference solutions were used to implement this adapter. Keep
benchmark checkouts separate from Brain and never pass their `solution/`, tests,
verifier files or result directories to the solver as context.

## 1. Ubuntu 24.04 x86-64 VM setup

Use a dedicated VM with adequate storage/RAM and the GPUs required by the selected
benchmark. The commands install local infrastructure. **Frontier's full run can
allocate hundreds of long GPU trials; do not launch it without approved billing.**
Docker group membership grants root-equivalent access on this dedicated VM.

```bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y git python3.12 python3.12-venv docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Start a new login session so Docker group membership applies (or run `newgrp docker`
in the terminal), then use the following in that session. Do not run the agent as
root on the VM; only the supervisor **inside the task container** is root.

```bash
set -euo pipefail
export EVAL_ROOT="$HOME/brain-container-eval-20261124"
mkdir -p "$EVAL_ROOT" "$EVAL_ROOT/results"
export BRAIN_ROOT="$EVAL_ROOT/brain"
export AGENT='canonical.runtime.harbor_epistemic_agent_v1:EpistemicBrainAgent'
export LITELLM_LOCAL_MODEL_COST_MAP=True
# No provider key is needed: this is a label for runner metadata, not an API model.
export MODEL_LABEL='brain-owned/no-external-model'

docker info >/dev/null
docker compose version
python3.12 --version
# For a private Brain repository, use your VM's existing authorized Git transport.
git clone --single-branch --branch arena/c889ffa2-brain \
  https://github.com/moxnixmdj/brain.git "$BRAIN_ROOT"
git -C "$BRAIN_ROOT" diff --exit-code
[[ -z "$(git -C "$BRAIN_ROOT" status --porcelain --untracked-files=all)" ]]
git -C "$BRAIN_ROOT" rev-parse HEAD > "$EVAL_ROOT/results/brain-commit.txt"

python3.12 -m venv "$EVAL_ROOT/harbor-027"
"$EVAL_ROOT/harbor-027/bin/python" -m pip install 'harbor==0.27.0' 'pytest==9.2.0'
export HARBOR="$EVAL_ROOT/harbor-027/bin/harbor"
export PYTHONPATH="$BRAIN_ROOT"
"$EVAL_ROOT/harbor-027/bin/python" -m pip freeze \
  > "$EVAL_ROOT/results/harbor-027-packages.txt"
cd "$BRAIN_ROOT"
"$EVAL_ROOT/harbor-027/bin/python" -m pytest -q \
  canonical/tests/test_harbor_epistemic_agent_v1.py \
  canonical/tests/test_harbor_container_solver_v1.py
python3.12 execution_guard/agent_orientation_check_v1.py verify
python3.12 execution_guard/agent_orientation_check_v1.py intent-check \
  canonical/action_intents/HARBOR_CONTAINER_LOCAL_SOLVER_20261124_V1.json
python3.12 execution_guard/repo_integrity_guard_v1.py \
  --base b182859b79766c758b49ac1117a8d4169116f125
```

These are engineering checks, not benchmark qualification. Keep the Brain checkout
unchanged throughout evaluation. The exported source manifest also binds the actual
source bytes, including any local changes. The current branch name is fixed by Arena;
the earlier `arena/d582a17b-brain` is only historical research, not the push target.

## 2. SWE-bench Pro V2 HARD-51 — authoritative pristine-image replay

Do not score the mutable agent container. The first job only produces patches;
verification is disabled there. The second job uses the **upstream PatchReplayAgent**
in fresh images and lets the official verifier score them. Do not change tests,
thresholds, images or the replay tool to rescue failed patches.

```bash
set -euo pipefail
export SWE_ROOT="$EVAL_ROOT/SWE-bench_Pro-os"
git clone https://github.com/scaleapi/SWE-bench_Pro-os.git "$SWE_ROOT"
git -C "$SWE_ROOT" checkout --detach 66f92766bba642462d4bbe5479e83f91f9211862
cd "$SWE_ROOT"
mapfile -t HARD51 < v2/hard51_ids.txt
[[ ${#HARD51[@]} -eq 51 ]]
TASK_ARGS=()
for task in "${HARD51[@]}"; do TASK_ARGS+=(-i "$task"); done
sha256sum v2/hard51_ids.txt v2/tooling/patch_replay.py \
  > "$EVAL_ROOT/results/hard51-inputs.sha256"
export SWE_JOBS="$EVAL_ROOT/results/hard51"

PYTHONPATH="$BRAIN_ROOT" "$HARBOR" run \
  -p "$SWE_ROOT/v2/tasks" "${TASK_ARGS[@]}" -e docker \
  -a "$AGENT" -m "$MODEL_LABEL" \
  --ak "brain_source=$BRAIN_ROOT" --ak solve_timeout_sec=2700 --ak mode=AUTO \
  --n-attempts 1 --n-concurrent 1 --max-retries 0 \
  --disable-verification --jobs-dir "$SWE_JOBS" --job-name brain-hard51-patches

# This is a separate job/environment, not a second solve in the original image.
PYTHONPATH="$SWE_ROOT/v2/tooling" "$HARBOR" run \
  -p "$SWE_ROOT/v2/tasks" "${TASK_ARGS[@]}" -e docker \
  -a patch_replay:PatchReplayAgent -m replay \
  --ak "source_job=$SWE_JOBS/brain-hard51-patches" \
  --n-attempts 1 --n-concurrent 1 --max-retries 0 \
  --enable-verification --jobs-dir "$SWE_JOBS" --job-name brain-hard51-pristine-replay
```

Public amd64 images are `ghcr.io/scaleapi/swe-bench_pro-v2:<instance_id>`.
Image pull/setup and the external verifier may require network; the Brain child
still cannot make network calls. The 2700-second solve plus transport reserve fits
the benchmark's 3000-second agent phase. Preserve both jobs, every `model.patch`,
`replay.json`, verifier log, task result and job result. Missing/empty patches are
not repaired by the operator. Report all 51 outcomes and all infrastructure errors;
only pristine replay verifier results are authoritative. This Docker adaptation of
the upstream command is **not yet exercised end to end** in this session.

## 3. FrontierSWE v2 — official px-eval, separate verifier images

Use the benchmark's pinned images and task profiles. Do not substitute a generic
Docker host for its calibrated Modal B200 performance task, remove GPU requirements,
change 20-hour budgets, override entrypoints, or flatten the `job.yaml` profiles.
Three performance tasks request Modal VM runtime for valgrind/cachegrind; the chess
recovery task requires working cgroup kill/freeze; the SGLang task uses the calibrated
B200 carrier. An ordinary CPU-only Ubuntu VM is only the orchestration host here.

Credential prerequisite: authenticate Modal on the VM through its normal CLI/UI,
and provision an authorized registry-pull secret named **`px-evals-gcr-secret`** in
that Modal account. Two task profiles require that exact name. The secret's valid
registry credentials/access cannot be invented by this runbook. Do not put credentials
in `--ak`, task env, repository files or chat. No external model key is required.
If access or paid capacity is absent, stop before preflight/rollouts and record
`BLOCKED_CARRIER_ACCESS`; do not claim a benchmark result.

```bash
set -euo pipefail
export PX_ROOT="$EVAL_ROOT/px-eval"
export FRONTIER_ROOT="$EVAL_ROOT/frontier-swe-v2"
git clone https://github.com/Proximal-Labs/px-eval.git "$PX_ROOT"
git -C "$PX_ROOT" checkout --detach ef9c4d1a6c69ce3e518bd11732dca109b1fc7919
git clone https://github.com/Proximal-Labs/frontier-swe-v2.git "$FRONTIER_ROOT"
git -C "$FRONTIER_ROOT" checkout --detach da83f84f8fbcec3cbf0f2b17c98ebc811355c2df
python3.12 -m venv "$EVAL_ROOT/px-tools"
"$EVAL_ROOT/px-tools/bin/python" -m pip install 'uv==0.13.9'
export UV="$EVAL_ROOT/px-tools/bin/uv"
cd "$PX_ROOT"
# Honor upstream's lockfile; do not upgrade Harbor to 0.27 in this environment.
"$UV" sync --frozen --python python3.12
export PX_PY="$PX_ROOT/.venv/bin/python"
"$PX_PY" -c 'import importlib.metadata as m; assert m.version("harbor") == "0.23.0"'

# Run only if not already authenticated. Complete sign-in locally, not in chat.
"$PX_ROOT/.venv/bin/modal" token new
"$PX_ROOT/.venv/bin/modal" secret list
# Ensure authorized px-evals-gcr-secret exists before continuing.

export FRONTIER_ENV="$EVAL_ROOT/frontier-environment.yaml"
cat > "$FRONTIER_ENV" <<'YAML'
type: modal
kwargs:
  registry_secret: px-evals-gcr-secret
  keepalive: null
extra_allowed_hosts: []
env: {}
YAML
export PYTHONPATH="$BRAIN_ROOT"
mkdir -p "$EVAL_ROOT/results/frontier-preflight" \
  "$EVAL_ROOT/results/frontier-rollout" "$EVAL_ROOT/results/frontier-grade"

# This starts provider environments and may incur charges. Approve billing first.
cd "$EVAL_ROOT/results/frontier-preflight"
"$PX_PY" "$PX_ROOT/examples/frontier_swe_v2/preflight.py" "$FRONTIER_ROOT/tasks" \
  --environment "$FRONTIER_ENV" --concurrent 1

# Verify the official separate-verifier requirement before allocating rollouts.
"$PX_PY" - "$FRONTIER_ROOT/tasks" <<'PY'
import sys
from pathlib import Path
from px_eval.rollout import require_separate_verifier
paths = sorted(p.parent for p in Path(sys.argv[1]).glob('*/task.toml'))
assert len(paths) == 34, len(paths)
require_separate_verifier(paths)
PY
cd "$EVAL_ROOT/results/frontier-rollout"
"$PX_PY" "$PX_ROOT/examples/frontier_swe_v2/rollout.py" "$FRONTIER_ROOT/tasks" \
  --environment "$FRONTIER_ENV" --agent "$AGENT" --model "$MODEL_LABEL" \
  --ak "brain_source=$BRAIN_ROOT" --ak workspace=/app \
  --ak solve_timeout_sec=71600 --ak mode=AUTO \
  --attempts 5 --concurrent 1 --grade later

# Official grading reads recorded artifacts into NEW verifier sandboxes.
mapfile -d '' -t FRONTIER_JOBS < <(find "$EVAL_ROOT/results/frontier-rollout/jobs" \
  -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
[[ ${#FRONTIER_JOBS[@]} -gt 0 ]]
cd "$EVAL_ROOT/results/frontier-grade"
"$PX_PY" "$PX_ROOT/examples/frontier_swe_v2/grade.py" "$FRONTIER_ROOT/tasks" \
  "${FRONTIER_JOBS[@]}" --environment "$FRONTIER_ENV" --concurrent 1
```

The official scripts apply every task's runtime profile and `TASK_BUDGET_SECS`.
The adapter's 71600-second solve budget leaves capture/transport margin within
72000 seconds; it is not capped to the older transport's one-hour limit.
The full comparison uses **mean@5**, not best-of-five: preserve 34 × 5 outcomes,
including failures. A one-attempt or shortened run is a separately labelled
partial/smoke result, never the full comparison. Grade-later separates artifact
production from official scoring. Default artifact transfer can require very large
host storage; the optional upstream Modal snapshot carrier is not enabled here.

## 4. Terminal-Bench 4.0 — Harbor's task verifiers

Use all 66 tasks of the exact requested version. Some require GPUs and/or multiple
containers. Install/configure the appropriate NVIDIA driver/container runtime on
the dedicated carrier if the task metadata requires it. Do not force CPU resources,
remove services, change instructions, or silently choose only runnable tasks.
If Harbor asks for registry authentication, run `"$HARBOR" auth login` in the VM
and complete its normal browser/device flow locally.

```bash
set -euo pipefail
export PYTHONPATH="$BRAIN_ROOT"
cd "$EVAL_ROOT"
"$HARBOR" datasets download 'terminal-bench/terminal-bench@4.0.0' --cache
"$HARBOR" run -d 'terminal-bench/terminal-bench@4.0.0' -e docker \
  -a "$AGENT" -m "$MODEL_LABEL" \
  --ak "brain_source=$BRAIN_ROOT" --ak solve_timeout_sec=2700 --ak mode=AUTO \
  --n-attempts 1 --n-concurrent 1 --max-retries 0 \
  --enable-verification --jobs-dir "$EVAL_ROOT/results/tb4" --job-name brain-tb4-4.0.0
```

Task-specific Harbor timeouts remain authoritative: shorter tasks may stop the
agent earlier. The original task verifier—not Brain's return flag—owns the score.
Unlike SWE Pro V2, this is **not** a general pristine-image patch-replay protocol;
non-Git filesystem/service effects are graded as specified by each TB task. Preserve
the resolved dataset configuration, all trial artifacts/verifier logs and all 66
outcomes, including unsupported-environment and transport errors. The existing
adapter does not support simulated-user, resume, or multi-step continuation runs;
those cannot be relabelled successful if encountered.

## Interpreting results and the broader learning proposal

Do not combine regression counts with benchmark scores. Do not count producer-run
checks as independent verification. Do not promote solver `pass` flags, edit the
scoreboard, or declare the mission complete. The build-time engineering assistant
has not solved any task for Brain here.

The repository already contains goal-directed scan/question/planning and external
knowledge mechanisms (`perfect_algorithm_v1.py`, `local_guide_v1.py`). They operate
on specific representations; keyword retrieval and finite-world planning are not
proof of general semantic understanding or arbitrary code synthesis. This change
fixes where the existing solver runs; it does not replace that solver with an LLM
or establish new general reasoning capability.

Retaining one successful experience establishes a candidate rule, not where that
rule transfers. A defensible external skill record keeps preconditions, the causal
transformation, applicability/invalidators, verification evidence and versioned
provenance; raw action traces are evidence, not universal rules. Goal-directed
uncertainty reduction is preferable to trying to scan/store everything. Unseen-task
and unseen-environment counterexamples still have to test those abstractions.
No single-experience generalization, GUI/browser universality, or §6 completion is
claimed without the requested independent hard evidence.

## Primary runner references

- [SWE Pro V2 pinned documentation](https://github.com/scaleapi/SWE-bench_Pro-os/tree/66f92766bba642462d4bbe5479e83f91f9211862/v2)
- [Official pristine replay agent](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/patch_replay.py)
- [Pinned px-eval runner](https://github.com/Proximal-Labs/px-eval/tree/ef9c4d1a6c69ce3e518bd11732dca109b1fc7919)
- [Pinned FrontierSWE v2](https://github.com/Proximal-Labs/frontier-swe-v2/tree/da83f84f8fbcec3cbf0f2b17c98ebc811355c2df)
- [Terminal-Bench v4.0.0 release](https://github.com/harbor-framework/terminal-bench/releases/tag/v4.0.0)
- [Harbor 0.23.0](https://github.com/harbor-framework/harbor/tree/3c305dc5611e3600afc3c818735a82322f0264f8)
- [Harbor 0.27.0](https://github.com/harbor-framework/harbor/tree/53e3bfd2a57208c5f24cc9fbf5e6579548581cf0)
