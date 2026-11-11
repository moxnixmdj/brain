from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess

SCHEMA = "PROJECT_BRAIN_ROOT3_KERNEL_EFFECT_INHERITED_FD_COUNTERMODEL_V1"


def run() -> dict:
    unshare = shutil.which("unshare")
    if not unshare:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__UNSHARE_MISSING",
            "countermodel": False,
        }

    parent, child = socket.socketpair()
    try:
        fd = child.fileno()
        os.set_inheritable(fd, True)
        code = (
            "import socket,sys;"
            "s=socket.socket(fileno=int(sys.argv[1]));"
            "s.sendall(b'X')"
        )
        p = subprocess.Popen(
            [unshare, "-Urn", "python3", "-c", code, str(fd)],
            pass_fds=(fd,),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        child.close()
        data = parent.recv(1)
        stdout, stderr = p.communicate(timeout=3)
        survived = p.returncode == 0 and data == b"X"
        return {
            "schema": SCHEMA,
            "status": (
                "PASS__INHERITED_FD_SURVIVES_NAMESPACE_ENTRY"
                if survived
                else "NO_COUNTERMODEL_OBSERVED"
            ),
            "countermodel": survived,
            "child_returncode": p.returncode,
            "received": data.decode("ascii", errors="replace"),
            "child_stdout": stdout,
            "child_stderr": stderr,
            "terminal_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }
    finally:
        try:
            parent.close()
        except Exception:
            pass
        try:
            child.close()
        except Exception:
            pass


if __name__ == "__main__":
    out = run()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out.get("countermodel") is True else 1)
