"""Transport regressions, NOT benchmark scores or a fake container qualification.

The mocked BaseEnvironment is only an I/O seam. Real Git/child-process tests live
in test_harbor_container_solver_v1.py. No stdlib/Harbor module is monkeypatched.
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import shlex
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from canonical.runtime import harbor_epistemic_agent_v1 as agent

ROOT = Path(__file__).resolve().parents[2]
PATCH_BYTES = b"diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -1 +1 @@\n-before\n+after\n"


def small_source(tmp_path):
    source = tmp_path / "source"
    for name in (agent.WORKER, "canonical/runtime/brain_unified_model_v1.py",
                 "canonical/runtime/worker_syscall_allowlist_v1.py"):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# transport-only fixture: never imported or executed\n")
    path = source / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    return source


class MockEnvironment:
    """Returns declared transport fixtures; never pretends to be Docker."""
    def __init__(self, *, failure=None, damage=None):
        self.files = {}
        self.commands = []
        self.events = []
        self.failure = failure
        self.damage = damage

    async def upload_dir(self, *, source_dir, target_dir):
        self.events.append("upload_dir")
        for p in Path(source_dir).rglob("*"):
            if p.is_file():
                self.files[target_dir + "/" + str(p.relative_to(source_dir))] = p.read_bytes()

    async def upload_file(self, *, source_path, target_path):
        self.events.append("upload_file")
        if target_path.endswith("/request.json") and self.failure == "request_upload":
            raise OSError("request upload failed; not safe to retry the run")
        self.files[target_path] = Path(source_path).read_bytes()

    async def exec(self, *, command, **kwargs):
        self.commands.append((command, kwargs))
        self.events.append("exec")
        argv = shlex.split(command)
        if "-c" in argv:
            return SimpleNamespace(return_code=0, stdout=json.dumps({"uid": 1000, "gid": 1000, "cwd": "/app"}), stderr="")
        if "prepare" in argv and self.failure == "setup":
            return SimpleNamespace(return_code=17, stdout="", stderr="read-only setup failed")
        if "run" in argv:
            if self.failure == "timeout":
                raise TimeoutError("unknown transport outcome")
            if self.failure == "invalid_receipt":
                return SimpleNamespace(return_code=True, stdout="", stderr="")
            scratch = argv[argv.index("--scratch") + 1]
            req = json.loads(self.files[scratch + "/request.json"])
            report = {
                "schema": agent.SCHEMA, "run_id": req["run_id"],
                "instruction_sha256": hashlib.sha256(req["instruction"].encode()).hexdigest(),
                "source_manifest_sha256": req["source_manifest_sha256"],
                "execution_locus": "task_container", "verified_by_agent": False,
                "task_completion_claimed": False, "model_calls": 0, "parameters_stored": 0,
                "network_egress": "DENIED_BY_INHERITED_SECCOMP", "status": "SOLVER_RETURNED",
                "worker_uid": 1000, "solver_dispatches": 1, "solver_exit_code": 0,
                "filter_sha256": hashlib.sha256(b"transport-only fixture").hexdigest(),
                "solver_result": {"pass": False, "reason": "FIXTURE_NOT_A_BENCHMARK_RESULT"},
                "patch": {"sha256": hashlib.sha256(PATCH_BYTES).hexdigest(), "bytes": len(PATCH_BYTES)},
            }
            if self.damage == "host_locus":
                report["execution_locus"] = "host"
            if self.damage == "self_verification":
                report["verified_by_agent"] = True
            if self.damage == "model_call":
                report["model_calls"] = 1
            if self.damage == "stale_run":
                report["run_id"] = "other-trial"
            if self.damage == "nested_counter":
                report["solver_result"]["child"] = {"external_model_calls": 1}
            if self.damage == "root_worker":
                report["worker_uid"] = 0
            if self.damage == "unknown_status":
                report["status"] = "PASSED_ALL_TESTS"
            if self.damage == "inconsistent_status":
                report["solver_exit_code"] = 124
            if self.damage == "missing_filter":
                report.pop("filter_sha256")
            trajectory = {
                "schema_version": "ATIF-v1.6", "session_id": req["run_id"],
                "agent": {"name": "brain-epistemic", "version": "2.0.0"},
                "steps": [{"step_id": 1, "source": "user", "message": req["instruction"]},
                          {"step_id": 2, "source": "agent", "message": "Mock transport result, not a benchmark score"}],
                "extra": report,
            }
            output = {
                "model.patch": PATCH_BYTES + (b"corrupt" if self.damage == "patch" else b""),
                "brain_result.json": json.dumps(report).encode(),
                "trajectory.json": json.dumps(trajectory).encode(), "solver.log": b"fixture log\n",
            }
            for name, raw in output.items():
                self.files[scratch + "/artifacts/" + name] = raw
        return SimpleNamespace(return_code=0, stdout="", stderr="")

    async def download_file(self, *, source_path, target_path):
        self.events.append("download_file")
        if self.failure == "download":
            raise OSError("artifact transfer failed")
        Path(target_path).write_bytes(self.files[source_path])


def test_solver_dispatch_is_only_environment_exec_and_patch_is_unmodified(tmp_path):
    from canonical.runtime import brain_unified_model_v1 as model_module
    env = MockEnvironment()
    inst = agent.EpistemicBrainAgent(tmp_path / "logs", brain_source=small_source(tmp_path), solve_timeout_sec=7)
    context = SimpleNamespace(cost_usd=99.0, n_input_tokens=13)
    instruction = "a quoted task: '; touch /tmp/NEVER; $HOME\nprint('not shell')"
    with patch.object(model_module, "open_model", side_effect=AssertionError("HOST SOLVER FORBIDDEN")) as sentinel:
        asyncio.run(inst.setup(env))
        asyncio.run(inst.run(instruction, env, context))
        sentinel.assert_not_called()
    runs = [(cmd, opts) for cmd, opts in env.commands if "run" in shlex.split(cmd)]
    assert len(runs) == 1
    argv = shlex.split(runs[0][0])
    assert argv[:4] == ["python3", "-I", "-S", "-B"]
    assert argv[4].endswith("/" + agent.WORKER)
    assert runs[0][1] == {"timeout_sec": 247, "user": "root"}
    assert instruction not in runs[0][0]
    request = json.loads(env.files[inst._scratch + "/request.json"])
    assert request["instruction"] == instruction
    assert env.events.index("upload_dir") < env.events.index("download_file")
    assert (tmp_path / "logs/model.patch").read_bytes() == PATCH_BYTES
    report = json.loads((tmp_path / "logs/brain_result.json").read_bytes())
    assert report["model_calls"] == report["parameters_stored"] == 0
    assert report["verified_by_agent"] is False
    assert report["solver_result"]["pass"] is False
    assert (context.cost_usd, context.n_input_tokens) == (99.0, 13)


def test_no_host_call_site_or_solver_import_exists():
    tree = ast.parse(Path(agent.__file__).read_text())
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                and ((isinstance(node.func, ast.Name) and node.func.id == "open_model")
                     or (isinstance(node.func, ast.Attribute) and node.func.attr == "solve"))]
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                and "brain_unified_model" in (node.module or "")]
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Import)
                and any(alias.name in {"subprocess", "asyncio"} for alias in node.names)]
    worker = ast.parse((ROOT / agent.WORKER).read_text())
    calls = [node for node in ast.walk(worker) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "open_model"]
    assert len(calls) == 1
    solve_fn = next(node for node in worker.body if isinstance(node, ast.FunctionDef) and node.name == "solve")
    assert calls[0] in list(ast.walk(solve_fn))


@pytest.mark.parametrize("failure", ["timeout", "invalid_receipt", "download", "request_upload"])
def test_uncertain_or_failed_transport_is_never_replayed(tmp_path, failure):
    env = MockEnvironment(failure=failure)
    inst = agent.EpistemicBrainAgent(tmp_path / "logs", brain_source=small_source(tmp_path))
    asyncio.run(inst.setup(env))
    with pytest.raises((agent.AgentRejected, OSError, TimeoutError)):
        asyncio.run(inst.run("task", env, SimpleNamespace()))
    with pytest.raises(agent.AgentRejected, match="ALREADY_DISPATCHED"):
        asyncio.run(inst.run("task", env, SimpleNamespace()))
    assert len([cmd for cmd, _ in env.commands if "run" in shlex.split(cmd)]) == (0 if failure == "request_upload" else 1)
    assert not (tmp_path / "logs/model.patch").exists()
    assert json.loads((tmp_path / "logs/transport_error.json").read_text())["status"] == "TRANSPORT_FAILED_NO_REPLAY"


@pytest.mark.parametrize("damage", ["host_locus", "self_verification", "model_call", "stale_run", "patch",
                                    "nested_counter", "root_worker", "unknown_status", "inconsistent_status", "missing_filter"])
def test_corrupt_or_self_credited_artifacts_are_not_published(tmp_path, damage):
    env = MockEnvironment(damage=damage)
    inst = agent.EpistemicBrainAgent(tmp_path / "logs", brain_source=small_source(tmp_path))
    asyncio.run(inst.setup(env))
    with pytest.raises(agent.AgentRejected):
        asyncio.run(inst.run("task", env, SimpleNamespace()))
    assert not (tmp_path / "logs/model.patch").exists()


def test_failed_readonly_setup_has_no_solver_fallback(tmp_path):
    env = MockEnvironment(failure="setup")
    inst = agent.EpistemicBrainAgent(tmp_path / "logs", brain_source=small_source(tmp_path))
    with pytest.raises(agent.AgentRejected, match="CONTAINER_COMMAND_FAILED:17"):
        asyncio.run(inst.setup(env))
    with pytest.raises(agent.AgentRejected, match="SETUP_REQUIRED"):
        asyncio.run(inst.run("task", env, SimpleNamespace()))
    assert not [cmd for cmd, _ in env.commands if "run" in shlex.split(cmd)]


def test_bundle_excludes_host_credentials_datasets_and_reference_solutions(tmp_path):
    source = small_source(tmp_path)
    for name in (".git/config", ".env", ".benchmarks/gold.py", "canonical/runtime/tests/gold.py",
                 "canonical/runtime/test_secret.py", "canonical/tasks/example/solution/solve.sh",
                 "canonical/runtime/weights.bin", "canonical/runtime/model.safetensors",
                 "canonical/capabilities/true/oracles/answer.py", "canonical/runtime/datasets/hidden.json"):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("MUST NOT UPLOAD")
    dest = tmp_path / "bundle"
    dest.mkdir()
    digest = agent.stage_source(source, dest)
    manifest = json.loads((dest / "source-manifest.json").read_text())
    assert len(manifest) == 4
    assert digest == hashlib.sha256((dest / "source-manifest.json").read_bytes()).hexdigest()
    assert not [path for path in dest.rglob("*") if path.is_file() and b"MUST NOT UPLOAD" in path.read_bytes()]


def test_bundle_rejects_symlinks_instead_of_dereferencing_host_files(tmp_path):
    source = small_source(tmp_path)
    (source / "canonical/runtime/leak.json").symlink_to(ROOT / "README.md")
    with pytest.raises(agent.AgentRejected, match="SOURCE_SYMLINK"):
        agent.stage_source(source, tmp_path / "bundle")


@pytest.mark.parametrize("options", [{"mode": "EPISTEMIC"}, {"solve_timeout_sec": True},
                                    {"solve_timeout_sec": 0}, {"workspace": "relative"},
                                    {"solve_timeout_sec": 71800}])
def test_invalid_options_fail_before_transport(tmp_path, options):
    with pytest.raises(agent.AgentRejected):
        agent.EpistemicBrainAgent(tmp_path, **options)


def test_frontierswe_budget_is_not_silently_capped_to_one_hour(tmp_path):
    inst = agent.EpistemicBrainAgent(tmp_path, solve_timeout_sec=71600)
    assert inst.solve_timeout_sec == 71600
    assert inst.version() == "2.0.0"
    assert agent.HarborEpistemicAgent is agent.EpistemicBrainAgent


def test_bundle_rejects_symlink_ancestor_not_only_leaf(tmp_path):
    source = small_source(tmp_path)
    alias = tmp_path / "alias"
    alias.mkdir()
    (alias / "canonical").symlink_to(source / "canonical", target_is_directory=True)
    with pytest.raises(agent.AgentRejected, match="SOURCE_SYMLINK"):
        agent.stage_source(alias, tmp_path / "bundle")


def test_host_publication_replaces_links_without_touching_their_targets(tmp_path):
    env = MockEnvironment()
    logs = tmp_path / "logs"
    logs.mkdir()
    victim = tmp_path / "do-not-touch"
    victim.write_bytes(b"unrelated host data")
    (logs / "model.patch").symlink_to(victim)
    inst = agent.EpistemicBrainAgent(logs, brain_source=small_source(tmp_path))
    asyncio.run(inst.setup(env))
    asyncio.run(inst.run("transport fixture", env, SimpleNamespace()))
    assert victim.read_bytes() == b"unrelated host data"
    assert not (logs / "model.patch").is_symlink()
    assert (logs / "model.patch").read_bytes() == PATCH_BYTES
    assert not list(logs.glob(".brain-*"))


def test_real_harbor_base_and_atif_when_dependency_is_installed(tmp_path):
    if agent.BaseAgent is object:
        pytest.skip("Harbor not installed; do not fake its schema or BaseAgent")
    from harbor.agents.base import BaseAgent
    from harbor.models.trajectories.trajectory import Trajectory
    env = MockEnvironment()
    inst = agent.EpistemicBrainAgent(tmp_path / "logs", brain_source=small_source(tmp_path))
    assert isinstance(inst, BaseAgent)
    assert inst.capabilities.atif is True
    asyncio.run(inst.setup(env))
    asyncio.run(inst.run("transport fixture", env, SimpleNamespace()))
    doc = Trajectory.model_validate_json((tmp_path / "logs/trajectory.json").read_text())
    assert doc.schema_version == "ATIF-v1.6"
    assert doc.session_id == inst._run_id


def test_toolchain_allowlist_matches_worker_and_is_restored_only_after_filter():
    module = ast.parse((ROOT / agent.WORKER).read_text())
    declaration = next(node for node in module.body if isinstance(node, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == "TOOL_ENV_KEYS" for t in node.targets))
    assert ast.literal_eval(declaration.value) == agent.TOOL_ENV_KEYS
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "worker")
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
    install = next(node for node in calls if isinstance(node.func, ast.Name) and node.func.id == "install_worker_boundary")
    restore = next(node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "update")
    invoke = next(node for node in calls if isinstance(node.func, ast.Name) and node.func.id == "solve")
    assert install.lineno < restore.lineno < invoke.lineno
