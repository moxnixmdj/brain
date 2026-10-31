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
import collections
import hashlib
import json
import os
import pathlib

_BUILTIN_NAMES = frozenset(dir(builtins))
_IN_MEM_ROW_CACHE: dict[tuple[str, str, bool], dict] = {}


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
    found: list[pathlib.Path] = []
    stack = [source_root]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    name = entry.name
                    if entry.is_dir(follow_symlinks=False):
                        if name not in IGNORED_DIRS:
                            stack.append(pathlib.Path(entry.path))
                    elif name.endswith(".py") and entry.is_file(follow_symlinks=False):
                        found.append(pathlib.Path(entry.path))
        except OSError:
            continue
    return sorted(found)


# Process-local attestations of bytes this producer actually derived. Neither a
# source digest nor a self-reported row digest authenticates persisted semantics.
# New processes rederive once; warm requests and sibling outputs retain reuse.
_TRUSTED_OUTPUTS: dict[str, str] = {}
_TRUSTED_DIGEST_ROWS: dict[str, tuple[dict, str, list]] = {}


def _remember_output(output, data, *, fast_rows=None, source_root_rel="", unparseable=None):
    digest = hashlib.sha256(data).hexdigest()
    key = str(output)
    _TRUSTED_OUTPUTS.pop(key, None)
    _TRUSTED_OUTPUTS[key] = digest
    while len(_TRUSTED_OUTPUTS) > 128:
        _TRUSTED_OUTPUTS.pop(next(iter(_TRUSTED_OUTPUTS)))
    if fast_rows is not None:
        _TRUSTED_DIGEST_ROWS.pop(digest, None)
        _TRUSTED_DIGEST_ROWS[digest] = (fast_rows, str(source_root_rel), list(unparseable or []))
        while len(_TRUSTED_DIGEST_ROWS) > 16:
            _TRUSTED_DIGEST_ROWS.pop(next(iter(_TRUSTED_DIGEST_ROWS)))
    return digest


def _cached_modules(output):
    """Reuse persisted rows only when their exact bytes have producer provenance."""
    _CACHE_META.clear()
    expected = _TRUSTED_OUTPUTS.get(str(output))
    if expected is None or not output.is_file():
        return {}
    try:
        data = output.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if expected != digest:
            return {}
        fast = _TRUSTED_DIGEST_ROWS.get(digest)
        if fast is not None:
            rows, sr_rel, unp = fast
            _CACHE_META.update(output_path=str(output), digest=digest, source_root=sr_rel, unparseable=list(unp))
            return rows
        old = json.loads(data)
    except (OSError, ValueError):
        return {}
    rows = _rows_from_artifact(old)
    _CACHE_META.update(output_path=str(output), digest=digest)
    return rows


def _rows_from_artifact(old) -> dict:
    """Module rows an already-verified index artifact proved, by path."""
    if not isinstance(old, dict) or old.get("schema") != "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1":
        return {}
    # Called only after exact artifact bytes are authenticated by this producer.
    # Current source bytes are checked separately before any row can be reused.
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


def _cached_modules_for_tree(output, source_root_rel, limit=3):
    """The rows an artifact for THIS TREE already proved, when this run has none of its own.

    THE CACHE KEY WAS THE ONE THING A CALLER COULD NOT REPEAT.  Measured 2026-10-31 on
    34f867a: the door names each request's artifact after the request, so two different
    sentences about ``canonical/runtime`` asked for two different files, ``_cached_modules``
    found nothing for either, and each re-parsed 2 287 files -- 15.5 s, for an answer that
    occupied 1.5 MB of a 105.8 MB artifact.  The previous request's artifact is on disk beside
    this one and describes the same tree.

    Nothing is trusted on the strength of being nearby: the artifact must declare this
    ``source_root`` and this schema, only the newest few are considered, and every row offered
    is then checked against the sha256 of the file's current bytes inside the caller -- the same
    check a fresh parse passes.  The source stays the authority; this only finds the rows.
    """
    try:
        siblings = sorted(
            (p for p in output.parent.glob("*.json") if p != output and p.is_file()),
            key=lambda p: p.stat().st_mtime_ns, reverse=True)[:max(1, int(limit))]
    except OSError:
        return {}
    for candidate in siblings:
        rows = _cached_modules(candidate)
        if rows and _CACHE_META.get("source_root") == str(source_root_rel):
            return rows
    return {}


