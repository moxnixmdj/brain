from __future__ import annotations

import json
import shutil
import subprocess

SCHEMA = "PROJECT_BRAIN_ROOT3_KERNEL_EFFECT_FD_HYGIENE_PROBE_V1"


def probe() -> dict:
    unshare = shutil.which("unshare")
    if not unshare:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__UNSHARE_MISSING",
            "pass": False,
        }

    code = (
        "import os,json;"
        "live=[fd for fd in range(64) "
        "if os.path.exists('/proc/self/fd/'+str(fd))];"
        "print(json.dumps(live))"
    )
    p = subprocess.run(
        [unshare, "-Urn", "python3", "-c", code],
        text=True,
        capture_output=True,
        close_fds=True,
        check=False,
    )
    observed = None
    try:
        observed = json.loads(p.stdout.strip())
    except Exception:
        pass

    ok = p.returncode == 0 and observed == [0, 1, 2]
    return {
        "schema": SCHEMA,
        "status": "PASS__ONLY_DECLARED_STDIO_FDS_SURVIVE" if ok else "FAIL_CLOSED",
        "pass": ok,
        "observed_live_fds": observed,
        "child_returncode": p.returncode,
        "stderr": p.stderr,
        "scope": "REPAIRS_ONLY_THE_PREEXISTING_UNAPPROVED_FD_COUNTERMODEL_FOR_A_NO_BROKER_LAUNCH",
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
