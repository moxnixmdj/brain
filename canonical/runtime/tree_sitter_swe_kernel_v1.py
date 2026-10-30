#!/usr/bin/env python3
"""Shared deterministic tree-sitter SWE substrate.

Integration glue only: parsing comes from the pinned tree-sitter wheels; path
safety, content hashes, and conservative artifact validation live here so the
index, impact, and patch capabilities share one exact byte model.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import posixpath
import re
from functools import lru_cache
from typing import Any, Iterator

INDEX_SCHEMA = "PROJECT_BRAIN_CODE_TREE_SITTER_INCREMENTAL_INDEX_V1"
IMPACT_SCHEMA = "PROJECT_BRAIN_CODE_TREE_SITTER_IMPACT_V1"
PATCH_SCHEMA = "PROJECT_BRAIN_CODE_TREE_SITTER_PATCH_V1"
SUBSTRATE = {"tree_sitter": "0.20.4", "tree_sitter_languages": "1.10.2"}
MAX_FILES = 5000
MAX_FILE_BYTES = 2_000_000
MAX_REFERENCES_PER_FILE = 50_000

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".c": "cpp", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp",
    ".h": "cpp", ".hh": "cpp", ".hpp": "cpp",
    ".yaml": "yaml", ".yml": "yaml",
}
EXTENSIONS_BY_LANGUAGE = {
    language: sorted({suffix for suffix, value in LANGUAGE_BY_SUFFIX.items() if value == language})
    for language in set(LANGUAGE_BY_SUFFIX.values())
}
IGNORED_DIRS = {".git", ".hg", ".svn", "node_modules", "vendor", "dist", "build", "target", "__pycache__", ".venv", "venv"}

DEFINITION_KINDS = {
    "function_definition": "function",
    "function_declaration": "function",
    "method_definition": "method",
    "method_declaration": "method",
    "constructor_declaration": "constructor",
    "class_definition": "class",
    "class_declaration": "class",
    "class_specifier": "class",
    "struct_specifier": "struct",
    "interface_declaration": "interface",
    "enum_declaration": "enum",
    "enum_specifier": "enum",
    "function_item": "function",
    "struct_item": "struct",
    "enum_item": "enum",
    "trait_item": "trait",
    "mod_item": "module",
    "type_declaration": "type",
    "type_alias_declaration": "type",
    "namespace_definition": "namespace",
    "variable_declarator": "variable",
    "block_mapping_pair": "mapping_key",
    "flow_mapping_pair": "mapping_key",
}
IDENTIFIER_TYPES = {
    "identifier", "type_identifier", "property_identifier", "field_identifier",
    "namespace_identifier", "module_identifier", "package_identifier",
    "scoped_identifier", "type_identifier", "constant",
}

_IMPORT_PATTERNS = {
    "python": [
        re.compile(r"^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+", re.M),
        re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)", re.M),
    ],
    "javascript": [
        re.compile(r"\b(?:import|export)\b[^\n;]*?\bfrom\s*['\"]([^'\"]+)['\"]"),
        re.compile(r"\brequire\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"),
        re.compile(r"\bimport\s*['\"]([^'\"]+)['\"]"),
        re.compile(r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"),
    ],
    "typescript": [],
    "rust": [re.compile(r"^\s*(?:use|mod)\s+([A-Za-z_][\w:]*)", re.M)],
    "go": [re.compile(r"^\s*import\s+(?:\(\s*)?[\"`]([^\"`]+)[\"`]", re.M)],
    "java": [re.compile(r"^\s*import\s+(?:static\s+)?([A-Za-z_][\w.]*)", re.M)],
    "cpp": [re.compile(r"^\s*#\s*include\s*[\"<]([^\">]+)[\">]", re.M)],
    "yaml": [],
}
_IMPORT_PATTERNS["typescript"] = _IMPORT_PATTERNS["javascript"]


class TreeSitterSWEError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def safe_path(root: pathlib.Path, raw: Any, *, must_exist: bool = False, allow_root: bool = False) -> pathlib.Path:
    root = pathlib.Path(root).resolve()
    if not isinstance(raw, str) or not raw.strip():
        raise TreeSitterSWEError("PATH_REQUIRED")
    candidate = pathlib.Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    for item in (candidate, *candidate.parents):
        if item == root:
            break
        if item.is_symlink():
            raise TreeSitterSWEError("SYMLINK_REFUSED:" + str(raw))
    path = candidate.resolve()
    if (path == root and not allow_root) or (path != root and root not in path.parents):
        raise TreeSitterSWEError("PATH_OUTSIDE_REPOSITORY:" + str(raw))
    if must_exist and not path.exists():
        raise TreeSitterSWEError("PATH_MISSING:" + str(raw))
    return path


def safe_output(root: pathlib.Path, raw: Any) -> pathlib.Path:
    path = safe_path(root, raw or "canonical/tmp_tree_sitter_swe.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def detect_language(path: pathlib.Path) -> str | None:
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower())


def relative_path(repo: pathlib.Path, path: pathlib.Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def source_files(source_root: pathlib.Path, *, max_files: int = MAX_FILES) -> list[pathlib.Path]:
    if not source_root.is_dir():
        raise TreeSitterSWEError("SOURCE_ROOT_MISSING")
    files: list[pathlib.Path] = []
    for path in sorted(source_root.rglob("*")):
        if any(part in IGNORED_DIRS for part in path.relative_to(source_root).parts):
            continue
        if path.is_symlink():
            raise TreeSitterSWEError("SYMLINK_REFUSED:" + str(path))
        if path.is_file() and detect_language(path):
            files.append(path)
            if len(files) > max_files:
                raise TreeSitterSWEError("SOURCE_FILE_LIMIT_EXCEEDED")
    return files


@lru_cache(maxsize=None)
def _language_for(language: str):
    from tree_sitter_languages import get_language
    return get_language(language)


def parser_for(language: str):
    try:
        from tree_sitter import Parser
        parser = Parser()
        parser.set_language(_language_for(language))
        return parser
    except ImportError as exc:
        raise TreeSitterSWEError("TREE_SITTER_SUBSTRATE_MISSING") from exc
    except Exception as exc:
        raise TreeSitterSWEError("TREE_SITTER_LANGUAGE_UNAVAILABLE:" + language) from exc


def parse_bytes(language: str, raw: bytes):
    return parser_for(language).parse(raw)


def walk_nodes(root: Any) -> Iterator[Any]:
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(node.children))


def _text(raw: bytes, node: Any) -> str:
    return raw[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _span(node: Any) -> dict[str, int]:
    return {
        "start_byte": int(node.start_byte),
        "end_byte": int(node.end_byte),
        "start_line": int(node.start_point[0]) + 1,
        "end_line": int(node.end_point[0]) + 1,
    }


def _cpp_function_name(node: Any) -> Any | None:
    declarator = node.child_by_field_name("declarator")
    seen = 0
    while declarator is not None and seen < 32:
        seen += 1
        if declarator.type in IDENTIFIER_TYPES:
            return declarator
        nxt = declarator.child_by_field_name("declarator")
        if nxt is None:
            for child in declarator.children:
                if child.type in IDENTIFIER_TYPES:
                    return child
            return None
        declarator = nxt
    return None


def _definition_name_node(node: Any) -> Any | None:
    if node.type in {"block_mapping_pair", "flow_mapping_pair"}:
        return node.child_by_field_name("key")
    if node.type == "function_definition":
        direct = node.child_by_field_name("name")
        return direct if direct is not None else _cpp_function_name(node)
    return node.child_by_field_name("name")


def _imports(language: str, raw: bytes) -> list[str]:
    text = raw.decode("utf-8", "replace")
    found: set[str] = set()
    if language == "python":
        import ast
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    prefix = "." * int(node.level or 0)
                    if node.module:
                        found.add(prefix + node.module)
                        for alias in node.names:
                            if alias.name != "*":
                                found.add(prefix + node.module + "." + alias.name)
                    else:
                        found.update(prefix + alias.name for alias in node.names)
            return sorted(found)
    if language == "go":
        for match in re.finditer(r"(?ms)^\s*import\s*\((.*?)^\s*\)", text):
            found.update(re.findall(r"[\"`]([^\"`]+)[\"`]", match.group(1)))
    for pattern in _IMPORT_PATTERNS[language]:
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            if value:
                found.add(value)
    return sorted(found)


def _row_with_hash(row: dict[str, Any]) -> dict[str, Any]:
    body = {key: value for key, value in row.items() if key != "row_sha256"}
    return {**body, "row_sha256": json_sha256(body)}


def parse_file(repo: pathlib.Path, path: pathlib.Path, language: str | None = None) -> dict[str, Any]:
    language = language or detect_language(path)
    if not language:
        raise TreeSitterSWEError("LANGUAGE_UNSUPPORTED:" + str(path))
    raw = path.read_bytes()
    if len(raw) > MAX_FILE_BYTES:
        raise TreeSitterSWEError("SOURCE_FILE_TOO_LARGE:" + relative_path(repo, path))
    tree = parse_bytes(language, raw)
    definitions: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    definition_name_spans: set[tuple[int, int, str]] = set()
    for node in walk_nodes(tree.root_node):
        kind = DEFINITION_KINDS.get(node.type)
        if not kind:
            continue
        name_node = _definition_name_node(node)
        if name_node is None:
            continue
        name = _text(raw, name_node).strip()
        if not name or len(name) > 300:
            continue
        definition_name_spans.add((name_node.start_byte, name_node.end_byte, name_node.type))
        definitions.append({"name": name, "kind": kind, "node_type": node.type, **_span(node)})
    for node in walk_nodes(tree.root_node):
        if node.type not in IDENTIFIER_TYPES:
            continue
        if (node.start_byte, node.end_byte, node.type) in definition_name_spans:
            continue
        name = _text(raw, node).strip()
        if not name or len(name) > 300:
            continue
        references.append({"name": name, "node_type": node.type, **_span(node)})
        if len(references) > MAX_REFERENCES_PER_FILE:
            raise TreeSitterSWEError("REFERENCE_LIMIT_EXCEEDED:" + relative_path(repo, path))
    definitions.sort(key=lambda row: (row["start_byte"], row["end_byte"], row["name"], row["kind"]))
    references.sort(key=lambda row: (row["start_byte"], row["end_byte"], row["name"]))
    row = {
        "path": relative_path(repo, path),
        "language": language,
        "source_sha256": bytes_sha256(raw),
        "byte_count": len(raw),
        "root_node_type": tree.root_node.type,
        "node_count": int(tree.root_node.descendant_count),
        "has_syntax_error": bool(tree.root_node.has_error),
        "definitions": definitions,
        "references": references,
        "imports": _imports(language, raw),
    }
    return _row_with_hash(row)


def validate_row(repo: pathlib.Path, row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise TreeSitterSWEError("INDEX_ROW_INVALID")
    declared = row.get("row_sha256")
    body = {key: value for key, value in row.items() if key != "row_sha256"}
    if not isinstance(declared, str) or json_sha256(body) != declared:
        raise TreeSitterSWEError("INDEX_ROW_HASH_MISMATCH")
    path = safe_path(repo, row.get("path"), must_exist=True)
    if not path.is_file():
        raise TreeSitterSWEError("INDEX_SOURCE_NOT_FILE")
    if bytes_sha256(path.read_bytes()) != row.get("source_sha256"):
        raise TreeSitterSWEError("INDEX_SOURCE_STALE:" + str(row.get("path")))
    if detect_language(path) != row.get("language"):
        raise TreeSitterSWEError("INDEX_LANGUAGE_MISMATCH")
    return row


def read_index(repo: pathlib.Path, path: pathlib.Path) -> dict[str, Any]:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TreeSitterSWEError("INDEX_UNREADABLE") from exc
    if not isinstance(artifact, dict) or artifact.get("schema") != INDEX_SCHEMA:
        raise TreeSitterSWEError("INDEX_SCHEMA_MISMATCH")
    rows = artifact.get("files")
    if not isinstance(rows, list) or not rows:
        raise TreeSitterSWEError("INDEX_EMPTY")
    for row in rows:
        validate_row(repo, row)
    return artifact


def write_artifact(path: pathlib.Path, artifact: dict[str, Any]) -> str:
    raw = canonical_bytes(artifact)
    path.write_bytes(raw)
    return bytes_sha256(raw)


def is_test_file(repo: pathlib.Path, row: dict[str, Any], source_root: str = ".") -> bool:
    relative = row["path"] if source_root == "." else posixpath.relpath(row["path"], source_root)
    path = pathlib.PurePosixPath(relative)
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    language = row["language"]
    if language == "python":
        return name.startswith("test_") or name.endswith("_test.py") or "tests" in parts
    if language in {"javascript", "typescript"}:
        return ".test." in name or ".spec." in name or "tests" in parts or "__tests__" in parts
    if language == "go":
        return name.endswith("_test.go")
    if language == "rust":
        if "tests" in parts:
            return True
        raw = safe_path(repo, row["path"], must_exist=True).read_bytes()
        return b"#[test]" in raw or b"#[cfg(test)]" in raw
    if language == "java":
        return name.endswith("test.java") or "test" in parts or "tests" in parts
    if language == "cpp":
        return "test" in name or "tests" in parts
    return False


def node_span_exists(tree: Any, start_byte: int, end_byte: int) -> bool:
    return any(node.start_byte == start_byte and node.end_byte == end_byte for node in walk_nodes(tree.root_node))
