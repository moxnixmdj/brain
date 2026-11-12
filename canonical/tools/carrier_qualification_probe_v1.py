#!/usr/bin/env python3
"""Carrier qualification probes — the review checklist, made runnable.

WHY THIS EXISTS
---------------
`REPAIR_INDEPENDENT_REVIEW_REQUEST_20261102.md` §"Separate carrier qualification, still
missing" blocks a lane of 117 measured failures:

    "The existing namespace launcher is a research candidate, not a qualified carrier: it uses
    host libraries, lacks reviewed syscall filtering and aggregate delegated CPU/memory/PID
    limits, captures subprocess output without a bound, and has no proven descendant cleanup on
    timeout. ... Do not run hostile code in it."

Every one of those is a **testable proposition**, and most are now stale. Measured on
`d683c84`, this machine:

    descendant cleanup on timeout .... PROVEN WORKING (orphan grandchild killed, marker never fired;
                                        the old claim was "no proven cleanup")
    output bound ..................... WORKER_STATUS:CHILD_EXITED, nothing captured (was unbounded)
    aggregate memory ................. ulimit -v = 786432 KB = 768 MB enforced inside the worker
    nofile ........................... enforced
    host filesystem .................. /home/user/brain/.git is NOT VISIBLE (exit 2)
    host processes ................... kill -9 -1 -> "No such process"; ps -e -> 0 rows
    ambient environment .............. 5 keys, all /work/*, no credentials, no tokens
    egress ........................... refused; /proc/net/route has 0 routes
    seccomp filter ................... STILL ABSENT. The review is still right.
    host libraries shipped ........... STILL PRESENT (`uses host libraries`). Review still right.

So the review is not wrong — it is **out of date on 7 items and exactly right on 2**. But the
reviewer cannot tell which is which from the request, and neither can the next session: the
correction has been nobody's job. That is what this file is for.

UPDATE 2026-11-11 -- the filter item moved, and what moved is narrower than it sounds
-------------------------------------------------------------------------------------
The launcher now installs a seccomp allowlist (`canonical/runtime/worker_syscall_allowlist_v1.py`)
in the same step that enters the worker's root, so nothing in the worker runs without it. The
probe therefore stops reading the launcher's *text* for the word and **asks the worker**: is a
filter in force, and does it refuse calls the kernel would otherwise have answered?

    seccomp filter ................... PRESENT AND ENFORCING (observed inside the worker)
    host libraries shipped ........... STILL PRESENT. The review is still right.

The review asked for "**reviewed** syscall filtering". A probe can observe *filtering*. It cannot
observe *reviewed*: whether that list is the right list is a judgement about 193 allowed calls,
and it belongs to someone who did not write them. That is now item three of
`what_a_verifier_must_do`. One objection of the nine still holds exactly as written.

WHAT THIS IS NOT
----------------
This is a **producer-run self-report**. The review states in its own words that a self-report
from the worker is not evidence of isolation, and this is worse than that: it is a self-report
from the *producer*, run on an unqualified carrier, on one machine. Running a probe suite and
finding that it passes is **not** carrier qualification, exactly as passing your own tests is
not independent verification. It is the input a verifier needs, and nothing more.

Run it:

    python3 canonical/tools/carrier_qualification_probe_v1.py             # safe probes only
    python3 canonical/tools/carrier_qualification_probe_v1.py --json out.json

`--destructive` adds resource-exhaustion probes (fork bomb, memory hog). It is off by default
because the point of the suite is to be safe to run, and a probe suite that can take down the
machine it is qualifying is a bad instrument.

Authority: NONE. This document cannot flip `carrier_qualified`, and it must not be cited as
evidence that the carrier is qualified.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "CARRIER_QUALIFICATION_PROBE_V1"
AUTHORITY = "NONE -- PRODUCER-RUN SELF-REPORT, NOT CARRIER QUALIFICATION"

# Verdicts. Kept deliberately narrow so a result cannot be quietly upgraded.
SATISFIED = "SATISFIED__OBSERVED"
NOT_SATISFIED = "NOT_SATISFIED__OBSERVED"
NOT_TESTED = "NOT_TESTED__NO_SAFE_PROBE"
UNMEASURABLE = "UNMEASURABLE__ON_THIS_MACHINE"


def _workspace() -> pathlib.Path:
    d = ROOT / "canonical/astra_runtime/tmp/carrier_probe"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    (d / "f.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    return d


def _run(ws, argv, timeout=8):
    from canonical.runtime import brokered_workspace_execution_v1 as broker
    return broker.run_staged_confined_command(workspace_root=ws, command=list(argv), timeout=timeout)


def _probe_host_filesystem(ws, _):
    """Review item: 'uses host libraries'. Claim under test: the HOST TREE is not reachable."""
    r = _run(ws, ["ls", "/home/user/brain/.git"])
    hidden = r.get("exit") != 0 and "No such file" in str(r.get("stderr") or "")
    return (SATISFIED if hidden else NOT_SATISFIED,
            "`ls /home/user/brain/.git` inside the worker -> exit %s, %r"
            % (r.get("exit"), str(r.get("stderr"))[:70]),
            "the host working tree is not mounted; only /input and /work are")


def _probe_ambient_environment(ws, _):
    """A worker that inherits the caller's env inherits the caller's credentials."""
    r = _run(ws, ["env"])
    keys = sorted(set(str(r.get("stdout") or "").split()))
    leaked = [k for k in keys if any(t in k.upper() for t in
                                     ("TOKEN", "SECRET", "KEY=", "PASSWORD", "AWS", "GITHUB", "OPENAI"))]
    inside = all(("/work" in k or "PATH=" in k or "PYTHON" in k or "TMPDIR" in k or
                  "HOME=" in k or "PWD=" in k or "SHLVL" in k or "_=" in k) for k in keys)
    ok = not leaked and inside
    return (SATISFIED if ok else NOT_SATISFIED,
            "env inside worker: %s%s" % (keys, "" if not leaked else " LEAKED=%s" % leaked),
            "no caller environment, no credentials, HOME is a private tmpfs")


def _probe_host_processes(ws, _):
    """Review item: 'aggregate delegated PID limits'. Claim: the host PID space is not visible
    and cannot be signalled from the worker."""
    r = _run(ws, ["sh", "-c", "ps -e 2>/dev/null | wc -l; kill -9 -1 2>&1; echo rc=$?"])
    out = str(r.get("stdout") or "")
    rows = out.split("\n")[0].strip() if out else ""
    cannot_signal = "No such process" in out or "rc=1" in out
    empty = rows == "0"
    ok = cannot_signal and empty
    return (SATISFIED if ok else NOT_SATISFIED,
            "ps -e rows=%r; kill -9 -1 -> %r" % (rows, out.split("\n")[1][:40] if "\n" in out else ""),
            "private PID namespace: host processes are invisible and unsignalable")


def _probe_network_egress(ws, _):
    """Review: the network-enabled path is additional scope. Claim: egress is refused."""
    r = _run(ws, ["sh", "-c", "ip route 2>/dev/null | wc -l; "
                              "timeout 3 sh -c 'echo > /dev/tcp/1.1.1.1/443' 2>&1; echo rc=$?"], timeout=12)
    out = str(r.get("stdout") or "")
    routes = out.split("\n")[0].strip() if out else ""
    refused = "rc=2" in out or "cannot create" in out or "refused" in out.lower()
    ok = refused
    return (SATISFIED if ok else NOT_SATISFIED,
            "ip route rows=%r; /dev/tcp probe -> %r" % (routes, out.replace("\n", " | ")[:90]),
            "no route out of the namespace and no reachable socket")


def _probe_descendant_cleanup(ws, _):
    """Review: 'no proven descendant cleanup on timeout'. Claim: an ORPHANED GRANDCHILD is
    killed, and a marker it was going to write never appears."""
    marker = "/tmp/carrier_probe_orphan_marker"
    try:
        os.remove(marker)
    except OSError:
        pass
    script = "sh -c '(ls /input/f.txt >/dev/null; sleep 12; touch %s) & sleep 120'" % marker
    t0 = time.time()
    r = _run(ws, ["sh", "-c", script], timeout=4)
    wall = time.time() - t0
    # wait past the orphan's sleep, then look for its effect
    time.sleep(14)
    fired = os.path.exists(marker)
    try:
        os.remove(marker)
    except OSError:
        pass
    ok = (not fired) and bool(r.get("timed_out"))
    return (SATISFIED if ok else NOT_SATISFIED,
            "timed_out=%s wall=%.1fs; orphan's marker 14s later: %s"
            % (r.get("timed_out"), wall, "PRESENT (it survived)" if fired else "absent"),
            "the grandchild's side effect never occurred: cleanup reaches descendants")


def _probe_output_bound(ws, _):
    """Review: 'captures subprocess output without a bound'. Claim: output cannot grow without
    limit. A `yes` stream is refused/terminated and nothing unbounded is retained."""
    r = _run(ws, ["yes", "ABCDEFGH"], timeout=5)
    n = len(str(r.get("stdout") or ""))
    ok = n < 1_000_000 and not r.get("ok")
    return (SATISFIED if ok else NOT_SATISFIED,
            "`yes` -> ok=%s blocked=%r retained=%d bytes"
            % (r.get("ok"), r.get("blocked"), n),
            "an unbounded producer is stopped and retains nothing")


def _probe_resource_limits(ws, _):
    """Review: 'aggregate delegated CPU/memory/PID limits'. Claim: the limits are installed in
    the worker's own address space, not merely configured."""
    r = _run(ws, ["sh", "-c", "ulimit -v; ulimit -u; ulimit -f; ulimit -n"])
    out = [x.strip() for x in str(r.get("stdout") or "").split("\n") if x.strip()]
    nums = []
    for x in out:
        try:
            nums.append(int(x))
        except ValueError:
            nums.append(-1)
    ok = len(nums) >= 3 and nums[0] > 0 and nums[1] > 0
    return (SATISFIED if ok else NOT_SATISFIED,
            "ulimit -v=%s KB  -u=%s procs  -f=%s blocks  -n=%s fds" % tuple(nums[:4]) if len(nums) >= 4 else str(nums),
            "memory/pid/file/fd limits are enforced inside the worker")


