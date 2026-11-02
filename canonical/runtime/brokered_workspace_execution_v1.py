#!/usr/bin/env python3
"""Staged read-only namespace + broker execution (`brokered_workspace_execution_v1`).

Replaces in-place `confine_v1` + `solve_v1.act` live-workspace mutation with a
staged broker pipeline built from existing repository primitives:

  1. Fast zero-copy read-only fast-path (`publish=False`, `checker=None`, `target=None`):
     mounts `workspace_root` directly at `/input` (`MS_RDONLY`, `nosuid`, `nodev`) inside
     `zero_ambient_namespace_launcher_v1.run_confined`, builds a `<0.5 ms` symlink view
     in private tmpfs `/work/project` (applying optional in-memory `candidate_overrides`
     without touching `workspace_root`), detects any in-worker file mutations via `lstat`,
     and verifies post-execution that `workspace_root` metadata/inodes never changed.
  2. Full four-phase publication pipeline (`publish=True`, `checker!=None`, or `target!=None`):
     `repair_candidate_broker_v1.snapshot_project` -> confined `/input` + `/work` worker ->
     parent-side `stage_project` + `acceptance_effect_request` + `checker(stage_dir)` ->
     race-checked atomic publication (`NamedTemporaryFile` + `fsync` + `os.replace`).

Honesty note: consistent with `REPAIR_INDEPENDENT_REVIEW_REQUEST_20261102.md`,
`zero_ambient_namespace_launcher_v1` mounts host `/usr` read-only and has not
undergone separate hostile-code carrier certification (`carrier_qualified=False`).
"""
from __future__ import annotations

import base64
import hashlib
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

