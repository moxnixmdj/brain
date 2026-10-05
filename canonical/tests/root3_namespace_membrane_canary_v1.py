#!/usr/bin/env python3
import json
import os
import pathlib
import socket
import subprocess
import tempfile

tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp.bind(("127.0.0.1", 0))
tcp.listen(1)
tcp_port = tcp.getsockname()[1]

abstract_token = "brain-root3-canary-%d" % os.getpid()
abstract_name = "\0" + abstract_token
ux = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
ux.bind(abstract_name)
ux.listen(1)

parent_sock, child_sock = socket.socketpair()
leak_r, leak_w = os.pipe()
root = tempfile.mkdtemp(prefix="brain-membrane-")
input_file = tempfile.NamedTemporaryFile(prefix="brain-input-", delete=False)
input_file.write(b"bound-input")
input_file.close()

child_py = r"""
import json, os, socket, resource
fd = int(os.environ["BROKER_FD"])
other = int(os.environ["UNPASSED_FD"])
report = {}
report["broker_fd_open"] = True
try:
    os.fstat(fd)
except OSError:
    report["broker_fd_open"] = False
try:
    os.fstat(other)
    report["unpassed_fd_closed"] = False
except OSError:
    report["unpassed_fd_closed"] = True
report["hidden"] = {
    p: not os.path.exists(p)
    for p in ["/etc", "/dev", "/proc", "/sys", "/home"]
}
report["input"] = open("/input/data", "rb").read().decode()
try:
    open("/usr/SHOULD_FAIL", "wb").write(b"x")
    report["usr_readonly"] = False
except OSError:
    report["usr_readonly"] = True
try:
    open("/input/data", "wb").write(b"x")
    report["input_readonly"] = False
except OSError:
    report["input_readonly"] = True
open("/tmp/private", "wb").write(b"ok")
report["private_scratch"] = open("/tmp/private", "rb").read() == b"ok"

ls = socket.socket()
ls.bind(("127.0.0.1", 0))
ls.listen(1)
report["inner_loopback_bind"] = True
ls.close()

s = socket.socket()
s.settimeout(0.2)
try:
    s.connect(("127.0.0.1", int(os.environ["OUTER_TCP_PORT"])))
    report["outer_tcp_unreachable"] = False
except OSError:
    report["outer_tcp_unreachable"] = True
s.close()

u = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
u.settimeout(0.2)
try:
    u.connect("\0" + os.environ["OUTER_ABSTRACT"])
    report["outer_abstract_unreachable"] = False
except OSError:
    report["outer_abstract_unreachable"] = True
u.close()

report["rlimits"] = {
    "cpu": resource.getrlimit(resource.RLIMIT_CPU)[0],
    "as": resource.getrlimit(resource.RLIMIT_AS)[0],
    "fsize": resource.getrlimit(resource.RLIMIT_FSIZE)[0],
    "nofile": resource.getrlimit(resource.RLIMIT_NOFILE)[0],
    "nproc": resource.getrlimit(resource.RLIMIT_NPROC)[0],
}
os.write(fd, (json.dumps(report, sort_keys=True) + "\n").encode())
"""
child_src = pathlib.Path("/tmp/brain_membrane_child.py")
child_src.write_text(child_py)

setup = r"""
set -euo pipefail
ROOT="$1"
INPUT="$2"
CHILD="$3"
mount --make-rprivate /
mount -t tmpfs -o size=96m,nosuid,nodev tmpfs "$ROOT"
mkdir -p "$ROOT"/{usr,bin,lib,lib64,tmp,input,work}
for d in /usr /bin /lib /lib64; do
  [ -e "$d" ] || continue
  mount --bind "$d" "$ROOT$d"
  mount -o remount,bind,ro "$ROOT$d"
done
mount -t tmpfs -o size=16m,nosuid,nodev,noexec tmpfs "$ROOT/tmp"
: > "$ROOT/input/data"
mount --bind "$INPUT" "$ROOT/input/data"
mount -o remount,bind,ro "$ROOT/input/data"
: > "$ROOT/work/child.py"
mount --bind "$CHILD" "$ROOT/work/child.py"
mount -o remount,bind,ro "$ROOT/work/child.py"
ip link set lo up
ulimit -t 2
ulimit -v 262144
ulimit -f 1024
ulimit -n 32
ulimit -u 32
exec chroot "$ROOT" /usr/bin/env -i \
 PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 BROKER_FD="$BROKER_FD" \
 UNPASSED_FD="$UNPASSED_FD" OUTER_TCP_PORT="$OUTER_TCP_PORT" OUTER_ABSTRACT="$OUTER_ABSTRACT" \
 /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all \
 /usr/bin/python3 -I /work/child.py
"""

cmd = [
    "unshare",
    "--user",
    "--map-root-user",
    "--mount",
    "--net",
    "--pid",
    "--fork",
    "--ipc",
    "--uts",
    "bash",
    "-c",
    setup,
    "_",
    root,
    input_file.name,
    str(child_src),
]
env = {
    "BROKER_FD": str(child_sock.fileno()),
    "UNPASSED_FD": str(leak_r),
    "OUTER_TCP_PORT": str(tcp_port),
    "OUTER_ABSTRACT": abstract_token,
}
proc = subprocess.Popen(
    cmd,
    pass_fds=(child_sock.fileno(),),
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
    text=True,
)
child_sock.close()

data = b""
while not data.endswith(b"\n"):
    chunk = parent_sock.recv(65536)
    if not chunk:
        break
    data += chunk
stderr = proc.communicate(timeout=10)[1]
report = json.loads(data.decode())
report["child_rc"] = proc.returncode
report["stderr_empty"] = not bool(stderr.strip())

required = [
    report["broker_fd_open"],
    report["unpassed_fd_closed"],
    all(report["hidden"].values()),
    report["usr_readonly"],
    report["input_readonly"],
    report["private_scratch"],
    report["inner_loopback_bind"],
    report["outer_tcp_unreachable"],
    report["outer_abstract_unreachable"],
    report["input"] == "bound-input",
    report["child_rc"] == 0,
    report["rlimits"]["cpu"] == 2,
    report["rlimits"]["as"] == 262144 * 1024,
    report["rlimits"]["nofile"] == 32,
    report["rlimits"]["nproc"] == 32,
]
report["status"] = "PASS" if all(required) else "FAIL"
print(json.dumps(report, sort_keys=True))
raise SystemExit(0 if report["status"] == "PASS" else 1)