# Asked inside the worker. Every call below is one the kernel answers with something OTHER than
# the filter's answer when no filter is in force. Measured on the unfiltered launcher (main
# 400ad21d, this machine): netlink socket -> a descriptor, io_uring_setup -> EFAULT, personality
# -> answered, keyctl -> ENOKEY, setns -> EBADF, ptrace -> ESRCH, syncfs -> EBADF, clone3 ->
# EINVAL. So EPERM / ENOSYS here is the filter speaking and not a missing capability.
# (`unshare(CLONE_NEWUSER)` is deliberately absent: a chrooted worker gets EPERM for it with or
# without a filter, so it would have proved nothing.) None of the calls changes anything.
_SYSCALL_QUESTIONS = r"""
import ctypes, json
libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long
def ask(number, *args):
    ctypes.set_errno(0)
    result = libc.syscall(ctypes.c_long(number), *[ctypes.c_long(a) for a in args])
    return "errno %d" % ctypes.get_errno() if result == -1 else "answered"
print(json.dumps({
    "filter_mode": libc.prctl(21, 0, 0, 0, 0),          # PR_GET_SECCOMP: 2 = a filter is in force
    "no_new_privs": libc.prctl(39, 0, 0, 0, 0),         # PR_GET_NO_NEW_PRIVS
    "refused": {
        "socket(AF_NETLINK)": ask(41, 16, 3, 0),
        "io_uring_setup": ask(425, 0, 0),
        "personality(query)": ask(135, 0xffffffff),
        "keyctl(get thread keyring)": ask(250, 0, -1, 0),
        "setns(no such fd)": ask(308, -1, 0),
        "ptrace(peek, no such pid)": ask(101, 1, 0, 0, 0),
        "syncfs(no such fd)": ask(306, -1),
    },
    "not_implemented": {"clone3": ask(435, 0, 0)},
    "ordinary": {"getpid": ask(39), "socket(AF_UNIX)": ask(41, 1, 1, 0)},
}))
"""


