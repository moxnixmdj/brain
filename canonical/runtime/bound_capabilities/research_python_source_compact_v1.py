"""Remove comments and shrink indentation of one Python file, proving the AST is unchanged.

Reuses ``compact`` from canonical/research/bytes/tools/rebuild_v81_from_v78.py, which tokenizes,
drops COMMENT tokens, re-indents one space per level, and raises unless the AST is identical.
The input is never modified: it is copied to the output path and compacted there.
"""
from __future__ import annotations

import ast
import hashlib
import io
import pathlib
import tokenize

from canonical.runtime.bound_capabilities import research_tool_loader_v1 as loader

SOURCE = "canonical/research/bytes/tools/rebuild_v81_from_v78.py"


def _dump(text: str) -> str:
    return ast.dump(ast.parse(text, type_comments=True), include_attributes=False)


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
    compact = loader.load_symbol(root, SOURCE, "compact")
    original = src.read_bytes()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(original)
    try:
        saved = compact(out)
    except BaseException:
        out.unlink(missing_ok=True)
        raise
    result = out.read_bytes()
    ast_identical = _dump(original.decode("utf-8")) == _dump(result.decode("utf-8"))
    comments_left = sum(1 for t in tokenize.tokenize(io.BytesIO(result).readline) if t.type == tokenize.COMMENT)
    verified = ast_identical and comments_left == 0 and len(result) <= len(original) and saved == len(original) - len(result)
    return {
        "adapter": "research_python_source_compact_v1",
        "status": "PASS" if verified else "FAIL",
        "input_path": src.relative_to(root).as_posix(),
        "input_bytes": len(original),
        "input_sha256": hashlib.sha256(original).hexdigest(),
        "output_path": out.relative_to(root).as_posix(),
        "output_bytes": len(result),
        "output_sha256": hashlib.sha256(result).hexdigest(),
        "bytes_saved": saved,
        "ast_identical": ast_identical,
        "comments_remaining": comments_left,
        "output_verified": verified,
        "research_source": SOURCE,
    }
