"""Transitive Brain-owned Python capability-closure byte census.

Counts exact source bytes for a selected root plus every recursively imported
module under the canonical.* namespace. Non-canonical imports are reported as
substrate dependencies and excluded from the Brain-owned source-byte total.
"""
from __future__ import annotations
import ast, hashlib
from pathlib import Path

class ClosureCensusError(ValueError): pass

def _module_file(root: Path, module: str) -> Path | None:
    p=root.joinpath(*module.split("."))
    py=p.with_suffix(".py")
    init=p/"__init__.py"
    if py.exists(): return py
    if init.exists(): return init
    return None

def _namespace_package(root: Path, module: str) -> Path | None:
    p=root.joinpath(*module.split("."))
    if p.is_dir() and _module_file(root,module) is None:
        return p
    return None

def _canonical_imports(source: str, root: Path | None = None) -> tuple[set[str], set[str]]:
    tree=ast.parse(source)
    owned=set(); external=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for a in node.names:
                name=a.name
                if name=="canonical" or name.startswith("canonical."):
                    if root is not None and _namespace_package(root,name) is not None:
                        continue
                    owned.add(name)
                else:
                    external.add(name)
        elif isinstance(node,ast.ImportFrom):
            module=node.module or ""
            if module=="canonical" or module.startswith("canonical."):
                resolved_child=False
                if root is not None:
                    for a in node.names:
                        if a.name=="*": continue
                        child=module+"."+a.name
                        if _module_file(root,child) is not None:
                            owned.add(child)
                            resolved_child=True
                        elif _namespace_package(root,child) is not None:
                            resolved_child=True
                if not resolved_child:
                    if module.endswith(".runtime"):
                        for a in node.names:
                            if a.name!="*": owned.add(module+"."+a.name)
                    else:
                        owned.add(module)
            elif module:
                external.add(module)
    return owned,external

def _module_path(root: Path,module: str)->Path:
    found=_module_file(root,module)
    if found is not None: return found
    raise ClosureCensusError("CANONICAL_IMPORT_UNRESOLVED:"+module)

def census(repo_root: str|Path, roots: list[str]) -> dict:
    base=Path(repo_root).resolve()
    queue=[base/r for r in roots]
    seen=set(); rows=[]; external=set()
    while queue:
        p=queue.pop(0).resolve()
        try: rel=p.relative_to(base).as_posix()
        except ValueError as e: raise ClosureCensusError("PATH_OUTSIDE_REPO") from e
        if rel in seen: continue
        if not p.is_file(): raise ClosureCensusError("ROOT_OR_IMPORT_NOT_FILE:"+rel)
        raw=p.read_bytes()
        try: src=raw.decode("utf-8")
        except UnicodeDecodeError as e: raise ClosureCensusError("NON_UTF8_PYTHON:"+rel) from e
        owned,ext=_canonical_imports(src,base)
        seen.add(rel); external.update(ext)
        rows.append({"path":rel,"byte_count":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
        for mod in sorted(owned):
            q=_module_path(base,mod)
            qrel=q.relative_to(base).as_posix()
            if qrel not in seen: queue.append(q)
    rows.sort(key=lambda r:r["path"])
    return {
        "status":"PASS",
        "brain_owned_transitive_files":rows,
        "brain_owned_transitive_source_bytes":sum(r["byte_count"] for r in rows),
        "brain_owned_file_count":len(rows),
        "external_or_stdlib_substrate_imports":sorted(external),
        "substrate_bytes_included":False,
        "warning":"THIS_IS_BRAIN_OWNED_SOURCE_CLOSURE_NOT_TOTAL_MACHINE_RUNTIME_BYTES",
    }
