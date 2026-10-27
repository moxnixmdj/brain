#!/usr/bin/env python3
"""Incremental multi-language symbol/reference index over pinned tree-sitter."""
from __future__ import annotations

import json
import pathlib
from typing import Any

from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel

SCHEMA = kernel.INDEX_SCHEMA
CAPABILITY_ID = "code.index.tree_sitter.incremental.v1"
PROVIDES = [
    "code.symbols.tree_sitter.indexed",
    "code.references.tree_sitter.indexed",
    "code.index.incremental.verified",
]
REQUIRES = ["code.ast.tree_sitter.available"]


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = kernel.safe_output(repo, args.get("output_path"))
    source_root = kernel.safe_path(repo, args.get("source_root"), must_exist=True, allow_root=True)
    if not source_root.is_dir():
        raise kernel.TreeSitterSWEError("SOURCE_ROOT_NOT_DIRECTORY")
    files = kernel.source_files(source_root, max_files=int(args.get("max_files", kernel.MAX_FILES)))
    if not files:
        raise kernel.TreeSitterSWEError("NO_SUPPORTED_SOURCE_FILES")

    cached: dict[str, dict[str, Any]] = {}
    if output.is_file():
        try:
            old = json.loads(output.read_text(encoding="utf-8"))
            if old.get("schema") == SCHEMA:
                for row in old.get("files") or []:
                    body = {key: value for key, value in row.items() if key != "row_sha256"}
                    if row.get("row_sha256") == kernel.json_sha256(body):
                        cached[str(row.get("path"))] = row
        except (OSError, ValueError, TypeError, AttributeError):
            cached = {}

    rows: list[dict[str, Any]] = []
    reused = 0
    for path in files:
        rel = kernel.relative_path(repo, path)
        source_sha = kernel.bytes_sha256(path.read_bytes())
        old = cached.get(rel)
        if old and old.get("source_sha256") == source_sha and old.get("language") == kernel.detect_language(path):
            rows.append(old)
            reused += 1
        else:
            rows.append(kernel.parse_file(repo, path))
    rows.sort(key=lambda row: row["path"])
    definitions = sum(len(row["definitions"]) for row in rows)
    references = sum(len(row["references"]) for row in rows)
    syntax_errors = sum(bool(row["has_syntax_error"]) for row in rows)
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "source_root": kernel.relative_path(repo, source_root) if source_root != repo else ".",
        "substrate": kernel.SUBSTRATE,
        "files": rows,
        "totals": {
            "files": len(rows),
            "definitions": definitions,
            "references": references,
            "syntax_error_files": syntax_errors,
            "languages": len({row["language"] for row in rows}),
        },
        "complete": syntax_errors == 0,
        "verified": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    digest = kernel.write_artifact(output, artifact)
    return {
        "adapter": "code_tree_sitter_incremental_index_v1",
        "output_path": kernel.relative_path(repo, output),
        "output_sha256": digest,
        "output_verified": True,
        "verified": True,
        "file_count": len(rows),
        "definition_count": definitions,
        "reference_count": references,
        "syntax_error_count": syntax_errors,
        "parsed_file_count": len(rows) - reused,
        "reused_file_count": reused,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