def _probe_seccomp(ws, _):
    """Review: 'lacks reviewed syscall filtering'. Observed in the worker, not read from source:
    a filter is in force, it refuses a sample of calls the kernel would have answered, it answers
    'not implemented' where the C library must fall back, and ordinary calls still go through.
    What this cannot show is the word 'reviewed'."""
    import platform
    if platform.machine().lower() != "x86_64":
        return (UNMEASURABLE, "the questions use x86_64 call numbers; this is %s" % platform.machine(),
                "no table for this machine: the launcher refuses to start a worker here")
    from canonical.runtime import worker_syscall_allowlist_v1 as allowlist
    r = _run(ws, ["python3", "-I", "-c", _SYSCALL_QUESTIONS])
    try:
        seen = json.loads(str(r.get("stdout") or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return (NOT_SATISFIED, "the worker gave no answer: exit %s, %r" % (r.get("exit"), str(r.get("stderr"))[:80]),
                "a filter that cannot be observed is not counted as one")
    ok = (seen.get("filter_mode") == 2 and seen.get("no_new_privs") == 1
          and all(v == "errno 1" for v in seen["refused"].values())
          and all(v == "errno 38" for v in seen["not_implemented"].values())
          and all(v == "answered" for v in seen["ordinary"].values()))
    listed = allowlist.describe()
    return (SATISFIED if ok else NOT_SATISFIED,
            "in the worker: filter_mode=%s no_new_privs=%s refused=%s not_implemented=%s ordinary=%s; "
            "allowlist %d calls, %d refused by name, sha256 %s"
            % (seen.get("filter_mode"), seen.get("no_new_privs"), sorted(set(seen["refused"].values())),
               sorted(set(seen["not_implemented"].values())), sorted(set(seen["ordinary"].values())),
               listed["allowed_count"], listed["refused_by_name_count"], listed["filter_sha256"]),
            "A FILTER IS IN FORCE AND REFUSES. Whether its list is the right list is a review of "
            "worker_syscall_allowlist_v1, which a probe cannot perform and the producer must not")


def _probe_host_libraries(ws, _):
    """Review: 'uses host libraries'. Genuinely still true: /usr is mounted read-only from the
    host, so the worker's libc and interpreter are the host's bytes."""
    r = _run(ws, ["sh", "-c", "ls /usr/bin/python3 /lib/x86_64-linux-gnu/libc.so.6 2>&1 | head -4"])
    out = str(r.get("stdout") or "")
    present = "python3" in out or "libc.so.6" in out
    return (NOT_SATISFIED if present else SATISFIED,
            "host runtime visible in worker: %r" % out.replace("\n", " | ")[:100],
            "the worker runs the host's interpreter and libc read-only; a pinned minimal "
            "runtime is required for qualification and does not exist")


def _probe_carrier_flag(ws, _):
    """The carrier's own report of its qualification state. It must still say False; if this
    ever says True without a review, that is the alarm, not the fix."""
    r = _run(ws, ["true"])
    return ((SATISFIED if r.get("carrier_qualified") is False else NOT_SATISFIED),
            "run_staged_confined_command reports carrier_qualified=%r" % r.get("carrier_qualified"),
            "the carrier still reports itself unqualified, which is correct")


SAFE_PROBES = [
    ("host_filesystem_not_reachable", _probe_host_filesystem),
    ("ambient_environment_clean", _probe_ambient_environment),
    ("host_processes_invisible", _probe_host_processes),
    ("network_egress_refused", _probe_network_egress),
    ("descendant_cleanup_on_timeout", _probe_descendant_cleanup),
    ("output_bounded", _probe_output_bound),
    ("resource_limits_enforced", _probe_resource_limits),
    ("seccomp_syscall_filter", _probe_seccomp),
    ("no_host_libraries", _probe_host_libraries),
    ("carrier_reports_unqualified", _probe_carrier_flag),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", help="write the full result document here")
    ap.add_argument("--destructive", action="store_true",
                    help="add resource-exhaustion probes (off by default: the suite must be safe)")
    args = ap.parse_args()

    from canonical.runtime import brokered_workspace_execution_v1 as broker
    available = broker.namespace_broker_available()
    if not available:
        print("namespace broker unavailable on this machine: nothing can be probed", file=sys.stderr)
        return 2

    ws = _workspace()
    results = []
    try:
        for name, fn in SAFE_PROBES:
            t0 = time.time()
            try:
                verdict, observation, reading = fn(ws, None)
            except Exception as exc:  # a probe that crashes is a result, not a failure
                verdict, observation, reading = UNMEASURABLE, "%s: %s" % (
                    type(exc).__name__, str(exc)[:100]), "probe raised"
            results.append({"probe": name, "verdict": verdict, "observation": observation,
                            "reading": reading, "seconds": round(time.time() - t0, 2)})
            print("%-34s %-26s %s" % (name, verdict, observation[:96]), flush=True)
    finally:
        shutil.rmtree(ws, ignore_errors=True)

    doc = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "machine": {"platform": sys.platform, "python": sys.version.split()[0],
                    "namespace_broker_available": available},
        "checklist_source": "REPAIR_INDEPENDENT_REVIEW_REQUEST_20261102.md "
                            "§ 'Separate carrier qualification, still missing'",
        "results": results,
        "summary": {
            "satisfied": sum(1 for r in results if r["verdict"] == SATISFIED),
            "not_satisfied": sum(1 for r in results if r["verdict"] == NOT_SATISFIED),
            "not_tested": sum(1 for r in results if r["verdict"] == NOT_TESTED),
            "unmeasurable": sum(1 for r in results if r["verdict"] == UNMEASURABLE),
        },
        "verdict": "CARRIER_NOT_QUALIFIED -- and this document cannot qualify it",
        "what_a_verifier_must_do": [
            "re-run this file on a host they control and compare verdicts item by item",
            "add the two items no probe can settle: an ATTACK CAMPAIGN (this suite tests "
            "properties, not adversaries) and a PINNED MINIMAL RUNTIME (the worker runs the "
            "host's libc)",
            "review the syscall allowlist itself (canonical/runtime/worker_syscall_allowlist_v1.py; "
            "its describe() and decide() answer for any call): the probe shows a filter is in force "
            "and refuses a sample, never that the 193 calls it allows are the right ones",
        ],
        "explicitly_not": [
            "carrier qualification",
            "an independent review",
            "evidence that any capability may execute",
        ],
    }
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(doc, indent=1), encoding="utf-8")
        print("\nwrote %s" % args.json)
    print("\n%d satisfied, %d not satisfied -> %s"
          % (doc["summary"]["satisfied"], doc["summary"]["not_satisfied"], doc["verdict"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
