from __future__ import annotations

import base64
import json
import math
import os
import pathlib
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_ROOT3_PDF_RASTER_TEMP_EXECUTOR_V1"
EFFECT_CLASS = "TEMPORARY_FILESYSTEM_TRANSFORM"
SUPPORTED_SITE = (
    "canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",
    29,
    "subprocess.run",
)
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_WRAPPER = r"""
import base64,json,os,subprocess,sys
spec=json.loads(base64.urlsafe_b64decode(sys.argv[1].encode("ascii")).decode("utf-8"))
try:
    p=subprocess.run(
        spec["argv"],
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=spec["timeout"],
        check=False,
    )
    out={
        "timed_out":False,
        "returncode":int(p.returncode),
        "stdout_b64":base64.b64encode(p.stdout or b"").decode("ascii"),
        "stderr_b64":base64.b64encode(p.stderr or b"").decode("ascii"),
    }
except subprocess.TimeoutExpired as exc:
    out={
        "timed_out":True,
        "returncode":None,
        "stdout_b64":base64.b64encode(exc.output or b"").decode("ascii"),
        "stderr_b64":base64.b64encode(exc.stderr or b"").decode("ascii"),
    }
fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"])
os.write(fd,(json.dumps(out,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8"))
"""

_SETUP = r"""set -euo pipefail
ROOT="$1"; INPUT="$2"; OUTPUT="$3"; BROKER="$4"; MEM_KB="$5"; CPU_S="$6"; FILE_KB="$7"; NOFILE="$8"; PIDS="$9"; SCRATCH_MB="${10}"; shift 10
mount --make-rprivate /
mount -t tmpfs -o size=64m,nosuid,nodev tmpfs "$ROOT"
mkdir -p "$ROOT/usr" "$ROOT/bin" "$ROOT/lib" "$ROOT/lib64" "$ROOT/tmp" "$ROOT/work" "$ROOT/input" "$ROOT/output"
for d in /usr /bin /lib /lib64; do
  [ -e "$d" ] || continue
  base="${d#/}"
  if [ -L "$d" ]; then rm -rf "$ROOT/$base"; ln -s "$(readlink "$d")" "$ROOT/$base"; fi
done
mount --bind "$ROOT" "$ROOT"
mount -o remount,bind,ro "$ROOT"
for d in /usr /bin /lib /lib64; do
  [ -e "$d" ] || continue
  [ -L "$d" ] && continue
  mount --bind "$d" "$ROOT$d"
  mount -o remount,bind,ro,nosuid,nodev "$ROOT$d"
done
mount --bind "$INPUT" "$ROOT/input"
mount -o remount,bind,ro,nosuid,nodev "$ROOT/input"
mount --bind "$OUTPUT" "$ROOT/output"
mount -o remount,bind,rw,nosuid,nodev,noexec "$ROOT/output"
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev,noexec tmpfs "$ROOT/tmp"
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev tmpfs "$ROOT/work"
IP_BIN="$(command -v ip)"; CHROOT_BIN="$(command -v chroot)"
"$IP_BIN" link set lo up
ulimit -t "$CPU_S"; ulimit -v "$MEM_KB"; ulimit -f "$FILE_KB"; ulimit -n "$NOFILE"; ulimit -u "$PIDS"
exec "$CHROOT_BIN" "$ROOT" /usr/bin/env -i PATH=/usr/bin:/bin HOME=/tmp PROJECT_BRAIN_BROKER_FD="$BROKER" "$@"
"""


class PdfRasterTempDenied(PermissionError):
    pass


def _inside_mounts(path: pathlib.Path) -> list[str]:
    target = str(path.resolve())
    hits: list[str] = []
    try:
        raw = pathlib.Path("/proc/self/mountinfo").read_text()
    except Exception as exc:
        raise PdfRasterTempDenied("MOUNTINFO_UNAVAILABLE") from exc
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        mountpoint = parts[4].replace("\\040", " ")
        try:
            mp = str(pathlib.Path(mountpoint).resolve())
        except Exception:
            continue
        if mp != target and mp.startswith(target.rstrip("/") + "/"):
            hits.append(mp)
    return sorted(set(hits))


