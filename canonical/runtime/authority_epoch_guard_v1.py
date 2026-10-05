"""Fail-closed authority epoch guard for Project Brain workers.

An authority epoch is a content hash over the small set of live control-plane
objects that can change whether previously scheduled work is still load-bearing:
current terminal authority, root partition, atomic acceptance ledger, and the
highest-version active zero-reality scheduling activation plus its bound cut.

Workers freeze the epoch before doing expensive work. Before execution, evidence
consumption, or merge, they compare that frozen epoch against the current base.
A mismatch means the plan may be stale and must fail closed and replan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]

STATIC_EPOCH_PATHS = (
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
)

ACTIVATION_RE = re.compile(
    r"^canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V(\d+)_ACTIVATION_V1\.json$"
)


class AuthorityEpochError(RuntimeError):
    pass


def _git(*args: str) -> str:
    p = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        raise AuthorityEpochError(
            "GIT_FAILED:" + " ".join(args) + ":" + p.stderr.strip()
        )
    return p.stdout.strip()


def git_blob_sha(path: str, ref: str = "HEAD") -> str:
    out = _git("rev-parse", f"{ref}:{path}")
    if not re.fullmatch(r"[0-9a-f]{40}", out):
        raise AuthorityEpochError(f"INVALID_GIT_BLOB_SHA:{path}:{out}")
    return out


def json_at_ref(path: str, ref: str = "HEAD") -> dict[str, Any]:
    raw = _git("show", f"{ref}:{path}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AuthorityEpochError(f"INVALID_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise AuthorityEpochError(f"NOT_JSON_OBJECT:{path}")
    return value


def compute_epoch(blob_map: Mapping[str, str]) -> str:
    if not blob_map:
        raise AuthorityEpochError("EMPTY_EPOCH_INPUT")
    lines = []
    for path, sha in sorted(blob_map.items()):
        if not path or not re.fullmatch(r"[0-9a-f]{40}", str(sha)):
            raise AuthorityEpochError(f"INVALID_EPOCH_COMPONENT:{path}:{sha}")
        lines.append(f"{path}={sha}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def select_latest_active_activation(
    candidates: Sequence[tuple[int, str, Mapping[str, Any]]]
) -> tuple[int, str, Mapping[str, Any]]:
    active = [
        row
        for row in candidates
        if row[2].get("scheduling_authority") is True
    ]
    if not active:
        raise AuthorityEpochError("NO_ACTIVE_ZERO_REALITY_ACTIVATION")
    active.sort(key=lambda row: (row[0], row[1]))
    return active[-1]


def _discover_active_activation(ref: str) -> tuple[str, dict[str, Any]]:
    names = _git("ls-tree", "-r", "--name-only", ref, "canonical/governance").splitlines()
    candidates: list[tuple[int, str, Mapping[str, Any]]] = []
    for path in names:
        m = ACTIVATION_RE.match(path)
        if not m:
            continue
        doc = json_at_ref(path, ref)
        candidates.append((int(m.group(1)), path, doc))
    _, path, doc = select_latest_active_activation(candidates)
    return path, dict(doc)


def epoch_components(ref: str = "HEAD") -> dict[str, str]:
    blobs = {path: git_blob_sha(path, ref) for path in STATIC_EPOCH_PATHS}

    activation_path, activation = _discover_active_activation(ref)
    activation_blob = git_blob_sha(activation_path, ref)
    blobs[activation_path] = activation_blob

    subject = activation.get("subject")
    if not isinstance(subject, Mapping):
        raise AuthorityEpochError("ACTIVE_ACTIVATION_SUBJECT_MISSING")
    cut_path = str(subject.get("path") or "")
    declared_cut_blob = str(subject.get("git_blob_sha") or "")
    if not cut_path:
        raise AuthorityEpochError("ACTIVE_ACTIVATION_CUT_PATH_MISSING")
    actual_cut_blob = git_blob_sha(cut_path, ref)
    if declared_cut_blob != actual_cut_blob:
        raise AuthorityEpochError(
            f"ACTIVE_ACTIVATION_CUT_BLOB_MISMATCH:{declared_cut_blob}:{actual_cut_blob}"
        )
    blobs[cut_path] = actual_cut_blob
    return blobs


def epoch_for_ref(ref: str = "HEAD") -> dict[str, Any]:
    components = epoch_components(ref)
    return {
        "schema": "PROJECT_BRAIN_AUTHORITY_EPOCH_V1",
        "ref": ref,
        "epoch_sha256": compute_epoch(components),
        "components": dict(sorted(components.items())),
    }


def verify_expected_epoch(expected: str, ref: str = "HEAD") -> dict[str, Any]:
    current = epoch_for_ref(ref)
    ok = bool(expected) and expected == current["epoch_sha256"]
    return {
        **current,
        "expected_epoch_sha256": expected,
        "status": "PASS__AUTHORITY_EPOCH_CURRENT" if ok else "FAIL_CLOSED__STALE_AUTHORITY_EPOCH",
        "pass": ok,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--expected")
    ns = ap.parse_args()
    try:
        out = (
            verify_expected_epoch(ns.expected, ns.ref)
            if ns.expected is not None
            else epoch_for_ref(ns.ref)
        )
        print(json.dumps(out, indent=2, sort_keys=True))
        if ns.expected is not None and not out["pass"]:
            return 42
        return 0
    except AuthorityEpochError as exc:
        print(json.dumps({
            "schema": "PROJECT_BRAIN_AUTHORITY_EPOCH_V1",
            "status": "FAIL_CLOSED__AUTHORITY_EPOCH_ERROR",
            "error": str(exc),
            "pass": False,
        }, indent=2, sort_keys=True))
        return 43


if __name__ == "__main__":
    raise SystemExit(main())
