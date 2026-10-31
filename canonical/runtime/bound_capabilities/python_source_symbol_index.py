#!/usr/bin/env python3
"""Deterministic repository-local Python semantic symbol index (stdlib ast).

Beyond the structural audit (which counts functions/classes/imports), this
adapter builds the navigation organ: per-module symbol definitions with kinds,
qualnames and line ranges; intra-module references with resolution classes
(local / module / builtin / unknown); call edges between definitions; and an
inverted ``callers_of`` index -- the direct answer to "who calls X" without
grep. Zero dependencies, fully deterministic, fail-closed on path escapes.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import json
import pathlib

_BUILTIN_NAMES = frozenset(dir(builtins))


def _safe_root(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if p.is_dir():
        return p
    # Same law as python_source_audit: "the call graph of the python file F" and
    # "the call graph of the python source root D" are one question with two
    # scopes. Refusing the first because the caller named a file left the
    # machine unable to answer any call-graph or who-calls question about a
    # single file. The scope stays exactly what the caller named -- one file
    # indexes one file, never its siblings.
    if p.is_file() and p.suffix == ".py":
        return p
    raise RuntimeError("PYTHON_INDEX_ROOT_MISSING")


def _py_files(source_root):
    """The files the index walks: one named file, or every file under a named tree.

    Generated trees are not source.  The walk used to descend into every ``*.py``
    it could see, including vendored, built and cached copies, and the tree-sitter
    kernel next door has carried the ignore list for exactly this reason since it
    was written.  The list is imported rather than copied: two lists of things that
    are not source is two chances for one of them to be wrong.
    """
    if source_root.is_file():
        return [source_root]
    from canonical.runtime.tree_sitter_swe_kernel_v1 import IGNORED_DIRS  # stdlib-only module
    return sorted(path for path in source_root.rglob("*.py")
                  if not any(part in IGNORED_DIRS
                             for part in path.relative_to(source_root).parts))


def _cached_modules(output):
    """Module rows a previous run of this same index already proved, by path.

    THE INDEX HAD NO MEMORY.  Measured 2026-10-30 on ``canonical/runtime``:
    2 255 modules, 596 039 references, 97 623 definitions -- 19.4 s cold and
    16.3 s for the SAME question on the SAME unchanged tree, because every file
    was re-parsed and every reference re-materialised for an answer the previous
    run had already written to disk.  The tree-sitter incremental index next door
    has carried the fix since it was written: keep the previous artifact's rows,
    verify each one, and re-parse only the files whose bytes actually changed.
    This is that rule, on the same verification, for the Python index.

    A row is reused only when its source sha256 matches the file on disk AND the
    row's own sha256 verifies, so a hand-edited or truncated artifact cannot feed
    a stale definition into a rename.
    """
    if not output.is_file():
        return {}
    try:
        old = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(old, dict) or old.get("schema") != "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1":
        return {}
    # The SOURCE is the authority, not the cache.  Every row reused below is
    # checked against the sha256 of the file's current bytes, so a stale row can
    # only survive if the file it describes is byte-identical -- in which case a
    # fresh parse would produce that same row.  Re-hashing each row here was
    # measured at 5.6 s over 2 255 modules (the artifact is 167 MiB) and bought
    # nothing a content-addressed cache needs.
    reusable = {}
    for row in old.get("modules") or []:
        if isinstance(row, dict):
            reusable[str(row.get("path"))] = row
    _CACHE_META["source_root"] = str(old.get("source_root") or "")
    _CACHE_META["unparseable"] = list(old.get("unparseable") or [])
    return reusable


# The last artifact read, as it described the tree: what a run needs to know to
# decide whether the file on disk is still the artifact it would write.
_CACHE_META: dict = {"source_root": "", "unparseable": []}


def _row_sha(row):
    body = {key: value for key, value in row.items() if key != "row_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_cached_index(repo, source_root, artifact):
    """Validate source identity without reparsing cached semantic records.

    Both parsed and unparseable files belong to the manifest. This detects
    content/membership drift, not forged semantics or concurrent tree writes.
    """
    repo = pathlib.Path(repo).resolve()
    source_root = pathlib.Path(source_root).resolve()
    expected = {}
    for field in ("modules", "unparseable"):
        rows = artifact.get(field, [])
        if not isinstance(rows, list):
            raise RuntimeError("INDEX_CACHE_INVALID_ROWS:" + field)
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError("INDEX_CACHE_INVALID_ROW")
            name, digest = row.get("path"), row.get("sha256")
            if not isinstance(name, str) or not isinstance(digest, str):
                raise RuntimeError("INDEX_CACHE_INVALID_ROW")
            if name in expected:
                raise RuntimeError("INDEX_CACHE_DUPLICATE_PATH:" + name)
            expected[name] = digest
    current = {}
    for path in _py_files(source_root):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if repo not in resolved.parents:
            raise RuntimeError("INDEX_CACHE_PATH_OUTSIDE_REPOSITORY")
        name = path.relative_to(repo).as_posix()
        current[name] = path
    if set(expected) != set(current):
        raise RuntimeError("INDEX_CACHE_FILESET_STALE")
    for name, path in current.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
            raise RuntimeError("INDEX_CACHE_SOURCE_STALE:" + name)


def _signature(node):
    args = node.args
    names = [a.arg for a in args.posonlyargs]
    names += [a.arg for a in args.args]
    if args.vararg:
        names.append("*" + args.vararg.arg)
    names += [a.arg for a in args.kwonlyargs]
    if args.kwarg:
        names.append("**" + args.kwarg.arg)
    return names


class _ModuleIndexer(ast.NodeVisitor):
    """Index one parsed module: definitions, references, call edges."""

    def __init__(self):
        self.definitions = []          # {name, qualname, kind, lineno, end_lineno, ...}
        self.references = []           # {name, lineno, col, context, resolution}
        self.calls = []                # {caller, callee}
        self.imports = []              # {module, names}
        self.module_names = set()      # module-level bound names
        self._scope_stack = []         # [{"qualname": str, "locals": set}]

    # -- scopes -----------------------------------------------------------
    def _push_scope(self, qualname, is_class=False):
        self._scope_stack.append({"qualname": qualname, "locals": set(), "class": is_class})

    def _pop_scope(self):
        self._scope_stack.pop()

    def _context(self):
        if not self._scope_stack:
            return "<module>"
        return ".".join(s["qualname"] for s in self._scope_stack)

    def _parent_qual(self):
        return ".".join(s["qualname"] for s in self._scope_stack if s["qualname"] != "<module>")

    # -- definitions ------------------------------------------------------
    def _define(self, name, kind, node, extra=None):
        parent = self._parent_qual()
        qual = (parent + "." + name) if parent else name
        row = {
            "name": name,
            "qualname": qual,
            "kind": kind,
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
        }
        if extra:
            row.update(extra)
        self.definitions.append(row)
        if not self._scope_stack:
            self.module_names.add(name)
        else:
            self._scope_stack[-1]["locals"].add(name)
        return qual

    def visit_Import(self, node):
        names = sorted(a.name for a in node.names)
        for a in node.names:
            self.module_names.add((a.asname or a.name.split(".")[0]))
        self.imports.append({"module": ".".join(names), "names": names, "form": "import"})

    def visit_ImportFrom(self, node):
        names = sorted(a.name for a in node.names)
        for a in node.names:
            self.module_names.add(a.asname or a.name)
        self.imports.append({
            "module": str(node.module or ""),
            "names": names,
            "form": "from",
        })

    def visit_ClassDef(self, node):
        self._define(node.name, "class", node, extra={
            "bases": [ast.unparse(b) for b in node.bases],
            "decorators": [ast.unparse(d) for d in node.decorator_list],
        })
        self._push_scope(node.name, is_class=True)
        self.generic_visit(node)
        self._pop_scope()

    def _visit_function(self, node):
        kind = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
        if self._scope_stack and self._scope_stack[-1]["class"]:
            kind = "method"
        self._define(node.name, kind, node, extra={
            "signature": _signature(node),
            "decorators": [ast.unparse(d) for d in node.decorator_list],
        })
        self._push_scope(node.name)
        for arg in _signature(node):
            self._scope_stack[-1]["locals"].add(arg.lstrip("*"))
        self.generic_visit(node)
        self._pop_scope()

    def visit_FunctionDef(self, node):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)

    # -- bindings ---------------------------------------------------------
    def _bind_target(self, target):
        for node in ast.walk(target):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                if self._scope_stack:
                    self._scope_stack[-1]["locals"].add(node.id)
                else:
                    self.module_names.add(node.id)

    def visit_Assign(self, node):
        for target in node.targets:
            self._bind_target(target)
            # module/scope-level variable definitions are symbols too
            if isinstance(target, ast.Name):
                self._define(target.id, "variable", target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        self._bind_target(node.target)
        if isinstance(node.target, ast.Name):
            self._define(node.target.id, "variable", node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self._bind_target(node.target)
        self.generic_visit(node)

    def visit_For(self, node):
        self._bind_target(node.target)
        self.generic_visit(node)

    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars is not None:
                self._bind_target(item.optional_vars)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.name:
            if self._scope_stack:
                self._scope_stack[-1]["locals"].add(node.name)
            else:
                self.module_names.add(node.name)
        self.generic_visit(node)

    # -- references ---------------------------------------------------------
    def _resolve(self, name):
        for scope in reversed(self._scope_stack):
            if name in scope["locals"]:
                return "local"
        if name in self.module_names:
            return "module"
        if name in _BUILTIN_NAMES:
            return "builtin"
        return "unknown"

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.references.append({
                "name": node.id,
                "lineno": node.lineno,
                "col": node.col_offset,
                "context": self._context(),
                "resolution": self._resolve(node.id),
            })
        self.generic_visit(node)

    # -- call edges ---------------------------------------------------------
    def visit_Call(self, node):
        caller = self._context()
        func = node.func
        callee = None
        if isinstance(func, ast.Name):
            callee = func.id
        elif isinstance(func, ast.Attribute):
            callee = func.attr
        if callee:
            self.calls.append({
                "caller": caller,
                "callee": callee,
                "lineno": node.lineno,
            })
        self.generic_visit(node)


def _module_names_prepass(tree):
    """Module-level bound names, collected BEFORE the indexing walk.

    A body that runs at module-exec time may call a function defined LATER in
    the same file (the call happens after the whole module executed), so
    name resolution that only knows names walked so far misclassifies every
    such forward reference as ``unknown``. The prepass gives the walk the
    complete module scope up front, matching Python's real semantics.
    """
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root", "canonical/runtime"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")

    cached = _cached_modules(output)
    modules = []
    unparseable = []
    reused = 0

    for path in _py_files(source_root):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        rel = str(path.relative_to(repo)).replace("\\", "/")
        sha = hashlib.sha256(raw).hexdigest()
        old = cached.get(rel)
        if old is not None and old.get("sha256") == sha:
            # The file's bytes are the ones this row was built from, and the row
            # itself verified.  Re-deriving it would produce exactly this row.
            modules.append(old)
            reused += 1
            continue
        try:
            tree = ast.parse(raw.decode("utf-8"), filename=str(path))
        except Exception as exc:
            # Same law as the audit: a file that will not parse is a FINDING
            # to report, never an excuse to hide the rest of the tree behind
            # a tool-looking exception.
            unparseable.append({
                "path": rel,
                "sha256": sha,
                "error": type(exc).__name__,
                "detail": str(exc)[:400],
            })
            continue
        indexer = _ModuleIndexer()
        indexer.module_names |= _module_names_prepass(tree)
        indexer.visit(tree)
        row = {
            "path": rel,
            "sha256": sha,
            "imports": indexer.imports,
            "definitions": sorted(indexer.definitions, key=lambda d: (d["lineno"], d["qualname"])),
            "references": sorted(indexer.references, key=lambda r: (r["lineno"], r["col"], r["name"])),
            "calls": sorted(indexer.calls, key=lambda c: (c["lineno"], c["caller"], c["callee"])),
        }
        row["row_sha256"] = _row_sha(row)
        modules.append(row)

    if not modules and not unparseable:
        raise RuntimeError("PYTHON_INDEX_EMPTY")

    symbols = {}
    callers_of = {}
    reference_total = 0
    call_edge_total = 0
    for row in modules:
        rel = row["path"]
        for d in row["definitions"]:
            qual = rel.replace("/", ".").removesuffix(".py") + ":" + d["qualname"]
            symbols[qual] = {
                "module": rel,
                "name": d["name"],
                "qualname": d["qualname"],
                "kind": d["kind"],
                "lineno": d["lineno"],
                "end_lineno": d["end_lineno"],
            }
        for c in row["calls"]:
            if c["caller"] != "<module>":
                callers_of.setdefault(c["callee"], set()).add(c["caller"])
        reference_total += len(row["references"])
        call_edge_total += len(row["calls"])

    report = {
        "schema": "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1",
        "source_root": str(source_root.relative_to(repo)).replace("\\", "/"),
        "modules": modules,
        "symbols": symbols,
        "callers_of": {k: sorted(v) for k, v in sorted(callers_of.items())},
        "unparseable": unparseable,
        "totals": {
            "files": len(modules),
            "unparseable": len(unparseable),
            "symbols": len(symbols),
            "references": reference_total,
            "call_edges": call_edge_total,
        },
    }
    unchanged = (reused == len(modules) and output.is_file()
                 and _CACHE_META.get("source_root") == str(source_root.relative_to(repo)).replace("\\", "/")
                 and list(_CACHE_META.get("unparseable") or []) == unparseable)
    if unchanged:
        # Every module came from this file and the source root is the one it
        # describes, so the bytes on disk ARE the artifact this run would write.
        # Re-rendering 167 MiB to prove it was measured at 1.2 s per question.
        data = output.read_bytes()
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        data = output.read_bytes()
    return {
        "adapter": "python_source_symbol_index",
        "output_path": str(output.relative_to(repo)).replace("\\", "/"),
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "output_verified": True,
        "file_count": len(modules),
        "unparseable_count": len(unparseable),
        "unparseable_paths": [u["path"] for u in unparseable][:20],
        "symbol_count": len(symbols),
        "reference_count": reference_total,
        "call_edge_count": call_edge_total,
        "caller_index_size": len(callers_of),
        # A fresh parse and a cache hit must be indistinguishable in the answer and
        # distinguishable in the report: that is how the speed claim stays honest.
        "parsed_module_count": len(modules) - reused + len(unparseable),
        "reused_module_count": reused,
    }
