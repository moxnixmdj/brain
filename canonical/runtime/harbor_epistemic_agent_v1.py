"""Transport-only Harbor agent. Brain is imported/executed ONLY by the container worker.

Host effects are limited to staging source/request bytes and collecting run artifacts.
There is deliberately no model factory, proposal loop, local subprocess fallback, or
verifier here. ``model.patch`` is the official SWE-bench Pro V2 replay filename;
Harbor/px-eval retain responsibility for their own task artifacts and verifiers.
"""
from __future__ import annotations

import hashlib
import json
import shlex
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

try:
    from harbor.agents.base import BaseAgent
    from harbor.agents.capabilities import AgentCapabilities
except ModuleNotFoundError as exc:
    if exc.name != "harbor":
        raise  # A broken Harbor install is not an excuse to silently use a stub.
    BaseAgent = object  # Permit transport unit tests without installing Harbor.
    AgentCapabilities = None

SCHEMA = "PROJECT_BRAIN_HARBOR_CONTAINER_RUN_V1"
# Image toolchain metadata only; never provider keys, LD_PRELOAD, or Python startup hooks.
TOOL_ENV_KEYS = (
    "PATH", "VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "CUDA_HOME", "CUDA_PATH",
    "CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES", "NVIDIA_DRIVER_CAPABILITIES",
    "LD_LIBRARY_PATH", "GOPATH", "GOROOT", "CARGO_HOME", "RUSTUP_HOME",
    "OMP_NUM_THREADS", "MKL_NUM_THREADS", "TASK_BUDGET_SECS",
)
WORKER = "canonical/runtime/harbor_container_solver_v1.py"
ARTIFACTS = ("model.patch", "trajectory.json", "brain_result.json", "solver.log")
MAX_PATCH_BYTES = 64 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_LOG_BYTES = 64 * 1024 * 1024
MAX_SOLVE_TIMEOUT_SEC = 71760  # +240 transport/capture reserve fits Frontier's 20 hours.
# Export trusted Brain source/registry data, not the host checkout or benchmark checkout.
# These roots contain pre-existing project evidence: the manifest is provenance, not
# a certification that the existing model/code has never seen a public benchmark.
BUNDLE_DIRS = (
    "canonical/runtime", "canonical/swe_kernel", "canonical/unified_model",
    "canonical/tools", "canonical/capabilities", "canonical/governance",
    "canonical/verification", "canonical/laws", "execution_guard",
    "canonical/astra_runtime/evidence", "canonical/astra_runtime/missions",
)
BUNDLE_FILES = ("canonical/CANONICAL_POINTER.json", "AGENTS.md", "README.md")
EXCLUDED_PARTS = frozenset({
    ".git", ".venv", "__pycache__", "tests", "test", "fixtures", "tasks",
    "solution", "solutions", "tmp", "node_modules", ".env", ".cache",
    "datasets", "benchmarks", "oracles", "evals", "gold", "reference_solutions",
})
SOURCE_SUFFIXES = frozenset({".py", ".json", ".md", ".toml", ".yaml", ".yml", ".sh", ".txt", ".js", ".mjs", ".html"})


class AgentRejected(RuntimeError):
    pass