def _path(value: Any) -> pathlib.Path:
    try:
        return pathlib.Path(os.fspath(value)).resolve()
    except Exception as exc:
        raise PdfRasterTempDenied("PATH_INVALID") from exc


def _resolve_pdftoppm(raw: Any) -> str:
    token = str(raw)
    if pathlib.Path(token).name != "pdftoppm":
        raise PdfRasterTempDenied("EXECUTABLE_NOT_PDFTOPPM")
    resolved = token if os.path.isabs(token) else shutil.which(token)
    if not resolved:
        raise PdfRasterTempDenied("PDFTOPPM_UNAVAILABLE")
    p = pathlib.Path(resolved).resolve()
    if not (str(p).startswith("/usr/") or str(p).startswith("/bin/")):
        raise PdfRasterTempDenied("PDFTOPPM_OUTSIDE_SYSTEM_MOUNTS")
    return str(p)


def _site(context: Mapping[str, Any]) -> tuple[str, int, str]:
    callsite = context.get("callsite")
    if not isinstance(callsite, Mapping):
        raise PdfRasterTempDenied("CALLSITE_MISSING")
    try:
        key = (
            str(callsite.get("module_path") or ""),
            int(callsite.get("lineno") or 0),
            str(callsite.get("process_api") or ""),
        )
    except Exception as exc:
        raise PdfRasterTempDenied("CALLSITE_INVALID") from exc
    if key != SUPPORTED_SITE:
        raise PdfRasterTempDenied("TEMP_TRANSFORM_CALLSITE_NOT_SUPPORTED:" + repr(key))
    return key


def _validate_output_dir(prefix: pathlib.Path) -> pathlib.Path:
    out_dir = prefix.parent
    tmp_root = pathlib.Path(tempfile.gettempdir()).resolve()
    try:
        out_dir.relative_to(tmp_root)
    except ValueError as exc:
        raise PdfRasterTempDenied("OUTPUT_DIR_NOT_SYSTEM_TEMP") from exc
    if not out_dir.name.startswith("project-brain-ocr-"):
        raise PdfRasterTempDenied("OUTPUT_DIR_PREFIX_INVALID")
    if prefix.name != "page":
        raise PdfRasterTempDenied("OUTPUT_PREFIX_MUST_BE_PAGE")
    if not out_dir.is_dir() or out_dir.is_symlink():
        raise PdfRasterTempDenied("OUTPUT_DIR_INVALID")
    if _inside_mounts(out_dir):
        raise PdfRasterTempDenied("OUTPUT_DIR_HAS_NESTED_MOUNTS")
    entries = list(out_dir.iterdir())
    if entries:
        raise PdfRasterTempDenied("OUTPUT_DIR_MUST_BE_EMPTY_BEFORE_RASTERIZATION")
    try:
        if out_dir.stat().st_uid != os.geteuid():
            raise PdfRasterTempDenied("OUTPUT_DIR_OWNER_MISMATCH")
    except OSError as exc:
        raise PdfRasterTempDenied("OUTPUT_DIR_STAT_FAILED") from exc
    return out_dir


