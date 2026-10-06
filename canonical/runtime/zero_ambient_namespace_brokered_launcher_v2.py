from __future__ import annotations

import math
import os
import pathlib
import pwd
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Mapping
from typing import Any

from canonical.runtime import root3_broker_rpc_v1 as rpc
from canonical.runtime import root3_parent_broker_server_v1 as parent_broker
from canonical.runtime import zero_ambient_namespace_launcher_v1 as base

SCHEMA="PROJECT_BRAIN_ZERO_AMBIENT_NAMESPACE_BROKERED_LAUNCHER_V2"

_SETUP=r'''set -euo pipefail
ROOT="$1"; INPUT="$2"; BROKER="$3"; MEM_KB="$4"; CPU_S="$5"; FILE_KB="$6"; NOFILE="$7"; PIDS="$8"; SCRATCH_MB="$9"; shift 9
mount --make-rprivate /
mount -t tmpfs -o size=64m,nosuid,nodev tmpfs "$ROOT"
mkdir -p "$ROOT/usr" "$ROOT/bin" "$ROOT/lib" "$ROOT/lib64" "$ROOT/tmp" "$ROOT/work" "$ROOT/input"
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
[ -d "$ROOT/input/canonical/astra_runtime/tmp" ] || exit 91
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev tmpfs "$ROOT/input/canonical/astra_runtime/tmp"
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev,noexec tmpfs "$ROOT/tmp"
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev tmpfs "$ROOT/work"
IP_BIN="$(command -v ip)"; CHROOT_BIN="$(command -v chroot)"
"$IP_BIN" link set lo up
ulimit -t "$CPU_S"; ulimit -v "$MEM_KB"; ulimit -f "$FILE_KB"; ulimit -n "$NOFILE"; ulimit -u "$PIDS"
exec "$CHROOT_BIN" "$ROOT" /usr/bin/env -i PATH=/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PROJECT_BRAIN_BROKER_FD="$BROKER" "$@"
'''

class BrokeredNamespaceError(RuntimeError):
    pass

def _nonroot_identity()->tuple[int,int]:
    if os.geteuid()!=0:
        return os.geteuid(),os.getegid()
    for name in ("oai","ubuntu","nobody"):
        try:
            ent=pwd.getpwnam(name)
        except KeyError:
            continue
        if ent.pw_uid>0 and ent.pw_gid>0:
            return ent.pw_uid,ent.pw_gid
    for ent in pwd.getpwall():
        if ent.pw_uid>=1000 and ent.pw_gid>0:
            return ent.pw_uid,ent.pw_gid
    raise BrokeredNamespaceError("NO_NONROOT_HOST_IDENTITY")

def production_policy(repo_root:pathlib.Path,mission_rel:str)->dict[str,Any]:
    root=repo_root.resolve(strict=True)
    mission_rel=str(mission_rel).replace("\\","/").lstrip("/")
    mission=(root/mission_rel).resolve(strict=True)
    if mission!=root and root not in mission.parents:
        raise BrokeredNamespaceError("MISSION_OUTSIDE_REPOSITORY")
    if mission.suffix.lower()!=".json":
        raise BrokeredNamespaceError("MISSION_JSON_REQUIRED")
    tmp=root/"canonical/astra_runtime/tmp"
    if not tmp.is_dir():
        raise BrokeredNamespaceError("ASTRA_RUNTIME_TMP_DIR_REQUIRED")
    uid,gid=_nonroot_identity()
    return {
        "argv":[
            "/usr/bin/python3","-I",
            "/input/canonical/runtime/root3_confined_astra_entry_v1.py",
            "/input/"+mission_rel,
        ],
        "input_dir":str(root),
        "host_uid":uid,
        "host_gid":gid,
        "env":{},
        "limits":{
            "pids":64,
            "memory_mb":2048,
            "cpu_seconds":300,
            "wallclock_s":600,
            "scratch_mb":512,
            "max_file_mb":512,
            "nofile":128,
            "broker_max_bytes":8_000_000,
        },
    }

def _required_primitives()->dict[str,str]:
    names=("unshare","mount","chroot","setpriv","ip","bash","env")
    out={name:shutil.which(name) or "" for name in names}
    missing=[k for k,v in out.items() if not v]
    if missing:
        raise BrokeredNamespaceError("HOST_PRIMITIVE_MISSING:"+",".join(missing))
    return out

