from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile

SCHEMA = "PROJECT_BRAIN_ROOT3_KERNEL_EFFECT_UNIX_SOCKET_COUNTERMODEL_V1"


def run() -> dict:
    unshare = shutil.which("unshare")
    if not unshare:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__UNSHARE_MISSING",
            "countermodel": False,
        }

    with tempfile.TemporaryDirectory(prefix="root3-unix-") as td:
        path = os.path.join(td, "sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(1)
        try:
            code = (
                "import socket,sys;"
                "s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);"
                "s.connect(sys.argv[1]);"
                "s.sendall(b'Y')"
            )
            p = subprocess.Popen(
                [unshare, "-Urn", "python3", "-c", code, path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                close_fds=True,
            )
            conn, _ = server.accept()
            try:
                data = conn.recv(1)
            finally:
                conn.close()
            stdout, stderr = p.communicate(timeout=3)
            survived = p.returncode == 0 and data == b"Y"
            return {
                "schema": SCHEMA,
                "status": (
                    "PASS__UNIX_SOCKET_PATH_SURVIVES_NETWORK_NAMESPACE"
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
            server.close()


if __name__ == "__main__":
    out = run()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out.get("countermodel") is True else 1)
