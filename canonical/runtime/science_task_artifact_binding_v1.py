"""Generic task-authoritative artifact binding for scientific execution.

Primary authority is the task package's declared artifacts array. Instruction
text parsing is a bounded fallback only when the package declares no artifacts.
This module discovers postconditions; it does not execute commands, judge task
success, or grant benchmark, acceptance, or terminal credit.
"""
from __future__ import annotations

import re
import tomllib
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SCIENCE_TASK_ARTIFACT_BINDING_V1"
MAX_ARTIFACTS = 32
_PATH_RE = re.compile(r"^/[A-Za-z0-9_./{}-]+\.[A-Za-z0-9]+$")
_FALLBACK_RE = re.compile(
    r"""(?is)\b(?:write|create|save|store|export|produce|deliver|emit)\b
        [^.\n]{0,320}?
        \b(?:to|at|as|into)\s+
        (?:(?:a|the)\s+)?
        (?:(?:file|artifact|output|result|results)\s+)?
        (?:(?:named|called)\s+)?
        [`'"\[]*
        (?P<path>/[A-Za-z0-9_./{}-]+\.[A-Za-z0-9]+)
    """,
    re.VERBOSE,
)


class ArtifactBindingError(ValueError):
    pass


def _path(value: Any) -> str:
    if not isinstance(value, str):
        raise ArtifactBindingError("ARTIFACT_PATH_NOT_STRING")
    path = value.strip().rstrip(".,;:")
    if not path.startswith("/") or "\x00" in path:
        raise ArtifactBindingError("ARTIFACT_PATH_INVALID")
    parts = path.split("/")[1:]
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ArtifactBindingError("ARTIFACT_PATH_INVALID")
    if _PATH_RE.fullmatch(path) is None:
        raise ArtifactBindingError("ARTIFACT_PATH_UNSUPPORTED")
    return path


def task_toml_artifacts(task_toml: str | bytes) -> list[str]:
    if isinstance(task_toml, str):
        raw = task_toml.encode("utf-8")
    elif isinstance(task_toml, bytes):
        raw = task_toml
    else:
        raise ArtifactBindingError("TASK_TOML_INVALID")
    try:
        doc = tomllib.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ArtifactBindingError(
            "TASK_TOML_PARSE_FAILED:" + type(exc).__name__
        ) from exc
    if not isinstance(doc, Mapping):
        raise ArtifactBindingError("TASK_TOML_NOT_OBJECT")
    values = doc.get("artifacts")
    if values is None:
        return []
    if not isinstance(values, list):
        raise ArtifactBindingError("TASK_ARTIFACTS_NOT_LIST")
    if len(values) > MAX_ARTIFACTS:
        raise ArtifactBindingError("TASK_ARTIFACTS_OVERFLOW")
    out: list[str] = []
    for value in values:
        p = _path(value)
        if p not in out:
            out.append(p)
    return out


def instruction_fallback_artifacts(instruction: str) -> list[str]:
    if not isinstance(instruction, str):
        raise ArtifactBindingError("INSTRUCTION_INVALID")
    out: list[str] = []
    for match in _FALLBACK_RE.finditer(instruction):
        p = _path(match.group("path"))
        if p not in out:
            out.append(p)
        if len(out) > MAX_ARTIFACTS:
            raise ArtifactBindingError("INSTRUCTION_ARTIFACTS_OVERFLOW")
    return out


def bind(*, task_toml: str | bytes | None, instruction: str) -> dict[str, Any]:
    """Return exact mandatory artifact postconditions, fail closed on bad authority."""
    try:
        declared = [] if task_toml is None else task_toml_artifacts(task_toml)
        if declared:
            paths = declared
            source = "TASK_TOML_ARTIFACTS"
            fallback_used = False
        else:
            paths = instruction_fallback_artifacts(instruction)
            source = "INSTRUCTION_EXPLICIT_OUTPUT_FALLBACK" if paths else "NONE"
            fallback_used = bool(paths)
        return {
            "schema": SCHEMA,
            "status": "BOUND" if paths else "NO_ARTIFACT_POSTCONDITION_FOUND",
            "pass": True,
            "paths": paths,
            "source": source,
            "task_authority_used": source == "TASK_TOML_ARTIFACTS",
            "instruction_fallback_used": fallback_used,
            "artifact_count": len(paths),
            "execution_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "paths": [],
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "execution_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
        }
