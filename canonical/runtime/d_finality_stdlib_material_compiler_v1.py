"""Route-specific material compiler for D-final stdlib bound capabilities V1.

Unlike the generic conservative compiler, this compiler does not treat every
dormant branch in the multi-purpose Astra runtime as part of a stdlib member's
operative closure.

The certified route is:
  D execution epoch -> D stdlib bound executor -> exact registry row ->
  exact selected adapter -> adapter's actual canonical imports/literal siblings.

The executor's dynamic adapter load is declared by the bound row and therefore
is not an unresolved dynamic-load residual. Dynamic loads originating inside the
selected adapter closure remain fail-closed unless their exact targets are
literal and recursively closed.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.brain_owned_python_closure_census_v1 import census
from canonical.runtime.d_finality_execution_epoch_v1 import material_closure_root

SCHEMA = "PROJECT_BRAIN_D_FINALITY_STDLIB_MATERIAL_COMPILER_V1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_REL = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
EXECUTOR_REL = "canonical/runtime/d_finality_stdlib_bound_executor_v1.py"
EPOCH_REL = "canonical/runtime/d_finality_execution_epoch_v1.py"


class DStdlibMaterialCompileError(ValueError):
    pass


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _safe_file(root: Path, rel: str) -> Path:
    raw = str(rel or "").strip()
    p = Path(raw)
    if not raw or p.is_absolute() or ".." in p.parts:
        raise DStdlibMaterialCompileError("NONCANONICAL_PATH:" + raw)
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError as exc:
        raise DStdlibMaterialCompileError("PATH_OUTSIDE_REPO:" + raw) from exc
    if not full.is_file():
        raise DStdlibMaterialCompileError("FILE_MISSING:" + raw)
    return full


def _load_registry(root: Path) -> tuple[Path, Mapping[str, Any]]:
    path = _safe_file(root, REGISTRY_REL)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(doc, Mapping)
        or doc.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1"
        or not isinstance(doc.get("capabilities"), Mapping)
    ):
        raise DStdlibMaterialCompileError("BOUND_REGISTRY_INVALID")
    return path, doc["capabilities"]


def _literal_sibling_loads(path: Path) -> tuple[list[Path], list[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise DStdlibMaterialCompileError("PYTHON_PARSE_FAILED:" + str(path)) from exc

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
    return sorted(set(targets), key=str), sorted(set(unresolved))


def _declared_stdlib_modules(source: Mapping[str, Any]) -> list[str]:
    raw = source.get("modules")
    if raw is None:
        one = str(source.get("module") or "").strip()
        values = [one] if one else []
    elif isinstance(raw, list):
        values = [str(x or "").strip() for x in raw]
    else:
        raise DStdlibMaterialCompileError("PYTHON_STDLIB_MODULES_INVALID")
    values = sorted(x for x in values if x)
    if not values or len(values) != len(set(values)):
        raise DStdlibMaterialCompileError("PYTHON_STDLIB_MODULES_INVALID")
    return values


def compile_candidate(
    capability_id: str,
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cid = str(capability_id or "").strip()
    if not cid:
        raise DStdlibMaterialCompileError("CAPABILITY_ID_REQUIRED")

    registry_path, caps = _load_registry(root)
    entry = caps.get(cid)
    if not isinstance(entry, Mapping):
        raise DStdlibMaterialCompileError("BOUND_CAPABILITY_UNKNOWN:" + cid)
    if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise DStdlibMaterialCompileError("BOUND_CAPABILITY_NOT_VERIFIED:" + cid)
    if float(entry.get("incremental_spend_usd", 0)) != 0:
        raise DStdlibMaterialCompileError("BOUND_CAPABILITY_NONZERO_COST:" + cid)
    source = entry.get("source")
    if not isinstance(source, Mapping) or source.get("type") != "python_stdlib":
        raise DStdlibMaterialCompileError("SOURCE_NOT_PYTHON_STDLIB:" + cid)

    module_name = str(entry.get("adapter_module") or "").strip()
    if not module_name or not module_name.replace("_", "").isalnum():
        raise DStdlibMaterialCompileError("ADAPTER_MODULE_INVALID")
    adapter_rel = "canonical/runtime/bound_capabilities/" + module_name + ".py"
    adapter_path = _safe_file(root, adapter_rel)

    executor_closure = census(root, [EXECUTOR_REL, EPOCH_REL])
    adapter_closure = census(root, [adapter_rel])

    executor_paths = {
        str(row["path"]) for row in executor_closure["brain_owned_transitive_files"]
    }
    adapter_paths = {
        str(row["path"]) for row in adapter_closure["brain_owned_transitive_files"]
    }

    unresolved: list[str] = []
    dynamic_targets: set[str] = set()
    queue = [root / rel for rel in sorted(adapter_paths)]
    scanned: set[str] = set()
    while queue:
        path = queue.pop(0).resolve()
        rel = path.relative_to(root).as_posix()
        if rel in scanned:
            continue
        scanned.add(rel)
        targets, residuals = _literal_sibling_loads(path)
        unresolved.extend(rel + ":" + x for x in residuals)
        for target in targets:
            try:
                target_rel = target.relative_to(root).as_posix()
            except ValueError as exc:
                raise DStdlibMaterialCompileError(
                    "DYNAMIC_TARGET_OUTSIDE_REPO:" + str(target)
                ) from exc
            dynamic_targets.add(target_rel)
            if target_rel not in adapter_paths:
                extra = census(root, [target_rel])
                for row in extra["brain_owned_transitive_files"]:
                    p = str(row["path"])
                    if p not in adapter_paths:
                        adapter_paths.add(p)
                        queue.append(root / p)
                adapter_closure["external_or_stdlib_substrate_imports"] = sorted(
                    set(adapter_closure["external_or_stdlib_substrate_imports"])
                    | set(extra["external_or_stdlib_substrate_imports"])
                )

    material_paths = sorted(
        executor_paths
        | adapter_paths
        | {registry_path.relative_to(root).as_posix()}
    )
    materials = []
    for rel in material_paths:
        raw = _safe_file(root, rel).read_bytes()
        materials.append({"path": rel, "git_blob_sha": _git_blob_sha(raw)})

    adapter_text = adapter_path.read_text(encoding="utf-8")
    external_imports = sorted(
        set(executor_closure["external_or_stdlib_substrate_imports"])
        | set(adapter_closure["external_or_stdlib_substrate_imports"])
    )
    modules = _declared_stdlib_modules(source)

    status = (
        "MATERIAL_CLOSURE_CANDIDATE_COMPILED"
        if not unresolved
        else "OPEN__UNRESOLVED_ADAPTER_DYNAMIC_LOAD"
    )
    return {
        "schema": SCHEMA,
        "status": status,
        "capability_id": cid,
        "route": "D_STDLIB_MINIMAL_EXECUTOR_V1",
        "registry_entry_sha256": hashlib.sha256(
            json.dumps(
                entry,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest(),
        "adapter_module": module_name,
        "adapter_path": adapter_rel,
        "adapter_git_blob_sha": next(
            row["git_blob_sha"] for row in materials if row["path"] == adapter_rel
        ),
        "executor_path": EXECUTOR_REL,
        "executor_git_blob_sha": next(
            row["git_blob_sha"] for row in materials if row["path"] == EXECUTOR_REL
        ),
        "material_count": len(materials),
        "materials": materials,
        "material_closure_root": material_closure_root(materials),
        "declared_python_stdlib_modules": modules,
        "substrate_contract_template": {
            "kind": "CPYTHON_STDLIB",
            "implementation": "cpython",
            "python_version": "BIND_AT_FRESH_REPLAY",
            "sys_platform": "BIND_AT_FRESH_REPLAY",
            "stdlib_modules": modules,
        },
        "dynamic_literal_targets": sorted(dynamic_targets),
        "unresolved_dynamic_loads": sorted(set(unresolved)),
        "external_or_stdlib_substrate_imports": external_imports,
        "signals": {
            "network_surface_detected": any(
                token in adapter_text
                for token in ("urllib.request", "urlopen(", "socket.", "http.client")
            ),
            "subprocess_surface_detected": any(
                token in adapter_text
                for token in ("subprocess.", "os.system(", "Popen(")
            ),
            "adapter_dynamic_literal_target_count": len(dynamic_targets),
            "unresolved_adapter_dynamic_load_count": len(set(unresolved)),
        },
        "proof_boundary": (
            "MEMBER_MATERIAL_ONLY__FRONT_DOOR_AND_PROVIDER_ENFORCEMENT_"
            "ARE_SEPARATE_EXACT_BYTE_PROVIDER_THEOREMS"
        ),
        "d_finality_authority": False,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
