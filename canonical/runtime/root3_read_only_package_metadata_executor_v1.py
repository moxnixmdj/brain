from __future__ import annotations

import glob
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_ROOT3_READ_ONLY_PACKAGE_METADATA_EXECUTOR_V1"
EFFECT_CLASS = "READ_ONLY_DECLARED_QUERY"

SUPPORTED = {
    ("canonical/runtime/astra_runtime.py", 918, "subprocess.run"): "APT_SHOW_BOUND",
    ("canonical/runtime/astra_runtime.py", 940, "subprocess.run"): "DPKG_QUERY_VERSION",
    ("canonical/runtime/capability_discovery.py", 267, "subprocess.run"): "APT_SEARCH",
    ("canonical/runtime/capability_discovery.py", 359, "subprocess.run"): "APT_POLICY",
    ("canonical/runtime/capability_discovery.py", 368, "subprocess.run"): "APT_SHOW_DISCOVERY",
    ("canonical/runtime/capability_discovery.py", 428, "subprocess.run"): "APT_INDEX_TARGETS_FILES",
    ("canonical/runtime/capability_discovery.py", 446, "subprocess.run"): "APT_HELPER_CAT",
    ("canonical/runtime/capability_discovery.py", 468, "subprocess.run"): "APT_DUMPAVAIL",
    ("canonical/runtime/capability_discovery.py", 581, "subprocess.run"): "APT_INDEX_TARGETS_CONTENTS",
    ("canonical/runtime/capability_discovery.py", 605, "subprocess.Popen"): "APT_HELPER_STREAM",
}

READ_ONLY_METADATA_ROOTS = (
    "/etc/apt",
    "/etc/dpkg",
    "/var/lib/apt",
    "/var/lib/dpkg",
    "/var/cache/apt",
)

_SETUP = r"""set -euo pipefail
ROOT="$1"; shift
mount --make-rprivate /
mount -t tmpfs -o size=64m,nosuid,nodev tmpfs "$ROOT"
mkdir -p "$ROOT/usr" "$ROOT/bin" "$ROOT/lib" "$ROOT/lib64" "$ROOT/tmp" "$ROOT/work" "$ROOT/etc/apt" "$ROOT/etc/dpkg" "$ROOT/var/lib/apt" "$ROOT/var/lib/dpkg" "$ROOT/var/cache/apt"
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
for d in /etc/apt /etc/dpkg /var/lib/apt /var/lib/dpkg /var/cache/apt; do
  [ -e "$d" ] || continue
  mount --bind "$d" "$ROOT$d"
  mount -o remount,bind,ro,nosuid,nodev,noexec "$ROOT$d"
done
mount -t tmpfs -o size=32m,nosuid,nodev,noexec tmpfs "$ROOT/tmp"
mount -t tmpfs -o size=32m,nosuid,nodev tmpfs "$ROOT/work"
IP_BIN="$(command -v ip)"; CHROOT_BIN="$(command -v chroot)"
"$IP_BIN" link set lo up
ulimit -t 120; ulimit -v 2097152; ulimit -f 1048576; ulimit -n 64; ulimit -u 32
exec "$CHROOT_BIN" "$ROOT" /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all /usr/bin/env -i PATH=/usr/bin:/bin HOME=/tmp LANG=C LC_ALL=C "$@"
"""

class PackageMetadataDenied(PermissionError):
    pass

class _ConfinedPopen:
    def __init__(self, proc: Any, root: str) -> None:
        self._proc = proc
        self._root = root
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.args = proc.args

    @property
    def returncode(self):
        return self._proc.returncode

    def poll(self):
        rc = self._proc.poll()
        if rc is not None:
            self._cleanup()
        return rc

    def wait(self, timeout=None):
        try:
            return self._proc.wait(timeout=timeout)
        finally:
            if self._proc.poll() is not None:
                self._cleanup()

    def kill(self):
        try:
            os.killpg(self._proc.pid, 9)
        except (ProcessLookupError, AttributeError):
            try:
                self._proc.kill()
            except Exception:
                pass

    def terminate(self):
        try:
            self._proc.terminate()
        except Exception:
            pass

    def _cleanup(self):
        if self._root:
            shutil.rmtree(self._root, ignore_errors=True)
            self._root = ""

