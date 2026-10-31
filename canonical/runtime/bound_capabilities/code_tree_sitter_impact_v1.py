#!/usr/bin/env python3
"""Conservative cross-language changed-code to test-set selection."""
from __future__ import annotations

import json
import pathlib
import posixpath
import re
from collections import defaultdict
from typing import Any

from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel
from canonical.runtime.bound_capabilities.python_change_impact_testselect import _parse_unified_diff

SCHEMA = kernel.IMPACT_SCHEMA
CAPABILITY_ID = "code.impact.tree_sitter.testselect.v1"
PROVIDES = ["code.impact.test_selection.verified", "code.test.slice.tree_sitter"]
REQUIRES = ["code.symbols.tree_sitter.indexed"]


def _module_name(source_root: str, path: str) -> str:
    rel = path if source_root == "." else posixpath.relpath(path, source_root)
    if rel.endswith("/__init__.py"):
        rel = rel[:-12]
    elif rel.endswith(".py"):
        rel = rel[:-3]
    return rel.replace("/", ".")


def _import_targets(importer: str, raw: str, rows: dict[str, dict[str, Any]], source_root: str) -> tuple[set[str], bool]:
    """Return (local targets, unresolved_local). External imports are not gaps."""
    language = rows[importer]["language"]
    targets: set[str] = set()
    unresolved_local = False
    if language == "python":
        wanted = raw.lstrip(".")
        for path in rows:
            if path.endswith(".py") and _module_name(source_root, path) in {wanted, wanted.rsplit(".", 1)[0]}:
                targets.add(path)
        if not targets:
            stem = wanted.rsplit(".", 1)[-1]
            targets = {path for path in rows if pathlib.PurePosixPath(path).stem == stem}
        unresolved_local = raw.startswith(".") and not targets
    elif language in {"javascript", "typescript", "cpp"} and raw.startswith("."):
        base = posixpath.normpath(posixpath.join(posixpath.dirname(importer), raw))
        candidates = {base}
        for suffix in kernel.LANGUAGE_BY_SUFFIX:
            candidates.add(base + suffix)
        for suffix in kernel.LANGUAGE_BY_SUFFIX:
            candidates.add(posixpath.join(base, "index" + suffix))
        targets = {candidate for candidate in candidates if candidate in rows}
        unresolved_local = not targets
    else:
        leaf = raw.replace("::", "/").replace(".", "/").rsplit("/", 1)[-1]
        if leaf:
            targets = {
                path for path in rows
                if pathlib.PurePosixPath(path).stem == leaf or pathlib.PurePosixPath(path).parent.name == leaf
            }
        if language == "cpp" and ("/" in raw or raw.endswith((".h", ".hh", ".hpp"))):
            unresolved_local = not targets
    targets.discard(importer)
    return targets, unresolved_local


