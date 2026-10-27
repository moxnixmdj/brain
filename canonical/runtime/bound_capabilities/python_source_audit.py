#!/usr/bin/env python3
"""Deterministic repository-local Python source structural audit."""
from __future__ import annotations
import ast, hashlib, json, pathlib

def _safe_root(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if p.is_dir():
        return p
    # "Audit the python file F" and "audit the python source root D" are one
    # question with two scopes. Refusing the first because the caller named a
    # file meant the machine could answer nothing about a single source file --
    # measured, "Count the functions defined in the python file <abs>/calc.py"
    # never reached an adapter at all. The scope stays exactly what the caller
    # named: one file audits one file, never its siblings.
    if p.is_file() and p.suffix == ".py":
        return p
    raise RuntimeError("PYTHON_AUDIT_ROOT_MISSING")


def _py_files(source_root):
    """The files the audit walks: one named file, or every file under a named tree."""
    if source_root.is_file():
        return [source_root]
    return sorted(source_root.rglob("*.py"))

def _imports(tree):
    out=set()
    for node in tree.body:
        if isinstance(node,ast.Import):
            for alias in node.names:
                out.add(alias.name.split(".")[0])
        elif isinstance(node,ast.ImportFrom):
            if node.module:
                out.add(node.module.split(".")[0])
    return sorted(out)

def run(args, root):
    repo=pathlib.Path(root).resolve()
    source_root=_safe_root(repo,args.get("source_root","canonical/runtime"))
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    files=[]
    unparseable=[]
    imports=set()
    total_functions=0
    total_classes=0
    for path in _py_files(source_root):
        if not path.is_file():
            continue
        raw=path.read_bytes()
        try:
            tree=ast.parse(raw.decode("utf-8"),filename=str(path))
        except Exception as exc:
            # AN AUDIT THAT CANNOT REPORT A FINDING IS NOT AN AUDIT.
            #
            # Aborting on the first unparseable file meant a 2078-file tree
            # answered "PYTHON_PARSE_FAILED" and named one path -- the audit
            # had already examined the other 2076 and said nothing about
            # them. The finding is the product; refusing to finish hides it
            # behind an exception that reads like a tool failure. Record the
            # file, keep going, and let the report carry every finding.
            unparseable.append({
                "path":str(path.relative_to(repo)).replace("\\","/"),
                "sha256":hashlib.sha256(raw).hexdigest(),
                "error":type(exc).__name__,
                "detail":str(exc)[:400],
            })
            continue
        functions=sorted(n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)))
        classes=sorted(n.name for n in tree.body if isinstance(n,ast.ClassDef))
        mods=_imports(tree)
        imports.update(mods)
        total_functions+=len(functions)
        total_classes+=len(classes)
        files.append({
            "path":str(path.relative_to(repo)).replace("\\","/"),
            "sha256":hashlib.sha256(raw).hexdigest(),
            "imports":mods,
            "functions":functions,
            "classes":classes,
        })
    if not files and not unparseable:
        raise RuntimeError("PYTHON_AUDIT_EMPTY")
    report={
        "schema":"PROJECT_BRAIN_PYTHON_SOURCE_AUDIT_V1",
        "source_root":str(source_root.relative_to(repo)).replace("\\","/"),
        "files":files,
        "unparseable":unparseable,
        "totals":{
            "files":len(files),
            "unparseable":len(unparseable),
            "functions":total_functions,
            "classes":total_classes,
            "distinct_imported_modules":len(imports),
        },
        "distinct_imported_modules":sorted(imports),
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    data=output.read_bytes()
    return {
        "adapter":"python_source_audit",
        "output_path":str(output.relative_to(repo)).replace("\\","/"),
        "output_sha256":hashlib.sha256(data).hexdigest(),
        "file_count":len(files),
        "unparseable_count":len(unparseable),
        "unparseable_paths":[u["path"] for u in unparseable][:20],
        "function_count":total_functions,
        "class_count":total_classes,
        "distinct_imported_module_count":len(imports),
        "output_verified":True,
    }
