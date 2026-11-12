"""Candidate namespace/chroot launcher; not an admitted security boundary.

The launcher attempts a fresh user and mount namespace, a tmpfs root, read-only
bind mounts of host system libraries, a writable project mount, a chroot and a
network namespace by default. It also attempts per-process resource limits.
Required mount and resource-limit failures must prevent execution. A successful
launch or the chroot availability probe is not independent evidence that these
measures isolate hostile code.

The launcher exposes host libraries, has no reviewed syscall filter or aggregate
cgroup limits, captures subprocess output without a bound, and has not proved
that timeouts clean up every descendant. The network-enabled mode has additional
risks. Do not use this candidate as an admitted carrier for untrusted code.
The observed behavior of individual probes is not a universal guarantee.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_CONFINE_V1"

_MOUNTS = ("/usr", "/bin", "/lib", "/lib64")

_HELPER = r'''
import os, subprocess, sys
BASE = sys.argv[1]; PROJ = os.path.realpath(sys.argv[2]); SCRIPT = sys.argv[3]
NETWORK = len(sys.argv) > 4 and sys.argv[4] == "1"
# The program must live INSIDE the chroot. Referencing it by its real
# path fails: after chroot that path no longer exists, and the run dies
# with "can't open file" -- which reads like the program failing rather
# than the harness misplacing it.
INSIDE = "/program.py"
def m(*a):
    r = subprocess.run(["mount"] + list(a), capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write("mount failed %s: %s\n" % (a, r.stderr.strip()))
        return False
    return True
def must_mount(*args):
    if not m(*args):
        sys.exit(90)
must_mount("-t", "tmpfs", "none", BASE)
for d in ("project", "work"):
    os.makedirs(BASE + "/" + d.lstrip("/"), exist_ok=True)
for s in {s for s in __MOUNTS__ if os.path.isdir(s)}:
    os.makedirs(BASE + s, exist_ok=True)
    must_mount("--bind", s, BASE + s)
    must_mount("-o", "remount,ro,bind", BASE + s)
must_mount("--bind", PROJ, BASE + "/project")
# A network namespace is not enough on its own. With no /etc in the
# chroot there is no resolv.conf, so every name fails to resolve and a
# program with perfectly good connectivity reports it has none --
# measured: 'NETWORK BLOCKED gaierror' even with the namespace left
# open. Reaching the network requires the means to resolve names.
if NETWORK:
    os.makedirs(BASE + "/etc", exist_ok=True)
    for f in ("/etc/resolv.conf", "/etc/hosts"):
        if os.path.exists(f):
            tgt = BASE + f
            try:
                open(tgt, "w").close()
            except OSError:
                continue
            must_mount("--bind", f, tgt)
# Only now, with the project separately mounted, is the root made
# read-only. Order matters: doing it earlier would freeze the project
# too, which is exactly how the withdrawn version destroyed work.
must_mount("-o", "remount,ro,bind", BASE)
# Copied only NOW, after every mount. Earlier it was written into BASE
# and then the tmpfs was mounted over BASE, hiding it -- the run died
# with "can't open file /program.py", which reads like the program
# failing rather than the harness putting it where it could not be seen.
# Its own writable mount, so the program never has to be written into
# the root (now read-only, correctly) nor into the project (which would
# leave the caller's own files altered by the harness).
must_mount("-t", "tmpfs", "none", BASE + "/work")
import shutil as _sh
_sh.copyfile(SCRIPT, BASE + "/work" + INSIDE)
os.chroot(BASE)
os.chdir("/project")

# Per-process limits are installed in the child before exec. They do not
# replace aggregate process-tree, memory or disk quotas.
def _limits():
    import resource
    for k, v in (
        ("RLIMIT_CPU", 60),          # seconds of CPU
        ("RLIMIT_AS", 2 << 30),      # 2 GiB address space
        ("RLIMIT_FSIZE", 1 << 30),   # 1 GiB per file
        ("RLIMIT_NPROC", 512),       # processes
        ("RLIMIT_NOFILE", 1024),     # descriptors
    ):
        # Refuse to exec the child if a required limit cannot be installed.
        # These per-process limits still do not replace aggregate cgroups.
        lim = getattr(resource, k)
        resource.setrlimit(lim, (v, v))

r = subprocess.run([sys.executable, "/work" + INSIDE],
                   capture_output=True, text=True, preexec_fn=_limits)
sys.stdout.write(r.stdout or "")
sys.stderr.write(r.stderr or "")
sys.exit(r.returncode if r.returncode is not None else 91)
'''


def _python_in_chroot() -> str:
    """The interpreter path that still exists after the helper chroots.

    The helper chroots into a tmpfs root that bind-mounts only ``_MOUNTS``
    (/usr, /bin, /lib, /lib64) plus the project.  Launching the helper with
    ``sys.executable`` is correct on a system interpreter and wrong in a venv:
    ``/tmp/venv/bin/python3`` is not among the mounts, so the helper's own
    post-chroot spawn of the program dies with FileNotFoundError at
    helper.py -- a harness fault that surfaces as the taught program
    failing (measured 2026-11-12 under a venv: every confined run exited 1
    before any program line ran).  Same rule the broker already follows in
    ``brokered_workspace_execution_v1._python_in_chroot``.
    """
    for cand in ("/usr/bin/python3", "/bin/python3", sys.executable):
        if cand and any(cand == root or cand.startswith(root + os.sep)
                        for root in _MOUNTS) and os.path.isfile(cand):
            return cand
    return "/usr/bin/python3"


def available() -> bool:
    """Probe user-namespace chroot availability, not carrier qualification."""
    if shutil.which("unshare") is None:
        return False
    probe = (
        "import os,sys\n"
        "try:\n"
        "    os.makedirs('/tmp/_cprobe', exist_ok=True)\n"
        "    os.chroot('/tmp/_cprobe')\n"
        "    sys.exit(0)\n"
        "except Exception:\n"
        "    sys.exit(1)\n"
    )
    try:
        r = subprocess.run(["unshare", "-r", "-m", sys.executable, "-c", probe],
                           timeout=60, capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False


def run(program: str, root: str, timeout: int = 300,
        network: bool = False) -> dict:
    """Run a program confined to the project. Only the project is writable.

    `network` is off by default and must be ASKED FOR.

    Least privilege, not maximum restriction. Cutting the network
    outright was the easy call and it was wrong: a system meant to do
    anything on a computer that cannot reach one cannot fetch a page,
    download a file, or send anything -- which is a large share of what
    people actually do there. A sandbox that prevents the work is not
    safety, it is amputation.

    So the default is closed and the escalation is explicit. The caller
    declares that this task needs the network, and that declaration is
    recorded in the receipt, so "which runs could talk to the outside"
    is answerable afterwards rather than inferred.
    """
    if not Path(root).is_dir():
        return {"schema": SCHEMA, "verdict": "INDETERMINATE",
                "detail": f"{root!r} is not a directory", "exit_status": None,
                "carrier_qualified": False}
    if not available():
        return {"schema": SCHEMA, "verdict": "INDETERMINATE",
                "detail": "confinement unavailable: "
                          "no user namespace or chroot denied",
                "exit_status": None, "carrier_qualified": False,
                "note": "caller must decide whether to run unconfined"}

    with tempfile.TemporaryDirectory(prefix="brain_confine_") as tmp:
        base = os.path.join(tmp, "root")
        os.makedirs(base, exist_ok=True)
        script = os.path.join(tmp, "program.py")
        Path(script).write_text(
            program if program.endswith("\n") else program + "\n")
        helper = _HELPER.replace("__MOUNTS__", repr(list(_MOUNTS)))
        helper_path = os.path.join(tmp, "helper.py")
        Path(helper_path).write_text(helper)
        try:
            r = subprocess.run(
                ["unshare", "-r", "-m"] + ([] if network else ["-n"]) + \
                [_python_in_chroot(), helper_path, base,
                 os.path.realpath(root), script, "1" if network else "0"],
                timeout=timeout, capture_output=True, text=True)
            return {"schema": SCHEMA,
                    "verdict": "OK" if r.returncode == 0 else "FAILED",
                    "exit_status": r.returncode,
                    "output": ((r.stdout or "") + (r.stderr or ""))[-3000:],
                    # Nonzero may be a setup failure before any confinement.
                    "confined": True if r.returncode == 0 else None,
                    "carrier_qualified": False, "network": bool(network)}
        except subprocess.TimeoutExpired:
            return {"schema": SCHEMA, "verdict": "INDETERMINATE",
                    "exit_status": None, "output": "timed out",
                    "confined": None, "carrier_qualified": False}
        except Exception as exc:
            return {"schema": SCHEMA, "verdict": "INDETERMINATE",
                    "exit_status": None,
                    "output": f"{type(exc).__name__}: {exc}",
                    "confined": False, "carrier_qualified": False}


def run_readonly(program: str, root: str, timeout: int = 60) -> dict:
    """Execute `program` inside the staged read-only `/input` + tmpfs `/work` broker."""
    from canonical.runtime.brokered_workspace_execution_v1 import run_staged_confined_command

    res = run_staged_confined_command(
        root,
        [sys.executable, "-c", program],
        publish=False,
        timeout=timeout,
        allow_cow_hardlinks=True,
    )
    return {
        "schema": SCHEMA,
        "verdict": "OK" if res.get("ok") else "FAILED",
        "exit_status": res.get("exit"),
        "output": ((res.get("stdout") or "") + (res.get("stderr") or ""))[-3000:],
        "confined": bool(res.get("confined")),
        "live_workspace_untouched": bool(res.get("live_workspace_untouched", True)),
        "carrier_qualified": False,
        "network": False,
    }

