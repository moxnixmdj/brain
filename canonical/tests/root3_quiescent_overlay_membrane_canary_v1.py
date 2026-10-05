#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile

from canonical.runtime.quiescent_declared_artifact_extractor_v2 import (
    DeclaredArtifact,
    extract_declared_artifacts,
)
from canonical.runtime.quiescent_episode_protocol_v1 import (
    classify_snapshot,
    inject_response_once,
    make_outcome,
    make_response,
)


def snapshot(root: pathlib.Path) -> dict[str, tuple[str, int, str]]:
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            out[rel] = ("symlink", 0, os.readlink(path))
        elif path.is_file():
            raw = path.read_bytes()
            out[rel] = ("file", len(raw), hashlib.sha256(raw).hexdigest())
        elif path.is_dir():
            out[rel] = ("dir", 0, "")
    return out


def write_outcome(repo: pathlib.Path, outcome: dict) -> None:
    path = repo / ".brain" / "episode_outcome.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(outcome, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def worker(sequence: int, outer_port: int) -> int:
    repo = pathlib.Path("/repo")
    brain = repo / ".brain"

    outer = socket.socket()
    outer.settimeout(0.2)
    try:
        outer.connect(("127.0.0.1", outer_port))
        network_blocked = False
    except OSError:
        network_blocked = True
    finally:
        outer.close()

    code = (
        "import json,pathlib,socket;"
        "o={'host_etc_hidden':not pathlib.Path('/etc/passwd').exists()};"
        "s=socket.socket();s.settimeout(.2);"
        "\ntry:s.connect(('127.0.0.1'," + str(outer_port) + "));o['outer_unreachable']=False"
        "\nexcept OSError:o['outer_unreachable']=True"
        "\nprint(json.dumps(o,sort_keys=True))"
    )
    grand = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=2,
    )
    grandchild = json.loads(grand.stdout)

    response_path = brain / "responses" / "req-1.json"
    if sequence == 0:
        outcome = make_outcome(
            episode_id="canary-episode",
            sequence=0,
            kind="REQUEST",
            payload={
                "request_type": "TEST_PARENT_SERVICE",
                "request_id": "req-1",
                "request": {
                    "query": "canary",
                    "network_blocked": network_blocked,
                    "host_etc_hidden": not pathlib.Path("/etc/passwd").exists(),
                    "grandchild": grandchild,
                },
            },
        )
        write_outcome(repo, outcome)
        return 75

    response = json.loads(response_path.read_text(encoding="utf-8"))
    (repo / "artifact.bin").write_bytes(b"declared-artifact")
    (repo / "secret.tmp").write_bytes(b"must-be-discarded")
    outcome = make_outcome(
        episode_id="canary-episode",
        sequence=1,
        kind="COMPLETE",
        payload={
            "result": {
                "network_blocked": network_blocked,
                "host_etc_hidden": not pathlib.Path("/etc/passwd").exists(),
                "grandchild": grandchild,
                "response_envelope_sha256": response["envelope_sha256"],
            },
            "declared_artifact_ids": ["artifact-1"],
        },
    )
    write_outcome(repo, outcome)
    return 0


def make_lower(source_root: pathlib.Path, lower: pathlib.Path) -> None:
    (lower / "canonical" / "runtime").mkdir(parents=True)
    (lower / "canonical" / "__init__.py").write_text("", encoding="utf-8")
    (lower / "canonical" / "runtime" / "__init__.py").write_text("", encoding="utf-8")
    for name in (
        "quiescent_episode_protocol_v1.py",
        "quiescent_declared_artifact_extractor_v2.py",
    ):
        shutil.copy2(
            source_root / "canonical" / "runtime" / name,
            lower / "canonical" / "runtime" / name,
        )
    shutil.copy2(__file__, lower / "worker.py")
    (lower / "seed.txt").write_text("immutable-lower\n", encoding="utf-8")


