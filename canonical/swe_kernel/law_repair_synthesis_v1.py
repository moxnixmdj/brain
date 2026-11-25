"""Synthesize a repair for a *law* violation, not for a test.

The oracle reports "this presented string has a trailing space". The repair follows from the law
alone: the value that is presented must be canonical, so canonicalize it at the point of presentation.
No test, no issue-specific logic, no model.

The candidate is deliberately one edit applied to every `return` of the named method — a law names a
method, and patching a subset of its exits would leave the law violated on the other paths.

Measured on `werkzeug@051fd663`: the law fires for `WWWAuthenticate("bearer").__str__` on the buggy
tree and the same construction is clean once the returns are stripped; the human fix (`return
self.type.title()` when there are no parameters) and this one agree on the observable.
"""

from __future__ import annotations

import ast
import pathlib
import textwrap
from typing import Any, Iterable, Sequence

__all__ = ["canonicality_candidates", "method_returns", "find_method"]


def _python_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    for path in root.rglob("*.py"):
        parts = path.relative_to(root).parts
        if any(p in {"tests", "test", "testing", "docs", ".git", "__pycache__"} for p in parts):
            continue
        yield path


def find_method(root: pathlib.Path | str, class_name: str, method_name: str) -> tuple[pathlib.Path, ast.FunctionDef] | None:
    """The method's definition and the file it lives in, or `None`."""
    base = pathlib.Path(root)
    for path in _python_files(base):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name != class_name:
                continue
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                    return path, item
    return None


def method_returns(source: str, func: ast.FunctionDef) -> list[ast.Return]:
    """Only the returns that belong to this function, not to a nested def inside it."""
    found: list[ast.Return] = []
    stack: list[ast.AST] = list(func.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue  # a nested scope's returns are not this method's exits
        if isinstance(node, ast.Return):
            found.append(node)
        stack.extend(ast.iter_child_nodes(node))
    found.sort(key=lambda r: (r.lineno, r.col_offset))
    return found


def canonicality_candidates(
    root: pathlib.Path | str,
    class_name: str,
    method_name: str,
    *,
    rel_path: str | None = None,
) -> list[tuple[str, str, bytes]]:
    """`(tag, relative path, patched bytes)` candidates that canonicalize every exit of the method."""
    located = find_method(root, class_name, method_name)
    if located is None:
        return []
    path, func = located
    base = pathlib.Path(root)
    raw = path.read_bytes()
    source = raw.decode("utf-8", errors="replace")
    lines = source.splitlines(keepends=True)
    returns = [r for r in method_returns(source, func) if r.value is not None and r.value.end_lineno]
    if not returns:
        return []

    def offsets(node: ast.Return) -> tuple[int, int]:
        start_line, start_col = node.value.lineno, node.value.col_offset
        end_line, end_col = node.value.end_lineno, node.value.end_col_offset
        start = sum(len(l) for l in lines[: start_line - 1]) + start_col
        end = sum(len(l) for l in lines[: end_line - 1]) + end_col
        return start, end

    edits: list[tuple[int, int, str, str]] = []
    for node in returns:
        start, end = offsets(node)
        original = source[start:end]
        # `return "Bearer " + x` -> `return ("Bearer " + x).strip()`: the parentheses keep
        # precedence honest, and the strip is what the law asks for.
        edits.append((start, end, f"({original}).strip()", original))

    patched = source
    for start, end, replacement, _old in sorted(edits, key=lambda e: e[0], reverse=True):
        patched = patched[:start] + replacement + patched[end:]

    try:
        ast.parse(patched)
    except SyntaxError:
        return []
    rel = rel_path or path.relative_to(base).as_posix()
    tag = f"LAW_CANONICALITY[{class_name}.{method_name}:strip every exit]"
    return [(tag, rel, patched.encode("utf-8"))]


def canonicality_candidates_multi(
    root: pathlib.Path | str,
    targets: Sequence[tuple[str, str]],
) -> list[tuple[str, dict[str, bytes]]]:
    """Patch *every* method the law fired on, in one candidate.

    Measured need: `werkzeug.WWWAuthenticate` presents its header through both `__str__` and
    `to_header`, and `to_header` builds the string itself. Stripping only `__str__` cleared the law's
    probe on one entry point and left the failing test red (`'Bearer ' == 'Bearer'`). A law names the
    observable, not one exit; a candidate that fixes half of it is not a repair.
    """
    base = pathlib.Path(root)
    per_file: dict[pathlib.Path, list[tuple[int, int, str]]] = {}
    labels: list[str] = []
    for class_name, method_name in targets:
        located = find_method(base, class_name, method_name)
        if located is None:
            continue
        path, func = located
        source = path.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines(keepends=True)
        for node in method_returns(source, func):
            if node.value is None or not node.value.end_lineno:
                continue
            start = sum(len(l) for l in lines[: node.value.lineno - 1]) + node.value.col_offset
            end = sum(len(l) for l in lines[: node.value.end_lineno - 1]) + node.value.end_col_offset
            per_file.setdefault(path, []).append((start, end, source[start:end]))
            labels.append(f"{class_name}.{method_name}")
    if not per_file:
        return []
    blobs: dict[str, bytes] = {}
    for path, edits in per_file.items():
        source = path.read_text(encoding="utf-8", errors="replace")
        patched = source
        for start, end, original in sorted(edits, key=lambda e: e[0], reverse=True):
            patched = patched[:start] + f"({original}).strip()" + patched[end:]
        try:
            ast.parse(patched)
        except SyntaxError:
            return []
        blobs[path.relative_to(base).as_posix()] = patched.encode("utf-8")
    tag = "LAW_CANONICALITY[" + "+".join(dict.fromkeys(labels)) + ":strip every exit]"
    return [(tag, blobs)]


def error_discipline_candidates(
    root: pathlib.Path | str,
    *,
    narrow_to: Sequence[str] | None = None,
    max_candidates: int = 4,
    extra_families: Sequence[Sequence[str]] | None = None,
) -> list[tuple[str, dict[str, bytes]]]:
    """Broaden a `try` that catches one builtin family so it also catches its siblings.

    The law says a function must not answer malformed input sometimes with the library's own error and
    sometimes with a bare builtin. The minimal edit that can satisfy it is on the handler: an expression
    guarded by `except ValueError:` that can also raise `TypeError` is exactly the mixed family the law
    observed (`int(None)` raises TypeError, `int("x")` raises ValueError — pyjwt's `exp`/`nbf`/`iat`).

    `max_candidates` bounds how many handlers are broadened at once: one, two, all. The law decides.

    `extra_families` says which sibling families to try, because "the sibling" is not one thing: `int(None)`
    raises `TypeError` and `int(float("inf"))` raises `OverflowError`, and a candidate that catches only the
    first clears nine of pyjwt's twelve hidden cases. A family the witness never exhibited is a wider edit
    than the evidence supported, so each family is offered separately and the law chooses.
    """
    base = pathlib.Path(root)
    sites: list[tuple[pathlib.Path, int, int, list[str]]] = []  # file, start, end, names
    for path in _python_files(base):
        if narrow_to and path.name not in narrow_to:
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        lines = source.splitlines(keepends=True)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler) or node.type is None:
                continue
            names = _handler_names(node.type)
            if not names or len(names) > 1:
                continue  # already a tuple: not the minimal mixed-family shape
            if names[0] not in {"ValueError", "TypeError", "KeyError", "IndexError"}:
                continue
            start = sum(len(l) for l in lines[: node.type.lineno - 1]) + node.type.col_offset
            end = sum(len(l) for l in lines[: (node.type.end_lineno or node.type.lineno) - 1]) + (
                node.type.end_col_offset or 0)
            sites.append((path, start, end, names))
    families = tuple(tuple(f) for f in extra_families) if extra_families else (("TypeError", "ValueError"),)
    out: list[tuple[str, dict[str, bytes]]] = []
    for count in sorted({1, 2, len(sites)} & set(range(1, max_candidates + 1)) | ({len(sites)} if sites else set())):
        chosen = sites[:count]
        if not chosen:
            continue
        for family in families:
            blobs: dict[str, bytes] = {}
            by_file: dict[pathlib.Path, list[tuple[int, int, list[str]]]] = {}
            for path, start, end, names in chosen:
                by_file.setdefault(path, []).append((start, end, names))
            for path, edits in by_file.items():
                source = path.read_text(encoding="utf-8", errors="replace")
                patched = source
                for start, end, names in sorted(edits, key=lambda e: e[0], reverse=True):
                    extra = [n for n in family if n not in names]
                    if not extra:
                        continue
                    joined = ", ".join([names[0], *extra])
                    patched = patched[:start] + f"({joined})" + patched[end:]
                try:
                    ast.parse(patched)
                except SyntaxError:
                    continue
                blobs[path.relative_to(base).as_posix()] = patched.encode("utf-8")
            if blobs:
                tag = (f"LAW_ERROR_DISCIPLINE[broaden {count} handler(s) to catch "
                       f"{', '.join(family)}]")
                out.append((tag, blobs))
    return out


