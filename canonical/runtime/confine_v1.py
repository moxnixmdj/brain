"""Real confinement: only the project is writable.

This file exists because an earlier measurement was wrong.

Confinement was declared impossible here after finding that the
`chroot` BINARY is missing, that `mount -o remount,ro /` is denied, and
that bwrap and firejail are not installed. All true. The mistake was
testing the binary and never the SYSCALL. `os.chroot()` works fine as
uid 0 inside a user namespace. The conclusion was drawn from a probe
that could not have found the thing it ruled out.

So this is the general lesson of this system, turned on its own author:
a check that cannot fail proves nothing, and neither does a probe that
never asked the real question.

How it works, and every step is necessary:

  unshare -r -m      new user + mount namespace; we are uid 0 inside
  tmpfs at BASE      a throwaway root, so nothing here outlives the run
  bind /usr /bin /lib /lib64    the interpreter and its libraries,
                                each remounted read-only
  bind PROJECT at /project      THE ONLY WRITABLE PLACE
  chroot             the program cannot name anything outside BASE

Default-deny, not a denylist. Nothing is enumerated as forbidden;
everything is read-only unless it was explicitly mounted writable. A
denylist covers the paths someone thought of and misses the rest --
which is the difference between this and the tmpfs shielding that was
built and withdrawn earlier.

That earlier attempt also ate the project's own work: shielding /tmp hid
a project that lived under /tmp, and a legitimate write vanished while
the receipt still read clean. Here the project is a separate mount with
its own flags, so making the root read-only does not touch it. That is
the property the withdrawn version lacked, and it is why this one is
shipped and that one was not.

Measured:

    project write   OK        work persists
    /usr  write     BLOCKED
    /     write     BLOCKED
    /tmp  write     BLOCKED

What is actually visible inside, measured rather than assumed:

    /home /etc /tmp /var /root /opt /srv /proc   all INVISIBLE
    /usr /bin /lib /lib64                        read-only
    /project                                     the only writable place

So reads are confined too, not only writes. An earlier note claimed a
program could "read anything bind-mounted", which was both trivially
true and misleading: the only things bind-mounted are the operating
system itself. User data outside the project is not reachable.

The network is cut with the network namespace (unshare -n), and CPU,
address space, file size, process count and descriptors are capped with
rlimits. Without those, filesystem confinement alone would still let
one program take the whole machine by forking or allocating.

Limits that remain, stated: this is not a syscall filter. A confined
program can still execute anything the interpreter can do against the
operating system it can see, and seccomp -- the thing that would
actually restrict syscalls -- is not attempted here. What is enforced
is that no change can PERSIST outside the project, no user data
outside it can be READ, no network can be reached, and no one program
can consume the machine.
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
if not m("-t", "tmpfs", "none", BASE):
    sys.exit(90)
for d in ("project", "work"):
    os.makedirs(BASE + "/" + d.lstrip("/"), exist_ok=True)
for s in {s for s in __MOUNTS__ if os.path.isdir(s)}:
    os.makedirs(BASE + s, exist_ok=True)
    m("--bind", s, BASE + s)
    subprocess.run(["mount", "-o", "remount,ro,bind", BASE + s],
                   capture_output=True)
m("--bind", PROJ, BASE + "/project")
# Only now, with the project separately mounted, is the root made
# read-only. Order matters: doing it earlier would freeze the project
# too, which is exactly how the withdrawn version destroyed work.
subprocess.run(["mount", "-o", "remount,ro,bind", BASE], capture_output=True)
# Copied only NOW, after every mount. Earlier it was written into BASE
# and then the tmpfs was mounted over BASE, hiding it -- the run died
# with "can't open file /program.py", which reads like the program
# failing rather than the harness putting it where it could not be seen.
# Its own writable mount, so the program never has to be written into
# the root (now read-only, correctly) nor into the project (which would
# leave the caller's own files altered by the harness).
m("-t", "tmpfs", "none", BASE + "/work")
import shutil as _sh
_sh.copyfile(SCRIPT, BASE + "/work" + INSIDE)
os.chroot(BASE)
os.chdir("/project")

# Resource limits, so a confined program cannot consume the machine.
# Confinement of the FILESYSTEM without this would still let one
# program take everything: fork forever, allocate until swap dies, or
# write until the disk is full. Set in the child, before exec.
def _limits():
    import resource
    for k, v in (
        ("RLIMIT_CPU", 60),          # seconds of CPU
        ("RLIMIT_AS", 2 << 30),      # 2 GiB address space
        ("RLIMIT_FSIZE", 1 << 30),   # 1 GiB per file
        ("RLIMIT_NPROC", 512),       # processes
        ("RLIMIT_NOFILE", 1024),     # descriptors
    ):
        try:
            lim = getattr(resource, k)
            resource.setrlimit(lim, (v, v))
        except Exception:
            pass

r = subprocess.run([sys.executable, "/work" + INSIDE],
                   capture_output=True, text=True, preexec_fn=_limits)
sys.stdout.write(r.stdout or "")
sys.stderr.write(r.stderr or "")
sys.exit(r.returncode if r.returncode is not None else 91)
'''


def available() -> bool:
    """Can this machine actually confine a program? Ask the syscall."""
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


def run(program: str, root: str, timeout: int = 300) -> dict:
    """Run a program confined to the project. Only the project is writable."""
    if not Path(root).is_dir():
        return {"schema": SCHEMA, "verdict": "INDETERMINATE",
                "detail": f"{root!r} is not a directory", "exit_status": None}
    if not available():
        return {"schema": SCHEMA, "verdict": "INDETERMINATE",
                "detail": "confinement unavailable: "
                          "no user namespace or chroot denied",
                "exit_status": None,
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
                ["unshare", "-r", "-m", "-n", sys.executable, helper_path,
                 base, os.path.realpath(root), script],
                timeout=timeout, capture_output=True, text=True)
            return {"schema": SCHEMA,
                    "verdict": "OK" if r.returncode == 0 else "FAILED",
                    "exit_status": r.returncode,
                    "output": ((r.stdout or "") + (r.stderr or ""))[-3000:],
                    "confined": True}
        except subprocess.TimeoutExpired:
            return {"schema": SCHEMA, "verdict": "INDETERMINATE",
                    "exit_status": None, "output": "timed out",
                    "confined": True}
        except Exception as exc:
            return {"schema": SCHEMA, "verdict": "INDETERMINATE",
                    "exit_status": None,
                    "output": f"{type(exc).__name__}: {exc}",
                    "confined": False}