def _prepare(context: Mapping[str, Any]) -> dict[str, Any]:
    if context.get("effect_class") != EFFECT_CLASS:
        raise PdfRasterTempDenied("EFFECT_CLASS_MISMATCH")
    _site(context)
    if context.get("api") != "subprocess.run":
        raise PdfRasterTempDenied("PROCESS_API_NOT_SUPPORTED")
    args = context.get("args")
    if not isinstance(args, (tuple, list)) or len(args) != 1:
        raise PdfRasterTempDenied("COMMAND_POSITIONAL_SHAPE_INVALID")
    command = args[0]
    if not isinstance(command, (tuple, list)) or len(command) != 10:
        raise PdfRasterTempDenied("PDFTOPPM_ARGV_SHAPE_INVALID")
    argv = [os.fspath(x) if isinstance(x, os.PathLike) else str(x) for x in command]
    if argv[1] != "-f" or argv[2] != "1" or argv[3] != "-l" or argv[5] != "-r" or argv[7] != "-png":
        raise PdfRasterTempDenied("PDFTOPPM_OPTIONS_INVALID")
    try:
        max_pages = int(argv[4])
        dpi = int(argv[6])
    except Exception as exc:
        raise PdfRasterTempDenied("PDFTOPPM_NUMERIC_OPTIONS_INVALID") from exc
    if not (1 <= max_pages <= 500):
        raise PdfRasterTempDenied("MAX_PAGES_OUT_OF_RANGE")
    if not (72 <= dpi <= 600):
        raise PdfRasterTempDenied("DPI_OUT_OF_RANGE")

    exe = _resolve_pdftoppm(argv[0])
    src = _path(argv[8])
    prefix = _path(argv[9])
    if not src.is_file():
        raise PdfRasterTempDenied("PDF_INPUT_MISSING")
    try:
        if src.read_bytes()[:5] != b"%PDF-":
            raise PdfRasterTempDenied("PDF_MAGIC_INVALID")
    except OSError as exc:
        raise PdfRasterTempDenied("PDF_INPUT_READ_FAILED") from exc

    input_dir = src.parent
    if _inside_mounts(input_dir):
        raise PdfRasterTempDenied("INPUT_DIR_HAS_NESTED_MOUNTS")
    output_dir = _validate_output_dir(prefix)

    kwargs = dict(context.get("kwargs") or {})
    if kwargs.get("shell", False):
        raise PdfRasterTempDenied("SHELL_FORBIDDEN")
    if kwargs.get("env") is not None:
        raise PdfRasterTempDenied("CUSTOM_ENV_FORBIDDEN")
    if kwargs.get("input") is not None or kwargs.get("stdin") not in (None, subprocess.DEVNULL):
        raise PdfRasterTempDenied("STDIN_OR_INPUT_FORBIDDEN")
    if kwargs.get("capture_output") is not True:
        raise PdfRasterTempDenied("CAPTURE_OUTPUT_REQUIRED")
    if not (kwargs.get("text") is True or kwargs.get("universal_newlines") is True or kwargs.get("encoding")):
        raise PdfRasterTempDenied("TEXT_MODE_REQUIRED")
    timeout = float(kwargs.get("timeout") or 180)
    if not (0 < timeout <= 300):
        raise PdfRasterTempDenied("TIMEOUT_OUT_OF_RANGE")

    inner = [
        exe,
        "-f", "1",
        "-l", str(max_pages),
        "-r", str(dpi),
        "-png",
        "/input/" + src.name,
        "/output/page",
    ]
    spec = {"argv": inner, "timeout": timeout}
    encoded = base64.urlsafe_b64encode(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return {
        "original_argv": argv,
        "kwargs": kwargs,
        "timeout": timeout,
        "input_dir": input_dir,
        "output_dir": output_dir,
        "inner_argv": inner,
        "wrapper_argv": ["/usr/bin/python3", "-I", "-c", _WRAPPER, encoded],
    }


def _run_confined(prepared: Mapping[str, Any], popen_impl: Callable[..., Any]) -> dict[str, Any]:
    required = ["unshare", "mount", "chroot", "setpriv", "ip", "bash", "env"]
    resolved = {name: shutil.which(name) for name in required}
    missing = [name for name, value in resolved.items() if not value]
    if missing:
        raise PdfRasterTempDenied("HOST_PRIMITIVE_MISSING:" + ",".join(missing))

    root = tempfile.mkdtemp(prefix="brain-pdf-raster-ns-")
    host_uid = os.geteuid()
    host_gid = os.getegid()
    if host_uid == 0:
        host_uid = 65534
        host_gid = 65534
        os.chown(root, host_uid, host_gid)

    parent, child = socket.socketpair()
    broker: list[bytes] = []
    overflow = [False]
    broker_max = 1_000_000

    def reader() -> None:
        total = 0
        try:
            while True:
                chunk = parent.recv(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > broker_max:
                    overflow[0] = True
                    try:
                        parent.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    break
                broker.append(chunk)
        except OSError:
            pass

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    timeout = float(prepared["timeout"])
    cmd = [
        resolved["unshare"], "--user", "--map-root-user", "--mount", "--net",
        "--pid", "--fork", "--ipc", "--uts",
        resolved["bash"], "-c", _SETUP, "_",
        root,
        str(prepared["input_dir"]),
        str(prepared["output_dir"]),
        str(child.fileno()),
        str(2048 * 1024),
        str(min(max(int(math.ceil(timeout)), 1), 300)),
        str(1024 * 1024),
        "64",
        "64",
        "128",
        resolved["setpriv"], "--no-new-privs", "--bounding-set=-all",
        "--inh-caps=-all", "--ambient-caps=-all",
        resolved["env"], "-i", "PATH=/usr/bin:/bin", "HOME=/tmp",
        "PYTHONDONTWRITEBYTECODE=1",
        "PROJECT_BRAIN_BROKER_FD=" + str(child.fileno()),
        *prepared["wrapper_argv"],
    ]
    popen_kw = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "pass_fds": (child.fileno(),),
        "env": {"PYTHONDONTWRITEBYTECODE": "1"},
        "start_new_session": True,
    }
    if os.geteuid() == 0:
        popen_kw.update(user=host_uid, group=host_gid, extra_groups=[])

    timed_out = False
    try:
        proc = popen_impl(cmd, **popen_kw)
        child.close()
        try:
            rc = proc.wait(timeout=timeout + 10)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, 9)
            except ProcessLookupError:
                pass
            rc = proc.wait(timeout=5)
        th.join(timeout=2)
    finally:
        try:
            child.close()
        except OSError:
            pass
        try:
            parent.close()
        except OSError:
            pass
        shutil.rmtree(root, ignore_errors=True)

    if timed_out:
        raise subprocess.TimeoutExpired(prepared["original_argv"], timeout)
    if overflow[0]:
        raise PdfRasterTempDenied("BROKER_OUTPUT_LIMIT_EXCEEDED")
    if rc != 0:
        raise PdfRasterTempDenied("CONFINEMENT_WRAPPER_FAILED:" + str(rc))
    try:
        result = json.loads(b"".join(broker).decode("utf-8"))
    except Exception as exc:
        raise PdfRasterTempDenied("BROKER_PAYLOAD_INVALID") from exc
    return result


