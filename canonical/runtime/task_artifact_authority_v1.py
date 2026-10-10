"""Normalize task-authoritative artifact metadata without conflating service ownership.

Harbor task manifests have used both legacy string artifact entries and structured
entries such as {"source": "/path", "service": "main"}. This module preserves
the full normalized artifact relation while exposing only artifacts owned by the
selected service to that service's agent finish gate.

It grants no task success, execution, acceptance, or terminal authority.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TASK_ARTIFACT_AUTHORITY_V1"
MAX_ARTIFACTS = 64
MAX_PATH_CHARS = 1024
MAX_SERVICE_CHARS = 128
DEFAULT_SERVICE = "main"

_FORBIDDEN_MAIN_ROOTS = frozenset({"/proc", "/sys", "/dev"})
_FORBIDDEN_MAIN_PREFIXES = ("/run/secrets/",)


class TaskArtifactAuthorityError(ValueError):
    pass


def _absolute_path(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise TaskArtifactAuthorityError(label + "_NOT_STRING")
    value = value.strip()
    if (
        not value
        or len(value) > MAX_PATH_CHARS
        or not value.startswith("/")
        or "\x00" in value
    ):
        raise TaskArtifactAuthorityError(label + "_INVALID")
    path = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in path.parts[1:]):
        raise TaskArtifactAuthorityError(label + "_INVALID")
    return str(path)


def _service(value: Any) -> str:
    if value is None:
        return DEFAULT_SERVICE
    if not isinstance(value, str):
        raise TaskArtifactAuthorityError("ARTIFACT_SERVICE_NOT_STRING")
    value = value.strip()
    if not value or len(value) > MAX_SERVICE_CHARS:
        raise TaskArtifactAuthorityError("ARTIFACT_SERVICE_INVALID")
    if any(ord(ch) < 32 for ch in value):
        raise TaskArtifactAuthorityError("ARTIFACT_SERVICE_INVALID")
    return value


def _main_service_path_allowed(path: str) -> bool:
    if path in _FORBIDDEN_MAIN_ROOTS:
        return False
    return not any(path.startswith(prefix) for prefix in _FORBIDDEN_MAIN_PREFIXES)


def normalize_artifacts(value: Any) -> list[dict[str, str]]:
    """Return canonical artifact rows, preserving service ownership.

    Accepted input forms:
      - legacy absolute path string -> service="main"
      - mapping with absolute string "source" and optional string "service"

    Other keys are ignored because they are not part of the finish-postcondition
    identity consumed here. Duplicate (source, service) rows collapse stably.
    """
    if value is None:
        return []
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > MAX_ARTIFACTS
    ):
        raise TaskArtifactAuthorityError("ARTIFACTS_INVALID")

    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in value:
        if isinstance(raw, str):
            source = _absolute_path(raw, label="ARTIFACT_SOURCE")
            service = DEFAULT_SERVICE
        elif isinstance(raw, Mapping):
            source = _absolute_path(raw.get("source"), label="ARTIFACT_SOURCE")
            service = _service(raw.get("service"))
        else:
            raise TaskArtifactAuthorityError("ARTIFACT_ROW_INVALID")

        key = (source, service)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"source": source, "service": service})

    rows.sort(key=lambda row: (row["service"], row["source"]))
    return rows


def service_artifact_paths(value: Any, *, service: str = DEFAULT_SERVICE) -> list[str]:
    """Return only artifact paths owned by one service.

    For the main agent, virtual/secret roots fail closed because the V12 finish
    gate is allowed to inspect arbitrary safe absolute task-authoritative paths.
    Non-main service artifacts remain represented in normalize_artifacts() but
    are never injected into the main agent's finish obligations.
    """
    target = _service(service)
    paths: list[str] = []
    for row in normalize_artifacts(value):
        if row["service"] != target:
            continue
        path = row["source"]
        if target == DEFAULT_SERVICE and not _main_service_path_allowed(path):
            raise TaskArtifactAuthorityError("MAIN_ARTIFACT_PATH_FORBIDDEN:" + path)
        paths.append(path)
    return paths


def normalize_task_manifest(task_manifest: Mapping[str, Any], *, service: str = DEFAULT_SERVICE) -> dict[str, Any]:
    if not isinstance(task_manifest, Mapping):
        raise TaskArtifactAuthorityError("TASK_MANIFEST_INVALID")
    rows = normalize_artifacts(task_manifest.get("artifacts"))
    paths = service_artifact_paths(rows, service=service)
    return {
        "schema": SCHEMA,
        "service": _service(service),
        "artifacts": rows,
        "service_artifact_paths": paths,
        "finish_authority": False,
        "task_success_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }
