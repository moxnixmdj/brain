"""Fail-closed Linux user-namespace carrier for untrusted bound capability execution.

This carrier is an experimental Root3 E2/E3 substrate. It executes a child
command in fresh user, mount, network and PID namespaces, presents only /usr
(read-only), the Project Brain repository (read-only except explicitly declared
writable repo-directory prefixes), and an ephemeral tmpfs /tmp. Before the
payload execs, all capability sets are dropped and no_new_privs is enabled.

It is intentionally networkless. Network-requiring work must remain on a
separately mediated broker path. This module grants no acceptance/Root3 credit.
"""
from __future__ import annotations

import os
import platform
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

SCHEMA="PROJECT_BRAIN_ROOT3_LINUX_USERNS_EFFECT_CARRIER_V1"


class CarrierError(ValueError):
    pass


@dataclass(frozen=True)
class CarrierResult:
    returncode: int
    stdout: str
    stderr: str


_REQUIRED_TOOLS=("unshare","bash","mount","chroot","setpriv","env")
_ENV_KEY=re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _tool(name: str) -> str:
    path=shutil.which(name)
    if not path:
        raise CarrierError("REQUIRED_TOOL_MISSING:"+name)
    return str(Path(path).resolve())


def _repo_prefix(repo: Path, raw: str) -> tuple[str,Path]:
    if not isinstance(raw,str) or not raw or raw.startswith(("/", "\\")):
        raise CarrierError("WRITABLE_PREFIX_INVALID")
    rel=Path(raw)
    if any(part in {"",".."} for part in rel.parts):
        raise CarrierError("WRITABLE_PREFIX_INVALID")
    resolved=(repo/rel).resolve()
    if resolved==repo:
        raise CarrierError("WRITABLE_PREFIX_REPO_ROOT_FORBIDDEN")
    if repo not in resolved.parents:
        raise CarrierError("WRITABLE_PREFIX_ESCAPE")
    if not resolved.is_dir():
        raise CarrierError("WRITABLE_PREFIX_NOT_DIRECTORY:"+raw)
    return rel.as_posix(),resolved


def _inside(path: Path, prefix: Path) -> bool:
    return path==prefix or prefix in path.parents


def _preflight_repo_tree(repo: Path, writable_paths: Sequence[Path]) -> None:
    """Reject host-tree aliases that could defeat mount-path confinement."""
    for root,dirs,files in os.walk(repo,topdown=True,followlinks=False):
        base=Path(root)

        if base!=repo and base.is_mount():
            raise CarrierError(
                "NESTED_MOUNTPOINT_FORBIDDEN:"
                +base.relative_to(repo).as_posix()
            )

        # os.walk lists symlinked directories in dirs but does not traverse them
        # when followlinks=False. Validate their lstat type explicitly.
        for name in list(dirs)+list(files):
            path=base/name
            st=path.lstat()
            mode=st.st_mode

            if stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
                continue

            if not stat.S_ISREG(mode):
                raise CarrierError(
                    "SPECIAL_FILE_FORBIDDEN:"
                    +path.relative_to(repo).as_posix()
                )

            if any(_inside(path,prefix) for prefix in writable_paths):
                # A pre-existing hard link in an authorized rw bind can alias
                # an inode outside the prefix and make the outer ro mount
                # irrelevant. Reject conservatively even if all aliases happen
                # to be inside the same authorized prefix.
                if int(st.st_nlink)!=1:
                    raise CarrierError(
                        "WRITABLE_PREFIX_HARDLINK_FORBIDDEN:"
                        +path.relative_to(repo).as_posix()
                    )


def probe() -> dict:
    tools={}
    for name in _REQUIRED_TOOLS:
        try:
            tools[name]=_tool(name)
        except CarrierError:
            tools[name]=None
    return {
        "schema":SCHEMA,
        "platform":platform.system().lower(),
        "tools":tools,
        "static_prerequisites_present":(
            platform.system().lower()=="linux"
            and all(tools.values())
            and Path("/usr").is_dir()
        ),
        "live_namespace_probe_required":True,
        "root3_credit_delta":0,
    }


