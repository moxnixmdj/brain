# PROJECT_BRAIN
"""python.source.crossfile_edit.choreograph.v1 — plan cross-file edits.

"Rename this function everywhere it is truly used" is the single highest
leverage edit a software engineer makes, and the one grep gets wrong.  This
adapter produces a deterministic edit PLAN (it does not mutate sources):
every site that a checked-in change must touch, each with the evidence for
why it is in the plan.

* input ``edits``: JSON array of edit ops.  v1 ops:
  ``{"op": "rename_symbol", "module": "pkg/a.py", "name": "helper",
    "new_name": "compute"}``
  ``{"op": "move_symbol", "module": "pkg/a.py", "qualname": "helper",
    "to_module": "pkg/b.py"}``
* for each op the plan contains SITE rows:
  - DEFINITION — the def/class line range in the defining module.
  - IMPORT_SITE — ``from X import name`` lines in modules that import the
    symbol (name-scoped: aliased imports are not invisible — the index
    loses ``asname``, so a module whose source text contains the old name
    token but whose import row cannot be classified becomes AMBIGUOUS).
  - REFERENCE — every reference row whose resolution proves it binds to the
    target (module-scope in the defining module, or module-scope in a
    module that from-imports it), with the exact ``(lineno, col)``.
  - AMBIGUOUS_SITE — unknown-resolution references with the same bare name,
    and plain-import modules whose raw source text carries ``.name``:
    never-miss means they are listed, never silently dropped.
* collision law: renaming to a name that already binds at module scope in
  the defining module, or is from-imported (unaliased) by any module that
  would pick up the rename, REFUSES the op with evidence.  A plan with a
  refused op still reports the other ops; refused count is in the result.
* completeness is claimed only when ambiguous_site_count == 0; otherwise
  ``complete: false`` — truthful over-approximation of risk, never silence.
* cache law: ``index_path`` may point at a previously built symbol-index
  artifact; its schema, source scope, file membership and source hashes are
  validated before its semantic records are reused.
  The plan artifact is byte-identical whether the index was fresh-built or
  cached (pin-proven); ``cache_used`` is only in the run() result.

Adapter lanes: run() returns registry ``result_fields``.  Refused inputs
(bad shape, path escape, unknown op) raise SystemExit with a JSON error.
Zero spend, everything local.
"""
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

CAPABILITY_ID = "python.source.crossfile_edit.choreograph.v1"
ARTIFACT_SCHEMA = "PROJECT_BRAIN_CROSSFILE_EDIT_PLAN_V1"
INDEX_SCHEMA = "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1"
ADAPTER_ERROR = "EDIT_PLAN_INPUT_INVALID"
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _systemic(message):
    print(json.dumps({"error": ADAPTER_ERROR, "error_kind": "systemic", "message": message}))
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


def _safe_path(root, value, allow_overwrite=False, must_exist=False):
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
    if must_exist and not resolved.exists():
        _systemic(f"input does not exist: {value}")
    if not allow_overwrite and not must_exist and resolved.exists():
        _systemic(f"output already exists: {value}")
    return resolved


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dotted(rel):
    rel = rel.replace("\\", "/")
    if rel.endswith(".py"):
        rel = rel[:-3]
    rel = rel.replace("/__init__", "")
    return rel.replace("/", ".")


# ---------------------------------------------------------------------------
# index load: fresh sibling build OR validated cache
# ---------------------------------------------------------------------------

