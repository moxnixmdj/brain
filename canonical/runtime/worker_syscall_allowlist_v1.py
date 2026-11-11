#!/usr/bin/env python3
"""The kernel calls a confined worker may make, and the seccomp filter that enforces the list.

Why this exists
---------------
`REPAIR_INDEPENDENT_REVIEW_REQUEST_20261102.md` names what the namespace launcher lacks before it
may carry code nobody has read: among them, "reviewed syscall filtering". Namespaces, dropped
capabilities and no-new-privileges decide *what a worker can see and own*. They do not decide
*which doors of the kernel it may knock on*: a worker inside them can still call `bpf`,
`io_uring_setup`, `userfaultfd`, `perf_event_open`, `keyctl`, `ptrace`, `unshare` -- the calls
kernel escapes are usually written with. `carrier_qualification_probe_v1` reported this item
NOT_SATISFIED since 2026-11-03, and it was right.

What this is
------------
One list, default deny, three answers:

* a call in `ALLOWED` runs;
* a call in `ARGUMENT_CHECKED` runs only in its harmless form (a new process, not a new
  namespace; a local socket, not a network one; a FIFO, not a device node);
* a call in `REFUSED_BY_NAME` fails with EPERM -- these are named so that a reader can see the
  refusal is a decision and not an omission;
* **every other call, including calls that do not exist yet, fails with ENOSYS.** ENOSYS and not
  EPERM because that is what the C library is written to recover from: `clone3` falls back to
  `clone`, `openat2` to `openat`, `pidfd_open` to waiting on the pid. A new kernel call is
  therefore closed until somebody adds it here.

A call that arrives under another instruction set (32-bit `int 0x80`, the x32 numbering) kills
the process: it is the classic way to walk around a filter written for one table.

How the list was made
---------------------
Measured, then read. 2026-11-11, x86_64, Python 3.11.2, glibc 2.36: `python-ptrace` followed
five batteries of ordinary work (files, archives, sqlite, subprocesses and their kills, threads,
asyncio, local sockets, signals, timers, limits), a `/bin/sh` and a `bash` running fifty common
commands, `pytest`, and the launcher's own `setpriv` step: 137 distinct calls. All of them are
here except the five that must not be: `ptrace` and `unshare` (the tracer and the launcher, not
the work), `clone3` (answered ENOSYS on purpose, see above), `get_mempolicy`/`set_mempolicy`
(libnuma probing; it recovers). The rest of `ALLOWED` is the older or newer spelling of a call
that was measured (`stat` beside `newfstatat`, `pipe` beside `pipe2`), so that a different C
library does not meet a closed door for the same request.

What this is not
----------------
* Not a review. The producer wrote this list. Whether it is the *right* list is exactly what an
  independent reviewer has to decide; `describe()` and `decide()` exist so that they can read the
  shipped program and question it call by call without trusting this docstring.
* Not carrier qualification. The worker still runs the host's libc and interpreter, no attack
  campaign has been run against it, and `carrier_qualified` stays False.
* Not a complete defence. `ioctl` and `prctl` are allowed whole; the worker has no device node
  beyond `/dev/null` and no terminal, which is what makes that tolerable, not the filter.
* x86_64 only. On any other machine there is no table here, so there is no filter, so the
  launcher refuses to start a worker. A filter nobody could test is not shipped as if it were one.

Zero external-model producer cognition. Zero incremental spend. No dependency: the program is
classic BPF assembled here, byte for byte the same on every x86_64 host, so its hash can be
pinned by whoever reviews it.
"""
from __future__ import annotations

import hashlib
import platform
import struct
from typing import Any, Sequence

SCHEMA = "PROJECT_BRAIN_WORKER_SYSCALL_ALLOWLIST_V1"
AUTHORITY = "NONE -- PRODUCER-WRITTEN LIST, NOT A REVIEWED ONE"

