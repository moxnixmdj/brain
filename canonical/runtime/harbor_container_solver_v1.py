"""Container-only supervisor/worker for the Harbor transport agent.

No Harbor dependency and no task/verifier code is imported. Only ``solve`` imports
Brain. The root supervisor never imports Brain, runs a model, or grades a task.
Source is root-owned and non-writable; the worker is non-root, has no capabilities,
no-new-privileges, and an inherited syscall filter (including network denial).
Harbor's task container remains the outer isolation boundary. No nested namespace.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import platform
import re
import resource
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_HARBOR_CONTAINER_RUN_V1"
# Image toolchain metadata only; never provider keys, LD_PRELOAD, or Python startup hooks.
TOOL_ENV_KEYS = (
    "PATH", "VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "CUDA_HOME", "CUDA_PATH",
    "CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES", "NVIDIA_DRIVER_CAPABILITIES",
    "LD_LIBRARY_PATH", "GOPATH", "GOROOT", "CARGO_HOME", "RUSTUP_HOME",
    "OMP_NUM_THREADS", "MKL_NUM_THREADS", "TASK_BUDGET_SECS",
)
SOURCE = Path(__file__).resolve().parents[2]
MAX_PATCH_BYTES = 64 * 1024 * 1024
MAX_RESULT_BYTES = 8 * 1024 * 1024


class BoundaryError(RuntimeError):
    pass


def write_json(path: Path, data: Any) -> None:
    raw = (json.dumps(data, sort_keys=True, ensure_ascii=True, indent=2) + "\n").encode()
    if len(raw) > MAX_RESULT_BYTES:
        raise BoundaryError("RESULT_TOO_LARGE")
    path.write_bytes(raw)


def git(workspace: Path, *args: str, index: str | None = None, output: Any = subprocess.PIPE) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
               GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")
    if index is not None:
        env["GIT_INDEX_FILE"] = index
    return subprocess.run(
        ["git", "-c", "safe.directory=" + str(workspace), "-c", "core.fsmonitor=false",
         "-c", "core.hooksPath=/dev/null", "-C", str(workspace), *args],
        env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.PIPE,
        timeout=120, check=True,
    )


def baseline(workspace: Path) -> str | None:
    """Return the initial commit. Non-repository tasks remain non-repositories."""
    try:
        top = Path(git(workspace, "rev-parse", "--show-toplevel").stdout.decode().strip()).resolve()
    except subprocess.CalledProcessError:
        return None
    if top != workspace.resolve():
        raise BoundaryError("WORKSPACE_MUST_BE_THE_GIT_ROOT")
    value = git(workspace, "rev-parse", "--verify", "HEAD^{commit}").stdout.decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
        raise BoundaryError("BASE_COMMIT_INVALID")
    # A dirty image is not a clean patch baseline; do not relabel image changes as ours.
    git(workspace, "diff", "--quiet", "--no-ext-diff", "--no-textconv", value, "--")
    if git(workspace, "ls-files", "--others", "--exclude-standard", "-z").stdout:
        raise BoundaryError("INITIAL_WORKSPACE_HAS_UNTRACKED_FILES")
    return value


def capture_patch(workspace: Path, base: str | None, output: Path) -> dict[str, Any]:
    """Binary-safe git diff, including new files, staged edits and solver commits.

    A private index avoids git add/reset on the task's real index. The initial
    commit is supplied by the supervisor, never read from a solver-moved HEAD.
    """
    if base is None:
        output.write_bytes(b"")
        kind = "NO_GIT_REPOSITORY__OFFICIAL_FILESYSTEM_VERIFIER_REQUIRED"
    else:
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", base):
            raise BoundaryError("BASE_COMMIT_INVALID")
        with tempfile.TemporaryDirectory(prefix="brain-patch-index-", dir=output.parent) as temp:
            index = str(Path(temp) / "index")
            git(workspace, "read-tree", base, index=index)
            git(workspace, "add", "--all", "--", ".", index=index)
            with output.open("wb") as stream:
                git(workspace, "diff", "--cached", "--binary", "--full-index", "--no-ext-diff",
                    "--no-textconv", "--no-color", base, "--", ".", index=index, output=stream)
        kind = "GIT_DIFF"
    size = output.stat().st_size
    if size > MAX_PATCH_BYTES:
        output.unlink()
        raise BoundaryError("PATCH_TOO_LARGE__NOT_TRUNCATED")
    return {"path": "model.patch", "kind": kind, "base_commit": base, "bytes": size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def check_trusted_paths(paths: list[Path], workspace: Path) -> None:
    """Pre-filter executable/import paths cannot be replaced by the task worker."""
    for original in paths:
        for path in (original, original.resolve()):
            if path.is_relative_to(workspace):
                raise BoundaryError("PYTHON_RUNTIME_INSIDE_TASK_WORKSPACE")
            for node in (path, *path.parents):
                if not node.exists():
                    continue
                info = node.stat()
                if info.st_uid != 0 or info.st_mode & 0o022:
                    raise BoundaryError("PYTHON_RUNTIME_REPLACEABLE:" + str(node))


def prepare(scratch: Path) -> None:
    if os.geteuid() != 0:
        raise BoundaryError("STAGING_REQUIRES_CONTAINER_ROOT")
    config = json.loads((SOURCE / "setup.json").read_text())
    if str(SOURCE) != config["source"] or str(scratch) != "/tmp/brain-harbor-" + config["run_id"]:
        raise BoundaryError("STAGING_PATH_MISMATCH")
    manifest_raw = (SOURCE / "source-manifest.json").read_bytes()
    if hashlib.sha256(manifest_raw).hexdigest() != config["source_manifest_sha256"]:
        raise BoundaryError("SOURCE_MANIFEST_MISMATCH")
    for relative, digest in json.loads(manifest_raw).items():
        path = SOURCE / relative
        if not path.resolve().is_relative_to(SOURCE) or path.is_symlink():
            raise BoundaryError("SOURCE_PATH_ESCAPE")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise BoundaryError("SOURCE_BYTES_CHANGED:" + relative)
    # Legacy readers mkdir these even in READ_ONLY mode. Empty immutable
    # directories support that initialization without importing host state/caches.
    for relative in ("canonical/astra_runtime/tmp", "canonical/astra_runtime/state"):
        (SOURCE / relative).mkdir(parents=True, exist_ok=True)
    # Do not trust chmod on root-executed code: every later solver runs as a
    # different uid without capabilities and cannot chmod/replace this tree.
    if SOURCE.parent.stat().st_uid != 0 or SOURCE.parent.stat().st_mode & 0o022:
        raise BoundaryError("SOURCE_PARENT_NOT_ROOT_OWNED_AND_READ_ONLY_TO_WORKER")
    for path in [*SOURCE.rglob("*"), SOURCE]:
        if path.is_symlink():
            raise BoundaryError("SOURCE_SYMLINK")
        os.chown(path, 0, 0)
        path.chmod(0o555 if path.is_dir() or path.stat().st_mode & 0o111 else 0o444)
    principal = config["principal"]
    candidates = [Path(config["workspace"])] if config["workspace"] else [
        Path(principal["cwd"]), Path("/app"), Path("/testbed"), Path("/workspace")]
    excluded = {"/", "/opt", "/tmp", "/usr", "/etc", "/var", "/home", "/root"}
    workspace = next((p.resolve() for p in candidates if p.is_dir() and str(p.resolve()) not in excluded), None)
    if workspace is None:
        raise BoundaryError("TASK_WORKSPACE_REQUIRED")
    if any(workspace.is_relative_to(p) or p.is_relative_to(workspace) for p in (SOURCE, scratch)):
        raise BoundaryError("TASK_AND_RUNTIME_PATHS_OVERLAP")
    # Python (including imported bytecode) runs before the worker installs its
    # filter. Do not chown an in-workspace interpreter or let a task replace a
    # pre-filter runtime path and thereby evade confinement during capture.
    runtime_paths = [Path(sys.executable), Path(platform.__file__)]
    runtime_paths.extend(Path(p) for p in sys.path if p and Path(p).is_absolute())
    for module in tuple(sys.modules.values()):
        for attribute in ("__file__", "__cached__"):
            value = getattr(module, attribute, None)
            if isinstance(value, str) and Path(value).is_absolute():
                runtime_paths.append(Path(value))
    check_trusted_paths(runtime_paths, workspace)
    uid, gid = principal["uid"], principal["gid"]
    if type(uid) is not int or type(gid) is not int or uid < 0 or gid < 0:
        raise BoundaryError("TASK_PRINCIPAL_INVALID")
    if uid == 0:
        uid = gid = 65534
        # Images that run the agent as root need a writable task checkout after
        # privilege drop. Do not follow symlinks out of that checkout.
        for directory, dirs, files in os.walk(workspace, followlinks=False):
            for path in [Path(directory), *(Path(directory) / n for n in dirs + files)]:
                info = path.lstat()
                if not stat.S_ISDIR(info.st_mode) and info.st_nlink != 1:
                    raise BoundaryError("WORKSPACE_HARDLINK_OWNERSHIP_UNSAFE")
                os.lchown(path, uid, gid)
    scratch.mkdir(mode=0o755)
    (scratch / "artifacts").mkdir(mode=0o755)  # root-owned publications
    (scratch / "work").mkdir(mode=0o700)
    os.chown(scratch / "work", uid, gid)
    config.update(workspace=str(workspace), uid=uid, gid=gid)
    write_json(scratch / "config.json", config)
    (scratch / "config.json").chmod(0o444)


def install_worker_boundary() -> str:
    """Tighten the existing filter, don't create a second sandbox implementation.

    socket/connect/send* are denied for ALL address families and descendants.
    setsid/setpgid are denied after the supervisor establishes a fresh process
    group, so a timed-out descendant cannot escape process-group cleanup.
    """
    if os.geteuid() == 0:
        raise BoundaryError("SOLVER_MUST_NOT_RUN_AS_ROOT")
    status = Path("/proc/self/status").read_text()
    for name in ("CapEff", "CapPrm", "CapInh", "CapAmb"):
        match = re.search(r"^" + name + r":\s*([0-9a-f]+)$", status, re.M)
        if match is None or int(match.group(1), 16):
            raise BoundaryError("WORKER_HAS_CAPABILITIES:" + name)
    sys.path.insert(0, str(SOURCE))
    from canonical.runtime import worker_syscall_allowlist_v1 as syscall_filter

    program = syscall_filter.program()  # fails closed on unsupported architectures
    _, numbers = syscall_filter._table(None)
    deny = []
    for name in ("socket", "connect", "sendto", "sendmsg", "setsid", "setpgid"):
        deny.extend([(0x15, 0, 1, numbers[name]), (0x06, 0, 0, 0x00050000 | errno.EPERM)])
    # Keep the architecture/x32 guards before the additional syscall checks.
    raw = b"".join(struct.pack("<HBBI", *row) for row in program[:6] + deny + program[6:])
    buf = ctypes.create_string_buffer(raw, len(raw))

    class Program(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ushort), ("filter", ctypes.c_void_p)]

    c_program = Program(len(raw) // 8, ctypes.addressof(buf))
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int] + [ctypes.c_ulong] * 4
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.addressof(c_program), 0, 0):
        raise BoundaryError("SECCOMP_INSTALL_FAILED:" + str(ctypes.get_errno()))
    return hashlib.sha256(raw).hexdigest()


def check_source_readonly() -> None:
    for path in [SOURCE, *SOURCE.rglob("*")]:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o222:
            raise BoundaryError("BRAIN_SOURCE_NOT_READ_ONLY:" + str(path))
    if os.access(SOURCE.parent, os.W_OK):
        raise BoundaryError("BRAIN_SOURCE_CAN_BE_REPLACED")


def _check_zero_counters(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"model_calls", "external_model_calls", "model_dependency_count",
                       "producer_cognition_model_dependency_count", "parameters_stored"}:
                if type(item) is not int or item != 0:
                    raise BoundaryError("NONZERO_OR_UNKNOWN_RUNTIME_COUNTER:" + key)
            _check_zero_counters(item)
    elif isinstance(value, list):
        for item in value:
            _check_zero_counters(item)


def solve(request: dict[str, Any], workspace: Path) -> dict[str, Any]:
    """The only open_model().solve() call site. Executed in the filtered child."""
    # -S prevents startup .pth/sitecustomize execution before the boundary.
    # Expose installed dependencies only after filtering; never execute .pth files.
    import site
    for directory in site.getsitepackages():
        if directory not in sys.path:
            sys.path.append(directory)
    from canonical.runtime.brain_unified_model_v1 import open_model
    from canonical.runtime.memory_policy_v1 import READ_ONLY, memory_policy_scope

    with memory_policy_scope(READ_ONLY):
        result = open_model().solve(
            request["instruction"], mode=request["mode"], cwd=workspace,
            context_paths=[str(workspace)], inputs={"allow_instant_knowledge": False},
        )
    if not isinstance(result, dict):
        raise BoundaryError("SOLVER_RESULT_NOT_AN_OBJECT")
    _check_zero_counters(result)
    return result


def validated_tool_env(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or any(key not in TOOL_ENV_KEYS for key in value):
        raise BoundaryError("IMAGE_TOOL_ENV_KEYS_INVALID")
    if any(not isinstance(item, str) or "\x00" in item for item in value.values()):
        raise BoundaryError("IMAGE_TOOL_ENV_VALUE_INVALID")
    return value


def worker(operation: str, scratch: Path) -> None:
    config = json.loads((scratch / "config.json").read_text())
    workspace = Path(config["workspace"])
    os.chdir(workspace)
    # Bound individual writes (including inherited stdout); never publish a
    # truncated patch/log as a successful transport. These hard limits inherit.
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_PATCH_BYTES, MAX_PATCH_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    filter_sha = install_worker_boundary()
    check_source_readonly()
    request = json.loads((scratch / "request.json").read_text())
    if operation == "snapshot":
        write_json(scratch / "work/baseline.json", {"base_commit": baseline(workspace), "filter_sha256": filter_sha})
    elif operation == "capture":
        base = json.loads((scratch / "baseline.json").read_text())["base_commit"]
        info = capture_patch(workspace, base, scratch / "work/model.patch")
        write_json(scratch / "work/patch.json", info)
    else:
        # Restore image toolchains only AFTER seccomp; even a task-controlled
        # tool/library path cannot execute pre-filter native startup code.
        os.environ.update(validated_tool_env(config["principal"].get("tool_env", {})))
        try:
            result = solve(request, workspace)
        except BoundaryError as exc:
            write_json(scratch / "work/solution.json", {"boundary_error": str(exc)})
            raise
        write_json(scratch / "work/solution.json", result)


def enable_child_subreaper() -> None:
    """Adopt orphan descendants so cleanup waits for exit, not just SIGKILL delivery."""
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0):  # PR_SET_CHILD_SUBREAPER
        raise BoundaryError("CHILD_SUBREAPER_UNAVAILABLE:" + str(ctypes.get_errno()))


def run_child(operation: str, scratch: Path, config: dict[str, Any], timeout: int, log: Any) -> int:
    """Start with no host/user credentials; reap the whole filtered process group."""
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(scratch / "work"),
        "TMPDIR": str(scratch / "work"), "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1", "BRAIN_COGNITIVE_STATE_DIR": str(scratch / "work/cognitive"),
    }
    process = subprocess.Popen(
        [str(Path(sys.executable).resolve()), "-I", "-S", "-B", str(Path(__file__).resolve()), operation, "--scratch", str(scratch)],
        cwd=config["workspace"], env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
        start_new_session=True, close_fds=True, user=config["uid"], group=config["gid"], extra_groups=[],
    )
    return wait_and_reap(process, timeout)


def wait_and_reap(process: subprocess.Popen, timeout: int) -> int:
    """Reap this fresh session; the caller must already be a child subreaper."""
    try:
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return 124
    finally:
        # Also kill background descendants after a normal solver exit; they must
        # not race the final patch capture or survive into the verifier phase.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)
        # SIGKILL delivery is asynchronous. The leader may already have exited;
        # wait for adopted descendants too before permitting patch capture.
        deadline = time.monotonic() + 10
        while True:
            try:
                pid, _ = os.waitpid(-process.pid, os.WNOHANG)
            except ChildProcessError:
                break
            if pid == 0:
                if time.monotonic() >= deadline:
                    raise BoundaryError("DESCENDANT_CLEANUP_TIMEOUT")
                time.sleep(0.01)


def read_worker_bytes(path: Path, maximum: int = MAX_RESULT_BYTES) -> bytes:
    """Never let a solver-created symlink, FIFO or oversized file drive root I/O."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > maximum:
            raise BoundaryError("WORKER_ARTIFACT_NOT_BOUNDED_REGULAR_FILE")
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise BoundaryError("WORKER_ARTIFACT_TOO_LARGE")
    return raw


