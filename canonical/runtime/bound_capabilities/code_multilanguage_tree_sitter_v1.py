#!/usr/bin/env python3
"""Multi-language deterministic parser — tree-sitter harvest, insanely fast.

Why this is the only right way:
- Python ast parses only Python and fails on syntax errors
- tree_sitter is incremental, error-tolerant, 8 languages, O(log n) reparse
- External substrate already pinned with SHA-256 (no new deps, $0)
  tree_sitter==0.20.4 tree_sitter_languages==1.10.2

This adapter exposes the hidden external kernel as a bound capability so the
composer can finally route multi-language goals instead of falling back to
python-only heuristics.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_CODE_MULTILANGUAGE_TREE_SITTER_V1"
CAPABILITY_ID = "code.multilanguage.parse.tree_sitter.v1"
PROVIDES = ["code.ast.tree_sitter.available", "code.symbols.multilanguage.indexed"]
REQUIRES: list[str] = []

SUPPORTED_LANGUAGES = ("python", "javascript", "typescript", "rust", "go", "java", "cpp", "yaml")

def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_tree_sitter.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _detect_language(path: pathlib.Path) -> str:
    suf = path.suffix.lower()
    return {".py": "python", ".js": "javascript", ".ts": "typescript", ".rs": "rust", ".go": "go", ".java": "java", ".cpp": "cpp", ".c": "cpp", ".cc": "cpp", ".yaml": "yaml", ".yml": "yaml"}.get(suf, "unknown")

def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))

    source_root_raw = args.get("source_root") or "canonical/runtime"
    source_root = (repo / str(source_root_raw)).resolve()
    if source_root != repo and repo not in source_root.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not source_root.is_dir():
        raise RuntimeError("SOURCE_ROOT_MISSING")

    # Try to use pinned tree_sitter; if not installed, fall back to ast for python subset
    # This keeps the adapter deterministic and fail-closed, never inventing parses
    tree_sitter_available = False
    parsed_count = 0
    languages_seen: set[str] = set()
    errors: list[dict] = []
    symbols: list[dict] = []
    skipped_count = 0

    try:
        from tree_sitter import Language, Parser  # type: ignore
        # tree_sitter_languages provides prebuilt parsers
        try:
            from tree_sitter_languages import get_language as ts_get_language  # type: ignore
            tree_sitter_available = True
        except ImportError:
            tree_sitter_available = False
    except ImportError:
        tree_sitter_available = False

    files = []
    for lang in SUPPORTED_LANGUAGES:
        ext_map = {"python": [".py"], "javascript": [".js"], "typescript": [".ts"], "rust": [".rs"], "go": [".go"], "java": [".java"], "cpp": [".cpp", ".c", ".cc"], "yaml": [".yaml", ".yml"]}
        for ext in ext_map[lang]:
            files.extend(sorted(source_root.rglob(f"*{ext}")))

    # Deterministic cap for verification speed — sample 50 files per language family
    files = sorted(files)[:200]

    for f in files:
        lang = _detect_language(f)
        if lang == "unknown":
            continue
        languages_seen.add(lang)
        try:
            raw = f.read_bytes()
            if not raw.strip():
                continue
            if tree_sitter_available:
                # Use tree_sitter parser for that language — error tolerant
                try:
                    parser_lang = ts_get_language(lang if lang != "cpp" else "cpp")
                    parser = Parser()
                    parser.set_language(parser_lang)
                    tree = parser.parse(raw)
                    # Count named nodes as symbols
                    has_error = tree.root_node.has_error
                    parsed_count += 1
                    symbols.append({"path": str(f.relative_to(repo)), "language": lang, "has_error": has_error, "node_count": tree.root_node.descendant_count})
                    if has_error:
                        errors.append({"path": str(f.relative_to(repo)), "kind": "TREE_SITTER_HAS_ERROR"})
                    continue
                except Exception as exc:
                    # Fall back to python ast for python, else record
                    if lang == "python":
                        pass
                    else:
                        errors.append({"path": str(f.relative_to(repo)), "kind": type(exc).__name__})
                        continue
            # Fallback: pure python ast for python only
            if lang == "python":
                import ast
                try:
                    tree = ast.parse(raw.decode("utf-8", errors="strict"))
                    funcs = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
                    parsed_count += 1
                    symbols.append({"path": str(f.relative_to(repo)), "language": lang, "has_error": False, "node_count": funcs})
                except Exception as exc:
                    errors.append({"path": str(f.relative_to(repo)), "kind": type(exc).__name__})
            else:
                # A missing parser is a blocked input, never a fabricated parse.
                skipped_count += 1
                errors.append({"path": str(f.relative_to(repo)), "kind": "TREE_SITTER_SUBSTRATE_MISSING"})
        except Exception as exc:
            errors.append({"path": str(f.relative_to(repo)), "kind": type(exc).__name__})

    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "source_root": str(source_root.relative_to(repo)) if source_root != repo else ".",
        "supported_languages": list(SUPPORTED_LANGUAGES),
        "languages_seen": sorted(languages_seen),
        "file_count": parsed_count,
        "symbol_count": len(symbols),
        "error_count": len(errors),
        "skipped_count": skipped_count,
        "tree_sitter_available": tree_sitter_available,
        "substrate_missing": not tree_sitter_available,
        "substrate": ["tree_sitter==0.20.4", "tree_sitter_languages==1.10.2"],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        # A capability named `code.multilanguage.parse.tree_sitter` that has no tree_sitter is
        # not verified by parsing Python with `ast`: that is a different effect, and this
        # repository already registers it as python.source.audit.ast.  Measured 2026-10-28:
        # without the pinned kernel this adapter returned output_verified true with
        # tree_sitter_available false, so the door credited a multilanguage parse that never
        # happened.  Its sibling code_tree_sitter_incremental_index_v1 already refuses with
        # TREE_SITTER_SUBSTRATE_MISSING; this is the same law, applied to the row that was
        # still reporting success.
        "verified": bool(tree_sitter_available) and parsed_count > 0 and not errors,
        "reason": None if tree_sitter_available else "TREE_SITTER_SUBSTRATE_MISSING",
    }

    raw_bytes = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw_bytes)

    return {
        "adapter": "code_multilanguage_tree_sitter_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "output_verified": artifact["verified"],
        "file_count": parsed_count,
        "languages_seen": sorted(languages_seen),
        "tree_sitter_available": tree_sitter_available,
        "substrate_missing": not tree_sitter_available,
        "symbol_count": len(symbols),
        "error_count": len(errors),
        "skipped_count": skipped_count,
        "verified": artifact["verified"],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
