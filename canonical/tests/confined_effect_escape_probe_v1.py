from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

REQUEST_SCHEMA = "PROJECT_BRAIN_EFFECT_REQUEST_V1"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def request_id(body):
    return hashlib.sha256(canonical(body)).hexdigest()


def attempt_repo_write():
    path = Path("/repo/.confined_effect_escape_probe")
    try:
        path.write_text("escape", encoding="utf-8")
        return False, "WRITE_SUCCEEDED"
    except Exception as exc:
        return True, type(exc).__name__


def attempt_network():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.connect(("1.1.1.1", 53))
        return False, "CONNECT_SUCCEEDED"
    except Exception as exc:
        return True, type(exc).__name__
    finally:
        sock.close()


def descendant_probe():
    code = r"""
from pathlib import Path
import json, socket
out={}
try:
    Path('/repo/.confined_effect_descendant_escape').write_text('escape')
    out['repo_write_blocked']=False
except Exception as exc:
    out['repo_write_blocked']=True
    out['repo_write_error']=type(exc).__name__
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.settimeout(1.0)
try:
    s.connect(('1.1.1.1',53))
    out['network_blocked']=False
except Exception as exc:
    out['network_blocked']=True
    out['network_error']=type(exc).__name__
finally:
    s.close()
print(json.dumps(out,sort_keys=True))
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        text=True,
        capture_output=True,
        timeout=5,
    )
    return proc.returncode, json.loads(proc.stdout.strip())


def main():
    spool = Path(sys.argv[1])
    repo_blocked, repo_error = attempt_repo_write()
    net_blocked, net_error = attempt_network()
    child_rc, child = descendant_probe()

    observation = {
        "schema": "PROJECT_BRAIN_CONFINED_EFFECT_ESCAPE_OBSERVATION_V1",
        "direct_repo_write_blocked": repo_blocked,
        "direct_repo_write_error": repo_error,
        "direct_network_blocked": net_blocked,
        "direct_network_error": net_error,
        "descendant_returncode": child_rc,
        "descendant_repo_write_blocked": child["repo_write_blocked"],
        "descendant_network_blocked": child["network_blocked"],
    }
    print(json.dumps(observation, sort_keys=True), flush=True)

    body = {
        "schema": REQUEST_SCHEMA,
        "effect_type": "write_text_artifact",
        "target": "proof/approved.txt",
        "payload": {"text": "broker-approved\n"},
        "guard_context": {"mode": "K1_K3_SUBSTRATE_PROBE_ONLY"},
    }
    request = dict(body)
    request["request_id"] = request_id(body)
    request_path = spool / "requests" / (request["request_id"] + ".json")
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n", encoding="utf-8")

    response_path = spool / "responses" / (request["request_id"] + ".json")
    deadline = time.monotonic() + 10
    while not response_path.exists():
        if time.monotonic() >= deadline:
            raise RuntimeError("BROKER_RESPONSE_TIMEOUT")
        time.sleep(0.02)
    response = json.loads(response_path.read_text(encoding="utf-8"))
    print(json.dumps(response, sort_keys=True), flush=True)
    if response.get("status") != "applied":
        raise RuntimeError("BROKER_DENIED_APPROVED_PROBE")


if __name__ == "__main__":
    main()
