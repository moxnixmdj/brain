#!/usr/bin/env python3
"""The workflow's shell steps must be checked as shell, not as prose.

A missing backslash on one of three `--note` lines cost a whole measured run: the
`collect` invocation lost `--out`, exited 2, and because the runner executes every step
under `bash -e`, the step died before its fallback could write -- so a shard that harbor had
finished successfully published nothing, and the aggregate correctly reported "no shard
report". That is the same failure shape as the `harbor run` exit-code bug this file also
pins: **an instrument that deletes evidence when it breaks is worse than no instrument.**

These tests therefore parse the workflow, join line continuations the way bash would, and
assert (a) every multi-line CLI invocation carries its required flags, and (b) the steps
that must publish evidence before reporting failure have opted out of `-e`.
"""
from __future__ import annotations

import pathlib
import re

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "engine-docker-eval.yml"


def _steps(job: str) -> dict[str, str]:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return {s["name"]: s.get("run", "") for s in doc["jobs"][job]["steps"] if "run" in s}


def _joined(run: str) -> list[str]:
    """Collapse backslash-continuations, exactly as bash does, one logical line per entry."""
    lines, buf = [], []
    for raw in run.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith("\\"):
            buf.append(styled := stripped[:-1].strip())
            continue
        buf.append(stripped)
        lines.append(" ".join(x for x in buf if x))
        buf = []
    if buf:
        lines.append(" ".join(x for x in buf if x))
    return lines


def test_collect_invocation_is_one_complete_command_per_arm() -> None:
    body = _steps("swe-eval")["Collect shard results"]
    (collect,) = [ln for ln in _joined(body) if "swe_pro_v2_ci collect" in ln]
    for flag in ("--jobs-dir", "--manifest", "--arm", "--out"):
        assert flag in collect, f"collect invocation lost {flag}: {collect}"
    notes = dict(re.findall(r'--note\s+(\w+)=("?\$\{?\w*\}?"?)', collect))
    assert set(notes) == {"engine_timeout_s", "n_shards", "eval_commit"}, notes
    assert '"$AGENT_TIMEOUT_S"' in collect and '"$N_SHARDS"' in collect and '"$GITHUB_SHA"' in collect


def test_materialize_and_job_config_invocations_are_complete() -> None:
    body = _steps("swe-eval")["Materialize tasks and generate this shard's job config"]
    lines = _joined(body)
    (mat,) = [ln for ln in lines if "swe_pro_v2_ci materialize" in ln]
    (cfg,) = [ln for ln in lines if "swe_pro_v2_ci job-config" in ln]
    assert "--dest" in mat and "--out-manifest" in mat, mat
    for flag in ("--arm", "--manifest", "--jobs-dir", "--out-dir", "--n-shards", "--store-path", "--agent-timeout-s"):
        assert flag in cfg, f"job-config lost {flag}: {cfg}"


def test_evidence_publishing_steps_opt_out_of_bash_e_before_they_fail() -> None:
    """Any step that must publish an artifact even when a command inside it fails needs `set +e`."""
    steps = _steps("swe-eval")
    for name in ("Run Harbor eval", "Collect shard results"):
        first = [ln.strip() for ln in steps[name].splitlines() if ln.strip() and not ln.strip().startswith("#")]
        assert first[0] == "set +e", f"{name} can still be killed by the runner's bash -e: {first[:2]}"
    # ...and the collect step must still fail loudly, after publishing.
    tail = steps["Collect shard results"].splitlines()[-3:]
    assert any("COLLECT_FAILED" in ln and "exit 1" in ln for ln in tail), tail
    assert "cx=$?" in steps["Collect shard results"]


def test_void_run_records_its_own_failure_flag_in_the_committed_report() -> None:
    body = _steps("swe-aggregate")["Aggregate"]
    lines = _joined(body)
    (envline,) = [ln for ln in lines if 'echo "RUN_FAILED=true"' in ln]
    assert "export RUN_FAILED=true" in lines[lines.index(envline) + 1], "the flag must be readable in the same step"
