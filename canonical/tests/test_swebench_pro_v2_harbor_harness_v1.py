"""Offline tests for the SWE-bench Pro V2 Harbor harness (no docker, no network).

These cover the ADAPTER logic only: what the agent is allowed to see, how edits are
detected and uploaded, and how results are aggregated. They never assert a benchmark
score -- scores exist only in a committed run report from CI.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import socket
import tempfile
import urllib.request

import pytest

from canonical.eval.harbor import swebench_pro_v2_agent as AG
from canonical.eval.harbor import swe_pro_v2_ci as CI


class _Res:
    def __init__(self, stdout: str = "", return_code: int = 0) -> None:
        self.stdout = stdout
        self.return_code = return_code


class FakeEnvironment:
    """Duck-typed harbor BaseEnvironment over a local directory tree."""

    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        self.uploaded: list[str] = []
        self.download_excludes: list[str] | None = None

    async def exec(self, command: str, cwd=None, env=None, timeout_sec=None, user=None) -> _Res:
        if command.strip() == "pwd":
            return _Res(stdout=f"{self.root}\n")
        return _Res(stdout="", return_code=0)

    async def is_dir(self, path: str, user=None) -> bool:
        return (pathlib.Path(path) == self.root) or self.root.joinpath(*pathlib.Path(path).parts[1:]).is_dir()

    async def download_dir_with_exclusions(self, *, source_dir: str, target_dir: str, exclude: list[str]) -> None:
        self.download_excludes = list(exclude)
        dst = pathlib.Path(target_dir)
        dst.mkdir(parents=True, exist_ok=True)
        for p in sorted(self.root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(self.root)
            if any(part in exclude for part in rel.parts):
                continue
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(p.read_bytes())

    async def upload_file(self, *, source_path, target_path: str) -> None:
        self.uploaded.append(target_path)
        # mirror into the fake container so downstream verification is realistic
        rel = pathlib.PurePosixPath(target_path).relative_to(pathlib.PurePosixPath(self.root.as_posix()))
        out = self.root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pathlib.Path(source_path).read_bytes())


def _seed_repo(root: pathlib.Path) -> None:
    (root / "pkg").mkdir(parents=True, exist_ok=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "core.py").write_text(
        "def label(row):\n"
        "    if row.name is None:\n"
        "        return None\n"
        "    name = row.name\n"
        "    return name.upper()\n",
        encoding="utf-8",
    )
    (root / "node_modules").mkdir(parents=True, exist_ok=True)
    (root / "node_modules" / "junk.js").write_text("x" * 100, encoding="utf-8")
    (root / "package-lock.json").write_text('{"lockfileVersion": 3}', encoding="utf-8")
    (root / "blob.bin").write_bytes(b"\x00\x01\x02\x03")


def test_snapshot_skips_excluded_dirs_lockfiles_and_binaries() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "repo"
        _seed_repo(root)
        snap = AG.snapshot_tree(root)
        rels = set(snap)
        assert "blob.bin" not in rels  # (binary guard, re-checked below)
        assert "pkg/core.py" in rels
        assert "node_modules/junk.js" not in rels
        assert "package-lock.json" not in rels
        assert "blob.bin" not in rels


def test_diff_trees_classifies_modifications_and_removals() -> None:
    before = {"a.py": (10, "h1"), "b.py": (20, "h2")}
    after = {"a.py": (11, "h1b"), "c.py": (5, "h3")}
    diff = AG.diff_trees(before, after)
    assert diff == {"modified": ["a.py"], "added": ["c.py"], "removed": ["b.py"]}


def test_extract_engine_edits_finds_nested_patched_files() -> None:
    res = {"status": "PASS", "epistemic_result": {"patched_files": {"pkg/core.py": "x = 1\n"}}}
    assert AG.extract_engine_edits(res) == {"pkg/core.py": "x = 1\n"}
    assert AG.extract_engine_edits({"status": "FAIL_CLOSED"}) == {}


def test_apply_edits_refuses_traversal_and_non_source_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tree = pathlib.Path(tmp)
        written = AG.apply_edits(
            tree,
            {"../escape.py": "bad\n", "pkg/ok.py": "good\n", "img.png": "not source\n"},
            before={},
        )
        assert written == ["pkg/ok.py"]
        assert (tree / "pkg" / "ok.py").read_text(encoding="utf-8") == "good\n"
        assert not (tree.parent / "escape.py").exists()


def test_agent_run_uploads_engine_edits_and_reports_zero_cost() -> None:
    def solver(*, instruction: str, tree: pathlib.Path, inputs: dict) -> dict:
        assert inputs["allow_web"] is False
        assert "hidden" not in instruction.lower()
        (tree / "pkg" / "core.py").write_text(
            "def label(row):\n    name = row.name\n    return name.upper() if name else ''\n",
            encoding="utf-8",
        )
        return {"status": "PASS", "pass": True}

    original = AG.run_engine_on_tree

    def patched(tree, instruction, **kwargs):
        kwargs["solver"] = solver
        return original(tree, instruction, **kwargs)

    AG.run_engine_on_tree = patched  # type: ignore[assignment]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            container = pathlib.Path(tmp) / "container"
            container.mkdir()
            _seed_repo(container)
            env = FakeEnvironment(container)
            logs = pathlib.Path(tmp) / "logs"
            logs.mkdir()
            agent = AG.CausalEngineAgent(logs_dir=logs, model_name=None, store_path=str(pathlib.Path(tmp) / "store.json"))

            class _Ctx:
                cost_usd = None
                n_input_tokens = None
                n_output_tokens = None
                n_cache_tokens = None
                metadata = None

            ctx = _Ctx()
            asyncio.run(agent.run("Make label tolerate a missing name by falling back to ''.", env, ctx))

            report = json.loads((logs / "causal_engine_report.json").read_text(encoding="utf-8"))
            assert report["status"] == "EDITS_UPLOADED"
            assert report["model_calls"] == 0
            assert report["cost_usd"] == 0.0
            assert report["changed"]["modified"] == ["pkg/core.py"]
            assert env.uploaded == [f"{container}/pkg/core.py"]
            assert ctx.cost_usd == 0.0
            assert ctx.metadata["causal_engine"]["status"] == "EDITS_UPLOADED"
            # the fix really landed in the "container"
            assert "if name else" in (container / "pkg" / "core.py").read_text(encoding="utf-8")
            # exclusions were honoured on the way down
            assert "node_modules" in env.download_excludes
    finally:
        AG.run_engine_on_tree = original  # type: ignore[assignment]


def test_agent_fails_closed_on_oversized_tree() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        container = pathlib.Path(tmp) / "c"
        container.mkdir()
        _seed_repo(container)
        env = FakeEnvironment(container)
        logs = pathlib.Path(tmp) / "logs"
        logs.mkdir()
        agent = AG.CausalEngineAgent(logs_dir=logs, model_name=None, max_tree_bytes=1)
        asyncio.run(agent.run("do the thing", env, None))
        report = json.loads((logs / "causal_engine_report.json").read_text(encoding="utf-8"))
        assert report["status"] == "TREE_TOO_BIG"
        assert env.uploaded == []


def test_job_config_arms_and_deterministic_sharding() -> None:
    ids = [f"instance_repo__name-{i:04d}" for i in range(11)]
    shards = CI.split_shards(ids, 3)
    assert sum(len(s) for s in shards) == 11
    assert sorted(t for s in shards for t in s) == sorted(ids)
    assert shards == CI.split_shards(ids, 3)  # deterministic

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "tasks").mkdir()
        cfg = CI.job_config(arm="causal", tasks=[root / "tasks" / "t0"], jobs_dir=root / "jobs", store_path=root / "s.json")
        assert cfg["agents"][0]["import_path"] == CI.AGENT_IMPORT_PATH
        assert cfg["agents"][0]["kwargs"]["store_path"] == str(root / "s.json")
        assert cfg["n_attempts"] == 1
        assert cfg["environment"] == {"type": "docker", "delete": True}
        assert "patched_files" not in json.dumps(cfg)
        written = CI.write_job_configs(cfg, root / "cfgs", CI.split_shards(ids, 3), root / "tasks")
        assert len(written) == 3
        body = written[0].read_text(encoding="utf-8")
        assert "swe-pro-v2-causal-s0" in body

        nop = CI.job_config(arm="nop", tasks=[root / "tasks" / "t0"], jobs_dir=root / "jobs")
        assert nop["agents"] == [{"name": "nop"}]
        orc = CI.job_config(arm="oracle", tasks=[root / "tasks" / "t0"], jobs_dir=root / "jobs")
        assert orc["agents"] == [{"name": "oracle"}]


def test_materialize_refuses_incomplete_tasks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        up = root / "up"
        tid = "instance_x__y-abc"
        (up / "v2" / "tasks" / tid / "tests").mkdir(parents=True)
        (up / "v2" / "tasks" / tid / "instruction.md").write_text("do it", encoding="utf-8")
        (up / "v2" / "tasks" / tid / "task.toml").write_text("x = 1", encoding="utf-8")
        # no solution/ dir yet -> must refuse
        try:
            CI.materialize(up, [tid], root / "out")
        except SystemExit as exc:
            assert "TASK_INCOMPLETE" in str(exc) and "solution" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("materialize accepted an incomplete task")
        (up / "v2" / "tasks" / tid / "solution").mkdir()
        rep = CI.materialize(up, [tid], root / "out")
        assert rep["n_tasks"] == 1
        assert (root / "out" / tid / "tests").is_dir()


def test_collect_and_aggregate_read_only_real_harbor_artifacts() -> None:
    ids = ["t0", "t1", "t2"]
    with tempfile.TemporaryDirectory() as tmp:
        jobs = pathlib.Path(tmp) / "jobs"
        for tid, reward, status in (("t0", "1.0", "EDITS_UPLOADED"), ("t1", "0.0", "NO_EDITS")):
            td = jobs / "job" / f"{tid}__abc"
            (td / "verifier").mkdir(parents=True)
            (td / "verifier" / "reward.txt").write_text(reward + "\n", encoding="utf-8")
            (td / "agent").mkdir(parents=True)
            (td / "agent" / "causal_engine_report.json").write_text(
                json.dumps({"status": status, "model_calls": 0, "cost_usd": 0.0, "wall_seconds": 3.5, "changed": {"modified": ["a.py"] if reward == "1.0" else [], "added": [], "removed": []}}),
                encoding="utf-8",
            )
            (td / "result.json").write_text(json.dumps({"task_name": tid, "verifier_result": {"rewards": {"reward": float(reward)}}}), encoding="utf-8")
        rep = CI.collect([jobs], arm="causal", expected_ids=ids)
        assert rep["n_expected"] == 3
        assert rep["resolved"] == 1
        assert rep["n_missing_trial"] == 1
        assert rep["missing_trials"] == ["t2"]
        assert rep["model_calls_total"] == 0
        assert rep["cost_usd_total"] == 0.0
        assert rep["wall_seconds_total"] == 7.0
        assert rep["tasks"]["t0"]["resolved"] is True
        assert rep["tasks"]["t2"]["agent_status"] == "NOT_RUN"

        def arm_rows(**kw):
            return {tid: {"reward": kw["reward"], "resolved": kw["reward"] == 1.0,
                          "agent_status": kw["status"], "n_files_changed": 0,
                          "trial_dir": f"{tid}__x"} for tid in ids}

        # Gates are recomputed from complete per-task truth: an arm with a missing
        # trial cannot pass, because silence is not evidence that nop did nothing.
        md = "\n".join(CI.to_markdown(
            {
                "causal": rep,
                "nop": {**rep, "arm": "nop", "resolved": 0, "tasks": arm_rows(reward=0.0, status="NO_EDITS")},
                "oracle": {**rep, "arm": "oracle", "resolved": 3, "tasks": arm_rows(reward=1.0, status="oracle")},
            },
            benchmark="SWE-bench Pro V2 (HARD-51)", commit="deadbeef",
        ))
        assert "`oracle_gate_pass`: **PASS**" in md
        assert "`nop_gate_pass`: **PASS**" in md

        md_broken = "\n".join(CI.to_markdown(
            {
                "causal": rep,
                "nop": {**rep, "arm": "nop", "tasks": arm_rows(reward=1.0, status="oracle")},
                "oracle": {**rep, "arm": "oracle", "resolved": 1, "tasks": arm_rows(reward=1.0, status="oracle"), "n_expected": 3},
            },
            benchmark="B", commit="c",
        ))
        assert "`nop_gate_pass`: **FAIL**" in md_broken  # nop resolved a task => tests are not the constraint
    assert "NO TRIAL DATA" not in md  # there IS trial data here

    # A run where no shard produced a result.json must shout, not print 0/N quietly.
    empty = CI.merge_arm_reports([])
    md2 = "\n".join(CI.to_markdown({"causal": empty}, benchmark="B", commit="x"))
    assert "NO TRIAL DATA — THIS RUN PRODUCED NO BENCHMARK NUMBER" in md2
def test_aggregate_merges_shard_reports_by_task_union() -> None:
    shard0 = {
        "arm": "causal",
        "n_expected": 2,
        "n_reported": 1,
        "n_missing_trial": 1,
        "missing_trials": ["t1"],
        "resolved": 1,
        "resolve_rate_pct": 50.0,
        "model_calls_total": 0,
        "cost_usd_total": 0.0,
        "wall_seconds_total": 4.0,
        "wall_seconds_mean": 4.0,
        "tasks": {
            "t0": {"reward": 1.0, "resolved": True, "agent_status": "EDITS_UPLOADED", "model_calls": 0, "cost_usd": 0.0, "seconds": 4.0, "n_files_changed": 2},
            "t1": {"reward": None, "resolved": False, "agent_status": "NOT_RUN", "n_files_changed": 0},
        },
    }
    shard1 = {
        "arm": "causal",
        "n_expected": 2,
        "n_reported": 1,
        "n_missing_trial": 1,
        "missing_trials": ["t0"],
        "resolved": 0,
        "resolve_rate_pct": 0.0,
        "model_calls_total": 0,
        "cost_usd_total": 0.0,
        "wall_seconds_total": 1.0,
        "wall_seconds_mean": 1.0,
        "tasks": {
            "t0": {"reward": None, "resolved": False, "agent_status": "NOT_RUN", "n_files_changed": 0},
            "t1": {"reward": 1.0, "resolved": True, "agent_status": "EDITS_UPLOADED", "model_calls": 0, "cost_usd": 0.0, "seconds": 1.0, "n_files_changed": 1},
        },
    }
    merged = CI.merge_arm_reports([shard0, shard1])
    assert merged["n_expected"] == 2
    assert merged["n_reported"] == 2
    assert merged["n_missing_trial"] == 0, "a task resolved in one shard must not stay NOT_RUN from another"
    assert merged["resolved"] == 2
    assert merged["resolve_rate_pct"] == 100.0
    assert merged["wall_seconds_total"] == 5.0
    assert merged["model_calls_total"] == 0
    assert merged["cost_usd_total"] == 0.0
    assert merged["tasks"]["t0"]["agent_status"] == "EDITS_UPLOADED"

    md = "\n".join(
        CI.to_markdown(
            {
                "causal": merged,
                "nop": {**merged, "arm": "nop", "resolved": 2, "resolve_rate_pct": 100.0},
                "oracle": {**merged, "arm": "oracle"},
            },
            benchmark="SWE-bench Pro V2 (HARD-51)",
            commit="abc123",
        )
    )
    # A nop arm that resolves anything means the grader is broken: the gate says so.
    assert "`oracle_gate_pass`: **PASS**" in md
    assert "`nop_gate_pass`: **FAIL**" in md
    # 5.0 is harbor's trial wall; the engine-seconds column stays None here because the
    # fixture wrote no agent report — the two quantities must never be conflated.
    assert "| causal | 2 | 2 | 100.0 | 0 | 0.0 | 5.0 | None | 0 |" in md


def test_network_guard_names_a_transport_refusal_without_hijacking_the_stdlib() -> None:
    """`allow_web: False` must be *visible* in the report, and the harness must not own the process.

    The first version enforced the flag by reassigning `socket.socket.connect` and
    `socket.create_connection` for the duration of the trial. That made every other caller in the
    interpreter answer to the harness, and the repo's integrity guard rejects stdlib rebinding for
    exactly that reason. What the guard still owes a reader is the distinction this file exists to
    keep: an engine that scored 0 because the network refused it is a different fact from an engine
    that scored 0 because it found nothing.
    """
    import socket
    import urllib.error

    real_connect = socket.socket.connect
    real_create = socket.create_connection
    real_open = urllib.request.urlopen

    # the standard library is untouched while the guard is "active" -- this is the pin that
    # keeps the old mechanism from creeping back in behind a green test suite
    guard0, attempts0 = AG.network_guard(True)
    with guard0:
        assert socket.socket.connect is real_connect
        assert socket.create_connection is real_create
        assert urllib.request.urlopen is real_open
    assert attempts0 == []
    # a guard is one region, not a global state: each use is its own context
    guard1, attempts1 = AG.network_guard(True)
    with pytest.raises(AG.NetworkRefusedByHarness):
        with guard1:
            raise urllib.error.URLError(ConnectionRefusedError("[Errno 111] Connection refused"))
    assert len(attempts1) == 1, attempts1
    assert "transport-refusal" in attempts1[0] and "ConnectionRefusedError" in attempts1[0], attempts1
    # a failure that already has a name is passed through unconverted
    guard2, attempts2 = AG.network_guard(True)
    with pytest.raises(ValueError):
        with guard2:
            raise ValueError("engine bug, not the network")
    # a disabled guard neither wraps nor counts anything
    guard_off, attempts_off = AG.network_guard(False)
    with guard_off:
        reached = True
    assert attempts_off == [] and reached


def test_egress_is_observed_rather_than_asserted() -> None:
    """`observe_egress` answers a question about the sandbox; it must not decide one about the run.

    Which of the three answers this machine gives depends on the container, so the test pins the
    shape and the honesty of the reporting, not the environment's state. What matters is that the
    report can say `REFUSED` only when a connect was actually tried and refused.
    """
    obs = AG.observe_egress(timeout_s=1.0)
    assert obs["observed"] in {"REFUSED", "AVAILABLE", "ERROR"}, obs
    assert isinstance(obs["detail"], str) and obs["detail"], obs
    # the classifier agrees with the probe about what counts as the environment talking
    if obs["observed"] == "REFUSED":
        assert AG._looks_like_egress_refusal(ConnectionRefusedError(obs["detail"].split(": ", 1)[-1]))


def test_the_guard_leaves_the_environment_alone() -> None:
    """`allow_web` = no external knowledge. Loopback is the environment, not the web."""

    assert AG._is_local_endpoint("127.0.0.1") and AG._is_local_endpoint(("localhost", 8000))
    assert AG._is_local_endpoint(("::1", 80)) and AG._is_local_endpoint("/run/x.sock")
    assert not AG._is_local_endpoint(("pypi.org", 443)) and not AG._is_local_endpoint("8.8.8.8")
    # a live local service stays reachable with the guard on, because nothing intercepts it now
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(2)
    guard, attempts = AG.network_guard(True)
    try:
        with guard:
            socket.create_connection(srv.getsockname(), timeout=2).close()
    finally:
        srv.close()
    assert attempts == [], "the environment is not a violation, and is not counted as one"


def test_run_engine_reports_the_guard_and_the_solver_sees_the_same_flag(tmp_path) -> None:
    tree = tmp_path / "repo"
    (tree / "pkg").mkdir(parents=True)
    (tree / "pkg" / "m.py").write_text("X = 1\n", encoding="utf-8")

    seen: dict = {}

    def solver(*, instruction, tree, inputs):  # noqa: ANN001 - test stand-in
        seen.update(inputs)
        import urllib.error

        # synthetic, not a real lookup: what the environment says when egress is closed is its
        # business; what the harness must do with it is ours
        raise urllib.error.URLError(ConnectionRefusedError("[Errno 111] Connection refused"))

    rep = AG.run_engine_on_tree(
        instruction="fix it", tree=tree, store_path=None, solver=solver, timeout_s=5.0
    )
    assert seen["allow_web"] is False, "the engine is told exactly what the harness reports on"
    assert rep["network_guard"] == "container-enforced__harness-classifies"
    assert rep["engine_result_status"] == "NETWORK_REFUSED__NOT_A_CAPABILITY_RESULT", rep
    assert rep["network_attempts"] == 1 and "transport-refusal" in rep["network_attempt_samples"][0]
    assert rep["egress_probe"]["observed"] in {"REFUSED", "AVAILABLE", "ERROR"}
    # isolated is a claim about the sandbox: it is True only under a REFUSED probe
    assert rep["external_knowledge_isolated"] is (rep["egress_probe"]["observed"] == "REFUSED")
    # the sample names what happened and where it came from, which is the point of the guard
    assert "Connection refused" in rep["network_attempt_samples"][0]
    # and an open-web run records that it was open instead of pretending otherwise
    rep2 = AG.run_engine_on_tree(
        instruction="fix it", tree=tree, store_path=None, solver=lambda **kw: {"status": "X"},
        timeout_s=5.0, inputs_allow_web=True,
    )
    assert rep2["network_guard"] == "open" and rep2["network_attempts"] == 0


def test_upload_falls_back_to_root_exec_and_reports_it() -> None:
    """A permission-walled repo must not silently drop the engine's edits."""

    class HostileEnv(FakeEnvironment):
        async def upload_file(self, *, source_path, target_path: str) -> None:
            raise PermissionError("owned by root")

    def solver(*, instruction: str, tree: pathlib.Path, inputs: dict) -> dict:
        (tree / "pkg" / "core.py").write_text("fixed = True\n", encoding="utf-8")
        return {"status": "PASS", "pass": True}

    original = AG.run_engine_on_tree

    def patched(tree, instruction, **kwargs):
        kwargs["solver"] = solver
        return original(tree, instruction, **kwargs)

    AG.run_engine_on_tree = patched  # type: ignore[assignment]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            container = pathlib.Path(tmp) / "c"
            container.mkdir()
            _seed_repo(container)
            env = HostileEnv(container)
            logs = pathlib.Path(tmp) / "logs"
            logs.mkdir()
            agent = AG.CausalEngineAgent(logs_dir=logs, model_name=None)
            asyncio.run(agent.run("fix it", env, None))
            report = json.loads((logs / "causal_engine_report.json").read_text(encoding="utf-8"))
            assert report["status"] == "EDITS_UPLOADED"
            assert report["upload_fallback_root_exec"] == 1
            assert report["upload_failures"] == []
            # The fake env's exec is a no-op, so nothing actually landed in the
            # container -- which is exactly why the report says fallback was used.
            assert "if name else" not in (container / "pkg" / "core.py").read_text(encoding="utf-8")
    finally:
        AG.run_engine_on_tree = original  # type: ignore[assignment]


