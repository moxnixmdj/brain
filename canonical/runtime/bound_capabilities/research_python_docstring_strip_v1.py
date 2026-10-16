"""Strip module, class, and function docstrings from one Python file with an AST round-trip check.

Reuses ``StripDocstrings`` from canonical/research/bytes/tools/conservative_docstring_strip_v76.py.
Output is ``ast.unparse`` text, so comments and original formatting are not preserved.
"""
from __future__ import annotations

import ast
import hashlib
import pathlib

from canonical.runtime.bound_capabilities import research_tool_loader_v1 as loader

SOURCE = "canonical/research/bytes/tools/conservative_docstring_strip_v76.py"
DOC_OWNERS = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _docstring_count(tree: ast.AST) -> int:
    return sum(1 for n in ast.walk(tree) if isinstance(n, DOC_OWNERS) and ast.get_docstring(n, clean=False) is not None)


def run(args, root):
    root = pathlib.Path(root).resolve()
    src = loader.safe_repo_path(root, args.get("input_path"))
    out = loader.safe_repo_path(root, args.get("output_path"))
    if not src.is_file() or src.suffix != ".py":
        raise RuntimeError("PYTHON_INPUT_REQUIRED")
    if out.suffix != ".py":
        raise RuntimeError("PYTHON_OUTPUT_REQUIRED")
    if out == src:
        raise RuntimeError("OUTPUT_MUST_DIFFER_FROM_INPUT")
    strip = loader.load_symbol(root, SOURCE, "StripDocstrings")
    text = src.read_text(encoding="utf-8")
    before = _docstring_count(ast.parse(text))
    target = strip().visit(ast.parse(text, type_comments=True))
    ast.fix_missing_locations(target)
    result = ast.unparse(target) + "\n"
    compile(result, str(out), "exec")
    reparsed = ast.parse(result, type_comments=True)
    if ast.dump(reparsed, include_attributes=False) != ast.dump(target, include_attributes=False):
        raise RuntimeError("POST_STRIP_AST_RECONSTRUCTION_MISMATCH")
    after = _docstring_count(reparsed)
    raw = result.encode("utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    verified = after == 0
    return {
        "adapter": "research_python_docstring_strip_v1",
        "status": "PASS" if verified else "FAIL",
        "input_path": src.relative_to(root).as_posix(),
        "input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "output_path": out.relative_to(root).as_posix(),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "docstrings_removed": before - after,
        "docstrings_remaining": after,
        "output_verified": verified,
        "research_source": SOURCE,
    }