def current_contents_index_files() -> list[str]:
    roots = []
    for pattern in ("/var/lib/apt/lists/*Contents*",):
        for raw in glob.glob(pattern):
            p = pathlib.Path(raw)
            try:
                rp = p.resolve()
            except Exception:
                continue
            if rp.is_file() and str(rp).startswith("/var/lib/apt/"):
                roots.append(str(rp))
    return sorted(set(roots))

def _safe_token(value: Any, label: str, max_len: int = 512) -> str:
    s = str(value)
    if not s or len(s) > max_len or "\x00" in s or "\n" in s or "\r" in s:
        raise PackageMetadataDenied(label + "_INVALID")
    return s

def _package(value: Any) -> str:
    s = _safe_token(value, "PACKAGE", 192)
    if s.startswith("-") or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+_.:-]{0,191}", s):
        raise PackageMetadataDenied("PACKAGE_INVALID")
    return s

def _version_spec(value: Any) -> str:
    s = _safe_token(value, "PACKAGE_VERSION_SPEC", 384)
    if s.startswith("-") or "=" not in s:
        raise PackageMetadataDenied("PACKAGE_VERSION_SPEC_INVALID")
    name, version = s.split("=", 1)
    _package(name)
    if not version or len(version) > 190 or any(ch.isspace() for ch in version) or "/" in version:
        raise PackageMetadataDenied("PACKAGE_VERSION_SPEC_INVALID")
    return s

def _query(value: Any) -> str:
    s = _safe_token(value, "QUERY", 512)
    if s.startswith("-"):
        raise PackageMetadataDenied("QUERY_INVALID")
    return s

def _metadata_path(value: Any) -> str:
    try:
        p = pathlib.Path(os.fspath(value)).resolve()
    except Exception as exc:
        raise PackageMetadataDenied("METADATA_PATH_INVALID") from exc
    if not p.is_file():
        raise PackageMetadataDenied("METADATA_PATH_MISSING")
    if not any(str(p) == root or str(p).startswith(root + "/") for root in READ_ONLY_METADATA_ROOTS):
        raise PackageMetadataDenied("METADATA_PATH_OUTSIDE_ALLOWLIST")
    return str(p)

def _resolve_exec(value: Any, names: set[str]) -> str:
    token = str(value)
    base = pathlib.Path(token).name
    if base not in names:
        raise PackageMetadataDenied("EXECUTABLE_NOT_ALLOWED:" + base)
    resolved = token if os.path.isabs(token) else shutil.which(token)
    if not resolved:
        raise PackageMetadataDenied("EXECUTABLE_UNAVAILABLE:" + base)
    p = pathlib.Path(resolved).resolve()
    if not (str(p).startswith("/usr/") or str(p).startswith("/bin/")):
        raise PackageMetadataDenied("EXECUTABLE_PATH_NOT_SYSTEM:" + str(p))
    return str(p)

def _validate_context(context: Mapping[str, Any]) -> tuple[list[str], dict[str, Any], tuple[str,int,str], str]:
    if context.get("effect_class") != EFFECT_CLASS:
        raise PackageMetadataDenied("EFFECT_CLASS_MISMATCH")
    cs = context.get("callsite")
    if not isinstance(cs, Mapping):
        raise PackageMetadataDenied("CALLSITE_MISSING")
    key = (str(cs.get("module_path") or ""), int(cs.get("lineno") or 0), str(cs.get("process_api") or ""))
    profile = SUPPORTED.get(key)
    if profile is None:
        raise PackageMetadataDenied("PACKAGE_METADATA_CALLSITE_NOT_SUPPORTED:" + repr(key))
    args = context.get("args")
    if not isinstance(args, (list, tuple)) or len(args) != 1:
        raise PackageMetadataDenied("POSITIONAL_SHAPE_INVALID")
    cmd = args[0]
    if not isinstance(cmd, (list, tuple)) or not cmd:
        raise PackageMetadataDenied("ARGV_REQUIRED")
    argv = [os.fspath(x) if isinstance(x, os.PathLike) else str(x) for x in cmd]
    kwargs = dict(context.get("kwargs") or {})
    if kwargs.get("shell", False):
        raise PackageMetadataDenied("SHELL_FORBIDDEN")
    if kwargs.get("env") is not None or kwargs.get("cwd") is not None:
        raise PackageMetadataDenied("CUSTOM_ENV_OR_CWD_FORBIDDEN")
    if kwargs.get("input") is not None or kwargs.get("stdin") not in (None, subprocess.DEVNULL):
        raise PackageMetadataDenied("STDIN_OR_INPUT_FORBIDDEN")
    if key[2] == "subprocess.run":
        if kwargs.get("capture_output") is not True:
            raise PackageMetadataDenied("CAPTURE_OUTPUT_REQUIRED")
        if not (kwargs.get("text") is True or kwargs.get("universal_newlines") is True or kwargs.get("encoding")):
            raise PackageMetadataDenied("TEXT_MODE_REQUIRED")
    else:
        if kwargs.get("stdout") != subprocess.PIPE or kwargs.get("stderr") != subprocess.DEVNULL:
            raise PackageMetadataDenied("POPEN_STDIO_SHAPE_INVALID")
        if kwargs.get("text") is not True:
            raise PackageMetadataDenied("POPEN_TEXT_MODE_REQUIRED")
    return argv, kwargs, key, profile

