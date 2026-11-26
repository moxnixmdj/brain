#!/usr/bin/env python3
"""A real kernel isolation boundary, and the probes that measure it.

WHY THIS EXISTS
---------------
`confinement_v1` is a disposable git clone plus a subprocess. Its own docstring
says it is "not a sandbox in the kernel sense", and the 2026-11-24 safety review
measured the consequence: `CONFINEMENT_FRONT_DOOR_WIRING_DESIGN_20261124_V1.md`
records a confined command that **wrote a sentinel outside the clone while the
result reported `host_untouched=True` and `verified=True`**. A claim of
confinement that the kernel does not enforce is not a boundary; it is a label.
Every route above it -- the front door, the curriculum, the Perfect Algorithm on
a real computer -- was therefore refused with
`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`, correctly,
because the substrate could not be trusted.

This module replaces the label with the mechanism: Linux namespaces plus a
chroot plus a capability drop, and then it PROVES the result by running a payload
that actively tries to escape and reporting each attempt.

WHAT THE SANDBOX IS (each part is one syscall, none is policy)
--------------------------------------------------------------
* `CLONE_NEWUSER` + `--map-root-user` -- an unprivileged user namespace. Root
  inside it has no authority the host user does not already have; there is no
  setuid binary anywhere in the path.
* `CLONE_NEWNS` -- a private mount namespace. The sandbox root is a fresh tmpfs;
  `/usr`, `/bin`, `/sbin`, `/lib*` are bind-mounted **read-only**. Host paths
  that are not mounted (`/home`, `/root`, `/var`, `/opt`, anything) do not exist
  inside -- not hidden behind a permission bit, absent from the tree.
* `CLONE_NEWPID` -- a fresh pid namespace, so `/proc` shows only this run.
* `CLONE_NEWNET` -- a fresh network namespace with only loopback, so there is no
  route and no resolver: a connection fails in the kernel, not in a filter.
* `CLONE_NEWIPC`, `CLONE_NEWUTS` -- no host shared memory, no host hostname.
* `chroot` -- the root of resolution. Mount requests made after the chroot can
  only name paths inside it.
* **capability drop** (`capset` to empty + `PR_CAPBSET_DROP`) -- after the
  chroot, the payload holds no capabilities, so `mount`, `umount`, `chroot`,
  `ptrace`, `mknod` and `setns` are `EPERM` for it. This is the difference
  between a chroot the payload can undo and one it cannot.
* `/etc` is **built, not mounted** -- a four-line passwd/group, localhost hosts
  file, empty resolv.conf. The host's configuration is not readable from inside.

WHAT THIS IS NOT
----------------
* Not a seccomp filter and not a cgroup. It bounds filesystem, network, process
  visibility, IPC and capabilities; it does not bound every syscall, and it does
  not cap memory or CPU beyond the wall-clock budget the caller sets.
* Not an admission decision. `probe()` measures; whether an admitted capability
  may run is the boundary's decision, and no flag here can make it.
* Not proof for every kernel. `support()` and `probe()` run for real on the
  machine in use; where unprivileged namespaces are unavailable this module
  REFUSES (`isolation: UNAVAILABLE`) rather than falling back to a clone.
  A silent fallback to a weaker substrate is how the false `host_untouched=True`
  happened in the first place.

Zero model calls, zero network at decision time, standard library only.
Authority: NONE. This module executes nothing on the host outside the sandbox.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_OS_ISOLATION_V1"
PROBE_SCHEMA = "PROJECT_BRAIN_OS_ISOLATION_PROBE_V1"

UNAVAILABLE = "UNAVAILABLE__NO_UNPRIVILEGED_NAMESPACES"
REFUSED = "REFUSED__ISOLATION_DID_NOT_MEASURE_AS_CLAIMED"

# The namespaces are the boundary. `--net` is dropped only when the caller
# explicitly asks for network, and the receipt then says so.
_NS_FLAGS = ["--user", "--map-root-user", "--mount", "--pid", "--fork",
             "--ipc", "--uts", "--kill-child"]

# Programs that must exist for the sandbox to be worth anything. Each is a
# read-only mount; a missing one is a refusal, not a silently smaller box.
_RO_BINDS = ("/usr", "/bin", "/sbin", "/lib", "/lib64", "/lib32")


def _unshare() -> str | None:
    return shutil.which("unshare")


# --------------------------------------------------------------------------- #
# the child: setup, then run the payload with no capabilities
# --------------------------------------------------------------------------- #

# Self-contained: it is passed with `python3 -c` because the repository is not
# mounted inside the sandbox (mounting it would put the host tree back in).
_CHILD_SOURCE = r'''
import ctypes, json, os, subprocess, sys, time

libc = ctypes.CDLL("libc.so.6", use_errno=True)

MS_REC, MS_PRIVATE, MS_BIND, MS_RDONLY, MS_REMOUNT = 16384, 1 << 18, 4096, 1, 32
MS_NOSUID, MS_NODEV, MS_NOEXEC = 2, 4, 8
PR_CAPBSET_DROP, PR_SET_NO_NEW_PRIVS = 24, 38
CAP_LAST_CAP = 40

spec = json.loads(sys.stdin.read())


def _numeric_pids():
    try:
        return len([p for p in os.listdir("/proc") if p.isdigit()])
    except OSError:
        return None
root = spec["root"]


def errno():
    return ctypes.get_errno()


def mount(src, dst, flags=0, data=None, fstype=None):
    rc = libc.mount(src.encode() if src else None,
                    dst.encode(),
                    fstype.encode() if fstype else None,
                    flags,
                    data.encode() if data else None)
    if rc != 0:
        raise OSError(errno(), "mount %r -> %r: %s" % (src, dst, os.strerror(errno())))


def fail(stage, error):
    json.dump({"ok": False, "stage": stage, "error": str(error)[:400]}, sys.stdout)
    sys.stdout.flush()
    os._exit(11)


try:
    mount(None, "/", MS_REC | MS_PRIVATE)
    mount("tmpfs", root, 0, "size=%dm,mode=755" % int(spec.get("root_mb", 256)), "tmpfs")
    for name in ("usr", "bin", "sbin", "lib", "lib64", "lib32", "etc", "work", "tmp", "proc", "dev"):
        os.makedirs(os.path.join(root, name), exist_ok=True)
    for name in ("usr", "bin", "sbin", "lib", "lib64", "lib32"):
        src = "/" + name
        if not os.path.isdir(src):
            continue
        dst = os.path.join(root, name)
        mount(src, dst, MS_BIND | MS_REC)
        mount(None, dst, MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV)
    # device files are bind-mounted, never created: mknod of a device node is
    # denied in an unprivileged user namespace, and faking it with a regular
    # file would silently change what a program reads from /dev/null.
    for dev in ("null", "zero", "urandom", "random"):
        src = "/dev/" + dev
        if os.path.exists(src):
            dst = os.path.join(root, "dev", dev)
            open(dst, "a").close()
            mount(src, dst, MS_BIND)
    for src, dst in (spec.get("extra_rw") or []):
        target = os.path.join(root, dst.lstrip("/"))
        os.makedirs(target, exist_ok=True)
        mount(src, target, MS_BIND | MS_REC)
    for src, dst in (spec.get("extra_ro") or []):
        target = os.path.join(root, dst.lstrip("/"))
        os.makedirs(target, exist_ok=True)
        mount(src, target, MS_BIND | MS_REC)
        mount(None, target, MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV)
    mount(spec["work"], os.path.join(root, "work"), MS_BIND | MS_REC)
    for name, body in (spec.get("etc") or {}).items():
        path = os.path.join(root, "etc", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(body)
    os.chroot(root)
    os.chdir("/work")
    mount("proc", "/proc", 0, None, "proc")
    mount("tmpfs", "/tmp", 0, "size=64m,mode=1777", "tmpfs")
except BaseException as error:  # noqa: BLE001 - a setup failure is a refusal
    fail("setup", error)

# Nothing outside this process may keep a descriptor: an inherited fd to a host
# directory is the classic way out of a chroot.
try:
    os.closerange(3, 256)
except BaseException:
    pass

# Drop every capability. After this line the payload cannot mount, umount,
# chroot, ptrace, mknod or setns -- the chroot stops being undoable.
try:
    libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    for cap in range(CAP_LAST_CAP + 1):
        libc.prctl(PR_CAPBSET_DROP, cap, 0, 0, 0)
    header = (ctypes.c_uint32 * 2)(0x20080522, 0)  # _LINUX_CAPABILITY_VERSION_3
    data = (ctypes.c_uint32 * 6)(0, 0, 0, 0, 0, 0)  # eff, perm, inh -- all zero
    libc.capset(header, data)
    caps_dropped = True
except BaseException as error:  # noqa: BLE001
    caps_dropped = False
    sys.stderr.write("capability drop failed: %r\n" % (error,))

env = dict(spec.get("env") or {})
started = time.monotonic()
try:
    done = subprocess.run(spec["argv"], cwd="/work", env=env,
                          stdin=subprocess.DEVNULL,
                          capture_output=True, text=True,
                          timeout=float(spec.get("budget_s", 60)))
    rc, out, err = done.returncode, done.stdout, done.stderr
    timed_out = False
except subprocess.TimeoutExpired as expired:
    rc, out, err = None, (expired.stdout or b"").decode("utf-8", "replace") if isinstance(expired.stdout, bytes) else (expired.stdout or ""), "BUDGET_EXCEEDED"
    timed_out = True
except FileNotFoundError as missing:
    rc, out, err, timed_out = 127, "", "FileNotFoundError: %s" % (missing,), False

json.dump({"ok": True, "rc": rc, "stdout": out[-20000:], "stderr": err[-8000:],
           "timed_out": timed_out, "caps_dropped": caps_dropped,
           "pid_count": _numeric_pids(),
           "uid": os.getuid(), "seconds": round(time.monotonic() - started, 3)},
          sys.stdout)
sys.stdout.flush()
'''


# --------------------------------------------------------------------------- #
# the payload used by probe(): it tries to escape, and reports what happened
# --------------------------------------------------------------------------- #

_PROBE_PAYLOAD = r'''
import json, os, socket, sys

findings = {}


def attempt(name, fn):
    try:
        value = fn()
        findings[name] = {"blocked": False, "value": value}
    except BaseException as error:  # noqa: BLE001
        findings[name] = {"blocked": True, "error": type(error).__name__,
                          "errno": getattr(error, "errno", None),
                          "message": str(error)[:160]}


canary_read = sys.argv[1]
canary_write = sys.argv[2]
canary_data = sys.argv[3]

attempt("read_host_canary", lambda: open(canary_read).read()[:40])
attempt("write_host_path", lambda: open(canary_write, "w").write("escaped") or "WROTE")
attempt("list_host_dir", lambda: sorted(os.listdir(os.path.dirname(canary_read)))[:3])
attempt("tcp_connect", lambda: socket.create_connection(("1.1.1.1", 80), timeout=2).close() or "CONNECTED")
attempt("dns_resolve", lambda: socket.gethostbyname("example.com"))
attempt("udp_connect", lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).connect(("8.8.8.8", 53)) or "CONNECTED")
def _mount():
    libc = __import__("ctypes").CDLL("libc.so.6", use_errno=True)
    os.makedirs("/tmp/over", exist_ok=True)
    if libc.mount(b"tmpfs", b"/tmp/over", b"tmpfs", 0, None) != 0:
        err = __import__("ctypes").get_errno()
        raise OSError(err, os.strerror(err))
    return "MOUNTED"


attempt("mount_tmpfs", _mount)
attempt("chroot_again", lambda: os.chroot("/tmp") or "CHROOTED")
attempt("read_host_proc", lambda: open("/proc/1/cmdline").read()[:60])
attempt("proc_one_root_home", lambda: sorted(os.listdir("/proc/1/root/home")))
attempt("escape_via_proc_root", lambda: open("/proc/1/root/etc/hostname").read()[:40])
attempt("host_pids", lambda: len([p for p in os.listdir("/proc") if p.isdigit()]))
attempt("dev_mem", lambda: open("/dev/mem", "rb").read(1))
attempt("host_home", lambda: sorted(os.listdir("/home")))
attempt("uid", lambda: os.getuid())
attempt("caps", lambda: open("/proc/self/status").read().split("CapEff:")[1].split()[0])
attempt("etc_passwd", lambda: open("/etc/passwd").read()[:120])
attempt("write_readonly_bind", lambda: open("/usr/.escape", "w").write("x") or "WROTE")
json.dump(findings, open("/work/.probe.json", "w"), indent=1)
'''


def _canary_root() -> pathlib.Path:
    base = pathlib.Path(tempfile.mkdtemp(prefix="brain-isolation-canary-"))
    (base / "inside-outside.txt").write_text("host-canary-do-not-read\n", encoding="utf-8")
    return base


def support() -> dict[str, Any]:
    """Is unprivileged namespacing available here? Asked by running it, once."""
    binary = _unshare()
    if binary is None:
        return {"schema": SCHEMA, "available": False, "reason": UNAVAILABLE,
                "detail": "the `unshare` program is not on this machine"}
    try:
        done = subprocess.run([binary, "--user", "--map-root-user", "--mount",
                               "--pid", "--fork", "--net", sys.executable, "-c",
                               "import os;print(os.getuid(), len(os.listdir('/proc')))"],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"schema": SCHEMA, "available": False, "reason": UNAVAILABLE,
                "detail": repr(error)}
    if done.returncode != 0:
        return {"schema": SCHEMA, "available": False, "reason": UNAVAILABLE,
                "detail": (done.stderr or "")[-400:]}
    return {"schema": SCHEMA, "available": True, "reason": None,
            "detail": (done.stdout or "").strip()}


def run(argv: Sequence[str], *, work_dir: str | pathlib.Path,
        budget_s: float = 60.0, env: Mapping[str, str] | None = None,
        allow_network: bool = False, root_mb: int = 512,
        extra_ro: Sequence[Sequence[str]] = (),
        extra_rw: Sequence[Sequence[str]] = ()) -> dict[str, Any]:
    """Run one argv inside the sandbox. Fail-closed: no fallback substrate.

    Returns a receipt. `receipt["isolated"]` is True only if the child reported
    that it reached the payload with capabilities dropped inside a fresh
    namespace; a setup failure returns `ok: False` with its stage, never a run.
    """
    binary = _unshare()
    if binary is None:
        return {"schema": SCHEMA, "ok": False, "isolated": False, "refused": UNAVAILABLE,
                "stage": "support", "detail": "`unshare` is not on this machine"}
    work = pathlib.Path(work_dir).resolve()
    if not work.is_dir():
        return {"schema": SCHEMA, "ok": False, "isolated": False,
                "refused": "REFUSED__WORK_DIR_MISSING", "stage": "admit",
                "detail": str(work)}
    root = tempfile.mkdtemp(prefix="brain-isolation-root-")
    real_env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/work",
                "TMPDIR": "/tmp", "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "0",
                "TERM": "dumb"}
    for key, value in dict(env or {}).items():
        if str(key).startswith("LD_"):
            continue  # never let the caller inject a loader into the payload
        real_env[str(key)] = str(value)
    etc = {
        "passwd": "root:x:0:0:root:/root:/bin/sh\nsandbox:x:1000:1000:sandbox:/work:/bin/sh\n",
        "group": "root:x:0:\nsandbox:x:1000:\n",
        "hosts": "127.0.0.1 localhost\n::1 localhost\n",
        "resolv.conf": "",
        "nsswitch.conf": "passwd: files\ngroup: files\nhosts: files\n",
    }
    read_only = [[str(src), str(dst)] for src, dst in extra_ro]
    for src, _dst in read_only:
        if not pathlib.Path(src).exists():
            shutil.rmtree(root, ignore_errors=True)
            return {"schema": SCHEMA, "ok": False, "isolated": False,
                    "refused": "REFUSED__EXTRA_RO_SOURCE_MISSING", "stage": "admit",
                    "detail": src}
    writable = [[str(src), str(dst)] for src, dst in extra_rw]
    spec = {"root": root, "work": str(work), "argv": [str(a) for a in argv],
            "budget_s": float(budget_s), "env": real_env, "etc": etc,
            "root_mb": int(root_mb), "extra_ro": read_only, "extra_rw": writable}
    flags = list(_NS_FLAGS)
    if not allow_network:
        flags.append("--net")
    command = [binary] + flags + [sys.executable, "-c", _CHILD_SOURCE]
    started = time.monotonic()
    try:
        done = subprocess.run(command, input=json.dumps(spec), capture_output=True,
                              text=True, timeout=float(budget_s) + 90.0, cwd="/")
    except subprocess.TimeoutExpired:
        shutil.rmtree(root, ignore_errors=True)
        return {"schema": SCHEMA, "ok": False, "isolated": False,
                "refused": "BUDGET_EXCEEDED", "stage": "outer_budget",
                "seconds": round(time.monotonic() - started, 3)}
    shutil.rmtree(root, ignore_errors=True)
    try:
        payload = json.loads(done.stdout or "{}")
    except json.JSONDecodeError:
        payload = {"ok": False, "stage": "child_output",
                   "error": (done.stderr or done.stdout or "")[-400:]}
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "ok": bool(payload.get("ok")),
        "isolated": bool(payload.get("ok")) and bool(payload.get("caps_dropped")),
        "allow_network": bool(allow_network),
        "namespaces": ["user", "mount", "pid", "ipc", "uts"]
                       + ([] if allow_network else ["net"]),
        "network": "HOST" if allow_network else "NONE__FRESH_NETNS",
        "argv": spec["argv"],
        "work_dir": str(work),
        "seconds": round(time.monotonic() - started, 3),
        "returncode": payload.get("rc"),
        "stdout": payload.get("stdout", ""),
        "stderr": payload.get("stderr", ""),
        "timed_out": bool(payload.get("timed_out")),
        "caps_dropped": bool(payload.get("caps_dropped")),
        "pid_count": payload.get("pid_count"),
        "uid_in_sandbox": payload.get("uid"),
        "payload_seconds": payload.get("seconds"),
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
    }
    if not receipt["ok"]:
        receipt["refused"] = REFUSED
        receipt["stage"] = payload.get("stage")
        receipt["detail"] = payload.get("error")
    return receipt


def probe(*, budget_s: float = 60.0) -> dict[str, Any]:
    """Admission by measurement: run a payload that tries every escape.

    The verdict is `ISOLATED` only when every attempt that must be blocked is
    blocked AND the payload is measured to hold no capabilities. Anything else
    is `NOT_ISOLATED`, with the failing attempts named -- the exact defect of
    2026-11-24 was a claim of isolation that had never been attacked.
    """
    state = support()
    if not state.get("available"):
        return {"schema": PROBE_SCHEMA, "verdict": "UNAVAILABLE",
                "isolated": False, "reason": state.get("reason"),
                "detail": state.get("detail")}
    canary = _canary_root()
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-isolation-work-"))
    try:
        receipt = run([sys.executable, "-c", _PROBE_PAYLOAD,
                       str(canary / "inside-outside.txt"),
                       str(canary / "written-from-inside.txt"),
                       "canary"],
                      work_dir=work, budget_s=budget_s)
        findings: dict[str, Any] = {}
        probe_file = work / ".probe.json"
        if probe_file.is_file():
            try:
                findings = json.loads(probe_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                findings = {}
        escaped = sorted(name for name, row in findings.items()
                         if not row.get("blocked") and name in _MUST_BLOCK)
        caps = (findings.get("caps") or {}).get("value")
        canary_written = (canary / "written-from-inside.txt").exists()
        verdict = "ISOLATED"
        reasons: list[str] = []
        if not receipt.get("isolated"):
            verdict = "NOT_ISOLATED"
            reasons.append("payload did not reach a capability-dropped namespace")
        if escaped:
            verdict = "NOT_ISOLATED"
            reasons.append("escape succeeded: " + ", ".join(escaped))
        if canary_written:
            verdict = "NOT_ISOLATED"
            reasons.append("a host file outside the sandbox was written")
        if findings and caps not in (None, "0000000000000000"):
            verdict = "NOT_ISOLATED"
            reasons.append("payload still holds capabilities: %s" % caps)
        for name, ok in _MUST_HAVE.items():
            row = findings.get(name) or {}
            if not (not row.get("blocked") and ok(row.get("value"))):
                verdict = "NOT_ISOLATED"
                reasons.append("%s did not hold: %r" % (name, row.get("value", row.get("message"))))
        if not findings:
            verdict = "NOT_ISOLATED"
            reasons.append("the probe payload produced no findings")
        return {
            "schema": PROBE_SCHEMA,
            "verdict": verdict,
            "isolated": verdict == "ISOLATED",
            "reasons": reasons,
            "caps_after_drop": caps,
            "host_canary_written": canary_written,
            "attempts": findings,
            "receipt": receipt,
            "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(canary, ignore_errors=True)


_MUST_BLOCK = (
    "read_host_canary", "write_host_path", "list_host_dir", "tcp_connect",
    "dns_resolve", "udp_connect", "mount_tmpfs", "chroot_again",
    "proc_one_root_home", "escape_via_proc_root", "write_readonly_bind",
    "dev_mem", "host_home",
)

# /proc/1 inside a fresh pid namespace is the sandbox's own child, so reading
# its cmdline is not an escape -- what would be an escape is seeing a real host
# process. These are the pid-namespace facts that must hold, checked by value.
_MUST_HAVE = {"host_pids": lambda value: isinstance(value, int) and value <= 8}


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "probe":
        print(json.dumps(probe(), indent=2, sort_keys=True))
        return 0
    print(json.dumps({"schema": SCHEMA, "usage": "python3 -m canonical.runtime.os_isolation_v1 probe"},
                     indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