ALLOWED = {
    "files": (
        "read", "write", "readv", "writev", "pread64", "pwrite64", "preadv", "pwritev", "preadv2",
        "pwritev2", "open", "openat", "creat", "close", "close_range", "lseek", "stat", "fstat",
        "lstat", "newfstatat", "statx", "access", "faccessat", "faccessat2", "readlink",
        "readlinkat", "getcwd", "chdir", "fchdir", "mkdir", "mkdirat", "rmdir", "unlink",
        "unlinkat", "rename", "renameat", "renameat2", "link", "linkat", "symlink", "symlinkat",
        "chmod", "fchmod", "fchmodat", "chown", "fchown", "lchown", "fchownat", "truncate",
        "ftruncate", "fallocate", "fsync", "fdatasync", "getdents", "getdents64", "fcntl", "flock",
        "dup", "dup2", "dup3", "pipe", "pipe2", "ioctl", "utime", "utimes", "utimensat",
        "futimesat", "statfs", "fstatfs", "fadvise64", "sendfile", "copy_file_range", "getxattr",
        "lgetxattr", "fgetxattr", "listxattr", "llistxattr", "flistxattr", "umask",
    ),
    "waiting": (
        "poll", "ppoll", "select", "pselect6", "epoll_create", "epoll_create1", "epoll_ctl",
        "epoll_wait", "epoll_pwait", "epoll_pwait2", "eventfd", "eventfd2",
    ),
    "sockets": (
        "connect", "bind", "listen", "accept", "accept4", "getsockname", "getpeername",
        "getsockopt", "setsockopt", "sendto", "recvfrom", "sendmsg", "recvmsg", "shutdown",
    ),
    "memory": (
        "brk", "mmap", "munmap", "mprotect", "mremap", "madvise", "msync",
    ),
    "processes": (
        "execve", "execveat", "exit", "exit_group", "wait4", "waitid", "fork", "vfork", "kill",
        "tgkill", "tkill", "getpid", "getppid", "gettid", "getpgid", "getpgrp", "getsid", "setsid",
        "setpgid", "prctl", "arch_prctl", "set_tid_address", "set_robust_list", "get_robust_list",
        "rseq", "futex", "capget", "capset", "uname", "sysinfo", "getcpu", "restart_syscall",
    ),
    "scheduling": (
        "sched_yield", "sched_getaffinity", "sched_getparam", "sched_getscheduler",
        "sched_get_priority_max", "sched_get_priority_min", "getpriority", "setpriority",
        "getrusage", "times", "getrlimit", "setrlimit", "prlimit64",
    ),
    "identity": (
        "getuid", "geteuid", "getgid", "getegid", "getgroups", "getresuid", "getresgid",
    ),
    "signals": (
        "rt_sigaction", "rt_sigprocmask", "rt_sigreturn", "rt_sigpending", "rt_sigsuspend",
        "rt_sigtimedwait", "sigaltstack", "pause", "alarm", "getitimer", "setitimer",
        "timer_create", "timer_settime", "timer_gettime", "timer_getoverrun", "timer_delete",
    ),
    "time": (
        "clock_gettime", "clock_getres", "clock_nanosleep", "nanosleep", "gettimeofday", "time",
        "getrandom",
    ),
}

# name -> (index of the argument that is read, what is required of it, in words)
ARGUMENT_CHECKED = {
    "clone": (0, "no CLONE_NEW* flag: a new process or thread, never a new namespace"),
    "socket": (0, "domain AF_UNIX only"),
    "socketpair": (0, "domain AF_UNIX only"),
    "mknod": (1, "file type S_IFIFO only: a named pipe, never a device node"),
    "mknodat": (2, "file type S_IFIFO only: a named pipe, never a device node"),
}

REFUSED_BY_NAME = {
    "the_file_tree": (
        "mount", "umount2", "pivot_root", "chroot", "open_by_handle_at", "name_to_handle_at",
        "fsopen", "fsconfig", "fsmount", "fspick", "move_mount", "open_tree", "mount_setattr",
        "quotactl", "fanotify_init", "sync", "syncfs",
    ),
    "namespaces_and_identity": (
        "unshare", "setns", "setuid", "setgid", "setreuid", "setregid", "setresuid", "setresgid",
        "setfsuid", "setfsgid", "setgroups", "sethostname", "setdomainname",
    ),
    "other_processes": (
        "ptrace", "process_vm_readv", "process_vm_writev", "kcmp", "pidfd_getfd", "process_madvise",
    ),
    "the_kernel_itself": (
        "bpf", "perf_event_open", "userfaultfd", "io_uring_setup", "io_uring_enter",
        "io_uring_register", "keyctl", "add_key", "request_key", "init_module", "finit_module",
        "delete_module", "kexec_load", "kexec_file_load", "reboot", "swapon", "swapoff", "acct",
        "syslog", "iopl", "ioperm", "modify_ldt", "vhangup", "personality", "seccomp",
    ),
    "the_clock_and_memory_policy": (
        "settimeofday", "clock_settime", "clock_adjtime", "adjtimex", "mbind", "set_mempolicy",
        "migrate_pages", "move_pages",
    ),
}

