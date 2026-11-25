"""Offline tests for the SWE-bench Pro V2 Harbor harness (no docker, no network).

These cover the ADAPTER logic only: what the agent is allowed to see, how edits are
detected and uploaded, and how results are aggregated. They never assert a benchmark
score -- scores exist only in a committed run report from CI.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import tempfile

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

        md = "\n".join(
            CI.to_markdown({"causal": rep, "nop": {**rep, "resolved": 0, "n_expected": 3}, "oracle": {**rep, "resolved": 0, "n_expected": 3}}, benchmark="SWE-bench Pro V2 (HARD-51)", commit="deadbeef")
        )
        assert "`oracle_gate_pass`: **FAIL**" in md
        assert "`nop_gate_pass`: **PASS**" in md
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
    assert "| causal | 2 | 2 | 100.0 | 0 | 0.0 | 5.0 | 2.5 | 0 |" in md


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