def _changed_inputs(repo: pathlib.Path, args: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    changed_paths = args.get("changed_paths")
    diff_path = args.get("diff_path")
    if bool(changed_paths) == bool(diff_path):
        raise kernel.TreeSitterSWEError("EXACTLY_ONE_CHANGE_INPUT_REQUIRED")
    if diff_path:
        path = kernel.safe_path(repo, diff_path, must_exist=True)
        changed = _parse_unified_diff(path.read_text(encoding="utf-8"))
        if not changed:
            raise kernel.TreeSitterSWEError("DIFF_HAS_NO_NEW_SIDE_CHANGES")
        return {str(key): value for key, value in changed.items()}
    if not isinstance(changed_paths, list) or not all(isinstance(path, str) and path for path in changed_paths):
        raise kernel.TreeSitterSWEError("CHANGED_PATHS_INVALID")
    return {path: [] for path in sorted(set(changed_paths))}


def _derived_index(repo: pathlib.Path, args: dict[str, Any],
                   output: pathlib.Path) -> pathlib.Path:
    """Build the index this capability declares it requires, from the tree.

    ``REQUIRES`` above already names ``code.symbols.tree_sitter.indexed``, and
    ``code.index.tree_sitter.incremental.v1`` already provides it.  The
    dependency was declared and never executed, so ``index_path`` was a required
    input that no sentence can state -- which is not a caller obligation.  When
    the adapter can obtain the data from data it already has, the input is
    derivable and must be derived; that is the same rule by which ``test_argv``
    is the adapter's own ``suite_argv`` rather than something the sentence
    invents.

    The scope is the smallest directory containing every changed file.  That is
    not a guess: ``run`` below raises ``CHANGED_FILE_NOT_INDEXED`` for any
    changed file the index does not carry, so a smaller tree cannot work, and a
    stated ``source_root`` always wins over it.
    """
    from canonical.runtime.bound_capabilities import code_tree_sitter_incremental_index_v1 as _index

    stated_root = args.get("source_root")
    if stated_root:
        source_root = str(stated_root)
    else:
        changed = _changed_inputs(repo, args)
        parents = {str(pathlib.PurePosixPath(p).parent) for p in changed}
        source_root = "."
        if parents:
            parts = [p.split("/") for p in sorted(parents)]
            common: list[str] = []
            for group in zip(*parts):
                if len(set(group)) != 1:
                    break
                common.append(group[0])
            source_root = "/".join(common) or "."
    index_path = output.parent / (".impact_index_" + output.name)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    _index.run({"source_root": source_root,
                "output_path": kernel.relative_path(repo, index_path)}, repo)
    return index_path


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = kernel.safe_output(repo, args.get("output_path"))
    stated_index = args.get("index_path")
    if stated_index:
        index_path = kernel.safe_path(repo, stated_index, must_exist=True)
        index_source = "stated"
    else:
        index_path = _derived_index(repo, args, output)
        index_source = "derived_under_changed_paths"
    index = kernel.read_index(repo, index_path)
    rows = {row["path"]: row for row in index["files"]}
    source_root = str(index.get("source_root") or ".")
    changed = _changed_inputs(repo, args)
    missing = sorted(set(changed) - set(rows))
    if missing:
        raise kernel.TreeSitterSWEError("CHANGED_FILE_NOT_INDEXED:" + ",".join(missing))

    explicit_tests = args.get("test_paths")
    if explicit_tests is not None:
        if not isinstance(explicit_tests, list) or not explicit_tests:
            raise kernel.TreeSitterSWEError("TEST_PATHS_INVALID")
        candidates = sorted({str(path) for path in explicit_tests})
        absent = sorted(set(candidates) - set(rows))
        if absent:
            raise kernel.TreeSitterSWEError("TEST_FILE_NOT_INDEXED:" + ",".join(absent))
    else:
        candidates = sorted(path for path, row in rows.items() if kernel.is_test_file(repo, row, source_root))

    reverse: dict[str, set[str]] = defaultdict(set)
    unresolved_by_file: dict[str, list[str]] = defaultdict(list)
    for importer, row in rows.items():
        for raw in row.get("imports") or []:
            targets, unresolved = _import_targets(importer, str(raw), rows, source_root)
            for target in targets:
                reverse[target].add(importer)
            if unresolved:
                unresolved_by_file[importer].append(str(raw))

    references: dict[tuple[str, str], set[str]] = defaultdict(set)
    for path, row in rows.items():
        for reference in row.get("references") or []:
            references[(str(row["language"]), str(reference["name"]))].add(path)

    changed_symbols: dict[str, list[str]] = {}
    affected = set(changed)
    frontier = list(changed)
    for path, ranges in changed.items():
        names = []
        for definition in rows[path].get("definitions") or []:
            if not ranges or any(
                definition["start_line"] <= end and start <= definition["end_line"]
                for start, end in ranges
            ):
                names.append(str(definition["name"]))
        names = sorted(set(names))
        changed_symbols[path] = names
        for name in names:
            for reference_file in references.get((str(rows[path]["language"]), name), set()):
                if reference_file not in affected:
                    affected.add(reference_file)
                    frontier.append(reference_file)

    # Import syntax is not the only way to name a local dependency: dynamic
    # loaders and multi-import syntax can hide one from a grammar-specific
    # import extractor. A same-language whole-word stem scan widens the closure
    # over those cases; it may over-select, never silently drop the evidence.
    text_cache: dict[str, str] = {}
    for changed_path in changed:
        stem = pathlib.PurePosixPath(changed_path).stem
        if len(stem) < 2:
            continue
        pattern = re.compile(r"\b" + re.escape(stem) + r"\b")
        language = rows[changed_path]["language"]
        for path, row in rows.items():
            if path in affected or row["language"] != language:
                continue
            if path not in text_cache:
                text_cache[path] = kernel.safe_path(repo, path, must_exist=True).read_text(encoding="utf-8", errors="replace")
            if pattern.search(text_cache[path]):
                affected.add(path)
                frontier.append(path)

    while frontier:
        target = frontier.pop()
        for importer in sorted(reverse.get(target, set())):
            if importer not in affected:
                affected.add(importer)
                frontier.append(importer)

    selected = sorted(affected & set(candidates))
    fallback_reasons: list[str] = []
    for path in changed:
        if rows[path].get("has_syntax_error"):
            fallback_reasons.append("CHANGED_FILE_HAS_SYNTAX_ERROR:" + path)
    for path in sorted(affected):
        for raw in unresolved_by_file.get(path, []):
            fallback_reasons.append("UNRESOLVED_LOCAL_IMPORT:" + path + ":" + raw)
    if candidates and not selected:
        fallback_reasons.append("NO_GRAPH_REACHABLE_TEST__FULL_SET_REQUIRED")
    if fallback_reasons:
        selected = list(candidates)
    selected = sorted(set(selected))
    omitted = sorted(set(candidates) - set(selected))
    verified = bool(candidates)
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "index_path": kernel.relative_path(repo, index_path),
        "index_source": index_source,
        "index_sha256": kernel.bytes_sha256(index_path.read_bytes()),
        "source_root": source_root,
        "changed_files": sorted(changed),
        "changed_symbols": changed_symbols,
        "affected_files": sorted(affected),
        "candidate_tests": candidates,
        "selected_tests": selected,
        "omitted_tests": omitted,
        "fallback_reasons": sorted(set(fallback_reasons)),
        "complete": not fallback_reasons and bool(candidates),
        "verified": verified,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    digest = kernel.write_artifact(output, artifact)
    return {
        "adapter": "code_tree_sitter_impact_v1",
        "output_path": kernel.relative_path(repo, output),
        "output_sha256": digest,
        "output_verified": verified,
        "verified": verified,
        "selected_test_count": len(selected),
        "candidate_test_count": len(candidates),
        "affected_file_count": len(affected),
        "fallback_count": len(set(fallback_reasons)),
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
