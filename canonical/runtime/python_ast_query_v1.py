"""Typed, read-only Python AST queries for the live front door.

This is a bounded engineering adapter, not a model-weight update and not a claim of
general semantic understanding.  It exists because the previous "semantic generalization"
path retrieved a *similar* stored sentence and then let keyword presence in the *current*
sentence choose the operation.  Measured failures on the shipped seed corpus:

* "Count methods" returned every function, including free and nested functions.
* "Count functions and classes" returned only the function count.
* "Do not count functions" returned the function count.
* A missing file could be answered by scanning a parent directory.
* An absolute path outside the caller workspace was read.

Contract
--------
* Only explicit, single-file, read-only count/list shapes are served.
* The operation and AST target are bound from the current request, never from memory.
* Source is resolved under the caller's workspace root; symlink escapes are refused.
* Negated, filtered, multi-file, effectful or unsupported refinements are refused.
* Success means the answer was computed from the current bytes by Python's own parser.
  It is structural acceptance, not an independent oracle about program behaviour.

Supported targets: functions (including methods and nested defs), methods (nearest
enclosing scope is a class), classes, if statements (including ``elif``).
"""
from __future__ import annotations

import ast
import hashlib
import pathlib
import re
from dataclasses import dataclass
from typing import Any

SCHEMA = "BRAIN_PYTHON_AST_QUERY_V1"
PASS_STATUS = "PASS__TIER0A_TYPED_PYTHON_AST_QUERY"
TIER = "tier0a_typed_python_ast_query"
MAX_SOURCE_BYTES = 4 * 1024 * 1024

_PATH_RE = re.compile(r"(?<![\w.])(?:[A-Za-z]:)?[^\s'\"`,;]+\.py\b", re.IGNORECASE)
_QUERY_START_RE = re.compile(
    r"^(?:please\s+)?(?:count|enumerate|list|identify|find|how\s+many|read|open|parse|inspect|analyze|do\s+not\s+count|don't\s+count)\b",
    re.IGNORECASE,
)
_EFFECT_RE = re.compile(
    r"\b(?:write|save|create|delete|remove|modify|edit|fix|repair|run|execute|install|commit|move|rename|copy|append|output)\b",
    re.IGNORECASE,
)
_NEGATION_RE = re.compile(r"\b(?:not|never|without|exclude|except|only\s+free|non[- ]method)\b", re.IGNORECASE)
_VERB = r"(count|enumerate|list|identify|find|how\s+many)"
_FILE_PREFIX = r"(?:the\s+)?(?:python\s+)?(?:source\s+file\s+|file\s+|module\s+)?"
_TARGET_PHRASE = r"(.+?)"
_TEMPLATES = (
    re.compile(rf"^(?:please\s+)?{_VERB}\s+(?:the\s+)?(?:number\s+of\s+)?{_TARGET_PHRASE}\s+in\s+{_FILE_PREFIX}FILE$", re.IGNORECASE),
    re.compile(rf"^(?:please\s+)?{_VERB}\s+(?:the\s+)?(?:number\s+of\s+)?{_TARGET_PHRASE}\s+defined\s+in\s+{_FILE_PREFIX}FILE$", re.IGNORECASE),
    re.compile(rf"^(?:please\s+)?(?:read|open|parse|inspect|analyze)\s+{_FILE_PREFIX}FILE\s+and\s+{_VERB}\s+(?:the\s+)?(?:number\s+of\s+)?{_TARGET_PHRASE}$", re.IGNORECASE),
    re.compile(rf"^in\s+{_FILE_PREFIX}FILE[, ]+\s*(?:please\s+)?{_VERB}\s+(?:the\s+)?(?:number\s+of\s+)?{_TARGET_PHRASE}$", re.IGNORECASE),
)
_TARGET_ALIASES = {
    "function": "functions", "functions": "functions",
    "subroutine": "functions", "subroutines": "functions",
    "method": "methods", "methods": "methods",
    "class": "classes", "classes": "classes",
    "if statement": "if_statements", "if statements": "if_statements",
    "if": "if_statements", "ifs": "if_statements",
}
_FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)


