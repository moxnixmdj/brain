"""Real Git/process regressions for the container protocol; no benchmark tasks.

No Docker is impersonated here. The Linux filter probes run in expendable child
processes, never change the test runner's syscall policy, and use the live tree.
"""
from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from canonical.runtime import harbor_container_solver_v1 as worker

ROOT = Path(__file__).resolve().parents[2]


def git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True).stdout


def repository(path):
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.email", "transport-test@example.invalid")
    git(path, "config", "user.name", "Transport test")
    (path / "kept.txt").write_bytes(b"before\n")
    (path / "deleted.txt").write_text("remove me\n")
    (path / "binary.dat").write_bytes(b"\x00\xffbefore\x01")
    (path / ".gitignore").write_text("ignored-cache/\n")
    git(path, "add", "--all")
    git(path, "commit", "-qm", "initial test state")
    return path


def test_patch_replays_binary_new_deleted_staged_committed_and_mode_changes(tmp_path):
    task = repository(tmp_path / "task")
    pristine = repository(tmp_path / "pristine")
    base = worker.baseline(task)
    (task / "kept.txt").write_bytes(b"after\n")
    (task / "deleted.txt").unlink()
    (task / "binary.dat").write_bytes(b"\x00\xfeafter\x02")
    (task / "new file.txt").write_text("new\n")
    (task / "link").symlink_to("kept.txt")
    (task / "kept.txt").chmod(0o755)
    git(task, "add", "--all")
    git(task, "commit", "-qm", "solver advanced HEAD")
    (task / "staged.txt").write_bytes(b"staged\n")
    git(task, "add", "staged.txt")
    (task / "untracked.txt").write_bytes(b"untracked\n")
    (task / "ignored-cache").mkdir()
    (task / "ignored-cache/generated.txt").write_text("not part of patch")
    index_before = (task / ".git/index").read_bytes()
    patch = tmp_path / "model.patch"
    info = worker.capture_patch(task, base, patch)
    assert (task / ".git/index").read_bytes() == index_before
    assert info["base_commit"] == base
    assert info["kind"] == "GIT_DIFF"
    assert b"GIT binary patch" in patch.read_bytes()
    assert b"ignored-cache" not in patch.read_bytes()
    git(pristine, "apply", "--check", str(patch))
    git(pristine, "apply", "--binary", str(patch))
    for name in ("kept.txt", "binary.dat", "new file.txt", "staged.txt", "untracked.txt"):
        assert (pristine / name).read_bytes() == (task / name).read_bytes()
    assert not (pristine / "deleted.txt").exists()
    assert (pristine / "link").is_symlink()
    assert os.readlink(pristine / "link") == "kept.txt"
    assert (pristine / "kept.txt").stat().st_mode & 0o111
    assert not [path for path in task.iterdir() if path.name.startswith("brain-patch")]


def test_empty_patch_is_preserved_but_never_scored_by_agent(tmp_path):
    task = repository(tmp_path / "task")
    info = worker.capture_patch(task, worker.baseline(task), tmp_path / "model.patch")
    assert info["bytes"] == 0
    assert (tmp_path / "model.patch").read_bytes() == b""
    assert "pass" not in info


def test_non_git_task_is_not_silently_initialized_as_a_repository(tmp_path):
    task = tmp_path / "task"
    task.mkdir()
    (task / "artifact.dat").write_bytes(b"not a coding benchmark")
    assert worker.baseline(task) is None
    info = worker.capture_patch(task, None, tmp_path / "model.patch")
    assert info["kind"] == "NO_GIT_REPOSITORY__OFFICIAL_FILESYSTEM_VERIFIER_REQUIRED"
    assert not (task / ".git").exists()
    assert (task / "artifact.dat").read_bytes() == b"not a coding benchmark"


def test_dirty_tracked_image_and_non_root_workspace_are_rejected(tmp_path):
    task = repository(tmp_path / "task")
    (task / "subdir").mkdir()
    with pytest.raises(worker.BoundaryError, match="GIT_ROOT"):
        worker.baseline(task / "subdir")
    (task / "kept.txt").write_text("image already dirty\n")
    with pytest.raises(subprocess.CalledProcessError):
        worker.baseline(task)