def test_collect_surfaces_the_agents_own_report_without_treating_it_as_evidence() -> None:
    """A 0/N table must be distinguishable from 'the agent never acted'."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        trial = root / "jobs" / "j" / "t0__a"
        (trial / "agent").mkdir(parents=True)
        (trial / "result.json").write_text(
            json.dumps({"task_name": "t0", "verifier_result": {"rewards": {"reward": 0.0}}}),
            encoding="utf-8",
        )
        (trial / "agent" / "causal_engine_report.json").write_text(
            json.dumps(
                {
                    "status": "EDITS_UPLOADED",
                    "engine_result_status": "NO_DEFECT_EVIDENCE",
                    "edits_applied_by": "tree-mutation",
                    "tree_changed": True,
                    "store_saved": True,
                    "notes": ["no patch produced"],
                    "model_calls": 0,
                    "cost_usd": 0.0,
                    "wall_seconds": 3.5,
                    "changed": {"modified": ["a.py"], "added": [], "removed": []},
                }
            ),
            encoding="utf-8",
        )
        rep = CI.collect([root / "jobs"], arm="causal", expected_ids=["t0"])
        row = rep["tasks"]["t0"]
        assert row["agent_status"] == "EDITS_UPLOADED"
        assert row["engine_status"] == "NO_DEFECT_EVIDENCE"
        assert row["edits_applied_by"] == "tree-mutation"
        assert row["n_files_changed"] == 1
        assert row["resolved"] is False  # the agent's own report never counts as a fix
        assert rep["engine_statuses"] == {"EDITS_UPLOADED": 1}
        merged = CI.merge_arm_reports([rep])
        assert merged["engine_statuses"] == {"EDITS_UPLOADED": 1}
        md = "\n".join(CI.to_markdown({"causal": merged}, benchmark="B", commit="c"))
        assert "`EDITS_UPLOADED`×1" in md

        # no agent report at all must be visible as such, not blank
        (trial / "agent" / "causal_engine_report.json").unlink()
        rep2 = CI.collect([root / "jobs"], arm="nop", expected_ids=["t0"])
        assert rep2["tasks"]["t0"]["agent_status"] == "NO_AGENT_REPORT"



def test_collect_finds_trials_regardless_of_nesting_depth() -> None:
    """A harness that ran trials must not be reported as 'no data' because of a path guess."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        nested = root / "jobs" / "job-a" / "trials" / "t0__xyz"
        nested.mkdir(parents=True)
        (nested / "result.json").write_text(
            json.dumps({"task_name": "t0", "trial_name": "t0__xyz", "verifier_result": {"rewards": {"reward": 1.0}}}),
            encoding="utf-8",
        )
        # job-level result.json (different schema) must be ignored
        (root / "jobs" / "job-a" / "result.json").write_text(
            json.dumps({"job_name": "job-a", "n_total_trials": 1}), encoding="utf-8"
        )
        rep = CI.collect([root / "jobs"], arm="causal", expected_ids=["t0", "t1"])
        assert rep["n_reported"] == 1, rep
        assert rep["resolved"] == 1
        assert rep["missing_trials"] == ["t1"]
        # and a jobs dir that does not exist at all is 'no data', not a crash
        rep2 = CI.collect([root / "nope"], arm="causal", expected_ids=["t0"])
        assert rep2["n_reported"] == 0 and rep2["resolved"] == 0