def _prepare(context: Mapping[str, Any]) -> dict[str, Any]:
    argv, kwargs, key, profile = _validate_context(context)
    if profile in {"APT_SHOW_BOUND","APT_SHOW_DISCOVERY"}:
        if len(argv) != 3 or argv[1] != "show":
            raise PackageMetadataDenied("APT_SHOW_SHAPE_INVALID")
        exe = _resolve_exec(argv[0], {"apt-cache"})
        inner = [exe, "show", _version_spec(argv[2])]
    elif profile == "DPKG_QUERY_VERSION":
        if len(argv) != 4 or argv[1] != "-W" or argv[2] != "-f=${Version}":
            raise PackageMetadataDenied("DPKG_QUERY_SHAPE_INVALID")
        exe = _resolve_exec(argv[0], {"dpkg-query"})
        inner = [exe, "-W", "-f=${Version}", _package(argv[3])]
    elif profile == "APT_SEARCH":
        if len(argv) != 3 or argv[1] != "search":
            raise PackageMetadataDenied("APT_SEARCH_SHAPE_INVALID")
        exe = _resolve_exec(argv[0], {"apt-cache"})
        inner = [exe, "search", _query(argv[2])]
    elif profile == "APT_POLICY":
        if len(argv) != 3 or argv[1] != "policy":
            raise PackageMetadataDenied("APT_POLICY_SHAPE_INVALID")
        exe = _resolve_exec(argv[0], {"apt-cache"})
        inner = [exe, "policy", _package(argv[2])]
    elif profile == "APT_INDEX_TARGETS_FILES":
        if len(argv) < 4 or argv[1:4] != ["indextargets","--format","$(FILENAME)"]:
            raise PackageMetadataDenied("APT_INDEX_TARGETS_FILES_SHAPE_INVALID")
        exe = _resolve_exec(argv[0], {"apt-get"})
        extra=[]
        for raw in argv[4:]:
            s=_safe_token(raw,"INDEX_TARGET_FILTER",256)
            if not (re.fullmatch(r"Identifier: [A-Za-z0-9_.+-]{1,128}",s) or re.fullmatch(r"Language: [A-Za-z0-9_.+-]{1,64}",s)):
                raise PackageMetadataDenied("INDEX_TARGET_FILTER_INVALID")
            extra.append(s)
        inner=[exe,"indextargets","--format","$(FILENAME)",*extra]
    elif profile == "APT_INDEX_TARGETS_CONTENTS":
        if argv != ["apt-get","indextargets","--format","$(IDENTIFIER)\t$(FILENAME)"]:
            if len(argv) != 4 or pathlib.Path(argv[0]).name != "apt-get" or argv[1:] != ["indextargets","--format","$(IDENTIFIER)\t$(FILENAME)"]:
                raise PackageMetadataDenied("APT_CONTENTS_TARGETS_SHAPE_INVALID")
        exe=_resolve_exec(argv[0],{"apt-get"})
        inner=[exe,"indextargets","--format","$(IDENTIFIER)\t$(FILENAME)"]
    elif profile in {"APT_HELPER_CAT","APT_HELPER_STREAM"}:
        if len(argv) != 3 or argv[1] != "cat-file":
            raise PackageMetadataDenied("APT_HELPER_CAT_SHAPE_INVALID")
        exe=_resolve_exec(argv[0],{"apt-helper"})
        if pathlib.Path(exe).resolve() != pathlib.Path("/usr/lib/apt/apt-helper").resolve():
            raise PackageMetadataDenied("APT_HELPER_PATH_MISMATCH")
        inner=[exe,"cat-file",_metadata_path(argv[2])]
    elif profile == "APT_DUMPAVAIL":
        if len(argv) != 2 or argv[1] != "dumpavail":
            raise PackageMetadataDenied("APT_DUMPAVAIL_SHAPE_INVALID")
        exe=_resolve_exec(argv[0],{"apt-cache"})
        inner=[exe,"dumpavail"]
    else:
        raise PackageMetadataDenied("PROFILE_UNREACHABLE")

    timeout = kwargs.get("timeout")
    if timeout is None:
        timeout = 30 if key[2] == "subprocess.run" else None
    if timeout is not None:
        try:
            timeout=float(timeout)
        except Exception as exc:
            raise PackageMetadataDenied("TIMEOUT_INVALID") from exc
        if not (0 < timeout <= 120):
            raise PackageMetadataDenied("TIMEOUT_OUT_OF_RANGE")
    return {"argv":inner,"original_argv":argv,"kwargs":kwargs,"key":key,"profile":profile,"timeout":timeout}