def stage_source(source: Path, target: Path) -> str:
    """Data-only export; never import Brain or copy the entire host checkout.

    Symlinks are refused rather than dereferenced into host secrets or datasets.
    The manifest binds exactly the bytes uploaded, including local source changes.
    """
    manifest: dict[str, str] = {}

    def copy_file(path: Path) -> None:
        relative = path.relative_to(source)
        if any((source / Path(*relative.parts[:i])).is_symlink()
               for i in range(1, len(relative.parts) + 1)):
            raise AgentRejected("SOURCE_SYMLINK:" + str(relative))
        raw = path.read_bytes()
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        dest.chmod(0o555 if path.stat().st_mode & 0o111 else 0o444)
        manifest[relative.as_posix()] = hashlib.sha256(raw).hexdigest()

    for directory in BUNDLE_DIRS:
        base = source / directory
        if not base.exists():
            continue
        if any((source / Path(*Path(directory).parts[:i])).is_symlink()
               for i in range(1, len(Path(directory).parts) + 1)):
            raise AgentRejected("SOURCE_SYMLINK:" + directory)
        for path in sorted(base.rglob("*")):
            relative = path.relative_to(source)
            if any(part in EXCLUDED_PARTS for part in relative.parts):
                continue
            if path.name.startswith("test_") or path.name.endswith("_test.py"):
                continue
            if path.is_symlink():
                raise AgentRejected("SOURCE_SYMLINK:" + str(relative))
            if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
                continue
            copy_file(path)
    for relative in BUNDLE_FILES:
        path = source / relative
        if path.exists():
            copy_file(path)
    required = (WORKER, "canonical/runtime/brain_unified_model_v1.py",
                "canonical/runtime/worker_syscall_allowlist_v1.py",
                "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json")
    if any(path not in manifest for path in required):
        raise AgentRejected("BRAIN_RUNTIME_BUNDLE_INCOMPLETE")
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    (target / "source-manifest.json").write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def validate_artifacts(directory: Path, request: dict[str, Any]) -> dict[str, Any]:
    """Validate transport integrity, NOT task correctness. Never rewrite the patch."""
    if any(not (directory / name).is_file() or (directory / name).is_symlink()
           for name in ARTIFACTS):
        raise AgentRejected("ARTIFACT_MISSING_OR_SYMLINK")
    for name, maximum in (("model.patch", MAX_PATCH_BYTES), ("solver.log", MAX_LOG_BYTES),
                          ("brain_result.json", MAX_JSON_BYTES), ("trajectory.json", MAX_JSON_BYTES)):
        if (directory / name).stat().st_size > maximum:
            raise AgentRejected("ARTIFACT_TOO_LARGE:" + name)
    report = json.loads((directory / "brain_result.json").read_text(encoding="utf-8"))
    trajectory = json.loads((directory / "trajectory.json").read_text(encoding="utf-8"))
    if not isinstance(report, dict) or not isinstance(trajectory, dict):
        raise AgentRejected("ARTIFACT_NOT_AN_OBJECT")
    expected = {
        "schema": SCHEMA, "run_id": request["run_id"],
        "instruction_sha256": hashlib.sha256(request["instruction"].encode()).hexdigest(),
        "source_manifest_sha256": request["source_manifest_sha256"],
        "execution_locus": "task_container", "verified_by_agent": False,
        "task_completion_claimed": False, "model_calls": 0, "parameters_stored": 0,
    }
    for key, value in expected.items():
        if type(report.get(key)) is not type(value) or report[key] != value:
            raise AgentRejected("ARTIFACT_CONTRACT_MISMATCH:" + key)
    if (trajectory.get("schema_version") != "ATIF-v1.6" or trajectory.get("extra") != report
            or trajectory.get("session_id") != request["run_id"]):
        raise AgentRejected("TRAJECTORY_CONTRACT_MISMATCH")
    if (type(report.get("worker_uid")) is not int or report["worker_uid"] <= 0
            or type(report.get("solver_dispatches")) is not int or report["solver_dispatches"] != 1):
        raise AgentRejected("WORKER_IDENTITY_OR_DISPATCH_INVALID")
    status, code = report.get("status"), report.get("solver_exit_code")
    if type(code) is not int or status not in {"SOLVER_RETURNED", "SOLVER_TIMEOUT", "SOLVER_ERROR"}:
        raise AgentRejected("SOLVER_STATUS_INVALID")
    if (status == "SOLVER_RETURNED") != (code == 0) or (status == "SOLVER_TIMEOUT") != (code == 124):
        raise AgentRejected("SOLVER_STATUS_MISMATCH")
    filter_sha = report.get("filter_sha256")
    if not isinstance(filter_sha, str) or len(filter_sha) != 64 or any(c not in "0123456789abcdef" for c in filter_sha):
        raise AgentRejected("FILTER_DIGEST_INVALID")
    pending = [report.get("solver_result")]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"model_calls", "external_model_calls", "model_dependency_count",
                           "producer_cognition_model_dependency_count", "parameters_stored"}:
                    if type(item) is not int or item != 0:
                        raise AgentRejected("NONZERO_OR_UNKNOWN_RUNTIME_COUNTER:" + key)
                pending.append(item)
        elif isinstance(value, list):
            pending.extend(value)
    patch = (directory / "model.patch").read_bytes()
    info = report.get("patch", {})
    if info.get("sha256") != hashlib.sha256(patch).hexdigest() or info.get("bytes") != len(patch):
        raise AgentRejected("PATCH_DIGEST_MISMATCH")
    if report.get("network_egress") != "DENIED_BY_INHERITED_SECCOMP":
        raise AgentRejected("NETWORK_BOUNDARY_NOT_ESTABLISHED")
    return report


