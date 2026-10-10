"""Deterministic reuse-first repair for existing R2 policy-adequacy evidence.

This module never invents semantics, policies, adequacy, or verification.
For an exact live CEGAR problem it searches canonical repository evidence for
already-proved Brain-owned policy adequacy matching the exact policy condition,
pairs it with the required independent verification, and returns only a request
patch for re-verification by the normal R2 authority path.

No discovered artifact gains authority here. The downstream P3 authenticator
must independently accept the content-addressed binding again.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_R2_EXISTING_POLICY_ADEQUACY_REPAIR_V1"
ADEQUACY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1"
ROOT = Path(__file__).resolve().parents[2]
_MAX_JSON_BYTES = 2 * 1024 * 1024
_MAX_FILES = 20000
_SUPPORTED_ARTIFACTS = {
    "POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
    "POSITIVE_POLICY_ADEQUACY_COVERAGE",
}


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _condition_sha256(condition: Mapping[str, Any]) -> str:
    return sha256(_canon(condition).encode("utf-8")).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "repair_authority": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "goal_satisfaction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _safe_json_files(base: Path, relative_root: str) -> list[Path]:
    root = (base / relative_root).resolve(strict=False)
    if not root.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(root.rglob("*.json")):
        if len(out) >= _MAX_FILES:
            break
        try:
            if path.is_symlink() or not path.is_file():
                continue
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(root):
                continue
            if path.stat().st_size > _MAX_JSON_BYTES:
                continue
        except (OSError, RuntimeError):
            continue
        out.append(path)
    return out


def _load_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _relative(base: Path, path: Path) -> str:
    return path.resolve(strict=True).relative_to(base.resolve(strict=True)).as_posix()


def _discover_bindings(
    policy_conditions: Mapping[str, Any],
    *,
    repo_root: Path,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    wanted: dict[tuple[str, str], Mapping[str, Any]] = {}
    for policy_id, condition in policy_conditions.items():
        if not isinstance(policy_id, str) or not policy_id:
            continue
        if not isinstance(condition, Mapping):
            continue
        wanted[(policy_id, _condition_sha256(condition))] = condition

    if not wanted:
        return {}, []

    certificate_rows: list[tuple[str, str, Path, str]] = []
    evidence_trace: list[dict[str, Any]] = []
    for path in (
        _safe_json_files(repo_root, "canonical/governance")
        + _safe_json_files(repo_root, "canonical/verification")
    ):
        doc = _load_object(path)
        if not isinstance(doc, Mapping) or doc.get("schema") != ADEQUACY_SCHEMA:
            continue
        policy_id = doc.get("policy_id")
        condition_sha = doc.get("policy_condition_sha256")
        if (policy_id, condition_sha) not in wanted:
            continue
        if (
            doc.get("adequacy_proved") is not True
            or doc.get("brain_owned") is not True
            or doc.get("load_bearing_constraints_preserved") is not True
        ):
            continue
        blob = _git_blob_sha(path)
        certificate_rows.append((str(policy_id), str(condition_sha), path, blob))

    if not certificate_rows:
        return {}, evidence_trace

    verifications: dict[tuple[str, str], list[tuple[Path, str]]] = {}
    subjects = {(policy_id, blob) for policy_id, _, _, blob in certificate_rows}
    for path in _safe_json_files(repo_root, "canonical/verification"):
        doc = _load_object(path)
        if not isinstance(doc, Mapping) or doc.get("schema") != VERIFY_SCHEMA:
            continue
        key = (doc.get("policy_id"), doc.get("subject_git_blob_sha"))
        if key not in subjects or doc.get("pass") is not True:
            continue
        verifications.setdefault((str(key[0]), str(key[1])), []).append(
            (path, _git_blob_sha(path))
        )

    discovered: dict[str, dict[str, Any]] = {}
    for policy_id, condition_sha, cert_path, cert_blob in sorted(
        certificate_rows,
        key=lambda row: (row[0], _relative(repo_root, row[2]), row[3]),
    ):
        verify_rows = sorted(
            verifications.get((policy_id, cert_blob), []),
            key=lambda row: (_relative(repo_root, row[0]), row[1]),
        )
        if not verify_rows or policy_id in discovered:
            continue
        verify_path, verify_blob = verify_rows[0]
        binding = {
            "adequacy_certificate_path": _relative(repo_root, cert_path),
            "adequacy_certificate_blob_sha": cert_blob,
            "independent_verification_path": _relative(repo_root, verify_path),
            "independent_verification_blob_sha": verify_blob,
        }
        discovered[policy_id] = binding
        evidence_trace.append(
            {
                "policy_id": policy_id,
                "policy_condition_sha256": condition_sha,
                **binding,
            }
        )
    return discovered, evidence_trace


def repair(
    request: Mapping[str, Any],
    next_policy_request: Mapping[str, Any] | None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping):
            return _base("FAIL_CLOSED", reason="REQUEST_NOT_OBJECT")
        if not isinstance(next_policy_request, Mapping):
            return _base("NOT_APPLICABLE__NO_POLICY_REQUEST")

        artifact = next_policy_request.get("required_artifact")
        if artifact not in _SUPPORTED_ARTIFACTS:
            return _base(
                "NOT_APPLICABLE__POLICY_ARTIFACT_NOT_REUSE_DISCOVERABLE",
                required_artifact=artifact,
            )

        decision = request.get("decision_payload")
        if not isinstance(decision, Mapping):
            return _base(
                "UNRESOLVED__DECISION_PAYLOAD_REQUIRED_FOR_ADEQUACY_REUSE"
            )
        loop = decision.get("bound_relevance_cegar_loop")
        if not isinstance(loop, Mapping):
            return _base("UNRESOLVED__CEGAR_LOOP_REQUIRED_FOR_ADEQUACY_REUSE")
        problem = loop.get("cegar_problem")
        if not isinstance(problem, Mapping):
            return _base("UNRESOLVED__CEGAR_PROBLEM_REQUIRED_FOR_ADEQUACY_REUSE")
        conditions = problem.get("policy_conditions")
        if not isinstance(conditions, Mapping) or not conditions:
            return _base("UNRESOLVED__POLICY_CONDITIONS_REQUIRED_FOR_ADEQUACY_REUSE")

        existing = problem.get("policy_adequacy_bindings", {})
        if not isinstance(existing, Mapping):
            return _base("FAIL_CLOSED", reason="EXISTING_POLICY_ADEQUACY_BINDINGS_NOT_OBJECT")

        root = Path(repo_root) if repo_root is not None else ROOT
        root = root.resolve(strict=True)
        discovered, evidence = _discover_bindings(conditions, repo_root=root)
        additions = {
            policy_id: binding
            for policy_id, binding in discovered.items()
            if policy_id not in existing
        }
        if not additions:
            return _base(
                "UNRESOLVED__NO_NEW_EXISTING_POLICY_ADEQUACY_BINDING_DISCOVERED",
                searched_policy_ids=sorted(
                    policy_id
                    for policy_id in conditions
                    if isinstance(policy_id, str)
                ),
                discovered_policy_ids=sorted(discovered),
                evidence_trace=evidence,
            )

        patched_decision = deepcopy(dict(decision))
        patched_loop = patched_decision.get("bound_relevance_cegar_loop")
        if not isinstance(patched_loop, dict):
            patched_loop = deepcopy(dict(loop))
            patched_decision["bound_relevance_cegar_loop"] = patched_loop
        patched_problem = patched_loop.get("cegar_problem")
        if not isinstance(patched_problem, dict):
            patched_problem = deepcopy(dict(problem))
            patched_loop["cegar_problem"] = patched_problem
        combined = deepcopy(dict(existing))
        combined.update(deepcopy(additions))
        patched_problem["policy_adequacy_bindings"] = combined

        return _base(
            "PASS__EXISTING_POLICY_ADEQUACY_BINDINGS_DISCOVERED_FOR_REVERIFICATION",
            passed=True,
            request_patch={"decision_payload": patched_decision},
            added_policy_ids=sorted(additions),
            evidence_trace=[
                row for row in evidence if row.get("policy_id") in additions
            ],
            downstream_reverification_required=True,
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            reason=type(exc).__name__ + ":" + str(exc),
        )
