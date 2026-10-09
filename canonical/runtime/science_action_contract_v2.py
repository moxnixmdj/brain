"""Pure typed-action contract for Brain science controller V2."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import shlex
from typing import Any, Mapping

from canonical.runtime.harbor_command_policy import validate_environment_command

LANGUAGES = frozenset({"shell", "python"})
_SCHEMA_MARKER = "SCHEMA_KEYS_JSON:"
_SHELL_PYTHON_RE = re.compile(r"(?i)(?:^|[;&|]\s*|\s)(?:python|python3)(?:\s|$)")
_SHELL_STRUCTURED_KEY_RE = re.compile(
    r"""(?ix)\b(?:jq|yq)\b[^\n]{0,160}?[\'\"]?\.(?P<key>[A-Za-z_][A-Za-z0-9_.-]{0,127})"""
)
_YAML_KEY_RE = re.compile(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_.-]{0,127})\s*:")


def normalize_language(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise RuntimeError(f"SCIENCE_{field}_INVALID")
    out = value.strip().lower()
    if out not in LANGUAGES:
        raise RuntimeError(f"SCIENCE_{field}_INVALID")
    return out


def looks_like_bare_python(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    strong = (
        ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.AugAssign,
        ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try,
        ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
    )
    return any(isinstance(node, strong) for node in ast.walk(tree))


def render_source(language: Any, source: Any, *, field: str) -> tuple[str, str]:
    language = normalize_language(language, field=field + "_LANGUAGE")
    if not isinstance(source, str) or not source.strip():
        raise RuntimeError(f"SCIENCE_{field}_REQUIRED")
    source = validate_environment_command(source.strip())
    if language == "shell":
        if looks_like_bare_python(source):
            raise RuntimeError(f"SCIENCE_{field}_EXECUTION_LANGUAGE_MISMATCH")
        if _SHELL_PYTHON_RE.search(source):
            raise RuntimeError(f"SCIENCE_{field}_PYTHON_REQUIRES_TYPED_LANGUAGE")
        return language, source
    rendered = "python -c " + shlex.quote(source)
    return language, validate_environment_command(rendered)


def action_fingerprint(language: Any, source: Any) -> str:
    language = normalize_language(language, field="COMMAND_LANGUAGE")
    if not isinstance(source, str) or not source.strip():
        raise RuntimeError("SCIENCE_COMMAND_REQUIRED")
    payload = json.dumps(
        {"language": language, "source": source.strip()},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _dotted_name(node: ast.AST, aliases: dict[str, str], funcs: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return funcs.get(node.id, aliases.get(node.id, node.id))
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value, aliases, funcs)
        return None if base is None else base + "." + node.attr
    return None


def python_external_literal_keys(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    aliases: dict[str, str] = {}
    funcs: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for name in node.names:
                aliases[name.asname or name.name.split(".")[0]] = name.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for name in node.names:
                funcs[name.asname or name.name] = node.module + "." + name.name
    loaders = {
        "json.load", "json.loads", "yaml.safe_load", "yaml.load",
        "tomllib.load", "numpy.load",
    }
    external_names: set[str] = set()

    def is_loader(node: ast.AST) -> bool:
        return isinstance(node, ast.Call) and _dotted_name(node.func, aliases, funcs) in loaders

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and is_loader(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    external_names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and node.value is not None and is_loader(node.value):
            if isinstance(node.target, ast.Name):
                external_names.add(node.target.id)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if is_loader(item.context_expr) and isinstance(item.optional_vars, ast.Name):
                    external_names.add(item.optional_vars.id)

    keys: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.ctx, ast.Load)
            and isinstance(node.value, ast.Name)
            and node.value.id in external_names
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            keys.add(node.slice.value)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in external_names
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.add(node.args[0].value)
    return sorted(keys)


def required_schema_keys(language: Any, source: Any) -> list[str]:
    language = normalize_language(language, field="COMMAND_LANGUAGE")
    if not isinstance(source, str):
        return []
    if language == "python":
        return python_external_literal_keys(source)
    return sorted({m.group("key") for m in _SHELL_STRUCTURED_KEY_RE.finditer(source)})


def _collect_json_keys(value: Any, out: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str):
                out.add(key)
            _collect_json_keys(child, out)
    elif isinstance(value, list):
        for child in value:
            _collect_json_keys(child, out)


def schema_keys_from_text(text: str, *, document: bool) -> set[str]:
    text = str(text or "")
    out: set[str] = set()
    for line in text.splitlines():
        if line.startswith(_SCHEMA_MARKER):
            try:
                value = json.loads(line[len(_SCHEMA_MARKER):].strip())
            except Exception:
                continue
            if isinstance(value, list):
                out.update(x for x in value if isinstance(x, str) and x)
    if not document:
        return out
    body = text.split("---CONTENT---", 1)[-1]
    try:
        parsed = json.loads(body.strip())
    except Exception:
        parsed = None
    if parsed is not None:
        _collect_json_keys(parsed, out)
    out.update(_YAML_KEY_RE.findall(body))
    return out


def prompt_observation_state(prompt: str) -> tuple[set[str], set[str]]:
    marker = "Recent observations: "
    if marker not in prompt:
        return set(), set()
    raw = prompt.rsplit(marker, 1)[1]
    try:
        rows = json.loads(raw)
    except Exception:
        return set(), set()
    if not isinstance(rows, list):
        return set(), set()

    observed: set[str] = set()
    failed: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("kind") == "BRAIN_DECLARED_INPUT_SNAPSHOT" and row.get("returncode") == 0:
            observed.update(schema_keys_from_text(row.get("stdout", ""), document=True))
        action = row.get("action_result")
        if isinstance(action, dict) and action.get("returncode") == 0:
            observed.update(schema_keys_from_text(action.get("stdout", ""), document=False))
        if (
            row.get("kind") == "BRAIN_SELECTED_RESEARCH_ACTION"
            and row.get("coverage_promoted") is False
        ):
            aid = row.get("action_id")
            if isinstance(aid, str) and len(aid) == 64 and all(c in "0123456789abcdef" for c in aid):
                failed.add(aid)
    return observed, failed