def run_brokered(
    policy:Mapping[str,Any],
    *,
    repo_root:str|os.PathLike[str],
    external_bridge_dir:str|None=None,
    external_wait_seconds:float=0.0,
)->dict[str,Any]:
    p=base.canonical_policy(policy)
    root_repo=pathlib.Path(repo_root).resolve(strict=True)
    if pathlib.Path(p["input_dir"]).resolve()!=root_repo:
        raise BrokeredNamespaceError("INPUT_DIR_MUST_EQUAL_REPOSITORY_ROOT")
    resolved=_required_primitives()
    lim=p["limits"]
    ns_root=tempfile.mkdtemp(prefix="brain-parent-membrane-v2-")
    os.chown(ns_root,p["host_uid"],p["host_gid"])

    parent,child=socket.socketpair()
    broker=parent_broker.ParentBroker(
        repo_root=root_repo,
        external_bridge_dir=external_bridge_dir,
        external_wait_seconds=external_wait_seconds,
    )
    broker_state={"summary":None,"error":None}

    def serve():
        try:
            broker_state["summary"]=rpc.serve_socket(parent,broker.handle)
        except Exception as exc:
            broker_state["error"]=type(exc).__name__+":"+str(exc)
            try:
                parent.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        finally:
            try:
                parent.close()
            except OSError:
                pass

    th=threading.Thread(target=serve,daemon=True)
    th.start()
    cmd=[
        resolved["unshare"],
        "--user","--map-root-user","--mount","--net","--pid","--fork","--ipc","--uts",
        resolved["bash"],"-c",_SETUP,"_",
        ns_root,p["input_dir"],str(child.fileno()),
        str(lim["memory_mb"]*1024),
        str(lim["cpu_seconds"]),
        str(math.ceil(lim["max_file_mb"]*1024)),
        str(lim["nofile"]),
        str(lim["pids"]),
        str(lim["scratch_mb"]),
        resolved["setpriv"],
        "--no-new-privs","--bounding-set=-all","--inh-caps=-all","--ambient-caps=-all",
        resolved["env"],"-i","PATH=/usr/bin:/bin","HOME=/tmp","PYTHONDONTWRITEBYTECODE=1",
        "PROJECT_BRAIN_BROKER_FD="+str(child.fileno()),
        *p["argv"],
    ]
    popen_kw={
        "stdin":subprocess.DEVNULL,
        "stdout":subprocess.DEVNULL,
        "stderr":subprocess.DEVNULL,
        "pass_fds":(child.fileno(),),
        "env":{"PYTHONDONTWRITEBYTECODE":"1"},
        "start_new_session":True,
    }
    if os.geteuid()==0:
        popen_kw.update(
            user=p["host_uid"],group=p["host_gid"],extra_groups=[]
        )
    started=time.monotonic()
    timed_out=False
    try:
        proc=subprocess.Popen(cmd,**popen_kw)
        child.close()
        try:
            rc=proc.wait(timeout=lim["wallclock_s"])
        except subprocess.TimeoutExpired:
            timed_out=True
            try:
                os.killpg(proc.pid,9)
            except ProcessLookupError:
                pass
            rc=proc.wait(timeout=5)
        th.join(timeout=5)
    finally:
        try:
            child.close()
        except OSError:
            pass
        try:
            parent.close()
        except OSError:
            pass
        shutil.rmtree(ns_root,ignore_errors=True)

    status="CHILD_EXITED"
    if timed_out:
        status="WALLCLOCK_LIMIT_EXCEEDED"
    elif broker_state["error"] is not None:
        status="BROKER_PROTOCOL_ERROR"
    elif rc!=0:
        status="CHILD_FAILED"

    return {
        "schema":SCHEMA,
        "status":status,
        "returncode":rc,
        "policy_sha256":base.policy_sha256(p),
        "wallclock_ms":round((time.monotonic()-started)*1000,3),
        "broker_summary":broker.summary(),
        "broker_transport_summary":broker_state["summary"],
        "broker_error":broker_state["error"],
        "material_effect_classes":[
            "EXTERNAL_TOOL",
            "DURABLE_ADMIN_WRITE",
        ],
        "artifact_persistence_authority":False,
        "repo_mutation_from_child":"DENIED_READ_ONLY_INPUT_EXCEPT_PRIVATE_TMP_OVERLAY",
        "network_from_child":"PRIVATE_NAMESPACE_LOOPBACK_ONLY",
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
        "terminal_credit_delta":0,
    }