class PythonAstQueryError(ValueError):
    """A recognized read-only AST query that this adapter must refuse."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class PythonAstQuery:
    operation: str
    targets: tuple[str, ...]
    path_text: str


def _parse_targets(phrase: str) -> tuple[str, ...]:
    text = phrase.strip().lower()
    text = re.sub(r"\s+definitions?$", "", text)
    parts = re.split(r"\s*(?:,|and)\s*", text)
    targets: list[str] = []
    for part in parts:
        part = part.strip()
        part = re.sub(r"^(?:the|all|every)\s+", "", part)
        if part not in _TARGET_ALIASES:
            raise PythonAstQueryError("UNSUPPORTED_TARGET", phrase)
        kind = _TARGET_ALIASES[part]
        if kind not in targets:
            targets.append(kind)
    if not targets:
        raise PythonAstQueryError("UNSUPPORTED_TARGET", phrase)
    return tuple(targets)


def parse_query(goal: str) -> PythonAstQuery | None:
    """Return a typed query, refuse an unsafe/unsupported recognized query, or None.

    ``None`` means "not this adapter's lane"; the caller may continue to other routes.
    A recognized but negated/ambiguous/effectful read-only query raises instead, so it
    cannot fall through to a weaker keyword matcher and be answered affirmatively.
    """
    text = " ".join(str(goal or "").strip().split())
    if text.endswith("."):
        text = text[:-1].rstrip()
    paths = _PATH_RE.findall(text)
    if not paths:
        return None
    if len(paths) != 1:
        if _QUERY_START_RE.match(text):
            raise PythonAstQueryError("AMBIGUOUS_SOURCE", "exactly one .py file is supported")
        return None
    path_text = paths[0].strip("`'\"")
    prose = text.replace(paths[0], "FILE")
    prose = " ".join(prose.split())
    if not _QUERY_START_RE.match(prose):
        return None
    if _EFFECT_RE.search(prose):
        # An effectful request belongs to the write/effect lane, not this read-only adapter.
        return None
    if _NEGATION_RE.search(prose):
        raise PythonAstQueryError("NEGATED_OR_FILTERED_QUERY", prose)
    for template in _TEMPLATES:
        match = template.match(prose)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 2:
            verb, phrase = groups
        else:
            verb, phrase = groups[0], groups[1]
        targets = _parse_targets(phrase)
        operation = "count" if verb.lower() in {"count", "how many"} else "list"
        return PythonAstQuery(operation=operation, targets=targets, path_text=path_text)
    raise PythonAstQueryError("UNSUPPORTED_QUERY_SHAPE", prose)


def _collect(tree: ast.AST) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def visit(node: ast.AST, scopes: tuple[str, ...], qual: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _FUNCS):
                name = child.name
                q = qual + (name,)
                rows.append({"kind": "functions", "name": name, "qualname": ".".join(q), "line": child.lineno, "end_line": child.end_lineno})
                if scopes and scopes[-1] == "class":
                    rows.append({"kind": "methods", "name": name, "qualname": ".".join(q), "line": child.lineno, "end_line": child.end_lineno})
                visit(child, scopes + ("function",), q)
            elif isinstance(child, ast.ClassDef):
                q = qual + (child.name,)
                rows.append({"kind": "classes", "name": child.name, "qualname": ".".join(q), "line": child.lineno, "end_line": child.end_lineno})
                visit(child, scopes + ("class",), q)
            elif isinstance(child, ast.If):
                rows.append({"kind": "if_statements", "name": None, "qualname": ".".join(qual), "line": child.lineno, "end_line": child.end_lineno})
                visit(child, scopes, qual)
            else:
                visit(child, scopes, qual)

    visit(tree, (), ())
    rows.sort(key=lambda row: (row["line"], row["kind"], row["qualname"]))
    return rows


def _structural_acceptance(tree: ast.AST, rows: list[dict[str, Any]], targets: tuple[str, ...]) -> dict[str, Any]:
    """Check the answer against the parsed tree.  This is not an independent behavioural oracle."""
    by_line: dict[int, list[ast.AST]] = {}
    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", None)
        if isinstance(lineno, int):
            by_line.setdefault(lineno, []).append(node)
    checked = 0
    for row in rows:
        if row["kind"] not in targets:
            continue
        nodes = by_line.get(row["line"], [])
        if row["kind"] == "functions":
            ok = any(isinstance(node, _FUNCS) and node.name == row["name"] for node in nodes)
        elif row["kind"] == "classes":
            ok = any(isinstance(node, ast.ClassDef) and node.name == row["name"] for node in nodes)
        elif row["kind"] == "if_statements":
            ok = any(isinstance(node, ast.If) for node in nodes)
        elif row["kind"] == "methods":
            ok = any(isinstance(node, _FUNCS) and node.name == row["name"] for node in nodes)
        else:
            ok = False
        if not ok:
            raise PythonAstQueryError("ACCEPTANCE_FAILED", str(row))
        checked += 1
    return {"checked": True, "basis": "python_ast", "independent_oracle": False, "rows_checked": checked}


def solve_query(goal: str, *, root: pathlib.Path | str) -> dict[str, Any] | None:
    """Serve a bounded read-only AST query, or return None when the goal is not this lane."""
    query = parse_query(goal)
    if query is None:
        return None
    workspace = pathlib.Path(root).resolve()
    raw = pathlib.Path(query.path_text)
    candidate = raw if raw.is_absolute() else workspace / raw
    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError) as exc:
        raise PythonAstQueryError("PATH_RESOLUTION_FAILED", str(exc)) from exc
    if not resolved.is_relative_to(workspace):
        raise PythonAstQueryError("PATH_OUTSIDE_ROOT", str(resolved))
    if not resolved.exists():
        raise PythonAstQueryError("SOURCE_MISSING", query.path_text)
    if not resolved.is_file():
        raise PythonAstQueryError("SOURCE_NOT_A_FILE", query.path_text)
    if resolved.suffix.lower() != ".py":
        raise PythonAstQueryError("SOURCE_NOT_PYTHON", query.path_text)
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise PythonAstQueryError("SOURCE_UNREADABLE", str(exc)) from exc
    if size > MAX_SOURCE_BYTES:
        raise PythonAstQueryError("SOURCE_TOO_LARGE", f"{size} bytes")
    try:
        source = resolved.read_bytes()
    except OSError as exc:
        raise PythonAstQueryError("SOURCE_UNREADABLE", str(exc)) from exc
    try:
        tree = ast.parse(source, filename=str(resolved))
    except (SyntaxError, ValueError, UnicodeError) as exc:
        raise PythonAstQueryError("PARSE_FAILED", str(exc)) from exc
    all_rows = _collect(tree)
    rows = [row for row in all_rows if row["kind"] in query.targets]
    acceptance = _structural_acceptance(tree, rows, query.targets)
    if query.operation == "count":
        if len(query.targets) == 1:
            answer: Any = len(rows)
        else:
            answer = {target: sum(1 for row in rows if row["kind"] == target) for target in query.targets}
    else:
        answer = rows
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": PASS_STATUS,
        "tier_used": TIER,
        "from_memory": False,
        "learned_from_this_request": False,
        "operation": query.operation,
        "targets": list(query.targets),
        "source_path": str(resolved.relative_to(workspace)).replace("\\", "/"),
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "answer": answer,
        "locations": rows,
        "acceptance": acceptance,
    }


def failure_result(exc: PythonAstQueryError) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "executed": False,
        "status": f"FAIL_CLOSED__PYTHON_AST_{exc.code}",
        "failure_class": f"PYTHON_AST_{exc.code}",
        "tier_used": TIER,
        "from_memory": False,
        "detail": exc.detail,
        "semantic_acceptance_complete": False,
    }
