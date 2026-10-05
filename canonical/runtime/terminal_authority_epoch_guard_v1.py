#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TERMINAL_AUTHORITY_EPOCH_GUARD_V1"
GOVERNANCE_PATH = "canonical/governance/TERMINAL_AUTHORITY_EPOCH_V1.json"


class EpochError(RuntimeError):
    pass


def _canonical_payload(bindings: Sequence[Mapping[str, str]]) -> str:
    payload = {
        "version": 1,
        "sources": [
            {"path": str(x["path"]), "git_blob_sha": str(x["git_blob_sha"])}
            for x in bindings
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_epoch_id(bindings: Sequence[Mapping[str, str]]) -> str:
    return hashlib.sha256(_canonical_payload(bindings).encode("utf-8")).hexdigest()


def admit(worker_epoch: str, current_epoch: str) -> dict[str, Any]:
    ok = bool(worker_epoch) and worker_epoch == current_epoch
    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_EPOCH" if ok else "STALE_ABORT__EPOCH_MISMATCH",
        "admitted": ok,
        "worker_epoch": worker_epoch,
        "current_epoch": current_epoch,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
    }


def _git_blob(root: pathlib.Path, path: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"HEAD:{path}"],
        check=True,
        text=True,
        capture_output=True,
    )
    return p.stdout.strip()


def verify_repository_epoch(root: pathlib.Path | None = None) -> dict[str, Any]:
    root = pathlib.Path(root or pathlib.Path(__file__).resolve().parents[2])
    gov = json.loads((root / GOVERNANCE_PATH).read_text(encoding="utf-8"))
    expected_bindings = list(gov["source_bindings"])
    observed = []
    mismatches = []
    for item in expected_bindings:
        got = _git_blob(root, str(item["path"]))
        row = {"path": str(item["path"]), "git_blob_sha": got}
        observed.append(row)
        if got != str(item["git_blob_sha"]):
            mismatches.append({
                "path": str(item["path"]),
                "expected": str(item["git_blob_sha"]),
                "observed": got,
            })
    expected_epoch = str(gov["epoch_algorithm"]["sha256"])
    recomputed_expected = compute_epoch_id(expected_bindings)
    observed_epoch = compute_epoch_id(observed)
    ok = (
        not mismatches
        and expected_epoch == recomputed_expected
        and observed_epoch == expected_epoch
    )
    return {
        "schema": SCHEMA,
        "status": "PASS__EPOCH_SOURCE_BINDINGS_CURRENT" if ok else "STALE_ABORT__SOURCE_AUTHORITY_CHANGED",
        "admitted": ok,
        "expected_epoch": expected_epoch,
        "recomputed_expected_epoch": recomputed_expected,
        "observed_epoch": observed_epoch,
        "mismatches": mismatches,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
    }


def run(args: Mapping[str, Any] | None = None, root: pathlib.Path | None = None) -> dict[str, Any]:
    args = dict(args or {})
    repo = verify_repository_epoch(root)
    if not repo["admitted"]:
        return repo
    worker_epoch = str(args.get("authority_epoch_id") or "")
    return admit(worker_epoch, str(repo["expected_epoch"]))


if __name__ == "__main__":
    import sys
    args = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(run(args), sort_keys=True))