def _row_sha(row):
    body = {key: value for key, value in row.items() if key != "row_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_cached_index(repo, source_root, artifact):
    """Validate current source identity and the provenance of cached semantics.

    Known producer bytes avoid rederivation. Unknown dictionaries must exactly
    match a fresh derivation; checksums alone are not authenticity evidence.
    This is not a source snapshot or a concurrent-writer isolation boundary.
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

    canonical = (json.dumps(artifact, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    if digest not in _TRUSTED_OUTPUTS.values():
        if artifact != build_index(source_root, repo):
            raise RuntimeError("INDEX_CACHE_DERIVATION_UNTRUSTED")



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
        self._local_counts = collections.Counter()
        self._cur_ctx = "<module>"
        self._cur_parent = ""

    # -- scopes -----------------------------------------------------------
    def _push_scope(self, qualname, is_class=False):
        self._scope_stack.append({"qualname": qualname, "locals": set(), "class": is_class})
        joined = ".".join(s["qualname"] for s in self._scope_stack)
        self._cur_ctx = joined
        self._cur_parent = joined

    def _pop_scope(self):
        popped = self._scope_stack.pop()
        lc = self._local_counts
        for nm in popped["locals"]:
            c = lc[nm] - 1
            if c <= 0:
                del lc[nm]
            else:
                lc[nm] = c
        if not self._scope_stack:
            self._cur_ctx = "<module>"
            self._cur_parent = ""
        else:
            joined = ".".join(s["qualname"] for s in self._scope_stack)
            self._cur_ctx = joined
            self._cur_parent = joined

    def _add_local(self, name: str) -> None:
        top = self._scope_stack[-1]["locals"]
        if name not in top:
            top.add(name)
            self._local_counts[name] += 1

    def _context(self):
        return self._cur_ctx

    def _parent_qual(self):
        return self._cur_parent

    # -- definitions ------------------------------------------------------
    def _define(self, name, kind, node, extra=None):
        parent = self._cur_parent
        qual = (parent + "." + name) if parent else name
        base_row = {
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "kind": kind,
            "lineno": node.lineno,
            "name": name,
            "qualname": qual,
        }
        if extra:
            base_row.update(extra)
            row = {k: base_row[k] for k in sorted(base_row)}
        else:
            row = base_row
        self.definitions.append(row)
        if not self._scope_stack:
            self.module_names.add(name)
        else:
            self._add_local(name)
        return qual

    def visit_Import(self, node):
        names = sorted(a.name for a in node.names)
        for a in node.names:
            self.module_names.add((a.asname or a.name.split(".")[0]))
        self.imports.append({"form": "import", "module": ".".join(names), "names": names})

    def visit_ImportFrom(self, node):
        names = sorted(a.name for a in node.names)
        for a in node.names:
            self.module_names.add(a.asname or a.name)
        self.imports.append({
            "form": "from",
            "module": str(node.module or ""),
            "names": names,
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
            self._add_local(arg.lstrip("*"))
        self.generic_visit(node)
        self._pop_scope()

    def visit_FunctionDef(self, node):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)

    # -- bindings ---------------------------------------------------------
    def _bind_target(self, target):
        if isinstance(target, ast.Name):
            if self._scope_stack:
                self._add_local(target.id)
            else:
                self.module_names.add(target.id)
            return
        for node in ast.walk(target):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                if self._scope_stack:
                    self._add_local(node.id)
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
                self._add_local(node.name)
            else:
                self.module_names.add(node.name)
        self.generic_visit(node)

    # -- references ---------------------------------------------------------
    def _resolve(self, name):
        if name in self._local_counts:
            return "local"
        if name in self.module_names:
            return "module"
        if name in _BUILTIN_NAMES:
            return "builtin"
        return "unknown"

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            name = node.id
            if name in self._local_counts:
                res = "local"
            elif name in self.module_names:
                res = "module"
            elif name in _BUILTIN_NAMES:
                res = "builtin"
            else:
                res = "unknown"
            self.references.append({
                "col": node.col_offset,
                "context": self._cur_ctx,
                "lineno": node.lineno,
                "name": name,
                "resolution": res,
            })

    # -- call edges ---------------------------------------------------------
    def visit_Call(self, node):
        caller = self._cur_ctx
        func = node.func
        if isinstance(func, ast.Name):
            self.calls.append({"callee": func.id, "caller": caller, "lineno": node.lineno})
        elif isinstance(func, ast.Attribute):
            self.calls.append({"callee": func.attr, "caller": caller, "lineno": node.lineno})
        self.generic_visit(node)

    def generic_visit(self, node):
        visit = self.visit
        for fname in node._fields:
            field_val = getattr(node, fname, None)
            if isinstance(field_val, list):
                for item in field_val:
                    if isinstance(item, ast.AST):
                        visit(item)
            elif isinstance(field_val, ast.AST):
                visit(field_val)

    def visit(self, node):
        fn = _VISITOR_TABLE.get(type(node))
        if fn is not None:
            fn(self, node)
        else:
            self.generic_visit(node)


_VISITOR_TABLE = {
    ast.Name: _ModuleIndexer.visit_Name,
    ast.Call: _ModuleIndexer.visit_Call,
    ast.Assign: _ModuleIndexer.visit_Assign,
    ast.AnnAssign: _ModuleIndexer.visit_AnnAssign,
    ast.AugAssign: _ModuleIndexer.visit_AugAssign,
    ast.For: _ModuleIndexer.visit_For,
    ast.With: _ModuleIndexer.visit_With,
    ast.ExceptHandler: _ModuleIndexer.visit_ExceptHandler,
    ast.FunctionDef: _ModuleIndexer.visit_FunctionDef,
    ast.AsyncFunctionDef: _ModuleIndexer.visit_AsyncFunctionDef,
    ast.ClassDef: _ModuleIndexer.visit_ClassDef,
    ast.Import: _ModuleIndexer.visit_Import,
    ast.ImportFrom: _ModuleIndexer.visit_ImportFrom,
}


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


def _parse_single_module_worker(item):
    """Top-level worker for parallel cold AST indexing on large trees."""
    rel, sha, path_str, json_only = item
    try:
        raw = pathlib.Path(path_str).read_bytes()
        tree = ast.parse(raw.decode("utf-8"), filename=path_str)
    except Exception as exc:
        return ("err", {
            "detail": str(exc)[:400],
            "error": type(exc).__name__,
            "path": rel,
            "sha256": sha,
        })
    indexer = _ModuleIndexer()
    indexer.module_names |= _module_names_prepass(tree)
    indexer.visit(tree)
    calls = sorted(indexer.calls, key=lambda c: (c["lineno"], c["caller"], c["callee"]))
    definitions = sorted(indexer.definitions, key=lambda d: (d["lineno"], d["qualname"]))
    references = sorted(indexer.references, key=lambda r: (r["lineno"], r["col"], r["name"]))
    body = {
        "calls": calls,
        "definitions": definitions,
        "imports": indexer.imports,
        "path": rel,
        "references": references,
        "sha256": sha,
    }
    body_json = json.dumps(body, separators=(",", ":"))
    row_sha = hashlib.sha256(body_json.encode("utf-8")).hexdigest()
    if json_only:
        suffix = f',"sha256":"{sha}"}}'
        row_json = body_json[:-len(suffix)] + f',"row_sha256":"{row_sha}"' + suffix
        return ("ok_json", {
            "path": rel,
            "sha256": sha,
            "definitions": definitions,
            "calls": calls,
            "ref_count": len(references),
            "row_json": row_json,
        })
    row = {
        "calls": calls,
        "definitions": definitions,
        "imports": indexer.imports,
        "path": rel,
        "references": references,
        "row_sha256": row_sha,
        "sha256": sha,
    }
    return ("ok", row)


def _collect_index_parts(source_root_arg, root, cached=None, *, json_only=False, cached_loader=None):
    """Request-local index construction shared by staged workflows and the adapter."""
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, source_root_arg)
    cached_loaded = cached is not None
    cached = cached or {}
    modules_by_rel = {}
    ordered_rels = []
    to_parse = []
    unparseable = []
    reused = 0

    for path in _py_files(source_root):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        rel = str(path.relative_to(repo)).replace("\\", "/")
        sha = hashlib.sha256(raw).hexdigest()
        if not cached_loaded and cached_loader is not None:
            cached = cached_loader() or {}
            cached_loaded = True
        old = cached.get(rel)
        if old is not None and old.get("sha256") == sha:
            modules_by_rel[rel] = old
            ordered_rels.append(rel)
            reused += 1
            continue
        ordered_rels.append(rel)
        to_parse.append((rel, sha, str(path), json_only))

    use_mp = False
    if len(to_parse) >= 64:
        try:
            import multiprocessing
            use_mp = not multiprocessing.current_process().daemon and (os.cpu_count() or 1) > 1
        except Exception:
            use_mp = False

    if use_mp:
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        workers = min(os.cpu_count() or 4, 8)
        mp_ctx = multiprocessing.get_context("fork") if "fork" in multiprocessing.get_all_start_methods() else None
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp_ctx) as ex:
            results = list(ex.map(_parse_single_module_worker, to_parse, chunksize=max(16, len(to_parse) // (workers * 4))))
    else:
        results = [_parse_single_module_worker(item) for item in to_parse]

    for (_rel_item, _sha_item, _, _jo_item), (kind, payload) in zip(to_parse, results):
        if kind in ("ok", "ok_json"):
            modules_by_rel[payload["path"]] = payload
        else:
            unparseable.append(payload)

    modules = [modules_by_rel[r] for r in ordered_rels if r in modules_by_rel]

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
                "end_lineno": d["end_lineno"],
                "kind": d["kind"],
                "lineno": d["lineno"],
                "module": rel,
                "name": d["name"],
                "qualname": d["qualname"],
            }
        for c in row["calls"]:
            if c["caller"] != "<module>":
                callers_of.setdefault(c["callee"], set()).add(c["caller"])
        reference_total += row["ref_count"] if "ref_count" in row else len(row["references"])
        call_edge_total += len(row["calls"])

    report = {
        "callers_of": {k: sorted(v) for k, v in sorted(callers_of.items())},
        "modules": modules,
        "schema": "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1",
        "source_root": str(source_root.relative_to(repo)).replace("\\", "/"),
        "symbols": {k: symbols[k] for k in sorted(symbols)},
        "totals": {
            "call_edges": call_edge_total,
            "files": len(modules),
            "references": reference_total,
            "symbols": len(symbols),
            "unparseable": len(unparseable),
        },
        "unparseable": unparseable,
    }
    return report, reused


def build_index(source_root, root):
    """Build the ordinary index without publishing a report or modifying sources."""
    report, _ = _collect_index_parts(source_root, root, json_only=False)
    return report


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root", "canonical/runtime"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")

    source_root_rel = source_root.relative_to(repo).as_posix()
    report, reused = _collect_index_parts(
        source_root_rel,
        repo,
        json_only=True,
        cached_loader=lambda: _cached_modules(output) or _cached_modules_for_tree(output, source_root_rel),
    )
    modules = report["modules"]
    unparseable = report["unparseable"]
    symbols = report["symbols"]
    callers_of = report["callers_of"]
    reference_total = report["totals"]["references"]
    call_edge_total = report["totals"]["call_edges"]
    unchanged = (reused == len(modules) and output.is_file()
                 and _CACHE_META.get("output_path") == str(output)
                 and _CACHE_META.get("source_root") == str(source_root.relative_to(repo)).replace("\\", "/")
                 and list(_CACHE_META.get("unparseable") or []) == unparseable)
    data = output.read_bytes() if unchanged else None
    if data is None or hashlib.sha256(data).hexdigest() != _CACHE_META.get("digest"):
        output.parent.mkdir(parents=True, exist_ok=True)
        row_jsons = [
            m["row_json"] if "row_json" in m else json.dumps(m, sort_keys=True, separators=(",", ":"))
            for m in modules
        ]
        head_part = '{"callers_of":' + json.dumps(callers_of, separators=(",", ":")) + ',"modules":['
        tail_obj = {
            "schema": report["schema"],
            "source_root": report["source_root"],
            "symbols": symbols,
            "totals": report["totals"],
            "unparseable": [
                {k: u[k] for k in sorted(u)} for u in unparseable
            ],
        }
        tail_part = "]," + json.dumps(tail_obj, separators=(",", ":"))[1:] + "\n"
        data = (head_part + ",".join(row_jsons) + tail_part).encode("utf-8")
        output.write_bytes(data)
    output_sha = _remember_output(
        output,
        data,
        fast_rows={m["path"]: m for m in modules},
        source_root_rel=report["source_root"],
        unparseable=unparseable,
    )
    return {
        "adapter": "python_source_symbol_index",
        "output_path": str(output.relative_to(repo)).replace("\\", "/"),
        "output_sha256": output_sha,
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
