#!/usr/bin/env python3
"""Docker-free zero-ambient launcher built from Linux namespace primitives."""
from __future__ import annotations
import os, pathlib, shutil, socket, subprocess, tempfile
from dataclasses import dataclass
from typing import Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_NAMESPACE_ZERO_AMBIENT_LAUNCHER_V1"
_ALLOWED_ENV = {"LANG","LC_ALL","TZ","PYTHONHASHSEED","PYTHONDONTWRITEBYTECODE"}

class NamespaceConfinementError(ValueError):
    pass

@dataclass(frozen=True)
class Policy:
    argv: tuple[str, ...]
    input_dir: str
    env: tuple[tuple[str, str], ...]
    cpu_seconds: int
    memory_mb: int
    file_size_mb: int
    open_fds: int
    processes: int
    scratch_mb: int

class ConfinedProcess:
    def __init__(self, process: subprocess.Popen[bytes], broker: socket.socket, root_dir: str) -> None:
        self.process = process
        self.broker = broker
        self.root_dir = root_dir
        self._cleaned = False
    def wait(self, timeout: float | None = None) -> int:
        try:
            return int(self.process.wait(timeout=timeout))
        finally:
            self.cleanup()
    def terminate(self) -> None:
        self.process.terminate()
    def kill(self) -> None:
        self.process.kill()
    def cleanup(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
        try:
            self.broker.close()
        finally:
            shutil.rmtree(self.root_dir, ignore_errors=True)
    def __enter__(self) -> "ConfinedProcess":
        return self
    def __exit__(self, exc_type, exc, tb) -> None:
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait()
        self.cleanup()

def canonical_policy(raw: Mapping[str, object]) -> Policy:
    if not isinstance(raw, Mapping):
        raise NamespaceConfinementError("POLICY_NOT_MAPPING")
    argv_raw = raw.get("argv")
    if not isinstance(argv_raw, Sequence) or isinstance(argv_raw, (str, bytes)) or not argv_raw:
        raise NamespaceConfinementError("ARGV_REQUIRED")
    argv = tuple(str(x) for x in argv_raw)
    if any(not x or "\x00" in x for x in argv):
        raise NamespaceConfinementError("ARGV_INVALID")
    if not argv[0].startswith("/"):
        raise NamespaceConfinementError("ARGV0_MUST_BE_ABSOLUTE_INSIDE_SANDBOX")
    input_dir = pathlib.Path(str(raw.get("input_dir") or "")).expanduser().resolve()
    if not input_dir.is_dir():
        raise NamespaceConfinementError("INPUT_DIR_REQUIRED")
    env_raw = raw.get("env") or {}
    if not isinstance(env_raw, Mapping):
        raise NamespaceConfinementError("ENV_NOT_MAPPING")
    env: list[tuple[str,str]] = []
    for k0,v0 in env_raw.items():
        k,v = str(k0),str(v0)
        if k not in _ALLOWED_ENV:
            raise NamespaceConfinementError("ENV_NOT_ALLOWLISTED:"+k)
        if "\x00" in v or len(v)>512:
            raise NamespaceConfinementError("ENV_VALUE_INVALID:"+k)
        env.append((k,v))
    limits = raw.get("limits") or {}
    if not isinstance(limits, Mapping):
        raise NamespaceConfinementError("LIMITS_NOT_MAPPING")
    def bounded(name:str, default:int, lo:int, hi:int)->int:
        try: value=int(limits.get(name,default))
        except Exception as exc: raise NamespaceConfinementError("LIMIT_INVALID:"+name) from exc
        if not lo<=value<=hi: raise NamespaceConfinementError("LIMIT_OUT_OF_RANGE:"+name)
        return value
    return Policy(
        argv=argv,input_dir=str(input_dir),env=tuple(sorted(env)),
        cpu_seconds=bounded("cpu_seconds",30,1,3600),
        memory_mb=bounded("memory_mb",1024,64,16384),
        file_size_mb=bounded("file_size_mb",64,1,4096),
        open_fds=bounded("open_fds",64,8,1024),
        processes=bounded("processes",64,1,1024),
        scratch_mb=bounded("scratch_mb",256,16,4096),
    )

def _require_host_primitives() -> None:
    required=("unshare","bash","mount","chroot","ip","setpriv")
    missing=[name for name in required if shutil.which(name) is None]
    if missing:
        raise NamespaceConfinementError("HOST_PRIMITIVES_MISSING:"+",".join(missing))

def spawn_confined(raw_policy: Mapping[str, object]) -> ConfinedProcess:
    policy=canonical_policy(raw_policy)
    _require_host_primitives()
    root=tempfile.mkdtemp(prefix="brain-namespace-membrane-")
    parent_sock,child_sock=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
    child_sock.set_inheritable(True)
    setup=r"""
set -euo pipefail
ROOT="$1"
INPUT="$2"
shift 2
mount --make-rprivate /
mount -t tmpfs -o "size=${SCRATCH_MB}m,nosuid,nodev" tmpfs "$ROOT"
mkdir -p "$ROOT"/usr "$ROOT"/bin "$ROOT"/lib "$ROOT"/lib64 "$ROOT"/tmp "$ROOT"/work "$ROOT"/input
for d in /usr /bin /lib /lib64; do
  if [ -e "$d" ]; then
    mount --bind "$d" "$ROOT$d"
    mount -o remount,bind,ro "$ROOT$d"
  fi
done
mount -t tmpfs -o "size=${SCRATCH_MB}m,nosuid,nodev,noexec" tmpfs "$ROOT/tmp"
mount -t tmpfs -o "size=${SCRATCH_MB}m,nosuid,nodev" tmpfs "$ROOT/work"
mount --bind "$INPUT" "$ROOT/input"
mount -o remount,bind,ro "$ROOT/input"
ip link set lo up
ulimit -t "$CPU_SECONDS"
ulimit -v "$MEMORY_KB"
ulimit -f "$FILE_BLOCKS"
ulimit -n "$OPEN_FDS"
ulimit -u "$PROCESSES"
ENV_ARGS=("PATH=/usr/bin:/bin" "HOME=/tmp" "PROJECT_BRAIN_BROKER_FD=${BROKER_FD}")
if [ -n "${PB_LANG:-}" ]; then ENV_ARGS+=("LANG=${PB_LANG}"); fi
if [ -n "${PB_LC_ALL:-}" ]; then ENV_ARGS+=("LC_ALL=${PB_LC_ALL}"); fi
if [ -n "${PB_TZ:-}" ]; then ENV_ARGS+=("TZ=${PB_TZ}"); fi
if [ -n "${PB_PYTHONHASHSEED:-}" ]; then ENV_ARGS+=("PYTHONHASHSEED=${PB_PYTHONHASHSEED}"); fi
if [ -n "${PB_PYTHONDONTWRITEBYTECODE:-}" ]; then ENV_ARGS+=("PYTHONDONTWRITEBYTECODE=${PB_PYTHONDONTWRITEBYTECODE}"); fi
exec chroot "$ROOT" /usr/bin/env -i "${ENV_ARGS[@]}"   /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all   "$@"
"""
    env={
        "PATH":os.environ.get("PATH","/usr/bin:/bin"),
        "BROKER_FD":str(child_sock.fileno()),
        "CPU_SECONDS":str(policy.cpu_seconds),
        "MEMORY_KB":str(policy.memory_mb*1024),
        "FILE_BLOCKS":str(policy.file_size_mb*1024),
        "OPEN_FDS":str(policy.open_fds),
        "PROCESSES":str(policy.processes),
        "SCRATCH_MB":str(policy.scratch_mb),
    }
    for key,value in policy.env:
        env["PB_"+key]=value
    cmd=[
        "unshare","--user","--map-root-user","--mount","--net","--pid","--fork","--ipc","--uts",
        "bash","-c",setup,"_",root,policy.input_dir,*policy.argv,
    ]
    try:
        proc=subprocess.Popen(
            cmd,pass_fds=(child_sock.fileno(),),env=env,
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except Exception:
        parent_sock.close(); child_sock.close(); shutil.rmtree(root,ignore_errors=True); raise
    finally:
        child_sock.close()
    return ConfinedProcess(proc,parent_sock,root)

def launcher_properties() -> dict[str, object]:
    return {
        "schema":SCHEMA,
        "ambient_host_network":False,
        "ambient_host_filesystem":False,
        "ambient_stdio_application_channel":False,
        "declared_input_read_only":True,
        "private_tmpfs_scratch":True,
        "single_deliberate_application_channel":"BROKER_SOCKET_FD",
        "no_new_privileges":True,
        "capability_bounding_set":"EMPTY",
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
