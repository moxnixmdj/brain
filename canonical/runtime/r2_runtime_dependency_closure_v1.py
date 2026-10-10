"""Deterministic canonical.runtime import-closure binding for R2 dynamic routes V1."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_R2_RUNTIME_IMPORT_CLOSURE_V1"
_SHA40=re.compile(r"^[0-9a-f]{40}$")


class RuntimeClosureError(ValueError):
    pass


def git_blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def _inside(root:Path,rel:str)->Path:
    p=Path(str(rel or "").strip())
    if not str(rel or "").strip() or p.is_absolute() or ".." in p.parts:
        raise RuntimeClosureError("RUNTIME_CLOSURE_PATH_INVALID")
    if not p.as_posix().startswith("canonical/runtime/"):
        raise RuntimeClosureError("RUNTIME_CLOSURE_PATH_OUTSIDE_RUNTIME:"+p.as_posix())
    full=(root/p).resolve(); rr=root.resolve()
    if full==rr or rr not in full.parents or not full.is_file():
        raise RuntimeClosureError("RUNTIME_CLOSURE_FILE_MISSING:"+p.as_posix())
    return full


def _module_path(root:Path,name:str)->str|None:
    if name=="canonical.runtime":
        rel="canonical/runtime/__init__.py"
        return rel if (root/rel).is_file() else None
    if not name.startswith("canonical.runtime."):
        return None
    suffix=name[len("canonical.runtime."):].replace(".","/")
    for rel in (
        "canonical/runtime/"+suffix+".py",
        "canonical/runtime/"+suffix+"/__init__.py",
    ):
        if (root/rel).is_file():
            return rel
    return None


def _package_parts(rel:str)->list[str]:
    p=Path(rel)
    parts=list(p.parts)
    if parts[:2]!=["canonical","runtime"] or p.suffix!=".py":
        raise RuntimeClosureError("RUNTIME_CLOSURE_SOURCE_INVALID:"+rel)
    return parts[:-1]


def _targets(root:Path,rel:str)->list[str]:
    path=_inside(root,rel)
    try:
        tree=ast.parse(path.read_text(encoding="utf-8"),filename=rel)
    except Exception as exc:
        raise RuntimeClosureError("RUNTIME_IMPORT_PARSE_FAILED:"+rel) from exc
    package=_package_parts(rel)
    out:set[str]=set()

    def add(name:str,required:bool=True)->None:
        if not name.startswith("canonical.runtime"):
            return
        resolved=_module_path(root,name)
        if resolved is None:
            if required:
                raise RuntimeClosureError(
                    "RUNTIME_IMPORT_MODULE_UNRESOLVED:"+rel+":"+name
                )
            init=_module_path(root,"canonical.runtime")
            if init is not None: out.add(init)
            return
        out.add(resolved)

    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for alias in node.names:
                if alias.name.startswith("canonical.runtime"):
                    add(alias.name)
        elif isinstance(node,ast.ImportFrom):
            if any(alias.name=="*" for alias in node.names):
                if str(node.module or "").startswith("canonical.runtime") or node.level:
                    raise RuntimeClosureError("RUNTIME_STAR_IMPORT_UNSUPPORTED:"+rel)
            if node.level==0:
                base=str(node.module or "")
            else:
                drop=node.level-1
                if drop>len(package): continue
                parts=package[:len(package)-drop]
                if node.module: parts+=str(node.module).split(".")
                base=".".join(parts)
            if base=="canonical.runtime":
                # canonical.runtime may be a namespace package with no __init__.py.
                # The package object itself contributes no file blob in that case.
                add(base,required=False)
                for alias in node.names:
                    add(base+"."+alias.name,required=False)
            elif base.startswith("canonical.runtime."):
                add(base)
        elif isinstance(node,ast.Call):
            name=None
            if isinstance(node.func,ast.Name):
                name=node.func.id
            elif isinstance(node.func,ast.Attribute):
                name=node.func.attr
            if name not in {"import_module"}:
                continue
            if not node.args or not isinstance(node.args[0],ast.Constant) or not isinstance(node.args[0].value,str):
                raise RuntimeClosureError("RUNTIME_DYNAMIC_IMPORT_UNRESOLVED:"+rel)
            add(node.args[0].value,required=True)
    return sorted(out)


def build(root:Path,runtime_path:str)->dict[str,Any]:
    root=Path(root).resolve()
    start=str(runtime_path or "").strip()
    _inside(root,start)
    queue=[start]; seen:set[str]=set(); rows=[]
    while queue:
        rel=queue.pop(0)
        if rel in seen: continue
        seen.add(rel)
        rows.append({"path":rel,"git_blob_sha":git_blob_sha(_inside(root,rel))})
        for dep in _targets(root,rel):
            if dep not in seen and dep not in queue: queue.append(dep)
    rows.sort(key=lambda x:x["path"])
    return {
        "schema":SCHEMA,
        "root_runtime_path":start,
        "file_count":len(rows),
        "files":rows,
    }


def validate(root:Path,runtime_path:str,raw:Any)->dict[str,Any]:
    if not isinstance(raw,Mapping):
        raise RuntimeClosureError("RUNTIME_DEPENDENCY_CLOSURE_REQUIRED")
    if raw.get("schema")!=SCHEMA:
        raise RuntimeClosureError("RUNTIME_DEPENDENCY_CLOSURE_SCHEMA_INVALID")
    if raw.get("root_runtime_path")!=runtime_path:
        raise RuntimeClosureError("RUNTIME_DEPENDENCY_CLOSURE_ROOT_MISMATCH")
    rows=raw.get("files")
    if not isinstance(rows,list) or not rows or raw.get("file_count")!=len(rows):
        raise RuntimeClosureError("RUNTIME_DEPENDENCY_CLOSURE_FILES_INVALID")
    pinned={}
    for row in rows:
        if not isinstance(row,Mapping):
            raise RuntimeClosureError("RUNTIME_DEPENDENCY_CLOSURE_ROW_INVALID")
        rel=str(row.get("path") or "").strip()
        sha=str(row.get("git_blob_sha") or "").strip().lower()
        if rel in pinned or not _SHA40.fullmatch(sha):
            raise RuntimeClosureError("RUNTIME_DEPENDENCY_CLOSURE_ROW_INVALID:"+rel)
        _inside(Path(root).resolve(),rel)
        pinned[rel]=sha

    current=build(Path(root),runtime_path)
    observed={x["path"]:x["git_blob_sha"] for x in current["files"]}
    if set(pinned)!=set(observed):
        raise RuntimeClosureError(
            "RUNTIME_DEPENDENCY_GRAPH_DRIFT:ADDED="
            +",".join(sorted(set(observed)-set(pinned)))
            +";REMOVED="+",".join(sorted(set(pinned)-set(observed)))
        )
    for rel in sorted(pinned):
        if pinned[rel]!=observed[rel]:
            raise RuntimeClosureError(
                "RUNTIME_DEPENDENCY_BLOB_DRIFT:"+rel+":"+pinned[rel]+"!="+observed[rel]
            )
    return current