# include/uapi/asm/unistd_64.h. These numbers are the x86_64 ABI and do not change; the test
# suite compares every one of them with the kernel header and with libseccomp when the host has them.
X86_64 = {
    "read": 0, "write": 1, "open": 2, "close": 3, "stat": 4, "fstat": 5,
    "lstat": 6, "poll": 7, "lseek": 8, "mmap": 9, "mprotect": 10, "munmap": 11,
    "brk": 12, "rt_sigaction": 13, "rt_sigprocmask": 14, "rt_sigreturn": 15, "ioctl": 16, "pread64": 17,
    "pwrite64": 18, "readv": 19, "writev": 20, "access": 21, "pipe": 22, "select": 23,
    "sched_yield": 24, "mremap": 25, "msync": 26, "madvise": 28, "dup": 32, "dup2": 33,
    "pause": 34, "nanosleep": 35, "getitimer": 36, "alarm": 37, "setitimer": 38, "getpid": 39,
    "sendfile": 40, "socket": 41, "connect": 42, "accept": 43, "sendto": 44, "recvfrom": 45,
    "sendmsg": 46, "recvmsg": 47, "shutdown": 48, "bind": 49, "listen": 50, "getsockname": 51,
    "getpeername": 52, "socketpair": 53, "setsockopt": 54, "getsockopt": 55, "clone": 56, "fork": 57,
    "vfork": 58, "execve": 59, "exit": 60, "wait4": 61, "kill": 62, "uname": 63,
    "fcntl": 72, "flock": 73, "fsync": 74, "fdatasync": 75, "truncate": 76, "ftruncate": 77,
    "getdents": 78, "getcwd": 79, "chdir": 80, "fchdir": 81, "rename": 82, "mkdir": 83,
    "rmdir": 84, "creat": 85, "link": 86, "unlink": 87, "symlink": 88, "readlink": 89,
    "chmod": 90, "fchmod": 91, "chown": 92, "fchown": 93, "lchown": 94, "umask": 95,
    "gettimeofday": 96, "getrlimit": 97, "getrusage": 98, "sysinfo": 99, "times": 100, "ptrace": 101,
    "getuid": 102, "syslog": 103, "getgid": 104, "setuid": 105, "setgid": 106, "geteuid": 107,
    "getegid": 108, "setpgid": 109, "getppid": 110, "getpgrp": 111, "setsid": 112, "setreuid": 113,
    "setregid": 114, "getgroups": 115, "setgroups": 116, "setresuid": 117, "getresuid": 118, "setresgid": 119,
    "getresgid": 120, "getpgid": 121, "setfsuid": 122, "setfsgid": 123, "getsid": 124, "capget": 125,
    "capset": 126, "rt_sigpending": 127, "rt_sigtimedwait": 128, "rt_sigsuspend": 130, "sigaltstack": 131, "utime": 132,
    "mknod": 133, "personality": 135, "statfs": 137, "fstatfs": 138, "getpriority": 140, "setpriority": 141,
    "sched_getparam": 143, "sched_getscheduler": 145, "sched_get_priority_max": 146, "sched_get_priority_min": 147, "vhangup": 153, "modify_ldt": 154,
    "pivot_root": 155, "prctl": 157, "arch_prctl": 158, "adjtimex": 159, "setrlimit": 160, "chroot": 161,
    "sync": 162, "acct": 163, "settimeofday": 164, "mount": 165, "umount2": 166, "swapon": 167,
    "swapoff": 168, "reboot": 169, "sethostname": 170, "setdomainname": 171, "iopl": 172, "ioperm": 173,
    "init_module": 175, "delete_module": 176, "quotactl": 179, "gettid": 186, "getxattr": 191, "lgetxattr": 192,
    "fgetxattr": 193, "listxattr": 194, "llistxattr": 195, "flistxattr": 196, "tkill": 200, "time": 201,
    "futex": 202, "sched_getaffinity": 204, "epoll_create": 213, "getdents64": 217, "set_tid_address": 218, "restart_syscall": 219,
    "fadvise64": 221, "timer_create": 222, "timer_settime": 223, "timer_gettime": 224, "timer_getoverrun": 225, "timer_delete": 226,
    "clock_settime": 227, "clock_gettime": 228, "clock_getres": 229, "clock_nanosleep": 230, "exit_group": 231, "epoll_wait": 232,
    "epoll_ctl": 233, "tgkill": 234, "utimes": 235, "mbind": 237, "set_mempolicy": 238, "kexec_load": 246,
    "waitid": 247, "add_key": 248, "request_key": 249, "keyctl": 250, "migrate_pages": 256, "openat": 257,
    "mkdirat": 258, "mknodat": 259, "fchownat": 260, "futimesat": 261, "newfstatat": 262, "unlinkat": 263,
    "renameat": 264, "linkat": 265, "symlinkat": 266, "readlinkat": 267, "fchmodat": 268, "faccessat": 269,
    "pselect6": 270, "ppoll": 271, "unshare": 272, "set_robust_list": 273, "get_robust_list": 274, "move_pages": 279,
    "utimensat": 280, "epoll_pwait": 281, "eventfd": 284, "fallocate": 285, "accept4": 288, "eventfd2": 290,
    "epoll_create1": 291, "dup3": 292, "pipe2": 293, "preadv": 295, "pwritev": 296, "perf_event_open": 298,
    "fanotify_init": 300, "prlimit64": 302, "name_to_handle_at": 303, "open_by_handle_at": 304, "clock_adjtime": 305, "syncfs": 306,
    "setns": 308, "getcpu": 309, "process_vm_readv": 310, "process_vm_writev": 311, "kcmp": 312, "finit_module": 313,
    "renameat2": 316, "seccomp": 317, "getrandom": 318, "kexec_file_load": 320, "bpf": 321, "execveat": 322,
    "userfaultfd": 323, "copy_file_range": 326, "preadv2": 327, "pwritev2": 328, "statx": 332, "rseq": 334,
    "io_uring_setup": 425, "io_uring_enter": 426, "io_uring_register": 427, "open_tree": 428, "move_mount": 429, "fsopen": 430,
    "fsconfig": 431, "fsmount": 432, "fspick": 433, "close_range": 436, "pidfd_getfd": 438, "faccessat2": 439,
    "process_madvise": 440, "epoll_pwait2": 441, "mount_setattr": 442,
}

