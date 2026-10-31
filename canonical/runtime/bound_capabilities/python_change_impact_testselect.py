#!/usr/bin/env python3
"""Deterministic diff-to-minimal-test-set selection (change impact analysis).

The speed tax of engineering is paying the full battery for a one-line edit.
This adapter ends it for Python: parse a unified diff (or an explicit changed
path list), locate the touched symbols in the semantic symbol index, walk the
call graph and the import graph downstream, and select exactly the tests that
can still observe the change. Over-approximation law: selectors must never
miss an affected test, but may over-select; every selected test carries the
evidence chain that selected it, and unresolvable changes fail into a named
truthful reason instead of a confident-looking empty set.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _safe_path(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _dotted(rel):
    rel = str(rel).replace("\\", "/")
    if rel.endswith("/__init__.py"):
        rel = rel[: -len("/__init__.py")]
    elif rel.endswith(".py"):
        rel = rel[: -3]
    return rel.replace("/", ".")


def _parse_unified_diff(text):
    """{path: [(start, end), ...]} of new-side changed line ranges."""
    changed = {}
    current = None
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            current = line[len("+++ b/"):]
            changed.setdefault(current, [])
        elif line.startswith("+++ "):
            current = None
        elif current is not None:
            m = _HUNK.match(line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2) or "1")
                changed[current].append((start, start + max(count, 1) - 1))
    return {k: v for k, v in changed.items() if v}


def _load_index(repo, source_root, work, cached_index_path=None):
    """The semantic symbol index, built fresh by the sibling adapter, or a
    validated cache artifact (optional ``index_path`` input).  A cache must
    carry the published schema, nonzero totals, and the exact requested
    source_root — a cache misdescribing the tree it measured is worse than
    no cache."""
    if cached_index_path is not None:
        try:
            artifact = json.loads(pathlib.Path(cached_index_path).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - truthfulness beats type lists
            raise RuntimeError(f"INDEX_CACHE_UNREADABLE:{type(exc).__name__}")
        if artifact.get("schema") != "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1" or int(
            (artifact.get("totals") or {}).get("files", 0)
        ) <= 0:
            raise RuntimeError("INDEX_CACHE_INVALID")
        if str(artifact.get("source_root")) != str(source_root.relative_to(repo)):
            raise RuntimeError("INDEX_CACHE_SOURCE_ROOT_MISMATCH")
        from canonical.runtime.bound_capabilities.python_source_symbol_index import validate_cached_index
        validate_cached_index(repo, source_root, artifact)
        return artifact, {"cache_used": 1}
    spec = importlib.util.spec_from_file_location(
        "python_source_symbol_index_sibling",
        pathlib.Path(__file__).with_name("python_source_symbol_index.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tmp = work / ".change_impact_index.json"
    result = module.run(
        {"source_root": str(source_root.relative_to(repo)), "output_path": str(tmp)},
        repo,
    )
    return json.loads(tmp.read_text(encoding="utf-8")), result


def _changed_symbols(index, changed):
    """Touched definitions per changed file; module-wide when outside any def."""
    out = {}
    modules = {m["path"]: m for m in index.get("modules") or []}
    for path, ranges in changed.items():
        module = modules.get(path)
        if module is None:
            out[path] = {"symbols": [], "module_wide": True, "reason": "MODULE_NOT_INDEXED"}
            continue
        hit = []
        spans = sorted((d["lineno"], d["end_lineno"], d["qualname"]) for d in module["definitions"])
        for start, end in ranges:
            for lo, hi, qual in spans:
                if lo <= end and start <= hi:
                    hit.append(qual)
        hit = sorted(set(hit))
        out[path] = {
            "symbols": hit,
            "module_wide": not hit,
            "reason": "NO_DEFINITION_SPANS_TOUCHED" if not hit else "DEFINITIONS_TOUCHED",
        }
    return out


def _dependency_maps(index):
    """Return (def_modules, name_edges, wide_edges).

    ``def_modules``: bare name -> modules defining it.
    ``name_edges``: target module -> {importing module -> imported names}.
      A ``from pkg.a import origin`` edge fires only when a changed name in
      ``pkg/a.py`` is one of the imported names (or the change is
      module-wide); an uncalled private neighbor must not drag importers in.
    ``wide_edges``: target module -> set(importing modules) for bare
      ``import pkg.a`` statements, which can touch ANY exported name and
      therefore fire on every change in the target.
    Suffix matching: intra-package imports written without the package prefix
    (``from a import x`` inside ``pkg``) resolve to the indexed module whose
    dotted name ends with the import's dotted name.
    """
    def_modules = {}
    for key, row in (index.get("symbols") or {}).items():
        def_modules.setdefault(row["name"], set()).add(row["module"])
    dotted = {m["path"]: _dotted(m["path"]) for m in index.get("modules") or []}
    name_edges = {}
    wide_edges = {}
    for module in index.get("modules") or []:
        for imp in module.get("imports") or []:
            base = str(imp.get("module") or "")
            names = [str(n) for n in imp.get("names") or []]
            targets = set()
            for dotted_target in dotted.values():
                if dotted_target == base or (
                    base and dotted_target.endswith("." + base)
                ):
                    targets.add(dotted_target)
            for target_dot in targets:
                target = [p for p, d in dotted.items() if d == target_dot][0]
                if target == module["path"]:
                    continue
                if str(imp.get("form") or "") == "from":
                    name_edges.setdefault(target, {}).setdefault(
                        module["path"], set()
                    ).update(n for n in names if n)
                else:
                    wide_edges.setdefault(target, set()).add(module["path"])
    return def_modules, name_edges, wide_edges


def _affected_modules(index, changed, changed_symbols):
    """Downstream closure that never misses: modules and call names together.

    BFS over two graphs at once: modules that import a changed module, and
    definitions that call a changed name. A reached caller escalates its own
    bare name, so ``helper -> origin -> entrypoint`` propagates as far as the
    graph goes. Same-named definitions across modules merge (documented
    over-approximation): the selector may widen, never omit.
    """
    callers_of = index.get("callers_of") or {}
    _def_modules, name_edges, wide_edges = _dependency_maps(index)
    qual_to_modules = {}
    for module in index.get("modules") or []:
        for d in module.get("definitions") or []:
            qual_to_modules.setdefault(str(d["qualname"]), set()).add(module["path"])
    affected = set(changed)
    module_frontier = list(changed)
    name_frontier = set()
    for row in changed_symbols.values():
        for qual in row["symbols"]:
            name_frontier.add(qual.rsplit(".", 1)[-1])
    processed_names = set()
    while module_frontier or name_frontier:
        while module_frontier:
            module = module_frontier.pop()
            wide_change = bool((changed_symbols.get(module) or {}).get("module_wide"))
            changed_names = {
                qual.rsplit(".", 1)[-1]
                for qual in (changed_symbols.get(module) or {}).get("symbols") or []
            }
            # bare ``import X`` importers observe anything in the module
            for importer in wide_edges.get(module) or ():
                if importer not in affected:
                    affected.add(importer)
                    module_frontier.append(importer)
            # ``from X import ...`` importers observe the imported names only
            for importer, names in (name_edges.get(module) or {}).items():
                if importer in affected:
                    continue
                if wide_change or changed_names & set(names):
                    affected.add(importer)
                    module_frontier.append(importer)
        if name_frontier:
            name = name_frontier.pop()
            if name in processed_names:
                continue
            processed_names.add(name)
            for caller in callers_of.get(name) or ():
                for other in qual_to_modules.get(caller) or ():
                    if other not in affected:
                        affected.add(other)
                        module_frontier.append(other)
                caller_bare = caller.rsplit(".", 1)[-1]
                if caller_bare not in processed_names:
                    name_frontier.add(caller_bare)
    return affected, processed_names


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_path(repo, args.get("source_root", ""))
    if not source_root.is_dir():
        raise RuntimeError("CHANGE_IMPACT_SOURCE_ROOT_MISSING")
    out_rel = str(args.get("output_path") or "")
    output = (repo / out_rel).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")

    # Refuse source/report aliases before parsing inputs or creating scratch.
    # Reuse the existing symlink/hardlink-aware authority boundary. The index
    # reads Python files; diff and cached index are additional explicit inputs.
    from canonical.runtime.write_authority_v1 import SOURCE_SUFFIXES, check_report
    protected = list(source_root.rglob('*.py'))
    protected.extend(_safe_path(repo, args[key]) for key in ('diff_path', 'index_path')
                     if args.get(key))
    check_report(repo, output, protected)
    if output.suffix.lower() in SOURCE_SUFFIXES:
        raise RuntimeError("REPORT_DESTINATION_IS_SOURCE")

    diff_path = str(args.get("diff_path") or "")
    changed_paths = args.get("changed_paths")
    if diff_path:
        text = _safe_path(repo, diff_path).read_text(encoding="utf-8")
        changed = _parse_unified_diff(text)
        changed_source = "unified_diff"
    elif isinstance(changed_paths, list) and changed_paths and all(
        isinstance(x, str) and x.strip() for x in changed_paths
    ):
        # An explicit path list cannot know line ranges: whole-module change.
        changed = {}
        for raw in changed_paths:
            p = _safe_path(repo, raw)  # containment is law even for reads
            # KEY THE CHANGE THE WAY THE INDEX IS KEYED.  The index holds
            # repo-relative posix paths and ``_changed_symbols`` looks the
            # changed file up in it by that key; storing ``str(raw)`` verbatim
            # meant an ABSOLUTE path -- which is what the composer binds -- never
            # matched, every changed module came back MODULE_NOT_INDEXED, and the
            # report said selected_tests: [] with candidate_test_count: 2.  An
            # empty selection a caller reads as "nothing to run" is worse than a
            # refusal: it is a green light to skip the tests that cover the
            # change.  Measured on main: a change to calc.py that
            # tests/test_calc.py imports selected zero tests.
            rel = str(p.relative_to(repo)).replace("\\", "/")
            changed[rel] = [(1, 10**9)]
        changed_source = "changed_paths"
    else:
        raise RuntimeError("CHANGE_IMPACT_INPUT_REQUIRED")

    py_changed = {p: r for p, r in changed.items() if p.endswith(".py")}
    ignored = sorted(set(changed) - set(py_changed))

    cached_index_path = None
    if args.get("index_path"):
        cached_index_path = _safe_path(repo, str(args["index_path"]))
        if not cached_index_path.is_file():
            raise RuntimeError("INDEX_CACHE_MISSING")
    work = repo / ".change_impact_work"
    work.mkdir(parents=True, exist_ok=True)
    try:
        index, _index_result = _load_index(repo, source_root, work, cached_index_path)
    finally:
        shutil_free = work / ".change_impact_index.json"
        if shutil_free.is_file():
            shutil_free.unlink()
        try:
            work.rmdir()
        except OSError:
            pass

    changed_symbols = _changed_symbols(index, py_changed)
    if changed_source == "changed_paths":
        # An explicit path list names FILES, not lines: every definition could
        # be touched and module scope could be touched. That is module-wide.
        for row in changed_symbols.values():
            row["module_wide"] = True
            if row["reason"] == "NO_DEFINITION_SPANS_TOUCHED":
                row["reason"] = "EXPLICIT_PATH_LIST__MODULE_WIDE"
    affected, _reached = _affected_modules(index, set(py_changed), changed_symbols)

    # THE TESTS THAT COVER A MODULE ARE NOT ONLY THE ONES IN THE REPOSITORY'S TEST ROOTS.
    #
    # ``test_roots`` defaulted to two literal directories, so a test file sitting BESIDE the changed
    # module -- the ordinary layout of any package, and the layout of every tree a sentence names
    # by path -- was never even considered: ``candidate_test_count: 0`` next to
    # ``affected_module_count: 2`` with the test module already named in ``affected_modules``.
    # Measured 2026-10-30 on ``canonical/astra_runtime/tmp/m1/cov``: ``selected_tests: []`` for a
    # change to ``calc.py`` that ``test_calc.py`` imports, which a caller reads as "nothing to run".
    # The anchor the sentence states (``source_root``) is added to the roots: it is evidence, not a
    # widening -- the index is already resolved from that same anchor.
    _declared_roots = [str(r) for r in (args.get("test_roots") or ["tests", "canonical/tests"])]
    _anchor = None
    try:
        _anchor = str(source_root.relative_to(repo)).replace("\\", "/")
    except ValueError:
        _anchor = None
    test_roots = _declared_roots + ([_anchor] if _anchor and _anchor not in _declared_roots else [])
    test_rows = []
    seen = set()
    for module in index.get("modules") or []:
        rel = module["path"]
        if not any(rel.startswith(str(r).rstrip("/") + "/") or str(r).rstrip("/") in rel
                   for r in test_roots):
            continue
        name = pathlib.PurePosixPath(rel).name
        if not (name.startswith("test_") or name.endswith("_test.py")):
            continue
        full = str((repo / rel).resolve())
        if full in seen:
            continue
        seen.add(full)
        reason = None
        if rel in affected:
            # The closure already chased import edges (name-scoped) and call
            # edges through the whole indexed tree, including test modules.
            reason = "MODULE_IN_AFFECTED_CLOSURE"
        test_rows.append({
            "path": rel,
            "selected": reason is not None,
            "reason": reason or "UNAFFECTED",
        })

    selected = sorted(r["path"] for r in test_rows if r["selected"])
    unknown = sorted(
        p for p, row in changed_symbols.items()
        if row["reason"] == "MODULE_NOT_INDEXED"
    )
    if unknown and not selected:
        # A changed Python module the index does not carry is not a module
        # nothing depends on -- it is a module this run could not reason about.
        # Reporting selected_tests: [] there is the same lie as a green empty
        # suite: the caller skips the tests that cover the change and believes
        # it was told they were unaffected.  The tree-sitter selector resolves
        # the same import correctly, so the honest answer is to refuse and let
        # the next capability be tried, not to certify an empty selection.
        raise RuntimeError("CHANGED_PYTHON_MODULE_NOT_INDEXED:" + ",".join(unknown))
    report = {
        "schema": "PROJECT_BRAIN_CHANGE_IMPACT_TEST_SELECTION_V1",
        "source_root": str(source_root.relative_to(repo)).replace("\\", "/"),
        "changed_source": changed_source,
        "changed_files": sorted(changed),
        "ignored_non_python": ignored,
        "changed_symbols": changed_symbols,
        "affected_modules": sorted(affected),
        "indexed_but_not_repo_test_root": False,
        "tests": test_rows,
        "selected_tests": selected,
        "unknown_symbol_modules": unknown,
        "totals": {
            "changed_files": len(changed),
            "changed_python_files": len(py_changed),
            "changed_symbols": sum(len(r["symbols"]) for r in changed_symbols.values()),
            "candidate_tests": len(test_rows),
            "selected_tests": len(selected),
            "affected_modules": len(affected),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    data = output.read_bytes()
    return {
        "adapter": "python_change_impact_testselect",
        "output_path": str(output.relative_to(repo)).replace("\\", "/"),
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "output_verified": True,
        "changed_file_count": len(changed),
        "changed_symbol_count": sum(len(r["symbols"]) for r in changed_symbols.values()),
        "affected_module_count": len(affected),
        "candidate_test_count": len(test_rows),
        "selected_test_count": len(selected),
        "ignored_non_python_count": len(ignored),
        "unknown_symbol_module_count": len(unknown),
    }