def test_invalid_base_cannot_become_a_git_option(tmp_path):
    task = repository(tmp_path / "task")
    with pytest.raises(worker.BoundaryError, match="BASE_COMMIT_INVALID"):
        worker.capture_patch(task, "--output=/outside", tmp_path / "model.patch")


@pytest.mark.parametrize("payload", [{"model_calls": 1}, {"external_model_calls": True},
                                     {"parameters_stored": None},
                                     {"result": [{"model_dependency_count": 2}]}])
def test_nonzero_or_unknown_counter_is_a_boundary_failure(payload):
    with pytest.raises(worker.BoundaryError, match="RUNTIME_COUNTER"):
        worker._check_zero_counters(payload)


def test_safe_zero_counters_are_accepted_without_promoting_pass():
    payload = {"pass": False, "model_calls": 0, "nested": [{"parameters_stored": 0}]}
    worker._check_zero_counters(payload)
    assert payload["pass"] is False


def test_root_reader_refuses_symlink_fifo_and_oversized_worker_outputs(tmp_path):
    ordinary = tmp_path / "normal"
    ordinary.write_bytes(b"123")
    link = tmp_path / "link"
    link.symlink_to(ordinary)
    with pytest.raises(OSError) as exc:
        worker.read_worker_bytes(link)
    assert exc.value.errno == errno.ELOOP
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(worker.BoundaryError, match="REGULAR_FILE"):
        worker.read_worker_bytes(fifo)
    with pytest.raises(worker.BoundaryError, match="BOUNDED_REGULAR"):
        worker.read_worker_bytes(ordinary, 2)
    assert worker.read_worker_bytes(ordinary, 3) == b"123"


def test_source_owned_by_worker_is_not_mistaken_for_readonly():
    if os.geteuid() == 0:
        pytest.skip("source ownership negative control requires a non-root checkout")
    with pytest.raises(worker.BoundaryError, match="READ_ONLY"):
        worker.check_source_readonly()


