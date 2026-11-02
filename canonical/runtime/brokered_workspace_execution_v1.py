#!/usr/bin/env python3
"""Staged read-only namespace + broker execution (`brokered_workspace_execution_v1`).

Replaces in-place `confine_v1` + `solve_v1.act` live-workspace mutation with a
four-phase staged broker pipeline built from existing repository primitives:

  1. Immutable pre-snapshot (`repair_candidate_broker_v1.snapshot_project`,
     `O_NOFOLLOW`, rejecting symlinks, hardlinks, special files, and races).
  2. Read-only `/input` + private tmpfs `/work` execution inside
     `zero_ambient_namespace_launcher_v1.run_confined` (user + mount + net + PID
     + IPC + UTS namespaces, `no_new_privs`, dropped capabilities, rlimits,
     bounded `PROJECT_BRAIN_BROKER_FD`, zero ambient host env secrets).
     The caller's live `workspace_root` is NEVER mounted inside the worker.
  3. Parent-side staging (`repair_candidate_broker_v1.stage_project`), optional
     single-target + protected-test scope enforcement (`compare_candidate` +
     `acceptance_effect_request`), and parent-side `checker(stage_dir)` BEFORE
     any byte of `workspace_root` is touched.
  4. Race-checked atomic publication (`snapshot_project(workspace_root).digest ==
     before.digest` + `NamedTemporaryFile` + `fsync` + `os.replace`) ONLY when
     `publish=True` and every verification check succeeded.

Honesty note: consistent with `REPAIR_INDEPENDENT_REVIEW_REQUEST_20261102.md`,
`zero_ambient_namespace_launcher_v1` mounts host `/usr` read-only and has not
undergone separate hostile-code carrier certification (`carrier_qualified=False`).
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import stat
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import repair_candidate_broker_v1 as rcb
from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns

SCHEMA = "PROJECT_BRAIN_BROKERED_WORKSPACE_EXECUTION_V1"

_AVAILABILITY_CACHE: dict[tuple[int, int], bool] = {}

_WORKER_SCRIPT = r"""
import base64, hashlib, json, os, pathlib, shutil, socket, stat, subprocess, sys

req = json.loads(pathlib.Path('/input/request.json').read_text(encoding='utf-8'))
src_proj = pathlib.Path('/input/project')
work_proj = pathlib.Path('/work/project')
work_tmp = pathlib.Path('/work/tmp')
work_tmp.mkdir(parents=True, exist_ok=True)
shutil.copytree(src_proj, work_proj)

cmd = req['cmd']
timeout_s = float(req.get('timeout_s') or 15.0)
env = {'PATH': '/usr/bin:/bin', 'HOME': '/work/tmp', 'TMPDIR': '/work/tmp', 'PYTHONDONTWRITEBYTECODE': '1'}
if req.get('pythonpath_work'):
    env['PYTHONPATH'] = str(work_proj)

timed_out = False
try:
    proc = subprocess.run(
        cmd,
        cwd=str(work_proj),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=timeout_s,
    )
    rc = int(proc.returncode)
    out_b = (proc.stdout or b'')[-32768:]
    err_b = (proc.stderr or b'')[-32768:]
except subprocess.TimeoutExpired as exc:
    timed_out = True
    rc = -9
    out_b = (exc.stdout or b'')[-16384:] if isinstance(exc.stdout, bytes) else b''
    err_b = (exc.stderr or b'')[-16384:] if isinstance(exc.stderr, bytes) else b''

