from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_ROOT3_KERNEL_EFFECT_CARRIER_PROBE_V1"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def probe() -> dict:
    errors: list[str] = []
    unshare = shutil.which("unshare")
    curl = shutil.which("curl")
    if not unshare:
        errors.append("UNSHARE_MISSING")
    if not curl:
        errors.append("CURL_MISSING")

    checks: dict[str, bool] = {}
    if unshare:
        for name, args in {
            "user_namespace": ["-Ur", "true"],
            "network_namespace": ["-Urn", "true"],
            "mount_namespace": ["-Urm", "true"],
            "combined_namespace": ["-Urnm", "true"],
        }.items():
            p = run([unshare, *args])
            checks[name] = p.returncode == 0
            if p.returncode != 0:
                errors.append(name.upper() + "_FAILED")

    if unshare and curl:
        outside = run([curl, "-I", "--max-time", "2", "https://example.com"])
        inside = run([
            unshare,
            "-Urn",
            curl,
            "-I",
            "--max-time",
            "2",
            "https://example.com",
        ])
        checks["outside_network_reachable"] = outside.returncode == 0
        checks["inside_network_blocked"] = inside.returncode != 0
        if outside.returncode != 0:
            errors.append("CONTROL_NETWORK_UNREACHABLE")
        if inside.returncode == 0:
            errors.append("NETWORK_NAMESPACE_DID_NOT_BLOCK_EXTERNAL_ACCESS")

    if unshare:
        with tempfile.TemporaryDirectory(prefix="root3-kernel-carrier-") as td:
            d = Path(td)
            (d / "a").write_text("x", encoding="utf-8")
            shell = (
                'mount --bind "$1" "$1" && '
                'mount -o remount,bind,ro "$1" && '
                'touch "$1/b"'
            )
            p = run([unshare, "-Urm", "sh", "-c", shell, "sh", str(d)])
            checks["readonly_bind_blocks_write"] = p.returncode != 0
            if p.returncode == 0:
                errors.append("READONLY_BIND_DID_NOT_BLOCK_WRITE")

    ok = not errors and all(checks.values())
    return {
        "schema": SCHEMA,
        "status": "PASS__KERNEL_EFFECT_CARRIER_PRIMITIVES_AVAILABLE" if ok else "FAIL_CLOSED",
        "pass": ok,
        "checks": checks,
        "errors": errors,
        "e2_closed": False,
        "e3_closed": False,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    out = probe()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