def _validate_outputs(output_dir: pathlib.Path) -> list[pathlib.Path]:
    entries = sorted(output_dir.iterdir())
    if not entries:
        raise PdfRasterTempDenied("PDF_RASTERIZE_NO_PAGES")
    for p in entries:
        if p.is_symlink() or not p.is_file():
            raise PdfRasterTempDenied("UNEXPECTED_OUTPUT_ENTRY:" + p.name)
        if not p.name.startswith("page-") or p.suffix.lower() != ".png":
            raise PdfRasterTempDenied("UNEXPECTED_OUTPUT_NAME:" + p.name)
        raw = p.read_bytes()
        if not raw.startswith(PNG_MAGIC):
            raise PdfRasterTempDenied("OUTPUT_NOT_PNG:" + p.name)
    return entries


def make_executor(*, popen_impl: Callable[..., Any]) -> Callable[[Mapping[str, Any]], Any]:
    if not callable(popen_impl):
        raise TypeError("POPEN_IMPL_NOT_CALLABLE")

    def execute(context: Mapping[str, Any]) -> subprocess.CompletedProcess:
        prepared = _prepare(context)
        result = _run_confined(prepared, popen_impl)
        if result.get("timed_out"):
            raise subprocess.TimeoutExpired(
                prepared["original_argv"],
                prepared["timeout"],
                output=base64.b64decode(result.get("stdout_b64") or ""),
                stderr=base64.b64decode(result.get("stderr_b64") or ""),
            )
        stdout_b = base64.b64decode(result.get("stdout_b64") or "")
        stderr_b = base64.b64decode(result.get("stderr_b64") or "")
        kwargs = prepared["kwargs"]
        encoding = kwargs.get("encoding") or "utf-8"
        errors = kwargs.get("errors") or "strict"
        cp = subprocess.CompletedProcess(
            args=prepared["original_argv"],
            returncode=int(result["returncode"]),
            stdout=stdout_b.decode(encoding, errors=errors),
            stderr=stderr_b.decode(encoding, errors=errors),
        )
        if cp.returncode == 0:
            _validate_outputs(prepared["output_dir"])
        return cp

    return execute