def test_collect_reads_job_level_trial_results_when_no_per_trial_file_exists() -> None:
    """Harbor's own summary pointed at <jobs>/<job>/result.json; that file is enough."""
    with tempfile.TemporaryDirectory() as tmp:
        job = pathlib.Path(tmp) / "jobs" / "causal-s0"
        job.mkdir(parents=True)
        (job / "result.json").write_text(
            json.dumps(
                {
                    "job_name": "causal-s0",
                    "n_total_trials": 2,
                    "stats": {"mean": 0.5},
                    "trial_results": [
                        {
                            "task_name": "t0",
                            "trial_name": "t0__aaa",
                            "verifier_result": {"rewards": {"reward": 1.0}},
                            "agent_result": {"model_calls": 0, "cost_usd": 0.0},
                        },
                        {
                            "task_name": "t1",
                            "trial_name": "t1__bbb",
                            "verifier_result": {"rewards": {"reward": 0.0}},
                            "exception_info": None,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        rep = CI.collect([pathlib.Path(tmp) / "jobs"], arm="causal", expected_ids=["t0", "t1", "t2"])
        assert rep["n_reported"] == 2, rep
        assert rep["resolved"] == 1
        assert rep["missing_trials"] == ["t2"]
        assert rep["tasks"]["t0"]["resolved"] is True
        assert rep["tasks"]["t0"]["trial_dir"] == "t0__aaa"


def test_truncated_harbor_trial_names_still_map_to_the_manifest_id() -> None:
    """Harbor cuts trial directory names at 32 chars; the task is not thereby unknown.

    This is the bug that made three real, scored trials read as 'no data': the collector
    keyed trials by the name in result.json and compared it to the manifest id, which
    differ exactly by that truncation.
    """
    long_id = "instance_qutebrowser__qutebrowser-3e21c8214a998cb1058def"
    truncated = long_id[:32]  # instance_qutebrowser__qutebrowse
    with tempfile.TemporaryDirectory() as tmp:
        td = pathlib.Path(tmp) / "jobs" / "job" / f"{truncated}__42E7bj6"
        td.mkdir(parents=True)
        (td / "verifier").mkdir()
        (td / "verifier" / "reward.txt").write_text("1.0\n", encoding="utf-8")
        (td / "result.json").write_text(
            json.dumps({"task_name": truncated, "trial_name": f"{truncated}__42E7bj6"}), encoding="utf-8"
        )
        assert CI.resolve_task_id(CI.trial_keys(td, {"task_name": truncated}), [long_id]) == long_id
        rep = CI.collect([pathlib.Path(tmp) / "jobs"], arm="causal", expected_ids=[long_id])
        assert rep["n_reported"] == 1, rep
        assert rep["resolved"] == 1
        assert rep["missing_trials"] == []
        assert rep["tasks"][long_id]["trial_dir"] == f"{truncated}__42E7bj6"
        # two ids sharing a 32-char prefix stay ambiguous rather than guessing one:
        # the trial keeps its own key, so it shows up as an extra row instead of a wrong one.
        other = truncated + "-ffffffffffffffffffffffffffff"
        got = CI.resolve_task_id([truncated], [long_id, other])
        assert got == truncated


def test_a_trial_the_manifest_cannot_name_is_reported_instead_of_dropped() -> None:
    """Losing the row is what turned three scored trials into 'no data'."""
    with tempfile.TemporaryDirectory() as tmp:
        td = pathlib.Path(tmp) / "jobs" / "job" / "whatever__zzzzzzz"
        td.mkdir(parents=True)
        (td / "result.json").write_text(
            json.dumps({"task_name": "whatever", "trial_name": "whatever__zzzzzzz",
                        "verifier_result": {"rewards": {"reward": 1.0}}}),
            encoding="utf-8",
        )
        rep = CI.collect([pathlib.Path(tmp) / "jobs"], arm="causal", expected_ids=["a", "b"])
        assert rep["unmatched_trial_keys"] == ["whatever"]
        assert rep["missing_trials"] == ["a", "b"]
        assert rep["n_reported"] == 1, "the stray row counts as data that exists"
        assert rep["tasks"]["whatever"]["resolved"] is True
        assert rep["tasks"]["a"]["agent_status"] == "NOT_RUN"
        md = "\n".join(CI.to_markdown({"causal": rep}, benchmark="B", commit="c"))
        assert "Names the manifest did not recognise" in md
        merged = CI.merge_arm_reports([rep])
        assert merged["unmatched_trial_keys"] == ["whatever"]


def test_conditions_travel_with_the_shard_report_so_a_budget_is_never_implicit() -> None:
    """A resolve rate measured with a 240 s engine budget is not the same claim as 900 s."""
    ids = ["t0"]
    with tempfile.TemporaryDirectory() as tmp:
        jobs = pathlib.Path(tmp) / "jobs"
        td = jobs / "job" / "t0__x"
        td.mkdir(parents=True)
        (td / "result.json").write_text(
            json.dumps({"task_name": "t0", "verifier_result": {"rewards": {"reward": 0.0}}}), encoding="utf-8"
        )
        rep = CI.collect([jobs], arm="causal", expected_ids=ids, notes={"engine_timeout_s": 240, "n_shards": 6})
        assert rep["conditions"] == {"engine_timeout_s": 240, "n_shards": 6}
        merged = CI.merge_arm_reports([rep])
        assert merged["conditions"]["engine_timeout_s"] == 240
        md = "\n".join(CI.to_markdown({"causal": merged}, benchmark="B", commit="c"))
        assert "Measured under: `engine_timeout_s=240`, `n_shards=6`" in md


def test_the_guard_refusal_is_a_transport_failure_so_callers_already_handle_it() -> None:
    """Measured: as a plain RuntimeError the guard itself created 4 HARNESS_ERRORs.

    The 51-task run showed the two fixes failing to compose — the acquisition layer treats
    "no reply" as a fact about the environment, but only for `urllib.error.URLError`, so a
    refusal raised by the harness escaped as an error. It must be indistinguishable, to the
    caller, from a connection that was refused by the network.
    """
    import urllib.error

    assert issubclass(AG.NetworkRefusedByHarness, urllib.error.URLError)

    from canonical.runtime import epistemic_scan_acquire_compress_v1 as esac

    guard, attempts = AG.network_guard(True)
    with guard:
        code, body = esac._http_json_request("http://example.invalid:80/spec.json", timeout_s=2.0)
    assert code == 0 and body["error"] == "unreachable", body
    # narrower than before, and honestly so: a transport error the caller already turned into a
    # fact never escapes to the guard, so `attempts` counts escaped refusals, not all egress.
    # The isolation fact is carried by `egress_probe` / the container, which is where it belongs.
    assert attempts == []


def test_the_engine_s_own_account_of_a_refusal_reaches_the_committed_report() -> None:
    """`resolved` says nothing about why; the run must be plannable against, not just scored."""
    diag = AG.engine_diagnosis(
        {
            "status": "FAIL_CLOSED",
            "patch": {},
            "epistemic_result": {
                "modality": "swe_codebase",
                "status": "NO_DEFECT_EVIDENCE",
                "mode": "ALREADY_PASSING__NO_PATCH",
                "gaps_queried": [f"gap-{i}" for i in range(30)],
                "elapsed_ms": 1234.5,
                "explanation": "x" * 500,
            },
        }
    )
    assert diag["mode"] == "ALREADY_PASSING__NO_PATCH"
    assert diag["status"] == "NO_DEFECT_EVIDENCE"
    assert diag["n_gaps_queried"] == 30 and len(diag["gaps_queried"]) == 8, "bounded, not truncated silently"
    assert len(diag["explanation"]) <= 200
    assert diag["patch_files"] == 0
    # and a result that is not the kernel's shape still yields something, not a crash
    assert AG.engine_diagnosis({"status": "PASS", "patch": {"a.py": "x"}}) == {
        "status": "PASS",
        "patch_files": 1,
    }

    ids = ["t0"]
    with tempfile.TemporaryDirectory() as tmp:
        td = pathlib.Path(tmp) / "jobs" / "j" / "t0__x"
        (td / "agent").mkdir(parents=True)
        (td / "result.json").write_text(
            json.dumps({"task_name": "t0", "verifier_result": {"rewards": {"reward": 0.0}}}), encoding="utf-8"
        )
        (td / "agent" / "causal_engine_report.json").write_text(
            json.dumps({"status": "NO_EDITS", "engine_result_status": "FAIL_CLOSED", "engine_diagnosis": diag}),
            encoding="utf-8",
        )
        rep = CI.collect([pathlib.Path(tmp) / "jobs"], arm="causal", expected_ids=ids)
        assert rep["tasks"]["t0"]["diagnosis"]["mode"] == "ALREADY_PASSING__NO_PATCH"
        md = "\n".join(CI.to_markdown({"causal": rep}, benchmark="B", commit="c"))
        assert "Why the trials ended the way they did" in md
        assert "ALREADY_PASSING__NO_PATCH" in md and "gap-0" in md


def test_observe_egress_reports_a_state_it_measured_not_a_policy_it_hopes_for() -> None:
    """`observe_egress` must answer with an observed value; a bare "no network" claim was the bug."""
    saved = AG._EGRESS_PROBE_TARGET
    try:
        AG._EGRESS_PROBE_TARGET = ("127.0.0.1", 9)  # discard port: no agent is listening here
        got = AG.observe_egress(timeout_s=0.5)
    finally:
        AG._EGRESS_PROBE_TARGET = saved
    assert set(got) >= {"observed", "detail"}, got
    assert got["observed"] in {"REFUSED", "AVAILABLE", "ERROR"}, got
    assert isinstance(got["detail"], str) and got["detail"], got
    assert got["observed"] != "AVAILABLE", f"nothing listens on port 9: {got}"


def test_network_guard_classifies_only_escaped_transport_errors() -> None:
    """The guard names and counts transport refusals; it does not decide tasks and does not blind us."""
    guard, attempts = AG.network_guard(True)
    with pytest.raises(AG.NetworkRefusedByHarness):
        with guard:
            raise OSError(101, "Network is unreachable")
    assert attempts and attempts[0].startswith("transport-refusal:"), attempts

    # a fresh guard: a generator context manager is single-use, reusing it would silently no-op
    guard2, attempts2 = AG.network_guard(True)
    with pytest.raises(ValueError):
        with guard2:
            raise ValueError("bad literal")
    assert attempts2 == [], "an engine bug is not an egress refusal and must not be laundered into one"


def test_network_guard_disabled_is_a_passthrough_not_a_blinder() -> None:
    guard, attempts = AG.network_guard(False)
    with guard:
        pass
    assert attempts == []
    guard_open, attempts_open = AG.network_guard(False)
    with pytest.raises(OSError):
        with guard_open:
            raise OSError(101, "unreachable")
    assert attempts_open == [], "allow_web=True must not relabel real failures as refusals"


def test_escaped_refusal_becomes_a_named_row_not_a_bare_harness_error(tmp_path: pathlib.Path) -> None:
    def solver(*, instruction: str, tree: object, inputs: dict) -> dict:
        raise OSError(101, "Network is unreachable")

    out = AG.run_engine_on_tree(tmp_path, "fix it", ablate_store=True, solver=solver, inputs_allow_web=False)
    assert "NETWORK_REFUSED__NOT_A_CAPABILITY_RESULT" in json.dumps(out, default=str), out


def test_engine_bug_stays_an_engine_bug(tmp_path: pathlib.Path) -> None:
    """Symmetrically: a solver crash must not be granted the mercy of a `not a capability result` label."""
    def solver(*, instruction: str, tree: object, inputs: dict) -> dict:
        raise ZeroDivisionError("our arithmetic, not the sandbox's")

    try:
        out = AG.run_engine_on_tree(tmp_path, "fix it", ablate_store=True, solver=solver, inputs_allow_web=False)
    except ZeroDivisionError:
        return  # propagated untouched: also correct
    blob = json.dumps(out, default=str)
    assert "NETWORK_REFUSED" not in blob, f"an engine bug was relabeled as an environment failure: {blob[:200]}"
