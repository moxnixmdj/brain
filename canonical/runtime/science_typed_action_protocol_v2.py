"""Brain-owned typed action, schema-grounding, and authoritative-artifact protocol for science carriers.

This module is task-agnostic. It converts explicitly typed candidate source into
deterministic executable commands, requires declared/authenticated schema keys for
literal Python mapping dereferences, content-addresses action identity, and defines
bounded deliverable postconditions. It grants no benchmark or finish authority.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import shlex
from pathlib import PurePosixPath
from typing import Any, Mapping

from canonical.runtime.harbor_command_policy import validate_environment_command

EXECUTOR_KINDS = frozenset({"shell", "python"})
SCHEMA_FORMATS = frozenset({"json", "npz"})
DELIVERABLE_FORMATS = frozenset({"file", "json", "python", "npz", "npy", "csv"})
MAX_SCHEMA_REQUIREMENTS = 16
MAX_SCHEMA_KEYS_PER_REQUIREMENT = 32
MAX_DELIVERABLES = 16
MAX_SCHEMA_KEY_CHARS = 128
_SCHEMA_KEY_RE = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")


class ScienceTypedActionError(ValueError):
    pass


def _app_path(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ScienceTypedActionError(label + "_PATH_INVALID")
    value = value.strip()
    if not value.startswith("/app/"):
        raise ScienceTypedActionError(label + "_PATH_OUTSIDE_APP")
    p = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in p.parts[1:]):
        raise ScienceTypedActionError(label + "_PATH_INVALID")
    return str(p)


_FORBIDDEN_AUTHORITATIVE_OUTPUT_ROOTS = frozenset({"/proc", "/sys", "/dev"})
_FORBIDDEN_AUTHORITATIVE_OUTPUT_PREFIXES = ("/proc/", "/sys/", "/dev/", "/run/secrets/")


def _authoritative_output_path(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ScienceTypedActionError(label + "_PATH_INVALID")
    value = value.strip()
    if not value.startswith("/") or len(value) > 1024 or "\\x00" in value:
        raise ScienceTypedActionError(label + "_PATH_INVALID")
    p = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in p.parts[1:]):
        raise ScienceTypedActionError(label + "_PATH_INVALID")
    normalized = str(p)
    if normalized in _FORBIDDEN_AUTHORITATIVE_OUTPUT_ROOTS or any(
        normalized.startswith(prefix) for prefix in _FORBIDDEN_AUTHORITATIVE_OUTPUT_PREFIXES
    ):
        raise ScienceTypedActionError(label + "_PATH_FORBIDDEN")
    return normalized


def _keys(value: Any) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > MAX_SCHEMA_KEYS_PER_REQUIREMENT:
        raise ScienceTypedActionError("SCHEMA_KEYS_INVALID")
    out: list[str] = []
    for raw in value:
        if not isinstance(raw, str):
            raise ScienceTypedActionError("SCHEMA_KEY_INVALID")
        key = raw.strip()
        if not key or _SCHEMA_KEY_RE.fullmatch(key) is None or len(key) > MAX_SCHEMA_KEY_CHARS:
            raise ScienceTypedActionError("SCHEMA_KEY_INVALID")
        if key in out:
            raise ScienceTypedActionError("SCHEMA_KEY_DUPLICATE")
        out.append(key)
    return out


def normalize_schema_requirements(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_SCHEMA_REQUIREMENTS:
        raise ScienceTypedActionError("SCHEMA_REQUIREMENTS_INVALID")
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in value:
        if not isinstance(row, Mapping):
            raise ScienceTypedActionError("SCHEMA_REQUIREMENT_OBJECT_REQUIRED")
        path = _app_path(row.get("path"), "SCHEMA")
        fmt = str(row.get("format") or "").strip().lower()
        if fmt not in SCHEMA_FORMATS:
            raise ScienceTypedActionError("SCHEMA_FORMAT_INVALID")
        ident = (path, fmt)
        if ident in seen:
            raise ScienceTypedActionError("SCHEMA_REQUIREMENT_DUPLICATE")
        seen.add(ident)
        out.append({"path": path, "format": fmt, "keys": _keys(row.get("keys"))})
    return out


def normalize_deliverables(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_DELIVERABLES:
        raise ScienceTypedActionError("DELIVERABLES_INVALID")
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in value:
        if not isinstance(row, Mapping):
            raise ScienceTypedActionError("DELIVERABLE_OBJECT_REQUIRED")
        path = _app_path(row.get("path"), "DELIVERABLE")
        fmt = str(row.get("format") or "").strip().lower()
        if fmt not in DELIVERABLE_FORMATS:
            raise ScienceTypedActionError("DELIVERABLE_FORMAT_INVALID")
        ident = (path, fmt)
        if ident in seen:
            raise ScienceTypedActionError("DELIVERABLE_DUPLICATE")
        seen.add(ident)
        out.append({"path": path, "format": fmt})
    return out


def _literal_mapping_keys(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ScienceTypedActionError("PYTHON_SOURCE_SYNTAX_INVALID") from exc
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            value = node.slice
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                keys.add(value.value)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"get", "pop", "setdefault"} and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    keys.add(arg.value)
    return keys


def compile_typed_source(
    executor: Any,
    source: Any,
    *,
    schema_requirements: list[dict[str, Any]] | None = None,
) -> tuple[str, set[str]]:
    kind = str(executor or "").strip().lower()
    if kind not in EXECUTOR_KINDS:
        raise ScienceTypedActionError("EXECUTOR_KIND_INVALID")
    if not isinstance(source, str) or not source.strip():
        raise ScienceTypedActionError("EXECUTOR_SOURCE_REQUIRED")
    source = source.strip()

    if kind == "shell":
        return validate_environment_command(source), set()

    literal_keys = _literal_mapping_keys(source)
    declared = {
        key
        for row in (schema_requirements or [])
        for key in row.get("keys", [])
        if isinstance(key, str)
    }
    missing = sorted(literal_keys - declared)
    if missing:
        raise ScienceTypedActionError(
            "PYTHON_LITERAL_SCHEMA_KEYS_UNDECLARED:" + ",".join(missing)
        )
    command = validate_environment_command("python -c " + shlex.quote(source))
    return command, literal_keys


def schema_probe_command(row: Mapping[str, Any]) -> str:
    path = _app_path(row.get("path"), "SCHEMA")
    fmt = str(row.get("format") or "").strip().lower()
    keys = _keys(row.get("keys"))
    if fmt == "json":
        code = (
            "import json;"
            f"p={path!r};"
            "d=json.load(open(p,'r',encoding='utf-8'));"
            "assert isinstance(d,dict);"
            f"ks={keys!r};"
            "m=[k for k in ks if k not in d];"
            "assert not m,m"
        )
    elif fmt == "npz":
        code = (
            "import numpy as np;"
            f"p={path!r};"
            "z=np.load(p,allow_pickle=False);"
            f"ks={keys!r};"
            "m=[k for k in ks if k not in z.files];"
            "assert not m,m"
        )
    else:
        raise ScienceTypedActionError("SCHEMA_FORMAT_INVALID")
    return validate_environment_command("python -c " + shlex.quote(code))


def deliverable_check_command(row: Mapping[str, Any]) -> str:
    path = _app_path(row.get("path"), "DELIVERABLE")
    fmt = str(row.get("format") or "").strip().lower()
    if fmt not in DELIVERABLE_FORMATS:
        raise ScienceTypedActionError("DELIVERABLE_FORMAT_INVALID")
    q = shlex.quote(path)
    if fmt == "file":
        return validate_environment_command(f"test -s {q}")
    if fmt == "json":
        return validate_environment_command(f"test -s {q} && python -m json.tool {q} >/dev/null")
    if fmt == "python":
        return validate_environment_command(f"test -s {q} && python -m py_compile {q}")
    if fmt == "npz":
        code = f"import numpy as np;z=np.load({path!r},allow_pickle=False);assert len(z.files)>0"
    elif fmt == "npy":
        code = f"import numpy as np;a=np.load({path!r},allow_pickle=False);assert getattr(a,'size',0)>0"
    else:
        code = (
            "import csv;"
            f"p={path!r};"
            "f=open(p,'r',encoding='utf-8',newline='');"
            "r=csv.reader(f);"
            "row=next(r);"
            "assert len(row)>0"
        )
    return validate_environment_command(f"test -s {q} && python -c " + shlex.quote(code))


def authoritative_deliverable_check_command(row: Mapping[str, Any]) -> str:
    """Check a Brain/task-authoritative artifact at a safe absolute container path.

    This function is intentionally separate from deliverable_check_command():
    planner-proposed deliverables remain /app-scoped, while immutable task metadata
    and exact instruction-bound outputs may live elsewhere in the task container.
    """
    path = _authoritative_output_path(row.get("path"), "AUTHORITATIVE_DELIVERABLE")
    fmt = str(row.get("format") or "").strip().lower()
    if fmt not in DELIVERABLE_FORMATS:
        raise ScienceTypedActionError("DELIVERABLE_FORMAT_INVALID")
    q = shlex.quote(path)
    if fmt == "file":
        return validate_environment_command(f"test -s {q}")
    if fmt == "json":
        return validate_environment_command(f"test -s {q} && python -m json.tool {q} >/dev/null")
    if fmt == "python":
        return validate_environment_command(f"test -s {q} && python -m py_compile {q}")
    if fmt == "npz":
        code = f"import numpy as np;z=np.load({path!r},allow_pickle=False);assert len(z.files)>0"
    elif fmt == "npy":
        code = f"import numpy as np;a=np.load({path!r},allow_pickle=False);assert getattr(a,'size',0)>0"
    else:
        code = (
            "import csv;"
            f"p={path!r};"
            "f=open(p,'r',encoding='utf-8',newline='');"
            "r=csv.reader(f);"
            "row=next(r);"
            "assert len(row)>0"
        )
    return validate_environment_command(f"test -s {q} && python -c " + shlex.quote(code))


def effect_fingerprint(executor: Any, compiled_command: Any) -> str:
    kind = str(executor or "").strip().lower()
    if kind not in EXECUTOR_KINDS:
        raise ScienceTypedActionError("EXECUTOR_KIND_INVALID")
    if not isinstance(compiled_command, str) or not compiled_command:
        raise ScienceTypedActionError("EFFECT_COMMAND_INVALID")
    material = {"executor": kind, "compiled_command": compiled_command}
    raw = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def action_fingerprint(row: Mapping[str, Any]) -> str:
    material = {
        "executor": row.get("executor"),
        "command_source": row.get("command_source"),
        "verify_executor": row.get("verify_executor"),
        "verify_source": row.get("verify_source"),
        "schema_requirements": row.get("schema_requirements") or [],
        "deliverables": row.get("deliverables") or [],
    }
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def inferred_format_from_path(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".json"):
        return "json"
    if lower.endswith(".py"):
        return "python"
    if lower.endswith(".npz"):
        return "npz"
    if lower.endswith(".npy"):
        return "npy"
    if lower.endswith(".csv"):
        return "csv"
    return "file"


def normalize_authoritative_artifacts(value: Any) -> list[dict[str, str]]:
    """Normalize immutable task-authoritative artifact paths.

    These paths do not come from planner output. They are permitted outside /app
    but remain absolute, traversal-free, bounded, and outside virtual/secret roots.
    """
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_DELIVERABLES:
        raise ScienceTypedActionError("AUTHORITATIVE_ARTIFACTS_INVALID")
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in value:
        path = _authoritative_output_path(raw, "AUTHORITATIVE_ARTIFACT")
        if path in seen:
            continue
        seen.add(path)
        out.append({"path": path, "format": inferred_format_from_path(path)})
    return out


def source_observed_deliverables(catalog: Any) -> list[dict[str, str]]:
    """Extract only literal /app paths from exact source-native output-key fields.

    This creates a conservative postcondition, never semantic identity or success
    authority. An incorrect extra output-like source field can only fail closed.
    """
    if not isinstance(catalog, list):
        raise ScienceTypedActionError("SOURCE_CATALOG_INVALID")
    output_keys = {"output", "output_path", "result_path", "submission_path"}
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in catalog:
        if not isinstance(row, Mapping):
            continue
        scalars = row.get("selected_scalars")
        if not isinstance(scalars, Mapping):
            continue
        for key in sorted(output_keys):
            value = scalars.get(key)
            if not isinstance(value, str):
                continue
            try:
                path = _app_path(value, "SOURCE_DELIVERABLE")
            except ScienceTypedActionError:
                continue
            if path in seen:
                continue
            seen.add(path)
            out.append({"path": path, "format": inferred_format_from_path(path)})
    return out