def supervise(scratch: Path) -> None:
    if os.geteuid() != 0:
        raise BoundaryError("SUPERVISOR_REQUIRES_CONTAINER_ROOT")
    enable_child_subreaper()
    config = json.loads((scratch / "config.json").read_text())
    request = json.loads((scratch / "request.json").read_text())
    if request["run_id"] != config["run_id"] or request["source_manifest_sha256"] != config["source_manifest_sha256"]:
        raise BoundaryError("REQUEST_IDENTITY_MISMATCH")
    if type(request["solve_timeout_sec"]) is not int or not 1 <= request["solve_timeout_sec"] <= 71760:
        raise BoundaryError("SOLVER_TIMEOUT_INVALID")
    if request["mode"] not in {"AUTO", "SOLVE_OR_LEARN"}:
        raise BoundaryError("SOLVER_MODE_INVALID")
    (scratch / "request.json").chmod(0o444)
    artifacts = scratch / "artifacts"
    # Root owns final publications. All worker output stays in work/ until
    # validated; it cannot write the final report/trajectory or self-grade.
    solution = None
    with (artifacts / "solver.log").open("wb") as log:
        snapshot_rc = run_child("snapshot", scratch, config, 60, log)
        if snapshot_rc:
            raise BoundaryError("SNAPSHOT_OR_BOUNDARY_FAILED:" + str(snapshot_rc))
        frozen = json.loads(read_worker_bytes(scratch / "work/baseline.json"))
        write_json(scratch / "baseline.json", frozen)
        (scratch / "baseline.json").chmod(0o444)
        solve_rc = run_child("solve", scratch, config, request["solve_timeout_sec"], log)
        result_path = scratch / "work/solution.json"
        if result_path.exists() or result_path.is_symlink():
            solution = json.loads(read_worker_bytes(result_path))
            if not isinstance(solution, dict):
                raise BoundaryError("SOLVER_RESULT_NOT_AN_OBJECT")
            if "boundary_error" in solution:
                raise BoundaryError("SOLVER_CONSTRAINT_FAILED:" + str(solution["boundary_error"]))
            _check_zero_counters(solution)
        elif solve_rc == 0:
            raise BoundaryError("SOLVER_RETURNED_WITHOUT_RESULT")
        capture_rc = run_child("capture", scratch, config, 120, log)
        if capture_rc:
            raise BoundaryError("PATCH_CAPTURE_FAILED:" + str(capture_rc))
    patch = json.loads(read_worker_bytes(scratch / "work/patch.json"))
    patch_bytes = read_worker_bytes(scratch / "work/model.patch", MAX_PATCH_BYTES)
    if patch["bytes"] != len(patch_bytes) or patch["sha256"] != hashlib.sha256(patch_bytes).hexdigest():
        raise BoundaryError("PATCH_CHANGED_DURING_CAPTURE")
    (artifacts / "model.patch").write_bytes(patch_bytes)
    report = {
        "schema": SCHEMA, "run_id": request["run_id"],
        "instruction_sha256": hashlib.sha256(request["instruction"].encode()).hexdigest(),
        "source_manifest_sha256": config["source_manifest_sha256"],
        "execution_locus": "task_container", "workspace": config["workspace"],
        "worker_uid": config["uid"], "solver_dispatches": 1,
        "model_calls": 0, "parameters_stored": 0,
        "network_egress": "DENIED_BY_INHERITED_SECCOMP", "filter_sha256": frozen["filter_sha256"],
        "status": "SOLVER_TIMEOUT" if solve_rc == 124 else ("SOLVER_RETURNED" if solve_rc == 0 else "SOLVER_ERROR"),
        "solver_exit_code": solve_rc, "solver_result": solution,
        "patch": patch, "verified_by_agent": False, "task_completion_claimed": False,
        "authority": "NONE__OFFICIAL_EXTERNAL_VERIFIER_DECIDES",
        "memory_policy": "READ_ONLY__NO_CROSS_TASK_UPDATES",
    }
    write_json(artifacts / "brain_result.json", report)
    write_json(artifacts / "trajectory.json", {
        "schema_version": "ATIF-v1.6", "session_id": request["run_id"],
        "agent": {"name": "brain-epistemic", "version": "2.0.0"},
        "steps": [
            {"step_id": 1, "source": "user", "message": request["instruction"]},
            {"step_id": 2, "source": "agent",
             "message": "Container-local solve ended. This is not a task-success verdict.",
             "extra": {"deterministic_dispatch": True, "solver_exit_code": solve_rc}},
        ],
        "notes": "One solver dispatch, not a fabricated shell-action history. Full returned evidence is in extra.solver_result; official verifiers own scoring.",
        "extra": report,
    })
    # Harbor copies its standard /logs/agent directory after run. Publish the same
    # bytes there as the explicit download contract, so neither path loses them.
    logs = Path("/logs/agent")
    if Path("/logs").is_symlink() or logs.is_symlink():
        raise BoundaryError("HARBOR_LOG_DIRECTORY_SYMLINK")
    logs.mkdir(parents=True, exist_ok=True)
    for name in ("model.patch", "trajectory.json", "brain_result.json", "solver.log"):
        fd, temporary = tempfile.mkstemp(prefix=".brain-", dir=logs)
        try:
            os.fchmod(fd, 0o644)  # Harbor's host user must read bind-mounted logs.
            with os.fdopen(fd, "wb") as dest, (artifacts / name).open("rb") as source:
                shutil.copyfileobj(source, dest)
            os.replace(temporary, logs / name)  # replace, never follow a planted link
        finally:
            Path(temporary).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "run", "snapshot", "solve", "capture"))
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        raise BoundaryError("PYTHON_3_10_OR_NEWER_REQUIRED")
    if args.operation == "prepare":
        prepare(args.scratch)
    elif args.operation == "run":
        supervise(args.scratch)
    else:
        worker(args.operation, args.scratch)


if __name__ == "__main__":
    main()