# Walk /work/project rejecting symlinks/special files and collect bounded delta vs /input/project
orig_hashes = req['orig_hashes']
after_files = {}
after_dirs = []
layout_error = None
for root_s, dirs, files in os.walk(work_proj, followlinks=False):
    dirs[:] = [d for d in sorted(dirs) if d != '__pycache__']
    root_p = pathlib.Path(root_s)
    rel_dir = root_p.relative_to(work_proj).as_posix()
    if rel_dir != '.':
        if root_p.is_symlink():
            layout_error = 'SYMLINK_DIR_CREATED'
            break
        after_dirs.append(rel_dir)
    for fn in sorted(files):
        if fn.endswith('.pyc'):
            continue
        fp = root_p / fn
        rel = fp.relative_to(work_proj).as_posix()
        try:
            st = os.lstat(fp)
        except OSError:
            layout_error = 'STAT_FAILED'
            break
        if not stat.S_ISREG(st.st_mode):
            layout_error = 'NON_REGULAR_FILE_CREATED'
            break
        if st.st_size > 2_000_000:
            layout_error = 'FILE_TOO_LARGE'
            break
        data = fp.read_bytes()
        h = hashlib.sha256(data).hexdigest()
        if orig_hashes.get(rel) != h:
            after_files[rel] = base64.b64encode(data).decode('ascii')
    if layout_error:
        break

present_set = set()
if not layout_error:
    for root_s, dirs, files in os.walk(work_proj, followlinks=False):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        root_p = pathlib.Path(root_s)
        for fn in files:
            if not fn.endswith('.pyc'):
                present_set.add((root_p / fn).relative_to(work_proj).as_posix())
deleted = sorted(set(orig_hashes) - present_set)