class EpistemicBrainAgent(BaseAgent):
    if AgentCapabilities is not None:
        capabilities = AgentCapabilities(atif=True)

    def __init__(
        self, logs_dir: Path, *, brain_source: str | Path | None = None,
        workspace: str | None = None, python_bin: str = "python3",
        solve_timeout_sec: int = 2700, mode: str = "AUTO", **kwargs: Any,
    ) -> None:
        if type(solve_timeout_sec) is not int or not 1 <= solve_timeout_sec <= MAX_SOLVE_TIMEOUT_SEC:
            raise AgentRejected("SOLVER_TIMEOUT_INVALID")
        if mode not in {"AUTO", "SOLVE_OR_LEARN"}:
            raise AgentRejected("MODE_MUST_BE_A_REAL_SOLVER_MODE")
        if workspace is not None and (not workspace.startswith("/") or "\x00" in workspace):
            raise AgentRejected("WORKSPACE_MUST_BE_ABSOLUTE")
        if not python_bin or "\x00" in python_bin:
            raise AgentRejected("PYTHON_EXECUTABLE_INVALID")
        if BaseAgent is object:
            self.logs_dir = Path(logs_dir)
        else:
            super().__init__(logs_dir=Path(logs_dir), **kwargs)
        self.brain_source = Path(brain_source or Path(__file__).resolve().parents[2]).resolve()
        self.workspace = workspace
        self.python_bin = python_bin
        self.solve_timeout_sec = solve_timeout_sec
        self.mode = mode
        self._run_id = uuid.uuid4().hex
        self._source = "/opt/brain-ro-" + self._run_id
        self._scratch = "/tmp/brain-harbor-" + self._run_id
        self._ready = False
        self._started = False

    @staticmethod
    def name() -> str:
        return "brain-epistemic"

    def version(self) -> str:
        return "2.0.0"

    async def _exec(self, environment: Any, command: str, timeout: int, *, user: Any = "root") -> Any:
        # No retries: a transport exception has an uncertain execution outcome.
        result = await environment.exec(command=command, timeout_sec=timeout, user=user)
        if type(getattr(result, "return_code", None)) is not int:
            raise AgentRejected("EXEC_RECEIPT_INVALID__NO_REPLAY")
        if result.return_code != 0:
            raise AgentRejected("CONTAINER_COMMAND_FAILED:" + str(result.return_code)
                                + ":" + str(result.stderr or "")[-2000:])
        return result

    def _command(self, operation: str) -> str:
        return shlex.join([self.python_bin, "-I", "-S", "-B", self._source + "/" + WORKER,
                           operation, "--scratch", self._scratch])

    async def setup(self, environment: Any) -> None:
        if self._ready:
            raise AgentRejected("SETUP_ALREADY_COMPLETED")
        # Observe the image/Harbor-selected user and cwd, not the Harbor host's.
        probe = ("import os,json; print(json.dumps({'uid':os.getuid(),'gid':os.getgid(),"
                 "'cwd':os.getcwd(),'tool_env':{k:os.environ[k] for k in " + repr(TOOL_ENV_KEYS)
                 + " if k in os.environ}}))")
        identity = await self._exec(environment, shlex.join([self.python_bin, "-I", "-S", "-B", "-c", probe]),
                                    30, user=None)
        principal = json.loads(identity.stdout)
        await self._exec(environment, "test ! -e " + shlex.quote(self._source)
                         + " && test ! -e " + shlex.quote(self._scratch), 30)
        with tempfile.TemporaryDirectory(prefix="brain-harbor-source-") as temp:
            bundle = Path(temp) / "source"
            bundle.mkdir()
            self._manifest_sha = stage_source(self.brain_source, bundle)
            await environment.upload_dir(source_dir=bundle, target_dir=self._source)
            config = {"run_id": self._run_id, "source": self._source,
                      "source_manifest_sha256": self._manifest_sha,
                      "workspace": self.workspace, "principal": principal}
            path = Path(temp) / "setup.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            await environment.upload_file(source_path=path, target_path=self._source + "/setup.json")
        await self._exec(environment, self._command("prepare"), 180)
        self._ready = True

    async def run(self, instruction: str, environment: Any, context: Any) -> None:
        if not isinstance(instruction, str) or not instruction.strip():
            raise AgentRejected("INSTRUCTION_REQUIRED")
        if not self._ready or self._started:
            raise AgentRejected("SETUP_REQUIRED_OR_RUN_ALREADY_DISPATCHED")
        self._started = True
        request = {
            "run_id": self._run_id, "instruction": instruction, "mode": self.mode,
            "solve_timeout_sec": self.solve_timeout_sec,
            "source_manifest_sha256": self._manifest_sha,
        }
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="brain-harbor-result-") as temp:
            request_path = Path(temp) / "request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            # The only solver dispatch. The worker handles deadlines, child cleanup,
            # git capture and trajectory creation entirely inside this exec.
            try:
                await environment.upload_file(source_path=request_path, target_path=self._scratch + "/request.json")
                await self._exec(environment, self._command("run"), self.solve_timeout_sec + 240)
                for name in ARTIFACTS:
                    await environment.download_file(source_path=self._scratch + "/artifacts/" + name,
                                                    target_path=Path(temp) / name)
                validate_artifacts(Path(temp), request)
            except BaseException as exc:
                # An uncertain invocation is never replayed and never masquerades as
                # an empty successful patch. Harbor still owns container teardown.
                (self.logs_dir / "transport_error.json").write_text(json.dumps({
                    "run_id": self._run_id, "status": "TRANSPORT_FAILED_NO_REPLAY",
                    "error_type": type(exc).__name__, "task_completion_claimed": False,
                }) + "\n", encoding="utf-8")
                raise
            for name in ARTIFACTS:
                # Container /logs/agent may be a host bind mount with root-owned
                # files. Replace atomically; do not open those files for writing
                # or follow a planted symlink in a previously published artifact.
                with tempfile.NamedTemporaryFile(dir=self.logs_dir, prefix=".brain-", delete=False) as dest:
                    temporary = Path(dest.name)
                    with (Path(temp) / name).open("rb") as source:
                        shutil.copyfileobj(source, dest)
                try:
                    temporary.replace(self.logs_dir / name)
                finally:
                    temporary.unlink(missing_ok=True)
        # Preserve Harbor's accounting; no injected zero cost/tokens hiding other work.
        # Verifier invocation belongs to the official runner, never this agent.


HarborEpistemicAgent = EpistemicBrainAgent