def test_real_inherited_filter_denies_network_and_process_group_escape(tmp_path):
    if sys.platform != "linux" or os.geteuid() == 0:
        pytest.skip("non-root Linux child required")
    script = r'''
import errno, json, os, pathlib, socket, subprocess, sys
sys.path.insert(0, sys.argv[1])
from canonical.runtime.harbor_container_solver_v1 import install_worker_boundary
sha = install_worker_boundary()
blocked = []
for family in (socket.AF_INET, socket.AF_INET6, socket.AF_UNIX):
    try:
        socket.socket(family, socket.SOCK_STREAM)
    except OSError as exc:
        assert exc.errno == errno.EPERM, exc
        blocked.append(family)
    else:
        raise AssertionError("network socket unexpectedly allowed")
for call in (os.setsid, lambda: os.setpgid(0, 0)):
    try:
        call()
    except OSError as exc:
        assert exc.errno == errno.EPERM, exc
    else:
        raise AssertionError("worker escaped its process group")
child = subprocess.run([sys.executable, "-c", "import socket; socket.socket()"], capture_output=True)
assert child.returncode != 0
assert b"Operation not permitted" in child.stderr
pathlib.Path(sys.argv[2]).write_text("local work remains possible")
print(json.dumps({"blocked_families": len(blocked), "child_exit": child.returncode, "filter_sha256": sha}))
'''
    result = subprocess.run([sys.executable, "-I", "-c", script, str(ROOT), str(tmp_path / "local")],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["blocked_families"] == 3
    assert observed["child_exit"] != 0
    assert len(observed["filter_sha256"]) == 64
    assert (tmp_path / "local").read_text() == "local work remains possible"


def test_initial_untracked_files_are_not_attributed_to_the_solver(tmp_path):
    task = repository(tmp_path / "task")
    (task / "image-supplied.txt").write_text("already present before solve")
    with pytest.raises(worker.BoundaryError, match="INITIAL_WORKSPACE_HAS_UNTRACKED_FILES"):
        worker.baseline(task)


def test_initial_ignored_files_are_not_in_the_patch(tmp_path):
    task = repository(tmp_path / "task")
    (task / "ignored-cache").mkdir()
    (task / "ignored-cache/image-data").write_bytes(b"baseline ignored data")
    base = worker.baseline(task)
    info = worker.capture_patch(task, base, tmp_path / "model.patch")
    assert info["bytes"] == 0


def test_root_reader_refuses_hardlinked_worker_outputs(tmp_path):
    target = tmp_path / "target"
    target.write_bytes(b"not a transport publication")
    link = tmp_path / "hardlink"
    os.link(target, link)
    with pytest.raises(worker.BoundaryError, match="BOUNDED_REGULAR"):
        worker.read_worker_bytes(link)


@pytest.mark.parametrize("wait_forever", [False, True])
def test_process_group_is_reaped_after_normal_exit_and_timeout(tmp_path, wait_forever):
    # Do not change the pytest runner's subreaper setting. A separate real
    # process exercises the same supervisor cleanup with a real grandchild.
    script = r'''
import json, pathlib, select, subprocess, sys
sys.path.insert(0, sys.argv[1])
from canonical.runtime.harbor_container_solver_v1 import enable_child_subreaper, wait_and_reap
enable_child_subreaper()
wait_forever = sys.argv[2] == "True"
code = ("import subprocess,sys,time; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
        "print(child.pid, flush=True); "
        + ("time.sleep(60)" if wait_forever else "sys.exit(7)"))
process = subprocess.Popen([sys.executable, "-I", "-c", code], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, start_new_session=True)
try:
    readable, _, _ = select.select([process.stdout], [], [], 10)
    assert readable, "child did not report its descendant"
    descendant = int(process.stdout.readline().strip())
    exit_code = wait_and_reap(process, 1)
    assert exit_code == (124 if wait_forever else 7)
    assert not pathlib.Path(f"/proc/{descendant}").exists(), "descendant not reaped"
    assert process.poll() is not None
    print(json.dumps({"exit_code": exit_code, "descendant_reaped": True}))
finally:
    if process.poll() is None:
        wait_and_reap(process, 1)
    process.stdout.close()
    process.stderr.close()
'''
    result = subprocess.run([sys.executable, "-I", "-c", script, str(ROOT), str(wait_forever)],
                            capture_output=True, text=True, timeout=25)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["exit_code"] == (124 if wait_forever else 7)
    assert report["descendant_reaped"] is True


@pytest.mark.parametrize("environment", [{"OPENAI_API_KEY": "never-transfer"},
                                         {"LD_PRELOAD": "/task/untrusted.so"},
                                         {"PYTHONPATH": "/task"}, {"PATH": 42}])
def test_image_tool_environment_cannot_smuggle_credentials_or_startup_hooks(environment):
    with pytest.raises(worker.BoundaryError, match="IMAGE_TOOL_ENV"):
        worker.validated_tool_env(environment)


def test_container_image_tool_paths_are_preserved_not_the_host_environment():
    tool_env = {"PATH": "/usr/local/go/bin:/usr/bin", "CUDA_HOME": "/usr/local/cuda", "TASK_BUDGET_SECS": "72000"}
    assert worker.validated_tool_env(tool_env) == tool_env


def test_task_cannot_own_the_interpreter_used_before_seccomp(tmp_path):
    interpreter = Path(sys.executable).resolve()
    with pytest.raises(worker.BoundaryError, match="INSIDE_TASK_WORKSPACE"):
        worker.check_trusted_paths([interpreter], interpreter.parent)


def test_readonly_but_worker_owned_runtime_path_is_rejected(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("negative ownership control requires a non-root test user")
    path = tmp_path / "not-an-interpreter"
    path.write_bytes(b"transport negative control")
    path.chmod(0o444)
    with pytest.raises(worker.BoundaryError, match="RUNTIME_REPLACEABLE"):
        worker.check_trusted_paths([path], tmp_path / "task")


def test_system_owned_interpreter_path_is_admissible(tmp_path):
    # This only checks permissions; it never executes Brain on the host.
    interpreter = Path("/usr/bin/python3").resolve()
    if not interpreter.exists():
        pytest.skip("system Python is not installed at the conventional Linux path")
    worker.check_trusted_paths([interpreter], tmp_path / "task")
    assert interpreter.stat().st_uid == 0
