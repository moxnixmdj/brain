#!/usr/bin/env python3
"""Atomically promote one independently verified R2 direct route into live use."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any, Iterator, Mapping

from canonical.runtime import r2_direct_route_dynamic_admission_v1 as admission

SCHEMA = "PROJECT_BRAIN_PROMOTE_R2_DIRECT_ROUTE_V1"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json"


class R2DirectRoutePromotionError(RuntimeError):
    pass


def _receipt_digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@contextmanager
def _promotion_lease(pointer: Path) -> Iterator[dict[str, str]]:
    try:
        import fcntl
    except ImportError as exc:
        raise R2DirectRoutePromotionError("PROMOTION_LEASE_UNAVAILABLE") from exc

    key = hashlib.sha256(str(pointer).encode("utf-8")).hexdigest()
    lock_path = (
        Path(tempfile.gettempdir())
        / ("project_brain_r2_direct_route_promotion_" + key + ".lock")
    )
    handle = lock_path.open("a+b")
    acquired = False
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError as exc:
            raise R2DirectRoutePromotionError("PROMOTION_LEASE_BUSY") from exc
        yield {
            "kind": "LOCAL_PROCESS_FLOCK_NONBLOCKING",
            "lock_key": key,
        }
    finally:
        if acquired:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _promote_locked(
    *,
    root: Path,
    pointer: Path,
    candidate_path: str,
    receipt_path: str,
    lease: Mapping[str, str],
) -> dict[str, Any]:
    current = admission.load_current_admissions(
        repo_root=root,
        pointer_path=pointer,
    )
    compiled = admission.compile_admission(
        repo_root=root,
        current_manifest=current["manifest"],
        candidate_path=candidate_path,
        receipt_path=receipt_path,
    )
    if compiled.get("frontier_changed") is not True:
        return {
            "schema": SCHEMA,
            "status": "ALREADY_LIVE_EXACT_BINDING",
            "pass": True,
            "frontier_changed": False,
            "route_id": compiled.get("route_id"),
            "current_manifest_git_blob_sha": current["target_git_blob_sha"],
            "promotion_lease": dict(lease),
            "verification_authority_mutated": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    raw = bytes(compiled["manifest_bytes"])
    sha = str(compiled["manifest_git_blob_sha"])
    rel = (
        "canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_"
        + sha[:16]
        + ".json"
    )
    target = (root / rel).resolve()
    if root != target and root not in target.parents:
        raise R2DirectRoutePromotionError("TARGET_OUTSIDE_REPOSITORY")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != raw:
            raise R2DirectRoutePromotionError("CONTENT_ADDRESSED_TARGET_CONFLICT")
    else:
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_bytes(raw)
        tmp.replace(target)

    before_commit = admission.load_current_admissions(
        repo_root=root,
        pointer_path=pointer,
    )
    if before_commit["target_git_blob_sha"] != current["target_git_blob_sha"]:
        raise R2DirectRoutePromotionError(
            "CURRENT_POINTER_CHANGED_DURING_PROMOTION"
        )

    pointer_doc = {
        "schema": admission.POINTER_SCHEMA,
        "date": "2026-10-09",
        "status": "ACTIVE_CURRENT_R2_DYNAMIC_ADMISSIONS_POINTER",
        "binding_semantics": (
            "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND"
        ),
        "target": {
            "path": rel,
            "git_blob_sha": sha,
            "schema": admission.MANIFEST_SCHEMA,
        },
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    pointer_raw = (
        json.dumps(pointer_doc, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    tmp_pointer = pointer.with_suffix(pointer.suffix + ".tmp")
    tmp_pointer.write_bytes(pointer_raw)
    tmp_pointer.replace(pointer)

    observed = admission.load_current_admissions(
        repo_root=root,
        pointer_path=pointer,
    )
    ids = {
        str(row["route_id"]) for row in observed["admissions"]
    }
    route_id = str(compiled["route_id"])
    if route_id not in ids or observed["target_git_blob_sha"] != sha:
        raise R2DirectRoutePromotionError("POSTCOMMIT_CURRENT_POINTER_REPLAY_FAILED")

    basis = {
        "route_id": route_id,
        "previous_manifest_git_blob_sha": current["target_git_blob_sha"],
        "new_manifest_git_blob_sha": sha,
        "current_pointer_path": str(pointer.relative_to(root)),
        "candidate_path": candidate_path,
        "receipt_path": receipt_path,
        "frontier_changed": True,
        "promotion_lease_kind": lease["kind"],
        "promotion_lease_key": lease["lock_key"],
        "verification_authority_mutated": False,
    }
    return {
        "schema": SCHEMA,
        "status": "PASS__R2_DIRECT_ROUTE_PROMOTED_AND_CURRENT_POINTER_REPLAYED",
        "pass": True,
        **deepcopy(basis),
        "receipt_sha256": _receipt_digest(basis),
        "promotion_executed": True,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def promote(
    *,
    candidate_path: str,
    receipt_path: str,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    pointer = Path(pointer_path).resolve() if pointer_path is not None else (
        root / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json"
    )
    with _promotion_lease(pointer) as lease:
        return _promote_locked(
            root=root,
            pointer=pointer,
            candidate_path=candidate_path,
            receipt_path=receipt_path,
            lease=lease,
        )

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_path")
    parser.add_argument("receipt_path")
    parser.add_argument("--repo-root", default=str(ROOT))
    args = parser.parse_args()
    try:
        out = promote(
            candidate_path=args.candidate_path,
            receipt_path=args.receipt_path,
            repo_root=args.repo_root,
        )
    except Exception as exc:
        out = {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