def _handler_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Tuple):
        names: list[str] = []
        for element in node.elts:
            names.extend(_handler_names(element))
        return names
    return []


def protocol_presence_candidates(
    root: pathlib.Path | str,
    function_name: str,
    *,
    target_file: str | None = None,
) -> list[tuple[str, dict[str, bytes]]]:
    """Rewrite `hasattr(x, "<attr>")` guards into `getattr(x, "<attr>", None)`.

    The law's witness is an object whose optional protocol is present but `None`; `hasattr` is True
    there and `reversed()` still fails, so the guard admits an object it cannot handle. This is the
    minimal edit that makes the guard mean what it says, and it is derived from the witness rather than
    from any test: the witness *is* a `None`-valued protocol.
    """
    base = pathlib.Path(root)
    out: list[tuple[str, dict[str, bytes]]] = []
    for path in _python_files(base):
        if target_file and path.name != target_file:
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        lines = source.splitlines(keepends=True)
        edits: list[tuple[int, int, str]] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != function_name:
                continue
            for call in ast.walk(node):
                if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "hasattr"):
                    continue
                if len(call.args) != 2:
                    continue
                start = sum(len(l) for l in lines[: call.lineno - 1]) + call.col_offset
                end = sum(len(l) for l in lines[: (call.end_lineno or call.lineno) - 1]) + (call.end_col_offset or 0)
                original = source[start:end]
                replacement = "getattr" + original[len("hasattr"):-1] + ", None)"
                edits.append((start, end, replacement))
        if not edits:
            continue
        patched = source
        for start, end, replacement in sorted(edits, key=lambda e: e[0], reverse=True):
            patched = patched[:start] + replacement + patched[end:]
        try:
            ast.parse(patched)
        except SyntaxError:
            continue
        tag = f"LAW_ITERABLE_RETYPING[{function_name}:hasattr->getattr(x,attr,None)]"
        out.append((tag, {path.relative_to(base).as_posix(): patched.encode("utf-8")}))
    return out
