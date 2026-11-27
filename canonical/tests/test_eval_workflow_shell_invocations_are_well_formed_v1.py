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

import contextlib
import io
import pathlib
import re

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
ROOT = REPO
WORKFLOW = REPO / ".github" / "workflows" / "engine-docker-eval.yml"


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


def _help_options(subcommand: str) -> set[str]:
    """What the real CLI accepts, read from its own --help (no argparse internals touched)."""
    from canonical.eval.harbor import swe_pro_v2_ci as ci

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), pytest.raises(SystemExit):
        ci.build_parser().parse_args([subcommand, "--help"])
    return set(re.findall(r"--[a-z][a-z0-9-]*", buf.getvalue()))


def test_collect_cli_round_trip_records_conditions(tmp_path: pathlib.Path) -> None:
    """The workflow calls the CLI, so the CLI is the thing under test -- not the python function.

    A fixture manifest with one task id and an empty jobs dir: `collect` must accept the exact flag
    set the workflow passes and land those notes in `conditions`, with ints kept ints.
    """
    import json
    import subprocess
    import sys

    from canonical.eval.harbor import swe_pro_v2_ci as ci

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"tasks": ["instance_qutebrowser__abc"]}), encoding="utf-8")
    out = tmp_path / "causal-s0.json"
    rc = subprocess.run(
        [sys.executable, "-m", "canonical.eval.harbor.swe_pro_v2_ci", "collect",
         "--jobs-dir", str(tmp_path / "jobs"), "--manifest", str(manifest), "--arm", "causal",
         "--note", "engine_timeout_s=240", "--note", "n_shards=6", "--note", "eval_commit=dda506c1",
         "--out", str(out)],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 0, rc.stdout + rc.stderr
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["conditions"] == {"engine_timeout_s": 240, "n_shards": 6, "eval_commit": "dda506c1"}, rep["conditions"]
    assert rep["n_expected"] == 1 and rep["resolved"] == 0
    # and the number this shard report would contribute is *no number at all*: no real trial row.
    assert sum(1 for v in rep["tasks"].values() if ci.row_is_real(v)) == 0, rep["tasks"]


def test_collect_invocation_is_one_complete_command_per_arm() -> None:
    body = _steps("swe-eval")["Collect shard results"]
    (collect,) = [ln for ln in _joined(body) if "swe_pro_v2_ci collect" in ln]
    for flag in ("--jobs-dir", "--manifest", "--arm", "--out"):
        assert flag in collect, f"collect invocation lost {flag}: {collect}"
    notes = dict(re.findall(r'--note\s+(\w+)=("?\$\{?\w*\}?"?)', collect))
    assert set(notes) == {"engine_timeout_s", "n_shards", "eval_commit"}, notes
    assert '"$AGENT_TIMEOUT_S"' in collect and '"$N_SHARDS"' in collect and '"$GITHUB_SHA"' in collect


def test_every_flag_the_ci_passes_is_accepted_by_the_ci_parser() -> None:
    """The bug this catches is real and cost a whole run: `collect --note` was passed by the workflow
    while `--note` had never been declared on the collect *subparser* (it was declared in the branch
    body, which is not the same thing). argparse exited 2 with 'unrecognized arguments', all 18 shards
    published COLLECT_FAILED, and every unit test stayed green because they called `collect(notes=...)`
    directly. So: ask the parser, through its own --help, what it accepts.
    """
    for step_name, subcommand, marker in (
        ("Materialize tasks and generate this shard's job config", "materialize", "swe_pro_v2_ci materialize"),
        ("Materialize tasks and generate this shard's job config", "job-config", "swe_pro_v2_ci job-config"),
        ("Collect shard results", "collect", "swe_pro_v2_ci collect"),
    ):
        flags = set()
        for line in _joined(_steps("swe-eval")[step_name]):
            if marker in line:
                flags.update(re.findall(r"--[a-z][a-z0-9-]*", line))
        assert flags, f"no {subcommand} invocation found in {step_name}"
        accepted = _help_options(subcommand)
        assert "--definitely-not-an-option" not in accepted and accepted, "the option probe must discriminate"
        missing = {f for f in flags if f not in accepted}
        assert not missing, f"{subcommand} was passed {sorted(missing)}, which its parser rejects"


def test_the_collector_reports_its_own_failure_in_the_committed_evidence() -> None:
    """A COLLECT_FAILED row must say WHY. Run 45676020414 had 18 of them and no text to read."""
    body = _steps("swe-eval")["Collect shard results"]
    assert ".collect.log" in body, "the collector's stdout+stderr must be written to a published log"
    assert "collector_output_tail" in body, "the failure marker must carry the collector's own words"
    agg = _steps("swe-aggregate")["Aggregate"]
    assert "collector_last_line" in agg, "the aggregate must surface the reason, not just the shard name"
    assert "*.collect.log" in agg, "the log is committed under diagnostics/ with the rest"


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
