# EPISTEMIC BENCHMARK ADAPTERS

**Two experimental wrappers, zero score claims. Do not start a VM run yet.**

**Safety and decision-gate update (2026-11-24):** The five-instance synthetic
post-candidate dry-run produced 0/5 patches for both EPISTEMIC and
SOLVE_OR_LEARN; none was receipt-verified. The candidate Phase A repair wiring
was reverted after review showed that the existing clone-based carrier is not
an OS sandbox and can write outside its clone even while reporting the host
untouched. Its receipt identifier alone does not verify outcome/effect bytes.
See the safety update at the top of
`CONFINEMENT_FRONT_DOOR_WIRING_DESIGN_20261124_V1.md`. The original repair
refusal remains; no external smoke test is approved. The wrapper currently
extracts a model-returned or worktree diff with applicability checks, **not**
receipt-verified patch bytes; a non-empty prediction by itself cannot satisfy
the gate. The commands below are planning material, not a green light.

Date: 2026-11-24 · Authority: `NONE__SANDBOX_ONLY` · Branch `arena/d582a17b-brain`

Local evidence: 20/20 unit tests pass (`python3 -m unittest` on the two new test
modules); 29/29 including the existing Harbor brain-agent tests. No benchmark was run here: this sandbox has Python 3.11, no Docker and
no SWE-bench/Harbor packages. A percentage requires the official harness on the
external machine described below.

## 1. What was actually added

| File | Role |
|---|---|
| `canonical/tools/swebench_verified_epistemic_adapter_v1.py` | Calls `open_model().solve(goal, inputs=..., mode="EPISTEMIC", ...)`, writes official `predictions.jsonl` plus a fail-closed trace sidecar. |
| `canonical/tests/test_swebench_verified_epistemic_adapter_v1.py` | 12 tests: prediction shape, answer-field exclusion, worktree diff, patch validation, no self-granted confinement, exception path, smoke-test filtering. |
| `canonical/runtime/harbor_epistemic_agent_v1.py` | External `BaseAgent` that calls the same engine, executes only explicitly proposed commands through the existing Harbor transport/command policy, and writes a trace. |
| `canonical/tests/test_harbor_epistemic_agent_v1.py` | 8 tests: proposal execution, fail-closed refusal, forbidden command, uncertain exec, trace and context handling. |

Both wrappers forward the mode string verbatim. **Correction to the plan that
was handed over:** `mode="EPISTEMIC"` is not a registered mode in
`open_model().solve()`; only `RECALL` and `SOLVE_OR_LEARN` are special-cased.
Every other string, including `EPISTEMIC` and `AUTO`, uses ordinary routing.
Both wrappers record this as `MODE_NOT_SPECIAL_CASED_BY_ENGINE:EPISTEMIC` in
their sidecars rather than implying a new engine capability.

## 2. SWE-bench Verified: produce predictions

### 2.1 External machine (not this sandbox)

Baseline from the SWE-bench harness docs: 8+ CPU cores, 16 GB+ RAM, 150 GB+
free SSD (Docker images are large), unrestricted outbound network access.

```bash
# Docker (the plan's "https://docker.com | sh" URL is not the installer)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER" && newgrp docker

# uv + Python 3.12 (the plan's "https://astral.sh" URL is incomplete)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
uv venv --python 3.12 .venv-swebench
source .venv-swebench/bin/activate
uv pip install swebench datasets
```

Pre-clone the task repositories once into `--repos-root` using
`<owner>__<repo>` directory names (for example `django__django`). The adapter
creates and removes a detached worktree at each instance's `base_commit`; it
never clones, fetches or installs anything. Task rows can come from a local
JSONL file or from `SWE-bench/SWE-bench_Verified` via `datasets`.

### 2.2 Generate a 50-task smoke test

```bash
python3 -m canonical.tools.swebench_verified_epistemic_adapter_v1 \
  --dataset-name SWE-bench/SWE-bench_Verified \
  --repos-root /data/swe_repos \
  --output predictions_smoke.jsonl \
  --report adapter_report_smoke.jsonl \
  --workdir /data/brain_swe_work \
  --limit 50 --run-id epistemic_smoke_50
```

`predictions_smoke.jsonl` has exactly the three official string fields per line:

```json
{"instance_id": "django__django-11099", "model_name_or_path": "b81b2217-epistemic-v1", "model_patch": "<git diff>"}
```

Every dataset instance is written, including unresolved ones with an empty
`model_patch`. The sidecar records `model_status`, `model_reason`, patch source,
`git apply --check` result and a reason code for each empty patch. A patch is
emitted only from a model result field or from an actual worktree diff, and it
must look like a unified diff and pass `git apply --check` (forward or reverse).

### 2.3 Grade with the official harness

```bash
python -m swebench.harness.run_evaluation \
  --dataset_name SWE-bench/SWE-bench_Verified \
  --predictions_path predictions_smoke.jsonl \
  --max_workers 6 \
  --run_id epistemic_smoke_50
```

Replace `--limit 50` with the full 500 only after the smoke test. Use a fresh
`--run_id` for each different prediction file: the harness caches by `run_id`
and `instance_id`, so reusing an ID silently re-scores the first patch set.
Read the resolved count in the harness's JSON report; that number, not the
sidecar, is the official score.

