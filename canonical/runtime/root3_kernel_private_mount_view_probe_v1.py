from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile

SCHEMA = "PROJECT_BRAIN_ROOT3_KERNEL_PRIVATE_MOUNT_VIEW_PROBE_V1"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        close_fds=True,
        check=False,
    )


def probe() -> dict:
    unshare = shutil.which("unshare")
    if not unshare:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__UNSHARE_MISSING",
            "pass": False,
        }

    errors: list[str] = []
    checks: dict[str, bool] = {}

    # Filesystem-named AF_UNIX must disappear when its parent path is hidden
    # by a private mount inside the isolated mount namespace.
    with tempfile.TemporaryDirectory(prefix="root3-unix-hide-") as td:
        path = os.path.join(td, "sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(1)
        try:
            child = r'''
import os,socket,sys,subprocess
target=sys.argv[1]
parent=os.path.dirname(target)
subprocess.run(["mount","-t","tmpfs","tmpfs",parent],check=True)
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
try:
    s.connect(target)
    print("CONNECTED")
    raise SystemExit(1)
except OSError:
    print("BLOCKED")
    raise SystemExit(0)
'''
            p = _run([unshare, "-Urnm", "python3", "-c", child, path])
            checks["filesystem_unix_socket_hidden"] = (
                p.returncode == 0 and "BLOCKED" in p.stdout
            )
        finally:
            server.close()

    # Abstract AF_UNIX is network-namespace scoped.
    abstract_name = chr(0) + "root3_abs_probe_v1"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(abstract_name)
    server.listen(1)
    try:
        encoded = "\\0root3_abs_probe_v1"
        child = (
            "import socket,sys;"
            "s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);"
            "s.settimeout(1);"
            "s.connect(sys.argv[1].encode().decode('unicode_escape'))"
        )
        p = _run([unshare, "-Urn", "python3", "-c", child, encoded])
        checks["abstract_unix_socket_isolated"] = p.returncode != 0
    finally:
        server.close()

    # /proc and /sys can be hidden behind private tmpfs mounts even when
    # mount-proc in a PID namespace is not permitted by the carrier.
    child = r'''
import os,subprocess,json
subprocess.run(["mount","-t","tmpfs","tmpfs","/proc"],check=True)
subprocess.run(["mount","-t","tmpfs","tmpfs","/sys"],check=True)
print(json.dumps({"proc":os.listdir("/proc"),"sys":os.listdir("/sys")}))
'''
    p = _run([unshare, "-Urmn", "python3", "-c", child])
    try:
        hidden = json.loads(p.stdout.strip()) if p.returncode == 0 else {}
    except Exception:
        hidden = {}
    checks["proc_hidden"] = hidden.get("proc") == []
    checks["sys_hidden"] = hidden.get("sys") == []

    # Rebuild /dev with only the minimal devices observed sufficient for a
    # descendant Python process on the independent carrier.
    child = r'''
import os,subprocess,json
os.makedirs("/tmp/root3-safe-dev",exist_ok=True)
for name in ("null","urandom"):
    target="/tmp/root3-safe-dev/"+name
    open(target,"a").close()
    subprocess.run(["mount","--bind","/dev/"+name,target],check=True)
subprocess.run(["mount","-t","tmpfs","tmpfs","/dev"],check=True)
for name in ("null","urandom"):
    target="/dev/"+name
    open(target,"a").close()
    subprocess.run(["mount","--bind","/tmp/root3-safe-dev/"+name,target],check=True)
p=subprocess.run(
    ["python3","-c","import os,json; print(json.dumps(sorted(os.listdir('/dev'))))"],
    text=True,capture_output=True,check=False
)
print(json.dumps({
    "after":sorted(os.listdir("/dev")),
    "descendant_rc":p.returncode,
    "descendant":json.loads(p.stdout.strip()) if p.returncode==0 else None
}))
'''
    p = _run([unshare, "-Urmn", "python3", "-c", child])
    try:
        dev = json.loads(p.stdout.strip()) if p.returncode == 0 else {}
    except Exception:
        dev = {}
    checks["minimal_dev_view"] = dev.get("after") == ["null", "urandom"]
    checks["descendant_runs_with_minimal_dev"] = (
        dev.get("descendant_rc") == 0
        and dev.get("descendant") == ["null", "urandom"]
    )

    for name, passed in checks.items():
        if not passed:
            errors.append(name.upper() + "_FAILED")

    ok = not errors and all(checks.values())
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__PRIVATE_MOUNT_VIEW_PRIMITIVES_AVAILABLE"
            if ok
            else "FAIL_CLOSED"
        ),
        "pass": ok,
        "checks": checks,
        "errors": errors,
        "e2_closed": False,
        "e3_closed": False,
        "terminal_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


if __name__ == "__main__":
    out = probe()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
