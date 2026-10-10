"""Verify the content-addressed professional-quality declared system subject.

This verifier grants identity/currentness evidence only. It never upgrades
component membership into root satisfaction, semantic closure, quality
authority, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_VERIFY_V1"
SUBJECT_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V2"
MATERIAL_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_V3_DECLARED_SYSTEM_SUBJECT_MATERIAL_V2"
DEFAULT_SUBJECT_PATH = "canonical/governance/PROFESSIONAL_QUALITY_P1_V3_DECLARED_SYSTEM_SUBJECT_20261010_V2.json"
ROOT = Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "subject_identity_verified": False,
        "component_currentness_verified": False,
        "root_subject_binding_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return _base("FAIL_CLOSED", reason=reason, **extra)


def _resolve(root: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.startswith("canonical/"):
        return None
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path


def verify(
    subject_path: str = DEFAULT_SUBJECT_PATH,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    path = _resolve(root, subject_path)
    if path is None or not path.is_file() or path.is_symlink():
        return _fail("SUBJECT_FILE_INVALID")

    try:
        subject = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _fail("SUBJECT_JSON_INVALID")
    if not isinstance(subject, dict):
        return _fail("SUBJECT_DOCUMENT_INVALID")
    if subject.get("schema") != SUBJECT_SCHEMA:
        return _fail("SUBJECT_SCHEMA_INVALID")
    if subject.get("subject_kind") != "DECLARED_SYSTEM":
        return _fail("SUBJECT_KIND_INVALID")
    subject_id = subject.get("subject_id")
    declared_sha = subject.get("subject_sha256")
    if not isinstance(subject_id, str) or not subject_id.strip():
        return _fail("SUBJECT_ID_INVALID")
    if (
        not isinstance(declared_sha, str)
        or len(declared_sha) != 64
        or any(c not in "0123456789abcdef" for c in declared_sha)
    ):
        return _fail("SUBJECT_SHA256_INVALID")

    material = subject.get("system_material")
    if not isinstance(material, dict) or material.get("schema") != MATERIAL_SCHEMA:
        return _fail("SYSTEM_MATERIAL_INVALID")
    actual_subject_sha = sha256(_canon(material)).hexdigest()
    if actual_subject_sha != declared_sha:
        return _fail(
            "SUBJECT_HASH_MISMATCH",
            declared_subject_sha256=declared_sha,
            actual_subject_sha256=actual_subject_sha,
        )

    components = material.get("components")
    if not isinstance(components, list) or not components:
        return _fail("COMPONENTS_INVALID")
    seen: set[str] = set()
    verified: list[dict[str, str]] = []
    for i, ref in enumerate(components):
        if not isinstance(ref, Mapping):
            return _fail("COMPONENT_REFERENCE_INVALID", component_index=i)
        raw_path = ref.get("path")
        declared_blob = ref.get("git_blob_sha")
        if not isinstance(raw_path, str) or raw_path in seen:
            return _fail("COMPONENT_PATH_INVALID_OR_DUPLICATE", component_index=i)
        seen.add(raw_path)
        resolved = _resolve(root, raw_path)
        if resolved is None or not resolved.is_file() or resolved.is_symlink():
            return _fail("COMPONENT_FILE_INVALID", component_index=i, component_path=raw_path)
        actual_blob = _git_blob_sha(resolved)
        if not isinstance(declared_blob, str) or actual_blob != declared_blob:
            return _fail(
                "COMPONENT_BLOB_STALE",
                component_index=i,
                component_path=raw_path,
                declared_git_blob_sha=declared_blob,
                actual_git_blob_sha=actual_blob,
            )
        verified.append({"path": raw_path, "git_blob_sha": actual_blob})

    identity = subject.get("identity_semantics")
    if not isinstance(identity, Mapping):
        return _fail("IDENTITY_SEMANTICS_INVALID")
    if identity.get("component_inclusion_does_not_imply_root_satisfaction") is not True:
        return _fail("ROOT_SATISFACTION_NONAUTHORITY_REQUIRED")
    if identity.get("scoped_evidence_inclusion_does_not_transport_scope") is not True:
        return _fail("SCOPE_NONTRANSPORT_REQUIRED")
    if identity.get("root_subject_binding_requires_independent_verification") is not True:
        return _fail("INDEPENDENT_ROOT_BINDING_REQUIRED")
    if identity.get("global_subject_identity_authority") is not False:
        return _fail("GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN")
    if subject.get("terminal_authority") is not False:
        return _fail("TERMINAL_AUTHORITY_FORBIDDEN")

    return _base(
        "PASS__DECLARED_SYSTEM_SUBJECT_CURRENT_AND_CONTENT_ADDRESSED",
        passed=True,
        subject_identity_verified=True,
        component_currentness_verified=True,
        subject_kind="DECLARED_SYSTEM",
        subject_id=subject_id,
        subject_sha256=declared_sha,
        subject_git_blob_sha=_git_blob_sha(path),
        component_count=len(verified),
        verified_components=verified,
    )


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