**Expectation to state out loud:** Brain's bound capabilities fail closed on
goals they do not represent. With unmodified routing the adapter may well emit
500 empty patches and score 0%. That is a real measurement, not a harness bug;
do not edit predictions or scores to improve it. A local one-instance probe on
2026-11-24 emitted an empty patch because routing selected
`python.swe.transform_and_synthesize.v1`, which refused with
`CAPABILITY_INPUTS_MISSING:operation,symbol,target_path,test_target`. The
adapter does not invent those values from an issue statement.

## 3. Terminal-Bench via Harbor

Harbor runs custom agents as importable Python modules in the Harbor process:

```bash
uv tool install 'harbor[modal]'

# Environment sanity check (oracle, not Brain)
harbor run -d terminal-bench/terminal-bench@4.0.0 --agent oracle -e docker -n 4

# Brain's engine as a custom external agent
PYTHONPATH=/path/to/brain harbor run -d terminal-bench/terminal-bench@4.0.0 \
  -e docker \
  -a canonical.runtime.harbor_epistemic_agent_v1:EpistemicBrainAgent \
  -n 4
```

For the zero-GPU suite, use the dataset ref from the handed-over plan:

```bash
harbor run -d terminal-bench-science/terminal-bench-science@v0.1 \
  -e docker \
  -a canonical.runtime.harbor_epistemic_agent_v1:EpistemicBrainAgent
harbor view jobs
```

`EpistemicBrainAgent` is an *external* agent: the solve loop and `open_model()`
stay in the Harbor process; only proposed commands run inside the task container
through `HarborEnvironmentTransport`. Each command goes through
`validate_environment_command` (no curl/wget, package installs, ssh or git
fetch/clone/pull). If the engine returns `pass: false` or no explicit action,
the agent performs zero commands and writes `BLOCKED_NO_MODEL_PROPOSAL`. A
finish action is recorded as a proposal; the agent never claims task completion
and never writes a reward. The Harbor verifier owns the score. The trace is
written to `<agent logs>/brain_epistemic_trace.json`.

## 4. Pre-VM gate checks, 2026-11-24 (measured, all local)

A five-instance synthetic dry-run (one small Python repo per instance, a public
`tests/test_*.py` in each worktree, test paths and test argv supplied to
`solve()`) produced:

| Mode | Patches | Status returned by the engine |
|---|---|---|
| `EPISTEMIC` (default) | 0 / 5 | `FAIL_CLOSED` — `CAPABILITY_INPUTS_MISSING:operation,symbol,target_path,test_target` |
| `SOLVE_OR_LEARN` | 0 / 5 | `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` |

Conclusions from those runs:

1. **Do not flip the default to `SOLVE_OR_LEARN`.** `solve()` forwards to
   `act_or_learn`, which escalates into `solve_or_learn`; on repository-shaped
   goals that route is refused by the computer-execution boundary. This is a
   refusal by design, not a missing test trigger. The `SOLVE_OR_LEARN` probe
   also incremented tracked associative-memory access counters; those
   incidental edits were reverted, so the working tree contains only the
   intended new files listed in section 1 plus this design note.
2. **Test discovery does not open the gate.** Supplying `test_paths`,
   `test_argv`, `target_path` and `source_root` changed the missing-input list
   under ordinary routing but did not produce a patch; under `SOLVE_OR_LEARN`
   the same inputs still hit the confinement refusal. The hidden
   `FAIL_TO_PASS` test names are not available to the solver anyway, and this
   adapter does not read them.
3. **No caller flag may grant execution authority.**
   `canonical/runtime/computer_execution_boundary_v1.py` says explicitly that
   no request flag, environment variable or caller can grant it. Setting
   `confinement_admitted=True` from this adapter would be self-authorization,
   so the adapter does not set it; a test pins that fact.
   **Correction (2026-11-24, see
   `CONFINEMENT_FRONT_DOOR_WIRING_DESIGN_20261124_V1.md`):** the substrate
   `confinement_v1.py` *is* wired into `live_brain_route_admission_v1`'s
   `run_adapter_locally` since 2026-11-12, and the repair capability has had a
   declaration row since 2026-11-13. My earlier "not yet wired" phrasing was
   imprecise. What is missing is the route from `open_model().solve()` (which
   uses `verified_bound_capability_execution_adapter_v1.execute()`) to that
   existing seam, plus the tier-2 controller carrier. The next real step is
   that reviewed wiring, not a mode string change.
4. The "179 OSS commits" figure in the review that prompted these checks does
   not appear in this repository's records. The measured local repair study
   here is 30 real commits with 1 verified repair
   (`A_SITE_IS_NOT_A_PRODUCTION_20261124_V1.md`); it used a restricted
   AST instrument, not a full SWE-bench repair pipeline.

**Recommendation: do not pay for or spin up the 500-task VM yet.** A run today
would score 0% for the two refusal reasons above, not for lack of a harness.

## 5. What would make a score meaningful

1. Run the oracle check on the external machine first; if the harness cannot
   pass its own oracle task, no Brain score means anything.
2. Keep the smoke test and full run IDs distinct; archive predictions, sidecar
   and the harness report together.
3. Report the resolved count together with the number of non-empty patches. An
   empty-patch run is not "0% intelligence", it is 0% of tasks resolved with
   the submitted patches.
4. Any claim of independent verification needs a verifier different from the
   producer and a run reference, per `AGENTS.md`. These wrappers produce
   neither.