_TABLES = {"x86_64": (0xC000003E, X86_64)}          # AUDIT_ARCH_X86_64
_X32_BIT = 0x40000000

KILL_PROCESS = 0x80000000
ALLOW = 0x7FFF0000
_ERRNO = 0x00050000
EPERM = 1
ENOSYS = 38

_CLONE_NEW_ANYTHING = 0x7E020000   # NEWNS | NEWCGROUP | NEWUTS | NEWIPC | NEWUSER | NEWPID | NEWNET
_AF_UNIX = 1
_S_IFMT = 0o170000
_S_IFIFO = 0o010000

# classic BPF opcodes (linux/bpf_common.h)
_LD_ABS = 0x20      # A = 32-bit word of seccomp_data at offset k
_JEQ = 0x15         # if A == k: skip jt else skip jf
_JGE = 0x35         # if A >= k
_JSET = 0x45        # if A & k
_AND = 0x54         # A &= k
_RET = 0x06         # return k

_NR, _ARCH, _ARGS = 0, 4, 16   # struct seccomp_data { int nr; __u32 arch; __u64 ip; __u64 args[6]; }


class SyscallFilterUnavailable(ValueError):
    """There is no reviewed table for this machine, so there is no filter to install."""


def machine() -> str:
    return platform.machine().lower()


def allowed_names() -> list[str]:
    return [name for group in ALLOWED.values() for name in group]


def refused_names() -> list[str]:
    return [name for group in REFUSED_BY_NAME.values() for name in group]


def _table(arch: str | None) -> tuple[int, dict[str, int]]:
    arch = arch or machine()
    if arch not in _TABLES:
        raise SyscallFilterUnavailable("SYSCALL_FILTER_UNAVAILABLE_FOR_ARCH:" + arch)
    return _TABLES[arch]


