#!/usr/bin/env python3
"""Shared deterministic tree-sitter SWE substrate.

Integration glue only: parsing comes from the pinned tree-sitter wheels; path
safety, content hashes, and conservative artifact validation live here so the
index, impact, and patch capabilities share one exact byte model.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from importlib import metadata
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
_IMPLEMENTATION_SHA256 = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
_PARSER_FILE_IDENTITIES: dict[str, tuple] = {}
_PARSER_SUBSTRATE_SHA256: str | None = None

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
    def walk_error(error):
        raise error
    # Prune before descending, rather than discovering and sorting excluded trees.
    for directory, dirs, names in os.walk(source_root, followlinks=False, onerror=walk_error):
        parent = pathlib.Path(directory)
        kept = []
        for name in sorted(dirs):
            if name in IGNORED_DIRS:
                continue
            if (parent / name).is_symlink():
                raise TreeSitterSWEError("SYMLINK_REFUSED:" + str(parent / name))
            kept.append(name)
        dirs[:] = kept
        for name in sorted(names):
            if name in IGNORED_DIRS:
                continue
            path = parent / name
            if path.is_symlink():
                raise TreeSitterSWEError("SYMLINK_REFUSED:" + str(path))
            if path.is_file() and detect_language(path):
                files.append(path)
                if len(files) > max_files:
                    raise TreeSitterSWEError("SOURCE_FILE_LIMIT_EXCEEDED")
    return sorted(files)


def _file_identity(path: pathlib.Path) -> tuple:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


@lru_cache(maxsize=128)
def _dependency_digest(path: str, identity: tuple) -> str:
    # Only installed parser dependencies use this metadata-keyed memo. Project
    # source is always read and content-hashed on every request.
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if _file_identity(pathlib.Path(path)) != identity:
        raise TreeSitterSWEError("PARSER_DEPENDENCY_CHANGED_DURING_HASH")
    return digest.hexdigest()


def analysis_context() -> dict[str, Any]:
    """Content/version-bound extractor identity, not a security attestation.

    Installed parser code is immutable during a process: changes require restart
    so a new on-disk digest is never assigned to an already-loaded old library.
    """
    global _PARSER_SUBSTRATE_SHA256
    packages = {}
    try:
        for name in ("tree-sitter", "tree-sitter-languages"):
            distribution = metadata.distribution(name)
            dependencies = {}
            for entry in distribution.files or []:
                if str(entry).split("/")[0] not in {"tree_sitter", "tree_sitter_languages"}:
                    continue
                if entry.suffix not in {".py", ".so", ".pyd", ".dll", ".dylib"}:
                    continue
                path = pathlib.Path(distribution.locate_file(entry)).resolve()
                identity = _file_identity(path)
                previous = _PARSER_FILE_IDENTITIES.setdefault(str(path), identity)
                if identity != previous:
                    raise TreeSitterSWEError("PARSER_DEPENDENCY_CHANGED_RESTART_REQUIRED")
                dependencies[str(entry)] = _dependency_digest(str(path), identity)
            if not dependencies:
                raise TreeSitterSWEError("PARSER_DEPENDENCY_IDENTITY_UNAVAILABLE")
            packages[name] = {"version": distribution.version, "files": dependencies}
    except (metadata.PackageNotFoundError, OSError) as exc:
        raise TreeSitterSWEError("TREE_SITTER_SUBSTRATE_IDENTITY_UNAVAILABLE") from exc
    substrate_sha = json_sha256(packages)
    if _PARSER_SUBSTRATE_SHA256 is None:
        _PARSER_SUBSTRATE_SHA256 = substrate_sha
    elif _PARSER_SUBSTRATE_SHA256 != substrate_sha:
        raise TreeSitterSWEError("PARSER_DEPENDENCY_CHANGED_RESTART_REQUIRED")
    context = {
        "schema": "PROJECT_BRAIN_TREE_SITTER_ANALYSIS_CONTEXT_V1",
        "implementation_sha256": _IMPLEMENTATION_SHA256,
        "python": {"implementation": sys.implementation.name, "version": list(sys.version_info[:3])},
        "packages": packages,
        "policy": {
            "expected_substrate": SUBSTRATE,
            "language_by_suffix": LANGUAGE_BY_SUFFIX,
            "definition_kinds": DEFINITION_KINDS,
            "identifier_types": sorted(IDENTIFIER_TYPES),
            "imports": {lang: [[p.pattern, p.flags] for p in patterns]
                        for lang, patterns in _IMPORT_PATTERNS.items()},
            "ignored_dirs": sorted(IGNORED_DIRS),
            "limits": [MAX_FILES, MAX_FILE_BYTES, MAX_REFERENCES_PER_FILE],
        },
    }
    return json.loads(canonical_bytes(context))


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


def parse_file(repo: pathlib.Path, path: pathlib.Path, language: str | None = None,
               *, raw: bytes | None = None) -> dict[str, Any]:
    language = language or detect_language(path)
    if not language:
        raise TreeSitterSWEError("LANGUAGE_UNSUPPORTED:" + str(path))
    raw = path.read_bytes() if raw is None else raw
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


def validate_row(repo: pathlib.Path, row: Any, *, raw: bytes | None = None) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise TreeSitterSWEError("INDEX_ROW_INVALID")
    declared = row.get("row_sha256")
    body = {key: value for key, value in row.items() if key != "row_sha256"}
    if not isinstance(declared, str) or json_sha256(body) != declared:
        raise TreeSitterSWEError("INDEX_ROW_HASH_MISMATCH")
    path = safe_path(repo, row.get("path"), must_exist=True)
    if not path.is_file():
        raise TreeSitterSWEError("INDEX_SOURCE_NOT_FILE")
    raw = path.read_bytes() if raw is None else raw
    if bytes_sha256(raw) != row.get("source_sha256"):
        raise TreeSitterSWEError("INDEX_SOURCE_STALE:" + str(row.get("path")))
    if detect_language(path) != row.get("language"):
        raise TreeSitterSWEError("INDEX_LANGUAGE_MISMATCH")
    if (type(row.get("byte_count")) is not int or row["byte_count"] != len(raw)
            or len(raw) > MAX_FILE_BYTES or type(row.get("node_count")) is not int
            or row["node_count"] < 1 or type(row.get("has_syntax_error")) is not bool
            or not isinstance(row.get("root_node_type"), str) or not row["root_node_type"]):
        raise TreeSitterSWEError("INDEX_ROW_SHAPE_INVALID")
    for key in ("definitions", "references", "imports"):
        if not isinstance(row.get(key), list):
            raise TreeSitterSWEError("INDEX_ROW_SHAPE_INVALID")
    if len(row["references"]) > MAX_REFERENCES_PER_FILE:
        raise TreeSitterSWEError("REFERENCE_LIMIT_EXCEEDED:" + str(row["path"]))
    if not all(isinstance(item, str) for item in row["imports"]):
        raise TreeSitterSWEError("INDEX_ROW_SHAPE_INVALID")
    for key in ("definitions", "references"):
        for entry in row[key]:
            if (not isinstance(entry, dict)
                    or any(not isinstance(entry.get(k), str) or not entry[k]
                           for k in (("name", "node_type", "kind") if key == "definitions"
                                     else ("name", "node_type")))
                    or any(type(entry.get(k)) is not int for k in
                           ("start_byte", "end_byte", "start_line", "end_line"))
                    or not 0 <= entry["start_byte"] <= entry["end_byte"] <= len(raw)
                    or not 1 <= entry["start_line"] <= entry["end_line"]):
                raise TreeSitterSWEError("INDEX_ROW_SHAPE_INVALID")
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
    context = analysis_context()
    if (artifact.get("analysis_context") != context
            or artifact.get("analysis_context_sha256") != json_sha256(context)):
        raise TreeSitterSWEError("INDEX_ANALYSIS_CONTEXT_STALE")
    source_root = safe_path(repo, artifact.get("source_root"), must_exist=True, allow_root=True)
    paths = [row.get("path") for row in rows if isinstance(row, dict)]
    if len(paths) != len(rows) or any(not isinstance(path, str) for path in paths):
        raise TreeSitterSWEError("INDEX_ROW_INVALID")
    if len(set(paths)) != len(paths):
        raise TreeSitterSWEError("INDEX_DUPLICATE_PATH")
    # Producers may explicitly index more than the default file budget. Admit
    # that existing inventory, but refuse any additional files beyond it.
    current = [relative_path(repo, path) for path in
               source_files(source_root, max_files=max(MAX_FILES, len(rows)))]
    if sorted(paths) != current:
        raise TreeSitterSWEError("INDEX_FILE_SET_CHANGED")
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