_FAST_RO_WORKER_SCRIPT = r"""
import base64, hashlib, json, os, pathlib, shutil, socket, stat, subprocess, sys

req = json.loads(sys.argv[1])
src_proj = pathlib.Path('/input')
work_proj = pathlib.Path('/work/project')
work_tmp = pathlib.Path('/work/tmp')
work_proj.mkdir(parents=True, exist_ok=True)
work_tmp.mkdir(parents=True, exist_ok=True)

overrides_raw = req.get('overrides_b64') or {}
overrides = {k: base64.b64decode(v) for k, v in overrides_raw.items()}
expected_files = set()
copied_hashes = {}

for root_s, dirs, files in os.walk(src_proj, followlinks=False):
    dirs[:] = [d for d in sorted(dirs) if d != '__pycache__']
    root_p = pathlib.Path(root_s)
    rel_dir = root_p.relative_to(src_proj).as_posix()
    if rel_dir != '.':
        (work_proj / rel_dir).mkdir(parents=True, exist_ok=True)
    for fn in sorted(files):
        if fn.endswith('.pyc'):
            continue
        src_fp = root_p / fn
        rel = src_fp.relative_to(src_proj).as_posix()
        expected_files.add(rel)
        dest = work_proj / rel
        if rel in overrides:
            dest.write_bytes(overrides[rel])
            copied_hashes[rel] = hashlib.sha256(overrides[rel]).hexdigest()
        elif overrides:
            # When overrides are active, materialize regular files in tmpfs RAM so ESM/compiler realpath stays in /work/project
            data = src_fp.read_bytes()
            dest.write_bytes(data)
            copied_hashes[rel] = hashlib.sha256(data).hexdigest()
        else:
            os.symlink('/input/' + rel, dest)

for rel, data in overrides.items():
    if rel not in expected_files:
        expected_files.add(rel)
        dest = work_proj / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        copied_hashes[rel] = hashlib.sha256(data).hexdigest()

cmd = req['cmd']
timeout_s = float(req.get('timeout_s') or 15.0)
env = {
    'PATH': '/usr/local/bin:/usr/bin:/bin',
    'HOME': '/work/tmp',
    'TMPDIR': '/work/tmp',
    'PYTHONDONTWRITEBYTECODE': '1',
}
if req.get('pythonpath_work'):
    env['PYTHONPATH'] = str(work_proj)

timed_out = False
# Single-process fast path when `cmd` is a direct Python `-c` or script invocation (eliminates 2nd cold Python spawn)
inproc_mode = None
inproc_target = None
if len(cmd) >= 2 and os.path.basename(cmd[0]).startswith('python'):
    rem = list(cmd[1:])
    while rem and rem[0] in ('-I', '-B', '-S', '-u'):
        rem.pop(0)
    if len(rem) == 2 and rem[0] == '-c':
        inproc_mode, inproc_target = 'code', rem[1]
    elif len(rem) == 1 and not rem[0].startswith('-') and rem[0].endswith('.py'):
        inproc_mode, inproc_target = 'file', rem[0]

if inproc_mode is not None:
    import contextlib, io, runpy, signal
    if inproc_mode == 'file' and '-S' not in cmd[1:]:
        import site
        site.main()
    out_io, err_io = io.StringIO(), io.StringIO()
    old_cwd = os.getcwd()
    old_argv = list(sys.argv)
    old_path = list(sys.path)
    def _alarm_handler(_s, _f):
        raise TimeoutError('INPROC_TIMEOUT')
    prev_sig = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, max(0.5, timeout_s))
    rc = 0
    try:
        os.chdir(str(work_proj))
        if req.get('pythonpath_work'):
            sys.path.insert(0, str(work_proj))
        sys.argv = [inproc_target if inproc_mode == 'file' else '-c']
        with contextlib.redirect_stdout(out_io), contextlib.redirect_stderr(err_io):
            if inproc_mode == 'code':
                exec(compile(inproc_target, '<string>', 'exec'), {'__name__': '__main__'})
            else:
                runpy.run_path(str(work_proj / inproc_target), run_name='__main__')
    except TimeoutError:
        timed_out = True
        rc = -9
    except SystemExit as exc:
        code = exc.code
        rc = 0 if code is None else (int(code) if isinstance(code, int) else 1)
    except BaseException:
        import traceback
        traceback.print_exc(file=err_io)
        rc = 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, prev_sig)
        sys.argv = old_argv
        sys.path[:] = old_path
        os.chdir(old_cwd)
    out_b = out_io.getvalue().encode('utf-8', errors='replace')[-32768:]
    err_b = err_io.getvalue().encode('utf-8', errors='replace')[-32768:]
else:
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

changed_files = []
present_files = set()
layout_error = None
for root_s, dirs, files in os.walk(work_proj, followlinks=False):
    dirs[:] = [d for d in sorted(dirs) if d != '__pycache__']
    root_p = pathlib.Path(root_s)
    if root_p != work_proj and root_p.is_symlink():
        layout_error = 'SYMLINK_DIR_CREATED'
        break
    for fn in sorted(files):
        if fn.endswith('.pyc'):
            continue
        fp = root_p / fn
        rel = fp.relative_to(work_proj).as_posix()
        present_files.add(rel)
        st = os.lstat(fp)
        if rel in copied_hashes:
            if not stat.S_ISREG(st.st_mode):
                layout_error = 'NON_REGULAR_FILE_CREATED'
                break
            if hashlib.sha256(fp.read_bytes()).hexdigest() != copied_hashes[rel]:
                changed_files.append(rel)
        else:
            if stat.S_ISLNK(st.st_mode):
                if os.readlink(fp) != '/input/' + rel:
                    layout_error = 'SYMLINK_REDIRECTED'
                    break
            elif stat.S_ISREG(st.st_mode):
                changed_files.append(rel)
            else:
                layout_error = 'NON_REGULAR_FILE_CREATED'
                break
    if layout_error:
        break

deleted = sorted(expected_files - present_files)
payload = {
    'rc': rc,
    'timed_out': timed_out,
    'stdout': out_b.decode('utf-8', errors='replace'),
    'stderr': err_b.decode('utf-8', errors='replace'),
    'layout_error': layout_error,
    'changed_files': sorted(set(changed_files) | set(deleted)),
    'deleted': deleted,
}
sock = socket.socket(fileno=int(os.environ['PROJECT_BRAIN_BROKER_FD']))
try:
    sock.sendall(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
finally:
    sock.close()
"""

