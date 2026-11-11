"""A confined worker may knock only on the kernel doors that are on one list.

`REPAIR_INDEPENDENT_REVIEW_REQUEST_20261102.md` lists what the namespace launcher lacks before it
may carry code nobody has read. One item is "reviewed syscall filtering". Until 2026-11-11 there
was no filtering to review: a worker inside the namespaces could still call `bpf`,
`io_uring_setup`, `keyctl`, `ptrace`, open a netlink socket -- every door kernel escapes are
written with -- and be answered by the kernel itself.

These tests pin three things, in this order of importance:

1. **Nothing runs in the worker without the filter**, and if the filter cannot be installed
   nothing runs at all (the last class).
2. **The list is the list**: the shipped bytes allow exactly the declared calls, refuse the named
   ones, answer "not implemented" for everything else including calls that do not exist yet, and
   kill a caller that switches instruction set to walk around the table.
3. **Ordinary work is not refused**: a project's tests, subprocesses, threads, a loopback
   server, `make`.

What they do not pin is the word "reviewed". The producer wrote the list. `PINNED` below is
the hash of the producer's bytes, so that a reviewer's approval of one exact program cannot
silently become approval of another; it is not that approval.

Run:  PYTHONPATH=. python3 canonical/tests/test_a_confined_worker_runs_behind_a_syscall_allowlist_v1.py
"""
from __future__ import annotations

import ctypes
import ctypes.util
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import worker_syscall_allowlist_v1 as allowlist  # noqa: E402
from canonical.runtime import zero_ambient_namespace_launcher_v1 as launcher  # noqa: E402

# The exact program the producer shipped on 2026-11-11. If this fails, the list changed: say so
# in the change, re-measure, and update the hash on purpose.
PINNED = "26cd1e65305ccf034a213df6a5f33a2ba5cda2e718a6fc418dff5b082f2617b6"

N = allowlist.X86_64
X86_64 = platform.machine().lower() == "x86_64"
HEADER = pathlib.Path("/usr/include/x86_64-linux-gnu/asm/unistd_64.h")
NEVER = (
    "mount umount2 pivot_root chroot ptrace bpf perf_event_open userfaultfd io_uring_setup "
    "io_uring_enter io_uring_register keyctl add_key request_key unshare setns init_module "
    "finit_module delete_module kexec_load kexec_file_load open_by_handle_at process_vm_readv "
    "process_vm_writev reboot swapon swapoff settimeofday clock_settime personality seccomp mbind "
    "move_pages fsopen fsmount move_mount open_tree pidfd_getfd kcmp acct quotactl syslog iopl "
    "ioperm modify_ldt vhangup sethostname setdomainname sync syncfs setgroups"
).split()


def decide(name_or_number, *args, **kw):
    number = N[name_or_number] if isinstance(name_or_number, str) else name_or_number
    return allowlist.decide(number, args, arch="x86_64", **kw)


