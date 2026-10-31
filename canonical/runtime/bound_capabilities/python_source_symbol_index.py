#!/usr/bin/env python3
"""Deterministic repository-local Python semantic symbol index (stdlib ast).

Beyond the structural audit (which counts functions/classes/imports), this
adapter builds the navigation organ: per-module symbol definitions with kinds,
qualnames and line ranges; intra-module references with resolution classes
(local / module / builtin / unknown); call edges between definitions; and an
inverted ``callers_of`` index -- the direct answer to "who calls X" without
grep.

Performance & Root-3 mediation architecture:
- Uses an incremental per-file `(st_mtime_ns, st_size)` cache (in-process +
  per-user temp binary cache) so repeated or post-edit indexing of multi-thousand-
  file trees reparses ONLY modified files while emitting byte-identical JSON.
- Cold indexing over large trees fans out via `subprocess.Popen` worker shards
  (mediated through the Root-3 `subprocess.Popen` chokepoint; zero
  `ProcessPoolExecutor` / unmediated process channels).
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
import pathlib
import pickle
import subprocess
import sys
import tempfile

_BUILTIN_NAMES = frozenset(dir(builtins))
_MEM_CACHE: dict[tuple[str, int, int], tuple[bool, dict]] = {}


def _cache_file_path(repo: pathlib.Path) -> pathlib.Path:
    uid = getattr(os, "getuid", lambda: 0)()
    repo_tag = hashlib.sha256(str(repo).encode("utf-8")).hexdigest()[:12]
    return pathlib.Path(tempfile.gettempdir()) / f"brain_py_sym_idx_v3_{uid}_{repo_tag}.pkl"


def _load_disk_cache(cache_path: pathlib.Path) -> dict[tuple[str, int, int], tuple[bool, dict]]:
    try:
        if cache_path.is_file() and not cache_path.is_symlink():
            data = pickle.loads(cache_path.read_bytes())
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_disk_cache(cache_path: pathlib.Path, data: dict[tuple[str, int, int], tuple[bool, dict]]) -> None:
    try:
        if len(data) > 8000:
            # Keep bounded to recent entries
            keys = list(data.keys())[-6000:]
            data = {k: data[k] for k in keys}
        tmp = cache_path.with_name(f"{cache_path.name}.{os.getpid()}.tmp")
        tmp.write_bytes(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
        os.replace(tmp, cache_path)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)  # type: ignore[possibly-unbound]
        except Exception:
            pass


def _safe_root(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if p.is_dir():
        return p
    if p.is_file() and p.suffix == ".py":
        return p
    raise RuntimeError("PYTHON_INDEX_ROOT_MISSING")


def _py_files_with_stat(source_root: pathlib.Path) -> list[tuple[pathlib.Path, os.stat_result]]:
    """Fast deterministic walk returning `(Path, stat_result)` without redundant syscalls."""
    if source_root.is_file():
        try:
            st = source_root.stat()
            return [(source_root, st)]
        except OSError:
            return []
    found: list[tuple[str, pathlib.Path, os.stat_result]] = []
    stack = [source_root]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            # Match rglob behavior on regular files/dirs safely
                            p = pathlib.Path(entry.path)
                            if p.is_dir():
                                stack.append(p)
                            elif p.is_file() and entry.name.endswith(".py"):
                                st = p.stat()
                                found.append((str(p), p, st))
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(pathlib.Path(entry.path))
                        elif entry.name.endswith(".py") and entry.is_file(follow_symlinks=False):
                            st = entry.stat(follow_symlinks=False)
                            p = pathlib.Path(entry.path)
                            found.append((str(p), p, st))
                    except OSError:
                        continue
        except OSError:
            continue
    found.sort(key=lambda row: row[0])
    return [(p, st) for _, p, st in found]


def _py_files(source_root):
    """The files the index walks: one named file, or every file under a named tree."""
    if source_root.is_file():
        return [source_root]
    return [p for p, _ in _py_files_with_stat(source_root)]


def validate_cached_index(repo, source_root, artifact):
    """Validate source identity without reparsing cached semantic records."""
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
        self.definitions = []
        self.references = []
        self.calls = []
        self.imports = []
        self.module_names = set()
        self._scope_stack = []

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
            "level": int(node.level or 0),
            "form": "from",
        })

    def visit_ClassDef(self, node):
        bases = [ast.unparse(b) for b in node.bases] if node.bases else []
        self._define(node.name, "class", node, extra={"bases": bases})
        self._push_scope(node.name, is_class=True)
        self.generic_visit(node)
        self._pop_scope()

    def _visit_function(self, node):
        kind = "function"
        if self._scope_stack and self._scope_stack[-1]["class"]:
            kind = "method"
        sig = _signature(node)
        decs = [ast.unparse(d) for d in node.decorator_list] if node.decorator_list else []
        self._define(node.name, kind, node, extra={
            "signature": sig,
            "decorators": decs,
        })
        self._push_scope(node.name)
        top_locals = self._scope_stack[-1]["locals"]
        for arg in sig:
            top_locals.add(arg.lstrip("*"))
        self.generic_visit(node)
        self._pop_scope()

    def visit_FunctionDef(self, node):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)

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
                "resolution": self._resolve(node.id),
                "context": self._context(),
            })
        self.generic_visit(node)

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
    """Module-level bound names, collected BEFORE the indexing walk."""
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


def _index_one_file(task: tuple[str, str]) -> tuple[bool, dict]:
    """Parse and index one Python file."""
    path_str, rel = task
    raw = pathlib.Path(path_str).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    try:
        tree = ast.parse(raw.decode("utf-8"), filename=path_str)
    except Exception as exc:
        return False, {
            "path": rel,
            "sha256": sha,
            "error": type(exc).__name__,
            "detail": str(exc)[:400],
        }
    indexer = _ModuleIndexer()
    indexer.module_names |= _module_names_prepass(tree)
    indexer.visit(tree)
    definitions = sorted(indexer.definitions, key=lambda d: (d["lineno"], d["qualname"]))
    references = sorted(indexer.references, key=lambda r: (r["lineno"], r["col"], r["name"]))
    calls = sorted(indexer.calls, key=lambda c: (c["lineno"], c["caller"], c["callee"]))
    mod_obj = {
        "path": rel,
        "sha256": sha,
        "imports": indexer.imports,
        "definitions": definitions,
        "references": references,
        "calls": calls,
    }
    return True, {
        "path": rel,
        "sha256": sha,
        "definitions": definitions,
        "calls": calls,
        "reference_count": len(references),
        "_mod_json": json.dumps(mod_obj, separators=(",", ":"), sort_keys=True),
    }


def _parallel_index_misses(misses: list[tuple[str, str]]) -> list[tuple[bool, dict]]:
    """Fan out cold AST misses across concurrent Root-3-mediated `subprocess.Popen` shards."""
    cpu = os.cpu_count() or 1
    if len(misses) < 128 or cpu <= 1:
        return [_index_one_file(t) for t in misses]
    workers = min(cpu, 8)
    shard_size = (len(misses) + workers - 1) // workers
    shards = [misses[i:i + shard_size] for i in range(0, len(misses), shard_size)]
    procs: list[subprocess.Popen[bytes]] = []
    script = str(pathlib.Path(__file__).resolve())
    try:
        for shard in shards:
            proc = subprocess.Popen(
                [sys.executable, "-B", script, "--worker-shard"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            assert proc.stdin is not None
            proc.stdin.write(pickle.dumps(shard, protocol=pickle.HIGHEST_PROTOCOL))
            proc.stdin.close()
            proc.stdin = None
            procs.append(proc)
        results: list[tuple[bool, dict]] = []
        raw_outs = []
        for proc in procs:
            out_bytes, _ = proc.communicate(timeout=60)
            if proc.returncode != 0 or not out_bytes:
                raise RuntimeError("SHARD_FAILED")
            raw_outs.append(out_bytes)
        for out_bytes in raw_outs:
            batch = pickle.loads(out_bytes)
            results.extend(batch)
        if len(results) != len(misses):
            raise RuntimeError("SHARD_LEN_MISMATCH")
        return results
    except Exception:
        for p in procs:
            try:
                p.kill()
                p.wait(timeout=1)
            except Exception:
                pass
        return [_index_one_file(t) for t in misses]


def _collect_index_parts(source_root_arg, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, source_root_arg)

    file_stats = _py_files_with_stat(source_root)
    cache_path = _cache_file_path(repo)
    disk_cache = _load_disk_cache(cache_path) if len(file_stats) >= 16 else {}

    outcomes: list[tuple[bool, dict] | None] = [None] * len(file_stats)
    miss_indices: list[int] = []
    miss_tasks: list[tuple[str, str]] = []
    miss_keys: list[tuple[str, str, int, int]] = []
    repo_key = str(repo)

    for idx, (path, st) in enumerate(file_stats):
        rel = str(path.relative_to(repo)).replace("\\", "/")
        key = (repo_key, rel, int(st.st_mtime_ns), int(st.st_size))
        cached = _MEM_CACHE.get(key)
        if cached is None and disk_cache:
            cached = disk_cache.get(key)
            if cached is not None:
                _MEM_CACHE[key] = cached
        if cached is not None:
            outcomes[idx] = cached
        else:
            miss_indices.append(idx)
            miss_tasks.append((str(path), rel))
            miss_keys.append(key)

    if miss_tasks:
        computed = _parallel_index_misses(miss_tasks)
        for idx, key, res in zip(miss_indices, miss_keys, computed):
            outcomes[idx] = res
            _MEM_CACHE[key] = res
            if len(file_stats) >= 16:
                disk_cache[key] = res
        if len(file_stats) >= 16:
            _save_disk_cache(cache_path, disk_cache)

    mod_jsons: list[str] = []
    unparseable = []
    symbols = {}
    callers_of: dict[str, set[str]] = {}
    reference_total = 0
    call_edge_total = 0

    for row in outcomes:
        assert row is not None
        ok, item = row
        if not ok:
            unparseable.append(item)
            continue
        rel = item["path"]
        definitions = item["definitions"]
        calls = item["calls"]
        mod_prefix = rel.replace("/", ".").removesuffix(".py") + ":"
        for d in definitions:
            qual = mod_prefix + d["qualname"]
            symbols[qual] = {
                "module": rel,
                "name": d["name"],
                "qualname": d["qualname"],
                "kind": d["kind"],
                "lineno": d["lineno"],
                "end_lineno": d["end_lineno"],
            }
        for c in calls:
            caller = c["caller"]
            if caller != "<module>":
                s = callers_of.get(c["callee"])
                if s is None:
                    callers_of[c["callee"]] = {caller}
                else:
                    s.add(caller)
        reference_total += int(item["reference_count"])
        call_edge_total += len(calls)
        mod_jsons.append(item["_mod_json"])

    if not mod_jsons and not unparseable:
        raise RuntimeError("PYTHON_INDEX_EMPTY")

    src_rel = str(source_root.relative_to(repo)).replace("\\", "/")
    totals = {
        "files": len(mod_jsons),
        "unparseable": len(unparseable),
        "symbols": len(symbols),
        "references": reference_total,
        "call_edges": call_edge_total,
    }
    callers_sorted = {k: sorted(v) for k, v in sorted(callers_of.items())}
    return repo, src_rel, mod_jsons, symbols, callers_sorted, unparseable, totals


def build_index(source_root, root):
    """Build a source-relative index without writing a probe into the source."""
    _, src_rel, mod_jsons, symbols, callers_sorted, unparseable, totals = _collect_index_parts(source_root, root)
    return {
        "schema": "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1",
        "source_root": src_rel,
        "modules": [json.loads(mj) for mj in mod_jsons],
        "symbols": symbols,
        "callers_of": callers_sorted,
        "unparseable": unparseable,
        "totals": totals,
    }


def run(args, root):
    repo = pathlib.Path(root).resolve()
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    _, src_rel, mod_jsons, symbols, callers_sorted, unparseable, totals = _collect_index_parts(
        args.get("source_root", "canonical/runtime"), repo
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        '{"callers_of":',
        json.dumps(callers_sorted, separators=(",", ":"), sort_keys=True),
        ',"modules":[',
        ",".join(mod_jsons),
        '],"schema":"PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1","source_root":',
        json.dumps(src_rel, separators=(",", ":")),
        ',"symbols":',
        json.dumps(symbols, separators=(",", ":"), sort_keys=True),
        ',"totals":',
        json.dumps(totals, separators=(",", ":"), sort_keys=True),
        ',"unparseable":',
        json.dumps(unparseable, separators=(",", ":"), sort_keys=True),
        "}\n",
    ]
    payload = "".join(parts).encode("utf-8")
    output.write_bytes(payload)
    data = output.read_bytes()
    return {
        "adapter": "python_source_symbol_index",
        "output_path": str(output.relative_to(repo)).replace("\\", "/"),
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "output_verified": True,
        "file_count": totals["files"],
        "unparseable_count": totals["unparseable"],
        "unparseable_paths": [u["path"] for u in unparseable][:20],
        "symbol_count": totals["symbols"],
        "reference_count": totals["references"],
        "call_edge_count": totals["call_edges"],
        "caller_index_size": len(callers_sorted),
    }


def _worker_main() -> int:
    shard = pickle.loads(sys.stdin.buffer.read())
    out = [_index_one_file(t) for t in shard]
    sys.stdout.buffer.write(pickle.dumps(out, protocol=pickle.HIGHEST_PROTOCOL))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--worker-shard":
    raise SystemExit(_worker_main())
