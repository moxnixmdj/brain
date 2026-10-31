# PROJECT_BRAIN
"""python.source.symbols.resolve.v1 — resolve a Python name to its definition.

The brain's adapter-binder needs to answer "which file and which definition
does this name come from?" before it can plan a cross-file edit.  This
adapter does that, from the existing deterministic build result:

* input ``source_root``: same treated tree as the index capability.
* input ``queries``: a JSON array of resolution requests, each shaped
  ``{"module": "pkg/a.py", "line": 3, "name": "helper"}`` or
  ``{"reference": "pkg.original.helper"}`` (dotted path form).
* for each ``module``-shaped query the adapter walks scopes from the line
  outward: enclosing class/function locals (slices), enclosing class
  attributes, the defining module's definitions, the module's imports
  (``name`` -> ``from`` module mapping, ``alias`` -> ``import`` module),
  and finally all modules that export a definition with that bare name.
* for each ``reference`` query the adapter resolves a dotted path through
  the module tree: leftmost part must be a known top-level module or
  package; then each attribute hop must be a definition exported at the
  module or class level.
* every resolution carries one of: RESOLVED (single target), MULTI_HOME
  with all candidates listed (ambiguous), BUILTIN (builtin module member),
  EXTERNAL (imported module that is not part of the index, e.g. stdlib or
  third-party), or UNRESOLVED with a truthful reason.
* the artifact is sorted and hashed; it contains the full result set.
* refusals: empty queries, sensible path guard; bad input shape is an
  adapter lane systemic error / resolvable-world error — so refused inputs
  raise SystemExit before any artifact is written.
* zero spend, everything local, bounded over-approximation never-miss: if
  a name could be defined in several modules, MULTI_HOME lists every one,
  never just the first hit.

Adapter lanes: run() returns the registry ``result_fields``.  ``--selfcheck``
produces the structural digest of a fresh artifact build.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from canonical.runtime.bound_capabilities import python_source_symbol_index as _index

CAPABILITY_ID = "python.source.symbols.resolve.v1"
ARTIFACT_SCHEMA = "PROJECT_BRAIN_SYMBOLS_RESOLVE_V1"
ADAPTER_ERROR = "RESOLUTION_INPUT_INVALID"


class _Refusal(Exception):
    pass


def _systemic(message):
    print(json.dumps({"error": ADAPTER_ERROR, "error_kind": "systemic", "message": message}))
    raise SystemExit(1)


def _resolvable(message):
    print(json.dumps({"error": ADAPTER_ERROR, "error_kind": "resolvable_world", "message": message}))
    raise SystemExit(1)


SPOOL_PREFIX = "canonical/astra_runtime/tmp/"


def _is_machine_spool(value):
    """Is this path one of OUR OWN intermediate artifacts?

    The DAG planner synthesises spool paths for slots a sentence does not name
    (``goal_front_compiler_v1._spool_path``), and it makes them deterministic on purpose: the same
    request always spools to the same place.  The consequence, measured 2026-10-30, is that the
    SECOND request needing that slot dies on the first one's leftovers::

        {"error": "EDIT_PLAN_INPUT_INVALID", "error_kind": "systemic",
         "message": "output already exists: canonical/astra_runtime/tmp/spool_0_output.json"}

    That is the machine refusing to write its own scratch, and it surfaced as a raw error on
    stdout in 2 of 46 advanced requests.  A spool artifact is scratch by construction, so a new
    run may replace the bytes of a previous run.  Every other path keeps the existing rule: an
    output that already exists is somebody's file and is never overwritten.
    """
    rel = str(value or "").replace("\\", "/")
    return rel.startswith(SPOOL_PREFIX) and rel.rsplit("/", 1)[-1].startswith("spool_")


def _safe_path(root, value, allow_overwrite=False):
    if not isinstance(value, str) or not value:
        _systemic("path inputs must be non-empty strings")
    if Path(value).is_absolute():
        _systemic("paths must be repository-relative")
    parts = Path(value).parts
    if any(part in ("..", "") or part.startswith("~") for part in parts):
        _systemic("paths must stay inside the repository")
    resolved = (Path(root) / value).resolve()
    base = Path(root).resolve()
    if base != resolved and base not in resolved.parents:
        _systemic(f"path escapes repository root: {value}")
    if not allow_overwrite and resolved.exists():
        _resolvable(f"output already exists: {value}")
    return resolved


def _dotted(rel):
    """pkg/a.py -> pkg.a (init-aware), same law as the sibling adapters."""
    rel = rel.replace("\\", "/")
    for cand in rel.split("/"):
        if cand.startswith("."):
            return rel
    if rel.endswith(".py"):
        rel = rel[:-3]
    rel = rel.replace("/__init__", "").replace("/__init__.py", "")
    return rel.replace("/", ".")


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _materialize(index):
    """index artifact -> (index, modules, definitions_by_module, qualnames)."""
    modules = {}
    for module in index.get("modules") or []:
        modules.setdefault(module["path"], module)
    definitions_by_module = {}
    qualnames = {}
    for module, row in modules.items():
        items = []
        for d in row.get("definitions") or []:
            record = {
                "module": module,
                "qualname": d["qualname"],
                "name": d["name"],
                "kind": d["kind"],
                "lineno": d["lineno"],
                "line_end": d.get("end_lineno", d["lineno"]),
                "static": bool(d.get("static")),
                "signature": d.get("signature") or "",
                "bases": list(d.get("bases") or []),
                "docstring": d.get("docstring") or "",
            }
            items.append(record)
            qualnames.setdefault(d["qualname"], []).append(record)
        definitions_by_module[module] = sorted(items, key=lambda r: (r["lineno"], r["qualname"]))
    return index, modules, definitions_by_module, qualnames


def _load_index(repo, source_abs, work, cached_index_path=None):
    """The semantic symbol index, built fresh by the sibling adapter
    (identical delegation pattern to the change-impact capability), or a
    validated cache artifact (optional ``index_path`` input).  Cache law:
    published schema, nonzero totals, exact source_root match.  Fresh and
    cached paths share one materialization, so results are identical."""
    if cached_index_path is not None:
        try:
            artifact = json.loads(Path(cached_index_path).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            _systemic(f"cached index unreadable: {type(exc).__name__}")
        if artifact.get("schema") != "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1" or int(
            (artifact.get("totals") or {}).get("files", 0)
        ) <= 0:
            _systemic("cached index invalid: schema or totals mismatch")
        want = str(source_abs.relative_to(repo)).replace("\\", "/")
        if str(artifact.get("source_root")) != want:
            _systemic("cached index invalid: source_root mismatch")
        from canonical.runtime.bound_capabilities.python_source_symbol_index import validate_cached_index
        try:
            validate_cached_index(repo, source_abs, artifact)
        except (RuntimeError, OSError) as exc:
            _systemic(str(exc))
        return _materialize(artifact)
    import importlib.util
    import pathlib as _plib
    spec = importlib.util.spec_from_file_location(
        "python_source_symbol_index_sibling",
        _plib.Path(__file__).with_name("python_source_symbol_index.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tmp = work / ".symbol_resolve_index.json"
    module.run(
        {"source_root": str(source_abs.relative_to(repo)), "output_path": str(tmp)},
        str(repo),
    )
    index = json.loads(tmp.read_text(encoding="utf-8"))
    return _materialize(index)


def _import_rows(module_row):
    """name -> (module, imported_name, kind) for covenient lookup."""
    rows = {}
    for imp in module_row.get("imports") or []:
        base = str(imp.get("module") or "")
        names = [str(n) for n in imp.get("names") or []]
        form = str(imp.get("form") or "")
        if form == "from":
            for name in names:
                rows[name] = (base, name, "from")
        else:
            # ``import pkg.mod`` binds the dotted root name in module scope
            root = base.split(".", 1)[0]
            rows.setdefault(root, (base, root, "import"))
            rows.setdefault(base, (base, base, "import"))
    return rows


def _resolve_in_module(index, modules, definitions_by_module, qualnames_by_qual, module_path, line, name):
    """Single name resolution with scope-first precedence."""
    module_row = modules.get(module_path)
    if module_row is None:
        return {
            "status": "UNRESOLVED",
            "reason": "MODULE_NOT_IN_INDEX",
            "definitions": [],
            "resolved_from": None,
        }
    if line is not None:
        defs = definitions_by_module[module_path]
        # enclosing scopes (outermost first)
        enclosing = [d for d in defs if d["lineno"] <= line <= d["line_end"]]
        enclosing.sort(key=lambda d: d["lineno"])
        cls = next((d for d in reversed(enclosing) if d["kind"] == "class"), None)
        # class attributes / methods first for a bare name used inside a class body
        if cls is not None:
            cells = qualnames_by_qual.get(cls["qualname"] + "." + name) or []
            cells = [c for c in cells if c["module"] == module_path]
            if cells:
                return {
                    "status": "RESOLVED",
                    "reason": None,
                    "definitions": sorted(cells, key=lambda r: (r["module"], r["lineno"], r["qualname"])),
                    "resolved_from": "CLASS_SCOPE",
                }
        # then module scope (the enclosing function's own module)
        for d in definitions_by_module[module_path]:
            if d["name"] == name and d["qualname"].count(".") == 0:
                return {
                    "status": "RESOLVED",
                    "reason": None,
                    "definitions": [d],
                    "resolved_from": "MODULE_SCOPE",
                }
        # import alias:  from X import name / import pkg as name
        imports = _import_rows(module_row)
        if name in imports:
            base, original, form = imports[name]
            target = None
            for cand, mod in (modules.items()):
                dot = _dotted(cand)
                if dot == base or dot.endswith("." + base):
                    target = cand
                    break
            if target is None:
                return {
                    "status": "EXTERNAL",
                    "reason": "IMPORT_TARGET_NOT_IN_INDEX",
                    "definitions": [],
                    "resolved_from": "IMPORT",
                    "import_from": base,
                }
            if form == "from":
                # resolve the imported name inside the target module
                inner = _resolve_in_module(index, modules, definitions_by_module, qualnames_by_qual, target, None, original)
                if inner["status"] == "RESOLVED":
                    inner = dict(inner)
                    inner["resolved_from"] = "IMPORT_ALIAS:" + target
                    return inner
                return {
                    "status": "UNRESOLVED",
                    "reason": "IMPORT_NAME_NOT_FOUND_IN_TARGET",
                    "definitions": [],
                    "resolved_from": "IMPORT",
                    "import_from": target,
                }
            # plain ``import x`` — name refers to the module itself
            return {
                "status": "RESOLVED",
                "reason": None,
                "definitions": [],
                "resolved_from": "IMPORT_MODULE:" + target,
                "import_from": target,
            }
        # last: any module that defines the bare name (MULTI_HOME is honest)
        global_hit = _resolve_bare_name_globally(definitions_by_module, name)
        if global_hit is not None:
            return global_hit
        return {
            "status": "UNRESOLVED",
            "reason": "NAME_NOT_FOUND_IN_MODULE_SCOPE_OR_IMPORTS",
            "definitions": [],
            "resolved_from": None,
        }
    # no line → module-level lookup only (definition qualified by module name)
    for d in definitions_by_module[module_path]:
        if d["name"] == name and d["qualname"].count(".") == 0:
            return {"status": "RESOLVED", "reason": None, "definitions": [d], "resolved_from": "MODULE_SCOPE"}
    return {
        "status": "UNRESOLVED",
        "reason": "MODULE_LEVEL_NAME_NOT_FOUND",
        "definitions": [],
        "resolved_from": None,
    }


def _resolve_dotted_reference(index, modules, definitions_by_module, qualnames_by_qual, reference):
    """Walk ``pkg.mod.Class.attr`` through the module tree truthfully."""
    parts = reference.split(".")
    if len(parts) < 1 or not parts[0]:
        return {"status": "UNRESOLVED", "reason": "EMPTY_REFERENCE", "definitions": [], "resolved_from": None}
    # longest dotted prefix that matches an indexed module path
    prefix = reference
    anchor = None
    while prefix:
        candidates = [p for p in modules if _dotted(p) == prefix]
        if candidates:
            anchor = candidates[0]
            break
        if "." not in prefix:
            break
        prefix = prefix.rsplit(".", 1)[0]
    if anchor is None:
        return {"status": "UNRESOLVED", "reason": "REFERENCE_ROOT_NOT_IN_INDEX", "definitions": [], "resolved_from": None}
    dot = _dotted(anchor)
    remaining = parts[len(dot.split(".")):]
    current_module = anchor
    current_qual = None
    current_row = None
    current_defs = definitions_by_module[current_module]
    for hop in remaining:
        if current_qual is None:
            module_hits = [d for d in current_defs if d["name"] == hop and d["qualname"].count(".") == 0]
        else:
            module_hits = [d for d in current_defs if d["qualname"] == current_qual + "." + hop]
        module_hits = sorted(module_hits, key=lambda r: (r["module"], r["lineno"], r["qualname"]))
        if not module_hits:
            return {"status": "UNRESOLVED", "reason": "ATTRIBUTE_NOT_FOUND:" + hop, "definitions": [], "resolved_from": None}
        if len(module_hits) > 1:
            return {"status": "MULTI_HOME", "reason": "AMBIGUOUS_ATTRIBUTE:" + hop, "definitions": module_hits, "resolved_from": None}
        current_row = module_hits[0]
        current_qual = current_row["qualname"]
    if current_row is None:
        # the reference named a module exactly — resolve to the module itself
        return {
            "status": "RESOLVED",
            "reason": None,
            "definitions": [],
            "resolved_from": "DOTTED_MODULE",
            "import_from": anchor,
        }
    return {"status": "RESOLVED", "reason": None, "definitions": [current_row], "resolved_from": "DOTTED_REFERENCE"}


def _resolve_bare_name_globally(definitions_by_module, name):
    """Every module that defines this bare name at module scope.

    One definition is RESOLVED, several is MULTI_HOME with all of them listed,
    and nothing found returns None so the caller can keep its own reason. This
    is the never-miss over-approximation the module docstring promises: a name
    defined in three places is reported as three, never as the first hit.
    """
    hits = []
    for cand_path, defs in definitions_by_module.items():
        for d in defs:
            if d["name"] == name and d["qualname"].count(".") == 0:
                hits.append(d)
    hits = sorted(hits, key=lambda r: (r["module"], r["lineno"], r["qualname"]))
    if len(hits) == 1:
        return {
            "status": "RESOLVED",
            "reason": "RESOLVED_VIA_GLOBAL_NAME_FALLBACK",
            "definitions": hits,
            "resolved_from": "GLOBAL_BY_BARE_NAME",
        }
    if hits:
        return {
            "status": "MULTI_HOME",
            "reason": "AMBIGUOUS_BARE_NAME_FALLBACK",
            "definitions": hits,
            "resolved_from": None,
        }
    return None


def _builtin_lookup(name):
    import builtins
    return {"status": "BUILTIN", "reason": None, "definitions": [], "resolved_from": "BUILTIN"} if hasattr(builtins, name) else None


def build_resolution(source_root, queries, root, cached_index_path=None):
    """Build the resolution artifact rows."""
    import shutil
    import tempfile
    repo = Path(root).resolve()
    source_abs = (repo / source_root).resolve()
    work = Path(tempfile.mkdtemp(dir=str(repo), prefix=".symbol_resolve_work_"))
    try:
        index, modules, definitions_by_module, qualnames_by_qual = _load_index(repo, source_abs, work, cached_index_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    rows = []
    for q in queries:
        if "reference" in q:
            ref = str(q.get("reference") or "")
            res = _resolve_dotted_reference(index, modules, definitions_by_module, qualnames_by_qual, ref)
            rows.append({
                "schema": ARTIFACT_SCHEMA,
                "query": {"reference": ref},
                "source_root": source_root,
                "status": res["status"],
                "resolved_from": res.get("resolved_from"),
                "reason": res.get("reason"),
                "definitions": res["definitions"],
            })
            continue
        module = str(q.get("module") or "")
        line = q.get("line")
        if line is not None:
            line = int(line)
        name = str(q.get("name") or "")
        if not module:
            # A bare name: search every module in the tree. One definition is
            # RESOLVED, several is MULTI_HOME with all of them, none is
            # UNRESOLVED with a truthful reason. Nothing is guessed.
            if not name:
                return _fail_row(q, "NAME_REQUIRED")
            builtin = _builtin_lookup(name)
            res = _resolve_bare_name_globally(definitions_by_module, name)
            if res is None:
                res = builtin or {
                    "status": "UNRESOLVED",
                    "reason": "NAME_NOT_DEFINED_IN_SOURCE_ROOT",
                    "definitions": [],
                    "resolved_from": None,
                }
            rows.append({
                "schema": ARTIFACT_SCHEMA,
                "query": {"name": name},
                "source_root": source_root,
                "status": res["status"],
                "resolved_from": res.get("resolved_from"),
                "reason": res.get("reason"),
                "definitions": res["definitions"],
            })
            continue
        if not name:
            return _fail_row(q, "MODULE_AND_NAME_REQUIRED")
        if module not in modules:
            rows.append({
                "schema": ARTIFACT_SCHEMA, "query": q, "source_root": source_root,
                "status": "UNRESOLVED", "resolved_from": None, "reason": "MODULE_NOT_IN_INDEX", "definitions": [],
            })
            continue
        builtin = _builtin_lookup(name)
        res = _resolve_in_module(index, modules, definitions_by_module, qualnames_by_qual, module, line, name)
        if res["status"] == "UNRESOLVED" and builtin is not None:
            res = builtin
        rows.append({
            "schema": ARTIFACT_SCHEMA,
            "query": {"module": module, "line": line, "name": name},
            "source_root": source_root,
            "status": res["status"],
            "resolved_from": res.get("resolved_from"),
            "reason": res.get("reason"),
            "import_from": res.get("import_from"),
            "definitions": res["definitions"],
        })
    by_status = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "capability_id": CAPABILITY_ID,
        "source_root": source_root,
        "query_count": len(queries),
        "resolved_count": by_status.get("RESOLVED", 0),
        "multi_home_count": by_status.get("MULTI_HOME", 0),
        "external_count": by_status.get("EXTERNAL", 0),
        "builtin_count": by_status.get("BUILTIN", 0),
        "unresolved_count": by_status.get("UNRESOLVED", 0),
        "results": sorted(rows, key=lambda r: json.dumps(r, sort_keys=True)),
    }
    return artifact


def _fail_row(q, reason):
    return {
        "schema": ARTIFACT_SCHEMA, "query": q, "source_root": None,
        "status": "UNRESOLVED", "resolved_from": None, "reason": reason, "definitions": [],
    }


def _queries_from_raw(raw):
    """Accept every way one resolution question can be written.

    The binder hands this adapter what the sentence said. "Resolve the symbol
    top" binds a bare name; "for the queries top leaf" binds a phrase. Both are
    the same question the JSON array form asks, and refusing them meant the
    capability was selected correctly and then died on ``json.loads`` --
    measured: ``JSONDecodeError: Expecting value: line 1 column 1`` on a
    perfectly good binding.

    A bare name is a whole-tree resolution: which file and which definition does
    this name come from. That is exactly what the adapter promises, and it is
    the one form a sentence can supply without also naming a module and a line.
    """
    if isinstance(raw, str):
        raw = [part for part in re.split(r"[,;]\s*|\s+", raw.strip()) if part]
    if not isinstance(raw, list) or not raw:
        _systemic("queries must be a non-empty JSON array or a non-empty list of names")
    out = []
    for q in raw:
        if isinstance(q, str):
            name = q.strip()
            if not name:
                _systemic("each query must name something")
            out.append({"name": name})
            continue
        if not isinstance(q, dict):
            _systemic("each query must be an object or a name")
        if "reference" in q:
            out.append({"reference": str(q["reference"])})
        elif "module" in q and "name" in q:
            out.append({"module": str(q["module"]), "line": q.get("line"), "name": str(q["name"])})
        elif "name" in q:
            out.append({"name": str(q["name"])})
        else:
            _systemic("each query must use `reference`, `name`, or (`module`, `name`)")
    return out


def run(args, root):
    args = dict(args or {})
    source_root = str(args.get("source_root") or ".")
    output_path = _safe_path(root, args.get("output_path"),
                             allow_overwrite=_is_machine_spool(args.get("output_path")))
    source_abs = _safe_path(root, source_root, allow_overwrite=True)
    if not source_abs.is_dir():
        _systemic(f"source_root does not exist: {source_root}")
    if output_path.is_dir():
        _systemic("output_path must be a file")
    raw_queries = args.get("queries")
    if raw_queries is None:
        _systemic("queries input is required")
    if isinstance(raw_queries, str):
        stripped = raw_queries.strip()
        try:
            raw_queries = json.loads(stripped)
        except ValueError:
            # Not JSON: the sentence stated the names directly. That is a
            # binding, not an error -- _queries_from_raw takes it apart.
            raw_queries = stripped
    queries = _queries_from_raw(raw_queries)
    cached_index_path = None
    if args.get("index_path"):
        candidate = _safe_path(root, str(args["index_path"]), allow_overwrite=True)
        if not candidate.is_file():
            _systemic("index_path does not exist: " + str(args["index_path"]))
        cached_index_path = candidate
    artifact = build_resolution(source_root, queries, root, cached_index_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    output_path.write_text(text, encoding="utf-8")
    sha = _sha256_text(text)
    reread = json.loads(output_path.read_text(encoding="utf-8"))
    verified = reread == artifact
    return {
        "adapter": "python_symbol_resolve",
        "output_path": str(args.get("output_path")),
        "output_sha256": sha,
        "output_verified": verified,
        "query_count": artifact["query_count"],
        "resolved_count": artifact["resolved_count"],
        "multi_home_count": artifact["multi_home_count"],
        "external_count": artifact["external_count"],
        "unresolved_count": artifact["unresolved_count"],
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source_root", default=".")
    p.add_argument("--output_path", required=True)
    p.add_argument("--queries", required=True)
    ns = p.parse_args()
    result = run({"source_root": ns.source_root, "output_path": ns.output_path, "queries": ns.queries}, str(Path.cwd()))
    print(json.dumps(result, indent=2))
