#!/usr/bin/env python3
"""Parse a caller-declared source tree using Brain's shared tree-sitter kernel.

All supported files in scope are enumerated; exceeding a bound is an error,
not silent sampling. Reports contain per-file definitions and syntax errors.
Ignored directories, grammar coverage and resource bounds limit the scope; a
successful parse is not semantic verification of the program.
"""
from __future__ import annotations

import ast
import hashlib
import pathlib
from typing import Any

from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel

SCHEMA = "PROJECT_BRAIN_CODE_MULTILANGUAGE_TREE_SITTER_V1"
CAPABILITY_ID = "code.multilanguage.parse.tree_sitter.v1"
PROVIDES = ["code.ast.tree_sitter.available", "code.symbols.multilanguage.indexed"]
REQUIRES: list[str] = []
SUPPORTED_LANGUAGES = ("python", "javascript", "typescript", "rust", "go", "java", "cpp", "yaml")


def _python_fallback(repo: pathlib.Path, path: pathlib.Path) -> dict[str, Any]:
    """Produce explicitly partial Python-only diagnostics without tree-sitter."""
    if path.stat().st_size > kernel.MAX_FILE_BYTES:
        raise kernel.TreeSitterSWEError("SOURCE_FILE_TOO_LARGE:" + kernel.relative_path(repo, path))
    raw = path.read_bytes()
    if len(raw) > kernel.MAX_FILE_BYTES:
        raise kernel.TreeSitterSWEError("SOURCE_FILE_TOO_LARGE:" + kernel.relative_path(repo, path))
    tree = ast.parse(raw, filename=str(path))
    definitions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.append({
                "name": node.name,
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "start_line": node.lineno,
                "end_line": node.end_lineno,
            })
    definitions.sort(key=lambda item: (item["start_line"], item["name"]))
    return {
        "path": kernel.relative_path(repo, path), "language": "python",
        "source_sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw),
        "has_syntax_error": False, "definitions": definitions,
        "parser": "python_ast_fallback",
    }


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    source_root = kernel.safe_path(repo, args.get("source_root"), must_exist=True, allow_root=True)
    if not source_root.is_dir():
        raise kernel.TreeSitterSWEError("SOURCE_ROOT_NOT_DIRECTORY")
    limit = args.get("max_files", kernel.MAX_FILES)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= kernel.MAX_FILES:
        raise kernel.TreeSitterSWEError("MAX_FILES_INVALID")
    files = kernel.source_files(source_root, max_files=limit)
    output = kernel.safe_output(repo, args.get("output_path"))
    # Do not replace a source file or a hard-linked alias, even if the caller
    # named it as output. Symlink paths are rejected by kernel.safe_output.
    if (kernel.detect_language(output) or
            (output.exists() and output.stat().st_nlink > 1)):
        raise kernel.TreeSitterSWEError("OUTPUT_OVERLAPS_INPUT")

    try:
        import tree_sitter  # noqa: F401
        import tree_sitter_languages  # noqa: F401
        tree_sitter_available = True
    except ImportError:
        tree_sitter_available = False

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    skipped = 0
    languages_seen = {kernel.detect_language(path) for path in files}
    for path in files:
        language = kernel.detect_language(path)
        rel = kernel.relative_path(repo, path)
        if not tree_sitter_available and language != "python":
            skipped += 1
            errors.append({"path": rel, "kind": "TREE_SITTER_SUBSTRATE_MISSING"})
            continue
        try:
            if path.stat().st_size > kernel.MAX_FILE_BYTES:
                raise kernel.TreeSitterSWEError("SOURCE_FILE_TOO_LARGE")
            row = (kernel.parse_file(repo, path, language) if tree_sitter_available
                   else _python_fallback(repo, path))
            rows.append(row)
            if row["has_syntax_error"]:
                errors.append({"path": rel, "kind": "TREE_SITTER_HAS_ERROR"})
        except (OSError, ValueError, SyntaxError, kernel.TreeSitterSWEError) as exc:
            skipped += 1
            errors.append({"path": rel, "kind": type(exc).__name__})

    rows.sort(key=lambda row: row["path"])
    symbol_count = sum(len(row["definitions"]) for row in rows)
    complete = bool(files) and tree_sitter_available and not errors and len(rows) == len(files)
    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "source_root": kernel.relative_path(repo, source_root) if source_root != repo else ".",
        "supported_languages": list(SUPPORTED_LANGUAGES),
        "languages_seen": sorted(lang for lang in languages_seen if lang),
        "scope": {"ignored_directories": sorted(kernel.IGNORED_DIRS),
                  "max_files": limit, "max_file_bytes": kernel.MAX_FILE_BYTES},
        "files": rows, "errors": errors,
        "file_count": len(rows), "symbol_count": symbol_count,
        "error_count": len(errors), "skipped_count": skipped,
        "tree_sitter_available": tree_sitter_available,
        "substrate": kernel.SUBSTRATE, "complete": complete, "verified": complete,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
        "limitations": ["Definitions are syntactic, not a complete semantic symbol table.",
                        "Ignored directories and unsupported extensions are outside the report's scope."],
    }
    raw = kernel.canonical_bytes(artifact)
    output.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    output_verified = output.read_bytes() == raw
    return {
        "adapter": "code_multilanguage_tree_sitter_v1",
        "output_path": kernel.relative_path(repo, output), "output_sha256": digest,
        "output_verified": output_verified, "file_count": len(rows),
        "languages_seen": artifact["languages_seen"],
        "tree_sitter_available": tree_sitter_available, "symbol_count": symbol_count,
        "error_count": len(errors), "skipped_count": skipped, "complete": complete,
        "verified": complete and output_verified,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