payload = {
    'rc': rc,
    'timed_out': timed_out,
    'stdout': out_b.decode('utf-8', errors='replace'),
    'stderr': err_b.decode('utf-8', errors='replace'),
    'layout_error': layout_error,
    'changed_or_created': after_files,
    'deleted': deleted,
    'after_dirs': sorted(after_dirs),
}
sock = socket.socket(fileno=int(os.environ['PROJECT_BRAIN_BROKER_FD']))
try:
    sock.sendall(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
finally:
    sock.close()
"""


def _python_in_chroot() -> str:
    for cand in ("/usr/bin/python3", "/bin/python3", sys.executable):
        if cand and (cand.startswith("/usr/") or cand.startswith("/bin/")) and os.path.isfile(cand):
            return cand
    return "/usr/bin/python3"


def namespace_broker_available(*, force_refresh: bool = False) -> bool:
    """Verify once per UID/GID that `zero_ambient_namespace_launcher_v1` can run a brokered worker."""
    key = (os.geteuid(), os.getegid())
    if not force_refresh and key in _AVAILABILITY_CACHE:
        return _AVAILABILITY_CACHE[key]
    py = _python_in_chroot()
    ok = False
    try:
        with tempfile.TemporaryDirectory(prefix="brain_ns_avail_") as td:
            inp = pathlib.Path(td) / "input"
            inp.mkdir()
            (inp / "probe.py").write_text(
                "import os,socket; s=socket.socket(fileno=int(os.environ['PROJECT_BRAIN_BROKER_FD'])); "
                "s.sendall(b'OK'); s.close()\n",
                encoding="utf-8",
            )
            res = ns.run_confined(
                {
                    "argv": [py, "-I", "/input/probe.py"],
                    "input_dir": str(inp),
                    "expose_null_device": True,
                    "limits": {
                        "pids": 16,
                        "memory_mb": 256,
                        "cpu_seconds": 5,
                        "wallclock_s": 10,
                        "scratch_mb": 16,
                        "max_file_mb": 2,
                        "nofile": 32,
                        "broker_max_bytes": 4096,
                    },
                }
            )
            ok = res.get("status") == "CHILD_EXITED" and res.get("returncode") == 0 and res.get("broker_payload") == b"OK"
    except Exception:
        ok = False
    _AVAILABILITY_CACHE[key] = ok
    return ok


def _atomic_publish_files(
    workspace_root: pathlib.Path,
    before: rcb.ProjectSnapshot,
    stage_dir: pathlib.Path,
    changed_rels: Sequence[str],
    deleted_rels: Sequence[str],
    created_dirs: Sequence[str],
) -> tuple[bool, str]:
    """Publish verified staged deltas into `workspace_root` iff `workspace_root` has not drifted."""
    try:
        current = rcb.snapshot_project(workspace_root)
    except rcb.CandidateDenied as exc:
        return False, f"SOURCE_CHANGED_BEFORE_PUBLISH:{exc}"
    if current.digest != before.digest:
        return False, "SOURCE_DRIFTED_DURING_EXECUTION"

    for d_rel in sorted(set(created_dirs)):
        rcb._relative(d_rel)
        (workspace_root / d_rel).mkdir(parents=True, exist_ok=True)

    for rel in sorted(set(changed_rels)):
        rcb._relative(rel)
        staged_file = stage_dir / rel
        data = staged_file.read_bytes()
        dest = workspace_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            return False, "DESTINATION_SYMLINK_DENIED"
        tmp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=dest.parent,
                prefix=".brain-pub-",
                delete=False,
            ) as handle:
                tmp_name = handle.name
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, dest)
            tmp_name = None
        finally:
            if tmp_name is not None:
                pathlib.Path(tmp_name).unlink(missing_ok=True)

    for rel in sorted(set(deleted_rels)):
        rcb._relative(rel)
        dest = workspace_root / rel
        if dest.is_symlink():
            return False, "DELETE_SYMLINK_DENIED"
        dest.unlink(missing_ok=True)
    return True, "PUBLISHED"


def _snapshot_allowing_cow_hardlinks(root: pathlib.Path) -> rcb.ProjectSnapshot:
    """Read-only snapshot helper ONLY for `publish=False` CoW sandboxes (`os.link`), still rejecting symlinks/special files."""
    if not root.is_dir() or root.is_symlink():
        raise rcb.CandidateDenied("PROJECT_ROOT_NOT_DIRECTORY")
    files: list[tuple[str, bytes]] = []
    dirs: list[str] = []
    for current, child_dirs, child_files in os.walk(root, followlinks=False):
        cur_p = pathlib.Path(current)
        if cur_p != root:
            rel_dir = cur_p.relative_to(root).as_posix()
            if cur_p.is_symlink():
                raise rcb.CandidateDenied("SYMLINK_DIRECTORY_REJECTED")
            if cur_p.name == "__pycache__":
                child_dirs[:] = []
                continue
            dirs.append(rel_dir)
        child_dirs[:] = [d for d in sorted(child_dirs) if d != "__pycache__"]
        for name in sorted(child_files):
            if name.endswith(".pyc"):
                continue
            fp = cur_p / name
            st = os.lstat(fp)
            if not stat.S_ISREG(st.st_mode):
                raise rcb.CandidateDenied("NON_REGULAR_FILE_REJECTED")
            data = fp.read_bytes()
            files.append((fp.relative_to(root).as_posix(), data))
    dirs_t = tuple(sorted(dirs))
    files_t = tuple(sorted(files))
    digest = rcb._digest(dirs_t, files_t)
    return rcb.ProjectSnapshot(
        origin=str(root),
        digest=digest,
        files=files_t,
        directories=dirs_t,
    )


def run_staged_confined_command(
    workspace_root: str | pathlib.Path,
    command: str | Sequence[str],
    *,
    checker: Callable[[pathlib.Path], bool] | None = None,
    publish: bool = False,
    target: str | None = None,
    protected_tests: tuple[str, ...] = (),
    timeout: int = 20,
    pythonpath_work: bool = True,
    allow_cow_hardlinks: bool = False,
    task_id: str = "staged-brokered-work",
    goal: str = "execute staged work",
    learning_mode: str = "off",
) -> dict[str, Any]:
    """Execute `command` on a staged copy inside `zero_ambient_namespace_launcher_v1`, never touching live `workspace_root` until verified."""
    ws = pathlib.Path(workspace_root).resolve()
    if not namespace_broker_available():
        return {
            "schema": SCHEMA,
            "ok": False,
            "confined": False,
            "carrier_qualified": False,
            "blocked": boundary.STATUS,
            "live_workspace_untouched": True,
        }

    try:
        if allow_cow_hardlinks and not publish:
            before = _snapshot_allowing_cow_hardlinks(ws)
        else:
            before = rcb.snapshot_project(ws)
    except rcb.CandidateDenied as exc:
        return {
            "schema": SCHEMA,
            "ok": False,
            "confined": False,
            "carrier_qualified": False,
            "blocked": f"WORKSPACE_SNAPSHOT_DENIED:{exc}",
            "live_workspace_untouched": True,
        }

    py = _python_in_chroot()
    if isinstance(command, str):
        cmd_list = ["/bin/sh", "-c", command]
    else:
        cmd_list = [py if i == 0 and tok == sys.executable else str(tok) for i, tok in enumerate(command)]

    with tempfile.TemporaryDirectory(prefix="brain_broker_outer_") as outer_tmp:
        outer = pathlib.Path(outer_tmp)
        inp = outer / "input"
        inp.mkdir()
        proj_stage_in = rcb.stage_project(before, staging_parent=inp)
        proj_in = inp / "project"
        os.replace(proj_stage_in, proj_in)

        orig_hashes = {
            rel: rcb._sha(data)
            for rel, data in before.files
        }
        (inp / "worker.py").write_text(_WORKER_SCRIPT, encoding="utf-8")
        (inp / "request.json").write_text(
            json.dumps(
                {
                    "cmd": cmd_list,
                    "timeout_s": max(1.0, float(timeout) - 2.0),
                    "orig_hashes": orig_hashes,
                    "pythonpath_work": bool(pythonpath_work),
                },
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        wall_s = max(3, min(600, int(timeout) + 3))
        cpu_s = max(2, min(300, int(timeout)))
        try:
            ns_res = ns.run_confined(
                {
                    "argv": [py, "-I", "/input/worker.py"],
                    "input_dir": str(inp),
                    "expose_null_device": True,
                    "expose_runtime_devices": True,
                    "limits": {
                        "pids": 64,
                        "memory_mb": 768,
                        "cpu_seconds": cpu_s,
                        "wallclock_s": wall_s,
                        "scratch_mb": 64,
                        "max_file_mb": 16,
                        "nofile": 64,
                        "broker_max_bytes": 4_000_000,
                    },
                }
            )
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "ok": False,
                "confined": False,
                "carrier_qualified": False,
                "blocked": f"NAMESPACE_LAUNCH_FAILED:{type(exc).__name__}",
                "live_workspace_untouched": True,
            }

        if ns_res.get("status") != "CHILD_EXITED" or ns_res.get("returncode") != 0:
            return {
                "schema": SCHEMA,
                "ok": False,
                "confined": ns_res.get("status") == "CHILD_EXITED",
                "carrier_qualified": False,
                "timed_out": ns_res.get("status") == "WALLCLOCK_LIMIT_EXCEEDED",
                "blocked": f"WORKER_STATUS:{ns_res.get('status')}",
                "live_workspace_untouched": True,
            }

        try:
            worker_data = json.loads((ns_res.get("broker_payload") or b"").decode("utf-8"))
        except Exception:
            return {
                "schema": SCHEMA,
                "ok": False,
                "confined": True,
                "carrier_qualified": False,
                "blocked": "BROKER_PAYLOAD_INVALID",
                "live_workspace_untouched": True,
            }

        if worker_data.get("layout_error"):
            return {
                "schema": SCHEMA,
                "ok": False,
                "confined": True,
                "carrier_qualified": False,
                "blocked": f"CANDIDATE_LAYOUT_DENIED:{worker_data['layout_error']}",
                "live_workspace_untouched": True,
            }

        # Reconstruct candidate in parent-owned private stage_dir for verification
        verify_parent = outer / "verify"
        verify_parent.mkdir()
        stage_dir = rcb.stage_project(before, staging_parent=verify_parent)

        changed_raw = worker_data.get("changed_or_created") or {}
        deleted_raw = worker_data.get("deleted") or []
        after_dirs_raw = worker_data.get("after_dirs") or []
        try:
            for d_rel in after_dirs_raw:
                rcb._relative(d_rel)
                (stage_dir / d_rel).mkdir(parents=True, exist_ok=True)
            for rel, b64 in changed_raw.items():
                rcb._relative(rel)
                raw_bytes = base64.b64decode(b64, validate=True)
                dest = stage_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw_bytes)
            for rel in deleted_raw:
                rcb._relative(rel)
                (stage_dir / rel).unlink(missing_ok=True)
            after = rcb.snapshot_project(stage_dir)
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "ok": False,
                "confined": True,
                "carrier_qualified": False,
                "blocked": f"STAGE_RECONSTRUCTION_DENIED:{type(exc).__name__}",
                "live_workspace_untouched": True,
            }

        effect_req: dict[str, Any] | None = None
        if target is not None and protected_tests:
            try:
                effect_req = rcb.acceptance_effect_request(
                    before,
                    after,
                    target=target,
                    protected_tests=tuple(protected_tests),
                    task_id=task_id,
                    goal=goal,
                    learning_mode="use" if learning_mode == "use" else "off",
                    mission_id="brokered-workspace-v1",
                    capsule_head_sha256=before.digest,
                    action_ref="staged_confined_command",
                )
            except rcb.CandidateDenied as exc:
                return {
                    "schema": SCHEMA,
                    "ok": False,
                    "confined": True,
                    "carrier_qualified": False,
                    "exit": int(worker_data.get("rc", -1)),
                    "stdout": str(worker_data.get("stdout") or ""),
                    "stderr": str(worker_data.get("stderr") or ""),
                    "blocked": f"CANDIDATE_SCOPE_DENIED:{exc}",
                    "live_workspace_untouched": True,
                }

        rc = int(worker_data.get("rc", -1))
        timed_out = bool(worker_data.get("timed_out"))
        passed_exec = rc == 0 and not timed_out
        if checker is not None:
            try:
                checked_ok = bool(passed_exec and checker(stage_dir))
            except Exception:
                checked_ok = False
        else:
            checked_ok = passed_exec

        published = False
        publish_status = "NOT_REQUESTED"
        if checked_ok and publish:
            published, publish_status = _atomic_publish_files(
                ws,
                before,
                stage_dir,
                list(changed_raw.keys()),
                list(deleted_raw),
                list(after_dirs_raw),
            )
            if not published:
                return {
                    "schema": SCHEMA,
                    "ok": False,
                    "confined": True,
                    "carrier_qualified": False,
                    "exit": rc,
                    "stdout": str(worker_data.get("stdout") or ""),
                    "stderr": str(worker_data.get("stderr") or ""),
                    "blocked": publish_status,
                    "live_workspace_untouched": True,
                }

        return {
            "schema": SCHEMA,
            "ok": checked_ok,
            "confined": True,
            "isolation_mode": "ZERO_AMBIENT_NAMESPACE_RO_INPUT_TMPFS_BROKER",
            "carrier_qualified": False,
            "exit": rc,
            "timed_out": timed_out,
            "stdout": str(worker_data.get("stdout") or ""),
            "stderr": str(worker_data.get("stderr") or ""),
            "before_sha256": before.digest,
            "after_sha256": after.digest,
            "changed_files": sorted(changed_raw.keys()),
            "published": published,
            "live_workspace_untouched": not published,
            "effect_request": effect_req,
            "blocked": None if checked_ok else ("TIMED_OUT" if timed_out else "CHECK_FAILED"),
        }