def build_unshare_command(
    *,
    repo_root: str | os.PathLike[str],
    sandbox_root: str | os.PathLike[str],
    writable_repo_prefixes: Sequence[str],
    argv: Sequence[str],
    environment: Mapping[str,str] | None=None,
) -> list[str]:
    if platform.system().lower()!="linux":
        raise CarrierError("LINUX_REQUIRED")
    repo=Path(repo_root).resolve()
    root=Path(sandbox_root).resolve()
    if not repo.is_dir():
        raise CarrierError("REPO_ROOT_INVALID")
    if not root.is_dir() or any(root.iterdir()):
        raise CarrierError("SANDBOX_ROOT_MUST_BE_EXISTING_EMPTY_DIRECTORY")
    if not argv or any(not isinstance(x,str) or "\x00" in x for x in argv):
        raise CarrierError("ARGV_INVALID")

    prefixes=[]
    seen=set()
    for raw in writable_repo_prefixes:
        rel,p=_repo_prefix(repo,raw)
        if rel in seen:
            raise CarrierError("WRITABLE_PREFIX_DUPLICATE:"+rel)
        for existing_rel,existing_path in prefixes:
            if _inside(p,existing_path) or _inside(existing_path,p):
                raise CarrierError(
                    "WRITABLE_PREFIX_OVERLAP:"+existing_rel+":"+rel
                )
        seen.add(rel)
        prefixes.append((rel,p))

    _preflight_repo_tree(repo,[p for _,p in prefixes])

    env={
        "PATH":"/usr/bin:/bin",
        "HOME":"/tmp",
        "TMPDIR":"/tmp",
        "PYTHONPATH":"/workspace",
        **dict(environment or {}),
    }
    for key,value in env.items():
        if not _ENV_KEY.fullmatch(str(key)) or not isinstance(value,str) or "\x00" in value:
            raise CarrierError("ENVIRONMENT_INVALID")

    unshare=_tool("unshare")
    bash=_tool("bash")

    q=shlex.quote
    setup=[
        "set -euo pipefail",
        f"root={q(str(root))}",
        f"repo={q(str(repo))}",
        'mount -t tmpfs tmpfs "$root"',
        'mkdir -p "$root/usr" "$root/workspace" "$root/tmp"',
        'mount --rbind /usr "$root/usr"',
        'mount --make-rslave "$root/usr"',
        'mount -o remount,bind,ro "$root/usr"',
        'ln -s usr/bin "$root/bin"',
        'ln -s usr/lib "$root/lib"',
        'if [ -e /usr/lib64 ]; then ln -s usr/lib64 "$root/lib64"; fi',
        'mount --bind "$repo" "$root/workspace"',
        'mount -o remount,bind,ro "$root/workspace"',
    ]
    for rel,host in prefixes:
        target="/workspace/"+rel
        setup.extend([
            f'mount --bind {q(str(host))} "$root"{q(target)}',
            f'mount -o remount,bind,rw "$root"{q(target)}',
        ])
    setup.append('mount -t tmpfs tmpfs "$root/tmp"')

    env_args=" ".join(q(str(k)+"="+v) for k,v in sorted(env.items()))
    payload=" ".join(q(x) for x in argv)
    setup.append(
        'chroot "$root" /usr/bin/setpriv '
        '--nnp --bounding-set=-all --inh-caps=-all --ambient-caps=-all '
        '/usr/bin/env -i '+env_args+" "+payload
    )

    return [
        unshare,
        "--user","--map-root-user",
        "--mount","--net","--pid",
        "--fork","--kill-child",
        bash,"-ceu","\n".join(setup),
    ]


def run_isolated(
    *,
    repo_root: str | os.PathLike[str],
    writable_repo_prefixes: Sequence[str],
    argv: Sequence[str],
    environment: Mapping[str,str] | None=None,
    timeout_s: float=60.0,
) -> CarrierResult:
    if not isinstance(timeout_s,(int,float)) or timeout_s<=0 or timeout_s>600:
        raise CarrierError("TIMEOUT_INVALID")
    with tempfile.TemporaryDirectory(prefix="project-brain-userns-carrier-") as td:
        cmd=build_unshare_command(
            repo_root=repo_root,
            sandbox_root=td,
            writable_repo_prefixes=writable_repo_prefixes,
            argv=argv,
            environment=environment,
        )
        proc=subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=float(timeout_s),
            close_fds=True,
        )
    return CarrierResult(
        returncode=int(proc.returncode),
        stdout=proc.stdout[-20000:],
        stderr=proc.stderr[-20000:],
    )