def _load_index(repo, source_abs, cached_index_path, source_root):
    """(index_artifact, cache_used).  Fresh build replays the sibling
    adapter exactly as the change-impact capability does; a cache must carry
    the published schema, nonzero totals, AND the exact requested
    source_root (a cache misdescribing the tree it measured is worse than
    no cache)."""
    if cached_index_path is not None:
        try:
            artifact = json.loads(cached_index_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - truthfulness beats type lists
            _systemic(f"cached index unreadable: {type(exc).__name__}")
        if artifact.get("schema") != INDEX_SCHEMA or int(
            (artifact.get("totals") or {}).get("files", 0)
        ) <= 0:
            _systemic("cached index invalid: schema or totals mismatch")
        if str(artifact.get("source_root")) != source_root:
            _systemic(
                "cached index invalid: source_root mismatch "
                f"(cache says {artifact.get('source_root')!r}, query wants {source_root!r})"
            )
        from canonical.runtime.bound_capabilities.python_source_symbol_index import validate_cached_index
        try:
            validate_cached_index(repo, source_abs, artifact)
        except (RuntimeError, OSError) as exc:
            _systemic(str(exc))
        return artifact, 1
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "python_source_symbol_index_sibling",
        Path(__file__).with_name("python_source_symbol_index.py"),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    work = Path(tempfile.mkdtemp(dir=str(repo), prefix=".edit_plan_work_"))
    try:
        tmp = work / "index.json"
        module.run(
            {"source_root": str(source_abs.relative_to(repo)),
             "output_path": str(tmp.relative_to(repo))},
            str(repo),
        )
        return json.loads(tmp.read_text(encoding="utf-8")), 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# site finders (never-miss: anything uncertain becomes AMBIGUOUS, not absent)
# ---------------------------------------------------------------------------

def _classify_sites(index, repo, source_abs, module, name):
    """(firm_sites, ambiguous_sites) for a module/name pair.

    firm IMPORT_SITE:   from-import rows whose names contain `name`
                        (unaliased by construction of the site kind).
    firm REFERENCE:     load-references equal to `name` whose module either
                        IS the defining module or from-imports it.
    AMBIGUOUS:          unknown-resolution references of the same bare name;
                        plain-import modules whose raw text contains
                        ``.name``; modules that contain the bare token in
                        their source text (e.g. under an alias the index
                        lost) but produced no firm row.  All carried with a
                        reason.  Nothing is silently dropped."""
    modules = {m["path"]: m for m in index.get("modules") or []}
    defining_dot = _dotted(module)
    firm, ambiguous = [], []

    importers = {}
    for path, row in modules.items():
        for imp in row.get("imports") or []:
            if str(imp.get("form") or "") != "from":
                continue
            base = str(imp.get("module") or "")
            if base == defining_dot or imp.get("module") and defining_dot.endswith(
                "." + str(base)
            ) or str(base).endswith("." + defining_dot):
                if name in [str(n) for n in imp.get("names") or []]:
                    importers.setdefault(path, set()).add(name)

    for path, row in modules.items():
        if path in importers:
            firm.append({
                "file": path, "kind": "IMPORT_SITE", "evidence":
                f"from-import of {name} from {defining_dot}",
            })
        for ref in row.get("references") or []:
            if str(ref.get("name")) != name:
                continue
            resolution = str(ref.get("resolution"))
            if resolution == "module" and (path == module or path in importers):
                firm.append({
                    "file": path, "kind": "REFERENCE",
                    "lineno": int(ref["lineno"]), "col": int(ref["col"]),
                    "context": str(ref.get("context") or ""),
                    "evidence": "module-scope load binds to target",
                })
            elif resolution == "unknown":
                ambiguous.append({
                    "file": path, "kind": "AMBIGUOUS_SITE",
                    "lineno": int(ref["lineno"]), "col": int(ref["col"]),
                    "context": str(ref.get("context") or ""),
                    "reason": "UNKNOWN_RESOLUTION_REFERENCE",
                })
        # plain-import attribute usage that the index cannot see
        imported_plain = any(
            str(imp.get("form")) == "import"
            and (str(imp.get("module")) == defining_dot
                 or str(imp.get("module")).endswith("." + defining_dot)
                 or defining_dot.endswith("." + str(imp.get("module"))))
            for imp in row.get("imports") or []
        )
        if imported_plain and path != module:
            try:
                text = (repo / path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            if re.search(r"\.\s*" + re.escape(name) + r"\b", text):
                ambiguous.append({
                    "file": path, "kind": "AMBIGUOUS_ATTR_USE",
                    "reason": "PLAIN_IMPORT_ATTRIBUTE_TEXT_MATCH",
                })

    firm.sort(key=lambda s: (s["file"], s.get("lineno", 0), s.get("col", 0)))
    ambiguous.sort(key=lambda s: (s["file"], s.get("lineno", 0), s.get("col", 0)))
    return firm, ambiguous


def _module_scope_names(index, module):
    for row in index.get("modules") or []:
        if row["path"] == module:
            return {d["name"] for d in row.get("definitions") or []
                    if str(d["qualname"]).count(".") == 0}
    return None


def _rename_sites(index, repo, source_abs, op):
    module, name, new_name = op["module"], op["name"], op["new_name"]
    scope = _module_scope_names(index, module)
    if scope is None:
        return None, "MODULE_NOT_IN_INDEX:" + module
    if name not in scope:
        return None, "NAME_NOT_AT_MODULE_SCOPE:" + module + ":" + name
    if new_name in scope:
        return None, "NAME_COLLISION_DEFINING_MODULE:" + new_name
    definition = None
    for row in index.get("modules") or []:
        if row["path"] != module:
            continue
        for d in row.get("definitions") or []:
            if d["name"] == name and str(d["qualname"]).count(".") == 0:
                definition = d
                break
    sites = [{
        "file": module, "kind": "DEFINITION",
        "lineno": int(definition["lineno"]), "line_end": int(definition["end_lineno"]),
        "qualname": str(definition["qualname"]), "kind_detail": str(definition["kind"]),
        "evidence": "defining module+def exactly as indexed",
    }]
    firm, ambiguous = _classify_sites(index, repo, source_abs, module, name)
    sites.extend(firm)
    # collision against any module that would pick up the rename
    for site in firm:
        if site["kind"] != "IMPORT_SITE":
            continue
        other = _module_scope_names(index, site["file"]) or set()
        for row in index.get("modules") or []:
            if row["path"] != site["file"]:
                continue
            for imp in row.get("imports") or []:
                if str(imp.get("form")) == "from" and new_name in (
                    str(n) for n in imp.get("names") or []
                ):
                    return None, ("NAME_COLLISION_IMPORTER:" + site["file"] +
                                  ":" + new_name)
        if new_name in other:
            return None, "NAME_COLLISION_IMPORTER_SCOPE:" + site["file"] + ":" + new_name
    return {"sites": sites, "ambiguous": ambiguous}, None


def _move_sites(index, repo, source_abs, op):
    module, qualname, to_module = op["module"], op["qualname"], op["to_module"]
    mods = {row["path"] for row in index.get("modules") or []}
    if module not in mods:
        return None, "MODULE_NOT_IN_INDEX:" + module
    if to_module not in mods:
        return None, "TARGET_MODULE_NOT_IN_INDEX:" + to_module
    definition = None
    for row in index.get("modules") or []:
        if row["path"] == module:
            for d in row.get("definitions") or []:
                if str(d["qualname"]) == qualname:
                    definition = d
    if definition is None:
        return None, "DEFINITION_NOT_FOUND:" + module + ":" + qualname
    target_scope = _module_scope_names(index, to_module) or set()
    if str(definition["name"]) in target_scope:
        return None, "NAME_COLLISION_TARGET_MODULE:" + to_module + ":" + str(definition["name"])
    name = str(definition["name"])
    sites = [{
        "file": module, "kind": "CUT_SPAN",
        "lineno": int(definition["lineno"]), "line_end": int(definition["end_lineno"]),
        "evidence": "definition leaves defining module",
    }, {
        "file": to_module, "kind": "INSERT_SPAN",
        "evidence": "definition inserted at target module end",
    }]
    firm, ambiguous = _classify_sites(index, repo, source_abs, module, name)
    for site in firm:
        if site["kind"] == "IMPORT_SITE":
            sites.append({
                "file": site["file"], "kind": "IMPORT_REWRITE",
                "evidence": f"from {_dotted(module)} import {name} -> from {_dotted(to_module)} import {name}",
            })
        else:
            sites.append(site)
    return {"sites": sites, "ambiguous": ambiguous}, None


OPS = {"rename_symbol": _rename_sites, "move_symbol": _move_sites}


def build_plan(source_root, edits, index, repo, source_abs):
    plans = []
    refused = []
    firm_total = 0
    ambiguous_total = 0
    for op in edits:
        kind = op.get("op")
        handler = OPS.get(kind)
        if handler is None:
            _systemic(f"unknown edit op: {kind}")
        plan, refusal = handler(index, repo, source_abs, op)
        if refusal:
            refused.append({"op": op, "refusal": refusal})
            continue
        firm_total += len(plan["sites"])
        ambiguous_total += len(plan["ambiguous"])
        plans.append({"op": op, "sites": plan["sites"], "ambiguous_sites": plan["ambiguous"]})
    plans.sort(key=lambda p: json.dumps(p["op"], sort_keys=True))
    refused.sort(key=lambda r: json.dumps(r["op"], sort_keys=True))
    affected_files = sorted({
        s["file"] for p in plans for s in p["sites"] + p["ambiguous_sites"]
    })
    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "capability_id": CAPABILITY_ID,
        "source_root": source_root,
        "edit_op_count": len(edits),
        "planned_op_count": len(plans),
        "refused_op_count": len(refused),
        "planned_site_count": firm_total,
        "ambiguous_site_count": ambiguous_total,
        "affected_file_count": len(affected_files),
        "affected_files": affected_files,
        "complete": ambiguous_total == 0,
        "completeness_law": "complete ⟺ zero ambiguous sites; ambiguity is listed, never dropped",
        "plans": plans,
        "refusals": refused,
    }
    return artifact


def run(args, root):
    args = dict(args or {})
    repo = Path(root).resolve()
    source_root = str(args.get("source_root") or ".")
    output_path = _safe_path(str(repo), args.get("output_path"),
                             allow_overwrite=_is_machine_spool(args.get("output_path")))
    source_abs = _safe_path(str(repo), source_root, must_exist=True)
    if not source_abs.is_dir():
        _systemic(f"source_root is not a directory: {source_root}")
    if output_path.is_dir():
        _systemic("output_path must be a file")

    raw_edits = args.get("edits")
    edits_path_raw = args.get("edits_path")
    if (raw_edits is None) == (edits_path_raw is None):
        _systemic("exactly one of edits / edits_path is required")
    if edits_path_raw is not None:
        edits_path = _safe_path(str(repo), edits_path_raw, must_exist=True)
        try:
            raw_edits = json.loads(edits_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            _systemic(f"edits_path unreadable JSON: {type(exc).__name__}")
    elif isinstance(raw_edits, str):
        raw_edits = json.loads(raw_edits)
    if not isinstance(raw_edits, list) or not raw_edits:
        _systemic("edits must be a non-empty JSON array")
    edits = []
    for op in raw_edits:
        if not isinstance(op, dict):
            _systemic("each edit must be an object")
        kind = op.get("op")
        if kind == "rename_symbol":
            module, name, new_name = (str(op.get("module") or ""),
                                      str(op.get("name") or ""),
                                      str(op.get("new_name") or ""))
            if not (module and name and new_name and NAME_RE.match(new_name)):
                _systemic("rename_symbol requires module, name, new_name(identifier)")
            edits.append({"op": kind, "module": module, "name": name, "new_name": new_name})
        elif kind == "move_symbol":
            module, qualname, to_module = (str(op.get("module") or ""),
                                           str(op.get("qualname") or ""),
                                           str(op.get("to_module") or ""))
            if not (module and qualname and to_module):
                _systemic("move_symbol requires module, qualname, to_module")
            edits.append({"op": kind, "module": module, "qualname": qualname,
                          "to_module": to_module})
        else:
            _systemic(f"unknown edit op: {kind}")

    cached_index_path = None
    if args.get("index_path"):
        cached_index_path = _safe_path(str(repo), str(args["index_path"]), must_exist=True)
    index, cache_used = _load_index(repo, source_abs, cached_index_path, source_root)
    artifact = build_plan(source_root, edits, index, repo, source_abs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    output_path.write_text(text, encoding="utf-8")
    sha = _sha256_text(text)
    verified = json.loads(output_path.read_text(encoding="utf-8")) == artifact
    return {
        "adapter": "python_crossfile_edit_choreograph",
        "output_path": str(args.get("output_path")),
        "output_sha256": sha,
        "output_verified": verified,
        "edit_op_count": artifact["edit_op_count"],
        "planned_op_count": artifact["planned_op_count"],
        "refused_op_count": artifact["refused_op_count"],
        "planned_site_count": artifact["planned_site_count"],
        "ambiguous_site_count": artifact["ambiguous_site_count"],
        "affected_file_count": artifact["affected_file_count"],
        "cache_used": cache_used,
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source_root", default=".")
    p.add_argument("--output_path", required=True)
    p.add_argument("--edits", default=None)
    p.add_argument("--edits_path", default=None)
    p.add_argument("--index_path", default=None)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), str(Path.cwd())), indent=2))