_WORKER_SCRIPT = r"""
import base64, hashlib, json, os, pathlib, shutil, socket, stat, subprocess, sys

req = json.loads(pathlib.Path('/input/request.json').read_text(encoding='utf-8'))
src_proj = pathlib.Path('/input/project')
work_proj = pathlib.Path('/work/project')
work_tmp = pathlib.Path('/work/tmp')
work_tmp.mkdir(parents=True, exist_ok=True)
shutil.copytree(src_proj, work_proj)

for rel, b64 in (req.get('overrides_b64') or {}).items():
    dest = work_proj / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(base64.b64decode(b64))

cmd = req['cmd']
timeout_s = float(req.get('timeout_s') or 15.0)
env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/work/tmp', 'TMPDIR': '/work/tmp', 'PYTHONDONTWRITEBYTECODE': '1'}
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


def _fast_stat_manifest(root: pathlib.Path, *, allow_cow_hardlinks: bool) -> tuple[str, tuple[tuple[str, int, int, int], ...]]:
    """O(entries) metadata manifest rejecting symlinks/special files without copying or reading file contents."""
    if not root.is_dir() or root.is_symlink():
        raise rcb.CandidateDenied("PROJECT_ROOT_NOT_DIRECTORY")
    rows: list[tuple[str, int, int, int]] = []
    h = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    for current, child_dirs, child_files in os.walk(root, followlinks=False):
        cur_p = pathlib.Path(current)
        if cur_p != root:
            if cur_p.is_symlink():
                raise rcb.CandidateDenied("SYMLINK_DIRECTORY_REJECTED")
            if cur_p.name == "__pycache__":
                child_dirs[:] = []
                continue
            rel_dir = cur_p.relative_to(root).as_posix()
            h.update(f"D:{rel_dir}\n".encode("utf-8"))
        child_dirs[:] = [d for d in sorted(child_dirs) if d != "__pycache__"]
        for name in sorted(child_files):
            if name.endswith(".pyc"):
                continue
            fp = cur_p / name
            st = os.lstat(fp)
            if not stat.S_ISREG(st.st_mode):
                raise rcb.CandidateDenied("NON_REGULAR_FILE_REJECTED")
            if not allow_cow_hardlinks and st.st_nlink > 1:
                raise rcb.CandidateDenied("HARDLINKED_SOURCE_REJECTED")
            if st.st_size > 2_000_000:
                raise rcb.CandidateDenied("PROJECT_FILE_TOO_LARGE")
            file_count += 1
            total_bytes += int(st.st_size)
            if file_count > 1000 or total_bytes > 16_000_000:
                raise rcb.CandidateDenied("PROJECT_LIMIT_EXCEEDED")
            rel = fp.relative_to(root).as_posix()
            row = (rel, int(st.st_ino), int(st.st_mtime_ns), int(st.st_size))
            rows.append(row)
            h.update(f"F:{rel}:{st.st_ino}:{st.st_mtime_ns}:{st.st_size}\n".encode("utf-8"))
    return h.hexdigest(), tuple(rows)


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


def _normalize_overrides(candidate_overrides: Mapping[str, bytes | str] | None) -> dict[str, str]:
    if not candidate_overrides:
        return {}
    out: dict[str, str] = {}
    for rel, val in candidate_overrides.items():
        clean_rel = str(rcb._relative(rel))
        raw = val.encode("utf-8") if isinstance(val, str) else bytes(val)
        if len(raw) > 2_000_000:
            raise rcb.CandidateDenied("OVERRIDE_FILE_TOO_LARGE")
        out[clean_rel] = base64.b64encode(raw).decode("ascii")
    return out


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
    candidate_overrides: Mapping[str, bytes | str] | None = None,
    task_id: str = "staged-brokered-work",
    goal: str = "execute staged work",
    learning_mode: str = "off",
) -> dict[str, Any]:
    """Execute `command` inside `zero_ambient_namespace_launcher_v1`, never touching live `workspace_root` until verified."""
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
        overrides_b64 = _normalize_overrides(candidate_overrides)
    except rcb.CandidateDenied as exc:
        return {
            "schema": SCHEMA,
            "ok": False,
            "confined": False,
            "carrier_qualified": False,
            "blocked": f"CANDIDATE_OVERRIDE_DENIED:{exc}",
            "live_workspace_untouched": True,
        }

    py = _python_in_chroot()
    if isinstance(command, str):
        cmd_list = ["/bin/sh", "-c", command]
    else:
        cmd_list = [py if i == 0 and tok == sys.executable else str(tok) for i, tok in enumerate(command)]

    wall_s = max(3, min(600, int(timeout) + 3))
    cpu_s = max(2, min(300, int(timeout)))

    # Zero-copy read-only `/input` fast path when no host publication / parent stage_dir checker is needed
    override_payload_bytes = sum(len(v) for v in overrides_b64.values())
    if not publish and checker is None and target is None and override_payload_bytes <= 49_152:
        try:
            before_digest, before_rows = _fast_stat_manifest(ws, allow_cow_hardlinks=allow_cow_hardlinks)
        except rcb.CandidateDenied as exc:
            return {
                "schema": SCHEMA,
                "ok": False,
                "confined": False,
                "carrier_qualified": False,
                "blocked": f"WORKSPACE_SNAPSHOT_DENIED:{exc}",
                "live_workspace_untouched": True,
            }
        req_json = json.dumps(
            {
                "cmd": cmd_list,
                "timeout_s": max(1.0, float(timeout) - 2.0),
                "pythonpath_work": bool(pythonpath_work),
                "overrides_b64": overrides_b64,
            },
            separators=(",", ":"),
        )
        try:
            need_rt_devs = any("node" in os.path.basename(tok) for tok in cmd_list) or cmd_list[:2] == ["/bin/sh", "-c"]
            ns_res = ns.run_confined(
                {
                    "argv": [py, "-I", "-S", "-c", _FAST_RO_WORKER_SCRIPT, req_json],
                    "input_dir": str(ws),
                    "expose_null_device": True,
                    "expose_runtime_devices": need_rt_devs,
                    "limits": {
                        "pids": 64,
                        "memory_mb": 768,
                        "cpu_seconds": cpu_s,
                        "wallclock_s": wall_s,
                        "scratch_mb": 64,
                        "max_file_mb": 16,
                        "nofile": 64,
                        "broker_max_bytes": 1_000_000,
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
        try:
            after_ws_digest, after_ws_rows = _fast_stat_manifest(ws, allow_cow_hardlinks=allow_cow_hardlinks)
        except rcb.CandidateDenied as exc:
            return {
                "schema": SCHEMA,
                "ok": False,
                "confined": True,
                "carrier_qualified": False,
                "blocked": f"POST_EXEC_WORKSPACE_CHECK_FAILED:{exc}",
                "live_workspace_untouched": False,
            }
        untouched = after_ws_digest == before_digest and after_ws_rows == before_rows
        rc = int(worker_data.get("rc", -1))
        timed_out = bool(worker_data.get("timed_out"))
        checked_ok = untouched and rc == 0 and not timed_out
        changed_files = list(worker_data.get("changed_files") or [])
        after_sha = (
            before_digest
            if not changed_files and not overrides_b64
            else hashlib.sha256(
                f"{before_digest}:{json.dumps(overrides_b64, sort_keys=True)}:{','.join(changed_files)}".encode("utf-8")
            ).hexdigest()
        )
        return {
            "schema": SCHEMA,
            "ok": checked_ok,
            "confined": True,
            "isolation_mode": "ZERO_COPY_RO_INPUT_SYMLINK_TMPFS_BROKER",
            "carrier_qualified": False,
            "exit": rc,
            "timed_out": timed_out,
            "stdout": str(worker_data.get("stdout") or ""),
            "stderr": str(worker_data.get("stderr") or ""),
            "before_sha256": before_digest,
            "after_sha256": after_sha,
            "changed_files": changed_files,
            "published": False,
            "live_workspace_untouched": untouched,
            "effect_request": None,
            "blocked": None if checked_ok else ("SOURCE_DRIFTED_DURING_EXECUTION" if not untouched else ("TIMED_OUT" if timed_out else "CHECK_FAILED")),
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
        for rel, b64 in overrides_b64.items():
            orig_hashes[rel] = rcb._sha(base64.b64decode(b64))

        (inp / "worker.py").write_text(_WORKER_SCRIPT, encoding="utf-8")
        (inp / "request.json").write_text(
            json.dumps(
                {
                    "cmd": cmd_list,
                    "timeout_s": max(1.0, float(timeout) - 2.0),
                    "orig_hashes": orig_hashes,
                    "pythonpath_work": bool(pythonpath_work),
                    "overrides_b64": overrides_b64,
                },
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

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

        verify_parent = outer / "verify"
        verify_parent.mkdir()
        stage_dir = rcb.stage_project(before, staging_parent=verify_parent)

        changed_raw = worker_data.get("changed_or_created") or {}
        deleted_raw = worker_data.get("deleted") or []
        after_dirs_raw = worker_data.get("after_dirs") or []
        try:
            for rel, b64 in overrides_b64.items():
                dest = stage_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(base64.b64decode(b64, validate=True))
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
            all_changed = sorted(set(changed_raw.keys()) | set(overrides_b64.keys()))
            published, publish_status = _atomic_publish_files(
                ws,
                before,
                stage_dir,
                all_changed,
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