def program(arch: str | None = None) -> list[tuple[int, int, int, int]]:
    """The filter as (opcode, skip-if-true, skip-if-false, constant) instructions, in order."""
    audit_arch, numbers = _table(arch)
    allowed, refused = allowed_names(), refused_names()
    names = allowed + list(ARGUMENT_CHECKED) + refused
    if len(set(names)) != len(names):
        raise SyscallFilterUnavailable("SYSCALL_LIST_NAMES_A_CALL_TWICE")
    missing = [n for n in names if n not in numbers]
    if missing:
        raise SyscallFilterUnavailable("SYSCALL_NUMBER_UNKNOWN:" + ",".join(sorted(missing)))
    low = lambda index: _ARGS + 8 * index   # little-endian: the low half of a 64-bit argument
    prog = [
        (_LD_ABS, 0, 0, _ARCH), (_JEQ, 1, 0, audit_arch), (_RET, 0, 0, KILL_PROCESS),
        (_LD_ABS, 0, 0, _NR), (_JGE, 0, 1, _X32_BIT), (_RET, 0, 0, KILL_PROCESS),
    ]
    refuse, allow = (_RET, 0, 0, _ERRNO | EPERM), (_RET, 0, 0, ALLOW)
    # Each block returns, so a call that is not the block's own falls through with A still its number.
    prog += [(_JEQ, 0, 4, numbers["clone"]), (_LD_ABS, 0, 0, low(ARGUMENT_CHECKED["clone"][0])),
             (_JSET, 0, 1, _CLONE_NEW_ANYTHING), refuse, allow]
    for name in ("socket", "socketpair"):
        prog += [(_JEQ, 0, 4, numbers[name]), (_LD_ABS, 0, 0, low(ARGUMENT_CHECKED[name][0])),
                 (_JEQ, 0, 1, _AF_UNIX), allow, refuse]
    for name in ("mknod", "mknodat"):
        prog += [(_JEQ, 0, 5, numbers[name]), (_LD_ABS, 0, 0, low(ARGUMENT_CHECKED[name][0])),
                 (_AND, 0, 0, _S_IFMT), (_JEQ, 0, 1, _S_IFIFO), allow, refuse]
    for name in sorted(allowed, key=numbers.__getitem__):
        prog += [(_JEQ, 0, 1, numbers[name]), allow]
    for name in sorted(refused, key=numbers.__getitem__):
        prog += [(_JEQ, 0, 1, numbers[name]), refuse]
    prog.append((_RET, 0, 0, _ERRNO | ENOSYS))
    return prog


def filter_bytes(arch: str | None = None) -> bytes:
    """`struct sock_filter[]`, ready for prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ...)."""
    return b"".join(struct.pack("<HBBI", code, jt, jf, k) for code, jt, jf, k in program(arch))


def filter_hex(arch: str | None = None) -> str:
    return filter_bytes(arch).hex()


def filter_sha256(arch: str | None = None) -> str:
    return hashlib.sha256(filter_bytes(arch)).hexdigest()


def decide(number: int, args: Sequence[int] = (), *, audit_arch: int | None = None,
           arch: str | None = None) -> str:
    """Run the shipped program on one call, here, without a kernel.

    Returns "ALLOW", "KILL_PROCESS" or "ERRNO:<n>". This is the same instruction list that is
    installed, interpreted in the open, so a reviewer can ask it about any call and any argument.
    """
    native_arch, _ = _table(arch)
    words = list(args) + [0] * (6 - len(args))
    data = struct.pack("<iIQ6Q", number if number < 2 ** 31 else number - 2 ** 32,
                       native_arch if audit_arch is None else audit_arch, 0,
                       *[w & 0xFFFFFFFFFFFFFFFF for w in words])
    prog, pc, acc = program(arch), 0, 0
    for _ in range(len(prog) + 1):
        code, jt, jf, k = prog[pc]
        pc += 1
        if code == _LD_ABS:
            acc = struct.unpack_from("<I", data, k)[0]
        elif code == _AND:
            acc &= k
        elif code == _JEQ:
            pc += jt if acc == k else jf
        elif code == _JGE:
            pc += jt if acc >= k else jf
        elif code == _JSET:
            pc += jt if acc & k else jf
        elif code == _RET:
            if k == ALLOW:
                return "ALLOW"
            if k == KILL_PROCESS:
                return "KILL_PROCESS"
            return "ERRNO:%d" % (k & 0xFFFF)
        else:  # an opcode this module never emits
            raise SyscallFilterUnavailable("UNKNOWN_OPCODE:%#x" % code)
    raise SyscallFilterUnavailable("PROGRAM_DID_NOT_RETURN")


def describe(arch: str | None = None) -> dict[str, Any]:
    """Everything a reviewer needs in one object: the lists, the size and the hash of the bytes."""
    prog = program(arch)
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "arch": arch or machine(),
        "default": "ERRNO:%d (ENOSYS) for every call that is not listed" % ENOSYS,
        "foreign_instruction_set": "KILL_PROCESS",
        "allowed": {group: list(names) for group, names in ALLOWED.items()},
        "allowed_count": len(allowed_names()),
        "argument_checked": {name: words for name, (_, words) in ARGUMENT_CHECKED.items()},
        "refused_by_name": {group: list(names) for group, names in REFUSED_BY_NAME.items()},
        "refused_by_name_count": len(refused_names()),
        "instructions": len(prog),
        "filter_sha256": filter_sha256(arch),
        "explicitly_not": ["an independent review of the list", "carrier qualification",
                           "evidence that any capability may execute"],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(describe(), indent=1))
