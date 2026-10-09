"""Content-addressed bound-capability material compiler for D-finality V1.

This compiler grants no D-finality or ownership credit. It derives a conservative
repository-owned material candidate for one bound capability by combining:
- the canonical bound registry;
- D epoch / universal invocation / bound executor roots;
- the selected adapter;
- transitive canonical Python imports;
- literal sibling Python files loaded through Path.with_name("*.py").

Non-canonical imports and external package/tool requirements remain declared
substrate/material obligations. Unresolved dynamic-load indicators remain OPEN.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.brain_owned_python_closure_census_v1 import census
from canonical.runtime.d_finality_execution_epoch_v1 import material_closure_root

SCHEMA = "PROJECT_BRAIN_D_FINALITY_BOUND_MATERIAL_COMPILER_V1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

SHARED_ROOTS = (
    "canonical/runtime/d_finality_execution_epoch_v1.py",
    "canonical/runtime/live_capability_invoker_v1.py",
    "canonical/runtime/verified_bound_capability_execution_adapter_v1.py",
    "canonical/runtime/astra_runtime.py",
)


class MaterialCompileError(ValueError):
    pass


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _safe_rel(root: Path, raw: str) -> Path:
    rel = str(raw or "").strip()
    p = Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise MaterialCompileError("NONCANONICAL_PATH:" + rel)
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError as exc:
        raise MaterialCompileError("PATH_OUTSIDE_REPO:" + rel) from exc
    if not full.is_file():
        raise MaterialCompileError("FILE_MISSING:" + rel)
    return full


def _literal_sibling_loads(path: Path) -> tuple[list[Path], list[str]]:
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        raise MaterialCompileError("PYTHON_PARSE_FAILED:" + str(path)) from exc
    targets: list[Path] = []
    unresolved: list[str] = []
    has_dynamic_loader = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute) and fn.attr == "spec_from_file_location":
            has_dynamic_loader = True
        if isinstance(fn, ast.Attribute) and fn.attr == "with_name":
            if len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
                raw = node.args[0].value
                if isinstance(raw, str) and raw.endswith(".py"):
                    target = path.with_name(raw).resolve()
                    if target.is_file():
                        targets.append(target)
                    else:
                        unresolved.append("LITERAL_SIBLING_MISSING:" + raw)
    if has_dynamic_loader and not targets:
        unresolved.append("DYNAMIC_LOADER_WITHOUT_LITERAL_SIBLING_TARGET")
    unique = sorted(set(targets), key=lambda p: str(p))
    return unique, sorted(set(unresolved))


def _load_registry(root: Path) -> tuple[Path, Mapping[str, Any], Mapping[str, Any]]:
    path = _safe_rel(root, "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise MaterialCompileError("BOUND_REGISTRY_INVALID")
    caps = doc.get("capabilities")
    if not isinstance(caps, Mapping):
        raise MaterialCompileError("BOUND_REGISTRY_CAPABILITIES_INVALID")
    return path, doc, caps


def _source_obligations(source: Mapping[str, Any]) -> dict[str, Any]:
    typ = str(source.get("type") or "").strip()
    out: dict[str, Any] = {"source_type": typ or None}
    if typ == "python_stdlib":
        modules = source.get("modules")
        if modules is None:
            one = str(source.get("module") or "").strip()
            modules = [one] if one else []
        out["declared_python_stdlib_modules"] = sorted(str(x) for x in modules if str(x))
        out["external_material_required"] = False
    elif typ == "system_tool":
        out["executable"] = source.get("executable")
        out["external_material_required"] = True
    elif typ in {"apt", "pypi", "npm", "git_source_tree"}:
        out["external_material_required"] = True
        out["source_record"] = dict(source)
    elif typ:
        out["external_material_required"] = True
        out["source_record"] = dict(source)
    else:
        out["external_material_required"] = False
    return out


def compile_candidate(
    capability_id: str,
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cid = str(capability_id or "").strip()
    if not cid:
        raise MaterialCompileError("CAPABILITY_ID_REQUIRED")

    registry_path, _registry_doc, caps = _load_registry(root)
    entry = caps.get(cid)
    if not isinstance(entry, Mapping):
        raise MaterialCompileError("BOUND_CAPABILITY_UNKNOWN:" + cid)
    if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise MaterialCompileError("BOUND_CAPABILITY_NOT_VERIFIED:" + cid)
    if float(entry.get("incremental_spend_usd", 0)) != 0:
        raise MaterialCompileError("BOUND_CAPABILITY_NONZERO_COST:" + cid)

    module_name = str(entry.get("adapter_module") or "").strip()
    if not module_name or not module_name.replace("_", "").isalnum():
        raise MaterialCompileError("ADAPTER_MODULE_INVALID")
    adapter_rel = "canonical/runtime/bound_capabilities/" + module_name + ".py"
    adapter_path = _safe_rel(root, adapter_rel)

    roots = list(SHARED_ROOTS) + [adapter_rel]
    closure = census(root, roots)
    python_paths = {
        str(row["path"])
        for row in closure["brain_owned_transitive_files"]
        if isinstance(row, Mapping)
    }

    dynamic_targets: set[str] = set()
    unresolved_dynamic: list[str] = []
    queue = [root / rel for rel in sorted(python_paths)]
    scanned: set[str] = set()
    while queue:
        path = queue.pop(0).resolve()
        rel = path.relative_to(root).as_posix()
        if rel in scanned:
            continue
        scanned.add(rel)
        targets, unresolved = _literal_sibling_loads(path)
        unresolved_dynamic.extend(rel + ":" + x for x in unresolved)
        for target in targets:
            try:
                target_rel = target.relative_to(root).as_posix()
            except ValueError as exc:
                raise MaterialCompileError("DYNAMIC_TARGET_OUTSIDE_REPO:" + str(target)) from exc
            if target_rel not in python_paths:
                extra = census(root, [target_rel])
                for row in extra["brain_owned_transitive_files"]:
                    p = str(row["path"])
                    if p not in python_paths:
                        python_paths.add(p)
                        queue.append(root / p)
                closure["external_or_stdlib_substrate_imports"] = sorted(
                    set(closure["external_or_stdlib_substrate_imports"])
                    | set(extra["external_or_stdlib_substrate_imports"])
                )
            dynamic_targets.add(target_rel)

    material_paths = sorted(python_paths | {registry_path.relative_to(root).as_posix()})
    materials = []
    for rel in material_paths:
        raw = _safe_rel(root, rel).read_bytes()
        materials.append({"path": rel, "git_blob_sha": _git_blob_sha(raw)})

    source = entry.get("source") or {}
    if not isinstance(source, Mapping):
        raise MaterialCompileError("BOUND_SOURCE_NOT_OBJECT")

    text = adapter_path.read_text(encoding="utf-8")
    signals = {
        "network_surface_detected": any(
            token in text for token in ("urllib.request", "urlopen(", "socket.", "http.client")
        ),
        "subprocess_surface_detected": any(
            token in text for token in ("subprocess.", "os.system(", "Popen(")
        ),
        "dynamic_literal_target_count": len(dynamic_targets),
        "unresolved_dynamic_load_count": len(set(unresolved_dynamic)),
    }

    return {
        "schema": SCHEMA,
        "status": (
            "MATERIAL_CLOSURE_CANDIDATE_COMPILED"
            if not unresolved_dynamic
            else "OPEN__UNRESOLVED_DYNAMIC_LOAD"
        ),
        "capability_id": cid,
        "registry_entry_sha256": hashlib.sha256(
            json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "adapter_module": module_name,
        "adapter_path": adapter_rel,
        "adapter_git_blob_sha": next(
            row["git_blob_sha"] for row in materials if row["path"] == adapter_rel
        ),
        "shared_executor_roots": list(SHARED_ROOTS),
        "material_count": len(materials),
        "materials": materials,
        "material_closure_root": material_closure_root(materials),
        "brain_owned_python_file_count": len(python_paths),
        "dynamic_literal_targets": sorted(dynamic_targets),
        "unresolved_dynamic_loads": sorted(set(unresolved_dynamic)),
        "external_or_stdlib_substrate_imports": sorted(
            closure["external_or_stdlib_substrate_imports"]
        ),
        "source_obligations": _source_obligations(source),
        "signals": signals,
        "d_finality_authority": False,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
