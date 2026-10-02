"""Dependency-cone proof cache for Project Brain.

A proof receipt may survive a repository change iff every explicitly bound
behavior-relevant dependency remains byte-identical and the manifest itself
declares no untracked dynamic dependency. This never grants terminal credit;
it only decides whether an existing independent receipt remains reusable or
must be revalidated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROOF_DEPENDENCY_CONE_CACHE_INPUT_V1"
VERDICT_SCHEMA = "PROJECT_BRAIN_PROOF_DEPENDENCY_CONE_CACHE_VERDICT_V1"


def _blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def evaluate(root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return _fail("INPUT_NOT_OBJECT")
    if payload.get("schema") != SCHEMA:
        errors.append("SCHEMA_INVALID")

    proof_id = payload.get("proof_id")
    if not isinstance(proof_id, str) or not proof_id:
        errors.append("PROOF_ID_INVALID")

    receipt = payload.get("independent_receipt")
    if not isinstance(receipt, str) or not receipt:
        errors.append("INDEPENDENT_RECEIPT_INVALID")

    if payload.get("dynamic_dependencies_complete") is not True:
        errors.append("DYNAMIC_DEPENDENCY_COMPLETENESS_NOT_PROVEN")
    if payload.get("opaque_runtime_dependency") is True:
        errors.append("OPAQUE_RUNTIME_DEPENDENCY_PRESENT")
    if payload.get("proof_semantics_changed") is True:
        errors.append("PROOF_SEMANTICS_CHANGED")

    deps = payload.get("dependencies")
    if not isinstance(deps, list) or not deps:
        errors.append("DEPENDENCIES_REQUIRED")
        deps = []

    seen: set[str] = set()
    changed: list[dict[str, str]] = []
    verified: list[dict[str, str]] = []
    for i, row in enumerate(deps):
        if not isinstance(row, Mapping):
            errors.append(f"DEPENDENCY_NOT_OBJECT:{i}")
            continue
        rel = row.get("path")
        expected = row.get("blob_sha")
        if not isinstance(rel, str) or not rel:
            errors.append(f"DEPENDENCY_PATH_INVALID:{i}")
            continue
        if rel in seen:
            errors.append(f"DEPENDENCY_DUPLICATE:{rel}")
            continue
        seen.add(rel)
        if not isinstance(expected, str) or len(expected) != 40:
            errors.append(f"DEPENDENCY_BLOB_SHA_INVALID:{rel}")
            continue
        path = root / rel
        if not path.exists() or not path.is_file():
            changed.append({"path": rel, "reason": "MISSING"})
            continue
        actual = _blob_sha(path)
        if actual != expected:
            changed.append({
                "path": rel,
                "reason": "BLOB_CHANGED",
                "expected": expected,
                "actual": actual,
            })
        else:
            verified.append({"path": rel, "blob_sha": actual})

    if errors:
        return _fail(*errors, proof_id=proof_id, changed_dependencies=changed)

    if changed:
        return {
            "schema": VERDICT_SCHEMA,
            "status": "REVALIDATION_REQUIRED__BEHAVIOR_RELEVANT_DEPENDENCY_CHANGED",
            "pass": True,
            "proof_reusable": False,
            "revalidation_required": True,
            "proof_id": proof_id,
            "independent_receipt": receipt,
            "changed_dependencies": changed,
            "unchanged_dependency_count": len(verified),
            "execution_authority": False,
            "promotion_authority": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "errors": [],
        }

    return {
        "schema": VERDICT_SCHEMA,
        "status": "PROOF_RECEIPT_REUSABLE__DEPENDENCY_CONE_UNCHANGED",
        "pass": True,
        "proof_reusable": True,
        "revalidation_required": False,
        "proof_id": proof_id,
        "independent_receipt": receipt,
        "verified_dependencies": verified,
        "dependency_count": len(verified),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": [],
        "rule": (
            "UNRELATED_REPOSITORY_CHANGES_DO_NOT_INVALIDATE_A_PROOF__"
            "ONLY_DECLARED_BEHAVIOR_RELEVANT_DEPENDENCY_OR_PROOF_SEMANTIC_CHANGES_DO"
        ),
    }


def _fail(*errors: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": VERDICT_SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "proof_reusable": False,
        "revalidation_required": True,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": sorted(set(errors)),
    }
    out.update(extra)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("manifest", type=Path)
    args = ap.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    out = evaluate(args.root, payload)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