class TheListIsTheListTests(unittest.TestCase):
    def test_no_call_is_listed_twice_and_the_three_lists_do_not_overlap(self):
        allowed, refused, checked = allowlist.allowed_names(), allowlist.refused_names(), list(allowlist.ARGUMENT_CHECKED)
        everything = allowed + refused + checked
        self.assertEqual(len(everything), len(set(everything)))
        self.assertEqual(set(everything), set(N), "a number nobody uses, or a name with no number")

    @unittest.skipUnless(HEADER.is_file(), "no kernel header on this host to compare with")
    def test_every_number_is_the_kernel_headers_number(self):
        header = {m.group(1): int(m.group(2))
                  for m in re.finditer(r"#define __NR_(\w+)\s+(\d+)", HEADER.read_text())}
        wrong = {name: (number, header.get(name)) for name, number in N.items() if header.get(name) != number}
        self.assertEqual(wrong, {}, "a wrong number allows or refuses a different call than the one named")

    @unittest.skipUnless(X86_64 and ctypes.util.find_library("seccomp"), "no libseccomp on this host to compare with")
    def test_every_number_is_libseccomps_number(self):
        lib = ctypes.CDLL(ctypes.util.find_library("seccomp"))
        lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
        wrong = {name: (number, lib.seccomp_syscall_resolve_name(name.encode()))
                 for name, number in N.items() if lib.seccomp_syscall_resolve_name(name.encode()) != number}
        self.assertEqual(wrong, {})

    def test_the_shipped_program_allows_exactly_the_declared_calls(self):
        allowed_numbers = {N[name] for name in allowlist.allowed_names()}
        with_no_arguments = {number for number in range(1024) if decide(number) == "ALLOW"}
        # clone with no flags at all is an ordinary new process; the other argument-checked calls
        # are refused when their argument is zero (no socket family, no file type).
        self.assertEqual(with_no_arguments, allowed_numbers | {N["clone"]})

    def test_a_named_refusal_is_eperm_and_everything_else_is_not_implemented(self):
        for name in allowlist.refused_names():
            self.assertEqual(decide(name), "ERRNO:1", name)
        listed = set(N.values())
        for number in [n for n in range(1024) if n not in listed]:
            self.assertEqual(decide(number), "ERRNO:38", number)
        for future in (435, 437, 434, 451, 462, 999):     # clone3, openat2, pidfd_open, and calls not invented yet
            self.assertEqual(decide(future), "ERRNO:38")

    def test_a_caller_that_changes_instruction_set_is_killed(self):
        self.assertEqual(decide("read", audit_arch=0x40000003), "KILL_PROCESS")     # 32-bit int 0x80
        self.assertEqual(decide("read", audit_arch=0xC00000B7), "KILL_PROCESS")     # another machine's table
        self.assertEqual(decide(0x40000000 | N["read"]), "KILL_PROCESS")            # x32 numbering
        self.assertEqual(decide(-1), "KILL_PROCESS")

    def test_a_new_process_is_allowed_and_a_new_namespace_is_not(self):
        sigchld, thread, vfork_like = 17, 0x3D0F00, 0x4111
        for flags in (0, sigchld, thread, vfork_like, 0x01200011):
            self.assertEqual(decide("clone", flags), "ALLOW", hex(flags))
        new = {"NEWNS": 0x00020000, "NEWCGROUP": 0x02000000, "NEWUTS": 0x04000000, "NEWIPC": 0x08000000,
               "NEWUSER": 0x10000000, "NEWPID": 0x20000000, "NEWNET": 0x40000000}
        for name, flag in new.items():
            self.assertEqual(decide("clone", flag), "ERRNO:1", name)
            self.assertEqual(decide("clone", flag | thread), "ERRNO:1", name)
        self.assertEqual(decide(435), "ERRNO:38", "clone3 hides its flags in memory: closed, and the C library falls back")

    def test_only_local_and_loopback_socket_families(self):
        for call in ("socket", "socketpair"):
            allowed = {family for family in range(64) if decide(call, family) == "ALLOW"}
            self.assertEqual(allowed, {1, 2, 10}, call)        # AF_UNIX, AF_INET, AF_INET6
            for family in (16, 17, 38, 40, 44):               # netlink, packet, alg, vsock, xdp
                self.assertEqual(decide(call, family), "ERRNO:1")

    def test_a_named_pipe_is_allowed_and_a_device_node_is_not(self):
        fifo, char, block, regular, sock = 0o010000, 0o020000, 0o060000, 0o100000, 0o140000
        self.assertEqual(decide("mknod", 0, fifo | 0o644), "ALLOW")
        self.assertEqual(decide("mknodat", 0, 0, fifo | 0o644), "ALLOW")
        for kind in (char, block, regular, sock, 0):
            self.assertEqual(decide("mknod", 0, kind | 0o644), "ERRNO:1", oct(kind))
            self.assertEqual(decide("mknodat", 0, 0, kind | 0o644), "ERRNO:1", oct(kind))

    def test_the_calls_escapes_are_written_with_are_never_allowed(self):
        for name in NEVER:
            self.assertIn(name, N, name)
            self.assertNotEqual(decide(name), "ALLOW", name)
            self.assertNotIn(name, allowlist.allowed_names(), name)

    def test_the_bytes_are_the_bytes_that_were_measured(self):
        raw = allowlist.filter_bytes("x86_64")
        self.assertEqual(len(raw) % 8, 0)
        self.assertLessEqual(len(raw) // 8, 4096, "the kernel refuses a longer program")
        self.assertEqual(allowlist.filter_sha256("x86_64"), PINNED)
        self.assertEqual(allowlist.describe("x86_64")["instructions"], len(raw) // 8)

    def test_the_setup_script_carries_the_filter_and_the_step_that_installs_it(self):
        self.assertNotIn("@@", launcher._SETUP)
        self.assertNotIn("'", launcher._ENTER_ROOT_BEHIND_SYSCALL_FILTER)
        self.assertIn("os._exit(126)", launcher._ENTER_ROOT_BEHIND_SYSCALL_FILTER)
        if X86_64:
            self.assertIn(allowlist.filter_hex(), launcher._SETUP)
            self.assertEqual(launcher.syscall_filter_sha256(), PINNED)

    def test_a_machine_without_a_table_gets_no_filter_and_therefore_no_worker(self):
        with self.assertRaises(allowlist.SyscallFilterUnavailable):
            allowlist.filter_bytes("aarch64")
        with tempfile.TemporaryDirectory() as td, mock.patch.object(allowlist, "machine", return_value="aarch64"):
            self.assertEqual(launcher.syscall_filter_hex(), "")
            self.assertIsNone(launcher.syscall_filter_sha256())
            with self.assertRaises(launcher.NamespaceConfinementError) as refused:
                launcher.run_confined({"argv": ["/usr/bin/true"], "input_dir": td})
            self.assertIn("SYSCALL_FILTER_UNAVAILABLE_FOR_ARCH:aarch64", str(refused.exception))


def _carrier_available() -> bool:
    if not X86_64:
        return False
    try:
        from canonical.runtime import brokered_workspace_execution_v1 as broker
        return bool(broker.namespace_broker_available())
    except Exception:
        return False


ASK = """
import ctypes, json, os, socket
libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long
def ask(number, *args):
    ctypes.set_errno(0)
    result = libc.syscall(ctypes.c_long(number), *[ctypes.c_long(a) for a in args])
    return "errno %d" % ctypes.get_errno() if result == -1 else "answered"
def report(rep):
    s = socket.socket(fileno=int(os.environ["PROJECT_BRAIN_BROKER_FD"])); s.sendall(json.dumps(rep).encode()); s.close()
"""


@unittest.skipUnless(_carrier_available(), "the namespace launcher cannot start a worker on this machine")
class InTheWorkerTests(unittest.TestCase):
    def _worker(self, body: str, **limits) -> tuple[dict, dict]:
        from canonical.tests.test_zero_ambient_namespace_launcher_v1 import policy, write_input
        td, root = write_input({"w.py": ASK + textwrap.dedent(body)})
        try:
            result = launcher.run_confined(policy(root, "w.py", **limits))
        finally:
            td.cleanup()
        self.assertEqual(result["status"], "CHILD_EXITED", result)
        payload = result["broker_payload"].decode()
        self.assertTrue(payload, "the worker said nothing: returncode %s" % result["returncode"])
        return result, json.loads(payload)

    def test_the_filter_is_in_force_before_the_first_line_of_the_workload(self):
        result, seen = self._worker("""
            report({"mode": libc.prctl(21, 0, 0, 0, 0), "no_new_privs": libc.prctl(39, 0, 0, 0, 0)})
        """)
        self.assertEqual(seen, {"mode": 2, "no_new_privs": 1})
        self.assertEqual(result["syscall_filter_sha256"], PINNED)

    def test_calls_the_kernel_would_have_answered_are_refused(self):
        # Measured on the unfiltered launcher (main 400ad21d, this machine): the kernel itself
        # answers each of these with something other than EPERM -- a descriptor, EFAULT, a value,
        # ENOKEY, EBADF, ESRCH, EBADF -- and clone3 with EINVAL. So EPERM here is the filter.
        _, seen = self._worker("""
            report({"netlink": ask(41, 16, 3, 0), "io_uring_setup": ask(425, 0, 0), "personality": ask(135, 0xffffffff),
                    "keyctl": ask(250, 0, -1, 0), "setns": ask(308, -1, 0), "ptrace": ask(101, 1, 0, 0, 0),
                    "syncfs": ask(306, -1), "clone3": ask(435, 0, 0)})
        """)
        self.assertEqual(seen.pop("clone3"), "errno 38")
        self.assertEqual(seen, {name: "errno 1" for name in seen})

    def test_calls_the_kernel_might_refuse_by_itself_are_refused_whether_it_does_or_not(self):
        # A caller without capabilities is often turned away from these by the kernel's own checks.
        # "Often" depends on sysctls and kernel version; the answer here must not.
        _, seen = self._worker("""
            report({"packet": ask(41, 17, 3, 0), "bpf": ask(321, 0, 0, 0), "userfaultfd": ask(323, 0),
                    "perf_event_open": ask(298, 0, 0, -1, -1, 0), "mount": ask(165, 0, 0, 0, 0, 0),
                    "unshare": ask(272, 0x10000000), "chroot": ask(161, 0), "swapon": ask(167, 0, 0),
                    "openat2": ask(437, -1, 0, 0, 0)})
        """)
        self.assertEqual(seen.pop("openat2"), "errno 38")
        self.assertEqual(seen, {name: "errno 1" for name in seen})

    def test_a_child_and_a_grandchild_are_behind_the_same_filter(self):
        _, seen = self._worker("""
            import subprocess, sys
            child = "import ctypes; l = ctypes.CDLL(None, use_errno=True); l.syscall.restype = ctypes.c_long; r = l.syscall(41, 16, 3, 0); print(l.prctl(21, 0, 0, 0, 0), ctypes.get_errno() if r == -1 else 0)"
            direct = subprocess.run([sys.executable, "-I", "-c", child], capture_output=True, text=True).stdout.split()
            through_a_shell = subprocess.run(["/bin/sh", "-c", sys.executable + " -I -c '" + child + "'"], capture_output=True, text=True).stdout.split()
            report({"direct": direct, "through_a_shell": through_a_shell})
        """)
        self.assertEqual(seen, {"direct": ["2", "1"], "through_a_shell": ["2", "1"]})

    def test_a_caller_that_changes_instruction_set_is_killed_and_the_worker_survives(self):
        _, seen = self._worker("""
            import signal
            pid = os.fork()
            if pid == 0:
                libc.syscall(ctypes.c_long(0x40000000 | 39)); os._exit(0)       # getpid, x32 numbering
            _, status = os.waitpid(pid, 0)
            report({"killed_by": os.WTERMSIG(status) if os.WIFSIGNALED(status) else None, "sigsys": int(signal.SIGSYS)})
        """)
        self.assertEqual(seen["killed_by"], seen["sigsys"])

    def test_ordinary_work_is_not_refused(self):
        _, seen = self._worker("""
            import pathlib, shutil, sqlite3, subprocess, sys, threading
            rep = {}
            work = pathlib.Path("/work/p"); work.mkdir()
            (work / "m.py").write_text("def add(a, b):\\n    return a + b\\n")
            (work / "test_m.py").write_text("import unittest\\nfrom m import add\\nclass T(unittest.TestCase):\\n    def test_a(self):\\n        self.assertEqual(add(1, 2), 3)\\n")
            rep["a_projects_tests"] = subprocess.run([sys.executable, "-m", "unittest", "-q", "test_m"], cwd=work, capture_output=True).returncode
            rep["a_shell_pipeline"] = subprocess.run("echo hi | cat", shell=True, capture_output=True, text=True).stdout.strip()
            got = []; t = threading.Thread(target=lambda: got.append(1)); t.start(); t.join(); rep["a_thread"] = got
            s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(1); c = socket.socket(); c.connect(s.getsockname())
            a, _ = s.accept(); c.sendall(b"hi"); rep["a_loopback_server"] = a.recv(2).decode()
            x, y = socket.socketpair(); x.sendall(b"k"); rep["a_local_socket"] = y.recv(1).decode()
            os.mkfifo(work / "fifo"); rep["a_named_pipe"] = (work / "fifo").is_fifo()
            shutil.copy2(work / "m.py", work / "copy.py"); rep["a_copy_with_metadata"] = (work / "copy.py").is_file()
            db = sqlite3.connect(work / "d.sqlite"); db.execute("create table t(a)"); db.execute("insert into t values(1)"); db.commit()
            rep["a_database"] = db.execute("select count(*) from t").fetchone()[0]
            make = shutil.which("make")
            if make:
                (work / "Makefile").write_text("out:\\n\\t@printf made > out.txt\\n")
                rep["make"] = [subprocess.run([make, "out"], cwd=work, capture_output=True).returncode, (work / "out.txt").read_text() if (work / "out.txt").exists() else None]
            report(rep)
        """, pids=32, memory_mb=512, nofile=64, wallclock_s=20, cpu_seconds=10)
        make = seen.pop("make", [0, "made"])
        self.assertEqual(make, [0, "made"], "make resets its ids before every command; that must go through")
        self.assertEqual(seen, {"a_projects_tests": 0, "a_shell_pipeline": "hi", "a_thread": [1], "a_loopback_server": "hi",
                                "a_local_socket": "k", "a_named_pipe": True, "a_copy_with_metadata": True, "a_database": 1})


@unittest.skipUnless(X86_64 and shutil.which("unshare"), "needs a user namespace to change root in")
class IfTheFilterCannotBeInstalledNothingRunsTests(unittest.TestCase):
    """The step that enters the worker's root installs the filter or exits 126. It never proceeds."""

    def _enter(self, filter_hex: str) -> tuple[int, bool]:
        with tempfile.TemporaryDirectory() as td:
            marker = pathlib.Path(td) / "the_command_ran"
            proc = subprocess.run(
                [shutil.which("unshare"), "--user", "--map-root-user", sys.executable, "-I", "-c",
                 launcher._ENTER_ROOT_BEHIND_SYSCALL_FILTER, "/", filter_hex, "/usr/bin/touch", str(marker)],
                capture_output=True, timeout=30)
            return proc.returncode, marker.exists()

    def setUp(self):
        probe = subprocess.run([shutil.which("unshare"), "--user", "--map-root-user", "/usr/bin/true"], capture_output=True)
        if probe.returncode != 0:
            self.skipTest("this machine does not allow an unprivileged user namespace")

    def test_the_harness_can_show_a_command_running(self):
        # Without this, every refusal below could be the harness failing rather than the step refusing.
        self.assertEqual(self._enter(allowlist.filter_hex()), (0, True))

    def test_no_bytes(self):
        self.assertEqual(self._enter(""), (126, False))

    def test_bytes_that_are_not_whole_instructions(self):
        self.assertEqual(self._enter("00" * 12), (126, False))

    def test_a_program_the_kernel_refuses(self):
        self.assertEqual(self._enter("00" * 8), (126, False))      # one instruction that never returns

    def test_text_that_is_not_bytes(self):
        code, ran = self._enter("not hex")
        self.assertNotEqual(code, 0)
        self.assertFalse(ran)


if __name__ == "__main__":
    unittest.main(verbosity=1)