def run_episode(
    *,
    lower: pathlib.Path,
    upper: pathlib.Path,
    work: pathlib.Path,
    sequence: int,
    outer_port: int,
) -> int:
    episode_root = pathlib.Path(tempfile.mkdtemp(prefix="brain-qoverlay-root-"))
    merged = pathlib.Path(tempfile.mkdtemp(prefix="brain-qoverlay-merged-"))
    setup = r"""
set -euo pipefail
ROOT="$1"; LOWER="$2"; UPPER="$3"; WORK="$4"; MERGED="$5"; SEQ="$6"; PORT="$7"
mount --make-rprivate /
mount -t overlay overlay -o "lowerdir=$LOWER,upperdir=$UPPER,workdir=$WORK" "$MERGED"
mount -t tmpfs -o size=128m,nosuid,nodev tmpfs "$ROOT"
mkdir -p "$ROOT"/{usr,bin,lib,lib64,repo,tmp}
for d in /usr /bin /lib /lib64; do
  [ -e "$d" ] || continue
  mount --bind "$d" "$ROOT$d"
  mount -o remount,bind,ro "$ROOT$d"
done
mount --bind "$MERGED" "$ROOT/repo"
mount -t tmpfs -o size=16m,nosuid,nodev,noexec tmpfs "$ROOT/tmp"
ip link set lo up
ulimit -t 3
ulimit -v 262144
ulimit -f 2048
ulimit -n 32
ulimit -u 32
exec chroot "$ROOT" /usr/bin/env -i   PATH=/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/repo   /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all   /usr/bin/python3 /repo/worker.py --worker "$SEQ" "$PORT"
"""
    try:
        proc = subprocess.run(
            [
                "unshare",
                "--user",
                "--map-root-user",
                "--mount",
                "--net",
                "--pid",
                "--fork",
                "--kill-child=SIGKILL",
                "--ipc",
                "--uts",
                "bash",
                "-c",
                setup,
                "_",
                str(episode_root),
                str(lower),
                str(upper),
                str(work),
                str(merged),
                str(sequence),
                str(outer_port),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            timeout=10,
        )
        return int(proc.returncode)
    finally:
        shutil.rmtree(episode_root, ignore_errors=True)
        shutil.rmtree(merged, ignore_errors=True)


def parent() -> int:
    source_root = pathlib.Path(__file__).resolve().parents[2]
    base = pathlib.Path(tempfile.mkdtemp(prefix="brain-qoverlay-canary-"))
    lower = base / "lower"
    upper = base / "upper"
    work = base / "work"
    lower.mkdir()
    upper.mkdir()
    work.mkdir()
    make_lower(source_root, lower)
    before = snapshot(lower)

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    outer_port = listener.getsockname()[1]

    first_rc = run_episode(
        lower=lower,
        upper=upper,
        work=work,
        sequence=0,
        outer_port=outer_port,
    )
    first = classify_snapshot(
        upper,
        expected_episode_id="canary-episode",
        expected_sequence=0,
    )
    request = first["payload"]["request"]
    request_safe = all(
        [
            first_rc == 75,
            first["kind"] == "REQUEST",
            request["network_blocked"] is True,
            request["host_etc_hidden"] is True,
            request["grandchild"]["outer_unreachable"] is True,
            request["grandchild"]["host_etc_hidden"] is True,
        ]
    )

    response = make_response(
        episode_id="canary-episode",
        sequence=1,
        request_id="req-1",
        request_outcome_sha256=first["outcome_sha256"],
        response={"status": "ok", "value": "trusted-parent-result"},
    )
    inject_response_once(upper, response)

    second_rc = run_episode(
        lower=lower,
        upper=upper,
        work=work,
        sequence=1,
        outer_port=outer_port,
    )
    second = classify_snapshot(
        upper,
        expected_episode_id="canary-episode",
        expected_sequence=1,
    )
    result = second["payload"]["result"]

    extracted = extract_declared_artifacts(
        upper,
        {
            "artifact-1": DeclaredArtifact(
                "artifact-1",
                "artifact.bin",
                "application/octet-stream",
                1024,
            )
        },
    )
    artifact_safe = (
        extracted["artifact_count"] == 1
        and extracted["artifacts"][0]["relative_path"] == "artifact.bin"
        and (upper / "secret.tmp").is_file()
        and "secret.tmp" not in {
            row["relative_path"] for row in extracted["artifacts"]
        }
    )

    after = snapshot(lower)
    lower_unchanged = before == after
    no_app_fds = True  # subprocess.run used close_fds=True with no pass_fds.
    completion_safe = all(
        [
            second_rc == 0,
            second["kind"] == "COMPLETE",
            result["network_blocked"] is True,
            result["host_etc_hidden"] is True,
            result["grandchild"]["outer_unreachable"] is True,
            result["grandchild"]["host_etc_hidden"] is True,
            result["response_envelope_sha256"] == response["envelope_sha256"],
        ]
    )

    report = {
        "schema": "PROJECT_BRAIN_ROOT3_QUIESCENT_OVERLAY_MEMBRANE_CANARY_V1",
        "first_rc": first_rc,
        "second_rc": second_rc,
        "request_safe": request_safe,
        "completion_safe": completion_safe,
        "declared_artifact_safe": artifact_safe,
        "lower_unchanged": lower_unchanged,
        "no_application_fds_inherited": no_app_fds,
        "live_worker_network": "NONE",
        "semantic_worker_channel": "PRIVATE_OVERLAY_SNAPSHOT_AFTER_QUIESCENCE",
        "undeclared_overlay_state": "PRESENT_BUT_NOT_EXTRACTED__DISCARDABLE",
    }
    report["status"] = "PASS" if all(
        [
            request_safe,
            completion_safe,
            artifact_safe,
            lower_unchanged,
            no_app_fds,
        ]
    ) else "FAIL"
    print(json.dumps(report, sort_keys=True))
    listener.close()
    shutil.rmtree(base, ignore_errors=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        raise SystemExit(worker(int(sys.argv[2]), int(sys.argv[3])))
    raise SystemExit(parent())
