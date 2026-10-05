"""Two-clock validity guard for Project Brain work units.

Separates semantic proposition validity from scheduler/control-plane freshness.
This module NEVER grants execution, promotion, or fresh-reality authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.authority_epoch_guard_v1 import epoch_for_ref

ROOT = Path(__file__).resolve().parents[2]
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


class WorkUnitValidityError(RuntimeError):
    pass


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise WorkUnitValidityError(
            "GIT_FAILED:" + " ".join(args) + ":" + proc.stderr.strip()
        )
    return proc.stdout.strip()


def git_blob_sha(path: str, ref: str = "HEAD") -> str:
    out = _git("rev-parse", f"{ref}:{path}")
    if not SHA40_RE.fullmatch(out):
        raise WorkUnitValidityError(f"INVALID_GIT_BLOB_SHA:{path}:{out}")
    return out


def compute_component_digest(blob_map: Mapping[str, str]) -> str:
    if not blob_map:
        raise WorkUnitValidityError("EMPTY_SEMANTIC_DEPENDENCY_SET")
    lines: list[str] = []
    for path, sha in sorted(blob_map.items()):
        if not path or not SHA40_RE.fullmatch(str(sha)):
            raise WorkUnitValidityError(f"INVALID_SEMANTIC_COMPONENT:{path}:{sha}")
        lines.append(f"{path}={sha}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def current_semantic_components(
    expected_components: Mapping[str, str], ref: str = "HEAD"
) -> dict[str, str]:
    if not expected_components:
        raise WorkUnitValidityError("EMPTY_SEMANTIC_DEPENDENCY_SET")
    return {path: git_blob_sha(path, ref) for path in sorted(expected_components)}


def evaluate_two_clock_lease(
    *,
    expected_semantic_components: Mapping[str, str],
    current_semantic_components_map: Mapping[str, str],
    expected_scheduler_epoch_sha256: str,
    current_scheduler_epoch_sha256: str,
    dependency_closure_verified: bool,
    work_class: str,
) -> dict[str, Any]:
    if work_class not in {"ZERO_REALITY_DERIVATION", "FRESH_REALITY_ACTION"}:
        raise WorkUnitValidityError(f"INVALID_WORK_CLASS:{work_class}")
    if not dependency_closure_verified:
        return {
            "status": "FAIL_CLOSED__DEPENDENCY_CLOSURE_UNVERIFIED",
            "semantic_valid": False,
            "semantic_reuse_allowed": False,
            "scheduler_current": False,
            "fresh_reality_gate_current": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }

    expected_digest = compute_component_digest(expected_semantic_components)
    current_digest = compute_component_digest(current_semantic_components_map)
    semantic_valid = (
        dict(expected_semantic_components) == dict(current_semantic_components_map)
        and expected_digest == current_digest
    )
    scheduler_current = bool(expected_scheduler_epoch_sha256) and (
        expected_scheduler_epoch_sha256 == current_scheduler_epoch_sha256
    )

    if not semantic_valid:
        status = "FAIL_CLOSED__SEMANTIC_DEPENDENCY_DRIFT"
        reuse = False
    elif scheduler_current:
        status = "PASS__SEMANTIC_AND_SCHEDULER_CURRENT"
        reuse = True
    elif work_class == "ZERO_REALITY_DERIVATION":
        status = "PASS__SEMANTIC_RESULT_REUSABLE__SCHEDULER_REPLAN_REQUIRED"
        reuse = True
    else:
        status = "FAIL_CLOSED__SCHEDULER_STALE_FOR_FRESH_REALITY"
        reuse = True

    return {
        "status": status,
        "work_class": work_class,
        "semantic_valid": semantic_valid,
        "semantic_reuse_allowed": reuse,
        "semantic_dependency_digest_expected": expected_digest,
        "semantic_dependency_digest_current": current_digest,
        "scheduler_current": scheduler_current,
        "fresh_reality_gate_current": semantic_valid and scheduler_current,
        "rule": (
            "SEMANTIC_VALIDITY_DEPENDS_ONLY_ON_THE_VERIFIED_TRANSITIVE_DEPENDENCY_CONE;"
            " FRESH_REALITY_OR_PROMOTION_REQUIRES_CURRENT_SCHEDULER_AUTHORITY."
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def load_lease(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkUnitValidityError(f"INVALID_LEASE:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise WorkUnitValidityError("LEASE_NOT_JSON_OBJECT")
    return value


def verify_lease(lease: Mapping[str, Any], ref: str = "HEAD") -> dict[str, Any]:
    expected = lease.get("semantic_dependencies")
    if not isinstance(expected, Mapping):
        raise WorkUnitValidityError("LEASE_SEMANTIC_DEPENDENCIES_MISSING")
    expected_map = {str(k): str(v) for k, v in expected.items()}

    closure = lease.get("dependency_closure")
    closure_path = (
        str(closure.get("certificate_path") or "")
        if isinstance(closure, Mapping)
        else ""
    )
    closure_sha = (
        str(closure.get("git_blob_sha") or "")
        if isinstance(closure, Mapping)
        else ""
    )
    closure_verified = (
        isinstance(closure, Mapping)
        and closure.get("independently_verified") is True
        and bool(closure_path)
        and SHA40_RE.fullmatch(closure_sha) is not None
        and expected_map.get(closure_path) == closure_sha
    )

    scheduler = lease.get("scheduler")
    if not isinstance(scheduler, Mapping):
        raise WorkUnitValidityError("LEASE_SCHEDULER_MISSING")
    expected_scheduler = str(scheduler.get("authority_epoch_sha256") or "")

    work_class = str(lease.get("work_class") or "")
    current_components = current_semantic_components(expected_map, ref)
    current_scheduler = epoch_for_ref(ref)["epoch_sha256"]

    result = evaluate_two_clock_lease(
        expected_semantic_components=expected_map,
        current_semantic_components_map=current_components,
        expected_scheduler_epoch_sha256=expected_scheduler,
        current_scheduler_epoch_sha256=current_scheduler,
        dependency_closure_verified=closure_verified,
        work_class=work_class,
    )
    result.update(
        {
            "schema": "PROJECT_BRAIN_TWO_CLOCK_WORK_UNIT_VALIDITY_GUARD_V1",
            "ref": ref,
            "dependency_closure_certificate": closure_path or None,
            "current_scheduler_epoch_sha256": current_scheduler,
            "expected_scheduler_epoch_sha256": expected_scheduler,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lease", required=True)
    parser.add_argument("--ref", default="HEAD")
    args = parser.parse_args()
    try:
        out = verify_lease(load_lease(args.lease), args.ref)
        print(json.dumps(out, indent=2, sort_keys=True))
        if out["status"].startswith("FAIL_CLOSED"):
            return 42
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema": "PROJECT_BRAIN_TWO_CLOCK_WORK_UNIT_VALIDITY_GUARD_V1",
                    "status": "FAIL_CLOSED__WORK_UNIT_VALIDITY_ERROR",
                    "error": f"{type(exc).__name__}:{exc}",
                    "execution_authority": False,
                    "promotion_authority": False,
                    "fresh_reality_authority": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 43


if __name__ == "__main__":
    raise SystemExit(main())