def _check_metadata_roots() -> None:
    for raw in READ_ONLY_METADATA_ROOTS:
        p=pathlib.Path(raw)
        if not p.exists():
            continue
        if p.is_symlink():
            raise PackageMetadataDenied("METADATA_ROOT_SYMLINK_FORBIDDEN:" + raw)

def _spawn(prepared: Mapping[str, Any], popen_impl: Callable[..., Any]) -> _ConfinedPopen:
    _check_metadata_roots()
    required=["unshare","mount","chroot","setpriv","ip","bash","env"]
    resolved={name:shutil.which(name) for name in required}
    missing=[name for name,path in resolved.items() if not path]
    if missing:
        raise PackageMetadataDenied("HOST_PRIMITIVE_MISSING:" + ",".join(missing))
    root=tempfile.mkdtemp(prefix="brain-pkg-meta-")
    try:
        os.chown(root,os.geteuid(),os.getegid())
        cmd=[
            resolved["unshare"],"--user","--map-root-user","--mount","--net","--pid","--fork","--ipc","--uts",
            resolved["bash"],"-c",_SETUP,"_",root,*prepared["argv"]
        ]
        kw={
            "stdin":subprocess.DEVNULL,
            "stdout":subprocess.PIPE,
            "stderr":subprocess.PIPE,
            "text":True,
            "encoding":prepared["kwargs"].get("encoding") or "utf-8",
            "errors":prepared["kwargs"].get("errors") or "replace",
            "start_new_session":True,
        }
        proc=popen_impl(cmd,**kw)
        return _ConfinedPopen(proc,root)
    except Exception:
        shutil.rmtree(root,ignore_errors=True)
        raise

def make_executor(*, popen_impl: Callable[..., Any]) -> Callable[[Mapping[str, Any]], Any]:
    if not callable(popen_impl):
        raise TypeError("POPEN_IMPL_NOT_CALLABLE")
    def execute(context: Mapping[str, Any]) -> Any:
        prepared=_prepare(context)
        confined=_spawn(prepared,popen_impl)
        if prepared["key"][2] == "subprocess.Popen":
            if confined.stderr is not None:
                confined.stderr.close()
                confined.stderr=None
            return confined
        try:
            try:
                stdout,stderr=confined._proc.communicate(timeout=prepared["timeout"])
            except subprocess.TimeoutExpired:
                confined.kill()
                stdout,stderr=confined._proc.communicate(timeout=5)
                raise subprocess.TimeoutExpired(prepared["original_argv"],prepared["timeout"],output=stdout,stderr=stderr)
            return subprocess.CompletedProcess(
                args=prepared["original_argv"],
                returncode=confined._proc.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        finally:
            confined._cleanup()
    return execute
