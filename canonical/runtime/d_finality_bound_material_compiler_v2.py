"""Path-sensitive bound-capability D-finality material compiler V2.

V1 deliberately over-approximated the closure by recursively scanning the entire
universal invocation/provider stack. That was safe but uselessly contagious:
an unrelated provider's dynamic loader or network import became a false member
obligation for every local bound capability.

V2 separates the proof exactly as D-finality requires:

1. provider theorem subject:
   exact shared executor code blobs, content-bound but NOT recursively treated as
   member material. A separate provider theorem must prove the bound-capability
   dispatch/control-flow semantics.

2. member material closure:
   exact bound registry + selected adapter + recursively imported canonical code
   actually reachable from that adapter + literal sibling Python loads.

No D-finality, ownership, promotion, or execution credit is granted by this
compiler. Provider theorem validity and clean-room replay remain separate proof
obligations.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.brain_owned_python_closure_census_v1 import census
from canonical.runtime.d_finality_execution_epoch_v1 import material_closure_root

SCHEMA = "PROJECT_BRAIN_D_FINALITY_BOUND_MATERIAL_COMPILER_V2"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_REL = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

PROVIDER_THEOREM_PATHS = (
    "canonical/runtime/d_finality_execution_epoch_v1.py",
    "canonical/runtime/live_capability_invoker_v1.py",
    "canonical/runtime/verified_bound_capability_execution_adapter_v1.py",
    "canonical/runtime/astra_runtime.py",
)


class MaterialCompileV2Error(ValueError):
    pass


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _safe_file(root: Path, raw: str) -> Path:
    rel = str(raw or "").strip()
    p = Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise MaterialCompileV2Error("NONCANONICAL_PATH:" + rel)
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError as exc:
        raise MaterialCompileV2Error("PATH_OUTSIDE_REPO:" + rel) from exc
    if not full.is_file():
        raise MaterialCompileV2Error("FILE_MISSING:" + rel)
    return full


def _row_for(path: Path, root: Path) -> dict[str, str]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "git_blob_sha": _git_blob_sha(raw),
    }


def _module_path_if_present(root: Path, module: str) -> Path | None:
    p = root.joinpath(*module.split("."))
    py = p.with_suffix(".py")
    init = p / "__init__.py"
    if py.is_file():
        return py.resolve()
    if init.is_file():
        return init.resolve()
    return None


def _canonical_from_import_children(path: Path, root: Path) -> list[Path]:
    """Resolve package-child modules missed by the legacy closure census.

    Example:
        from canonical.runtime.bound_capabilities import leaf

    The legacy census records the package __init__.py but not leaf.py. For a
    material proof that omission is unsound, so V2 explicitly admits only child
    modules whose exact canonical path exists.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    out: set[Path] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = str(node.module or "")
        if not (module == "canonical" or module.startswith("canonical.")):
            continue
        for alias in node.names:
            if alias.name == "*":
                continue
            candidate = _module_path_if_present(
                root, module + "." + str(alias.name)
            )
            if candidate is not None:
                out.add(candidate)
    return sorted(out, key=lambda p: p.as_posix())


def _literal_sibling_loads(path: Path) -> tuple[list[Path], list[str]]:
    """Find fixed sibling .py loads and unresolved dynamic loader surfaces.

    A spec_from_file_location call is considered resolved for this module iff its
    path argument is statically derived from at least one literal
    Path(...).with_name("x.py") expression present in the same module.

    This is conservative. False OPEN is acceptable; false closure is not.
    """
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise MaterialCompileV2Error(
            "PYTHON_PARSE_FAILED:" + path.as_posix()
        ) from exc

    literal_targets: list[Path] = []
    dynamic_loader_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr == "spec_from_file_location":
                dynamic_loader_count += 1
            if isinstance(fn, ast.Attribute) and fn.attr == "with_name":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
                    value = node.args[0].value
                    if isinstance(value, str) and value.endswith(".py"):
                        target = path.with_name(value).resolve()
                        literal_targets.append(target)

            # Bounded Project Brain helper pattern:
            #   _load_runtime_module(root, "goal_compiler.py", "module_name")
            # Resolve only exact literal filenames under canonical/runtime.
            if (
                isinstance(fn, ast.Name)
                and fn.id == "_load_runtime_module"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
            ):
                value = node.args[1].value
                if (
                    isinstance(value, str)
                    and value.endswith(".py")
                    and Path(value).name == value
                ):
                    repo_root = path
                    while repo_root.name != "canonical" and repo_root != repo_root.parent:
                        repo_root = repo_root.parent
                    if repo_root.name == "canonical":
                        target = (
                            repo_root.parent
                            / "canonical"
                            / "runtime"
                            / value
                        ).resolve()
                        literal_targets.append(target)

    unique = sorted(set(literal_targets), key=lambda p: p.as_posix())
    unresolved: list[str] = []
    missing = [p for p in unique if not p.is_file()]
    for p in missing:
        unresolved.append("LITERAL_SIBLING_MISSING:" + p.name)

    existing_count = sum(1 for p in unique if p.is_file())
    if dynamic_loader_count > existing_count:
        unresolved.append(
            "DYNAMIC_LOADER_COUNT_EXCEEDS_LITERAL_SIBLING_TARGETS:"
            + str(dynamic_loader_count)
            + ">"
            + str(existing_count)
        )
    return [p for p in unique if p.is_file()], sorted(set(unresolved))


def _load_registry(
    root: Path,
) -> tuple[Path, Mapping[str, Any], Mapping[str, Any]]:
    path = _safe_file(root, REGISTRY_REL)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(doc, Mapping)
        or doc.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1"
    ):
        raise MaterialCompileV2Error("BOUND_REGISTRY_INVALID")
    caps = doc.get("capabilities")
    if not isinstance(caps, Mapping):
        raise MaterialCompileV2Error("BOUND_REGISTRY_CAPABILITIES_INVALID")
    return path, doc, caps


def _source_obligations(source: Mapping[str, Any]) -> dict[str, Any]:
    typ = str(source.get("type") or "").strip()
    out: dict[str, Any] = {"source_type": typ or None}
    if typ == "python_stdlib":
        modules = source.get("modules")
        if modules is None:
            one = str(source.get("module") or "").strip()
            modules = [one] if one else []
        out["declared_python_stdlib_modules"] = sorted(
            str(x) for x in modules if str(x)
        )
        out["external_material_required"] = False
        out["substrate_class"] = "DECLARED_CPYTHON_STDLIB"
    elif typ == "system_tool":
        out["external_material_required"] = True
        out["substrate_class"] = "SYSTEM_EXECUTABLE"
        out["executable"] = source.get("executable")
    elif typ in {"apt", "pypi", "npm", "git_source_tree"}:
        out["external_material_required"] = True
        out["substrate_class"] = typ.upper()
        out["source_record"] = dict(source)
    elif typ:
        out["external_material_required"] = True
        out["substrate_class"] = "OTHER_DECLARED_SOURCE"
        out["source_record"] = dict(source)
    else:
        out["external_material_required"] = False
        out["substrate_class"] = "NONE_DECLARED"
    return out


def _member_closure(
    root: Path,
    adapter_rel: str,
) -> tuple[list[dict[str, str]], list[str], list[str], list[str]]:
    """Recursively close adapter-owned canonical code and fixed sibling loads."""
    provider_set = set(PROVIDER_THEOREM_PATHS)
    closure_paths: set[str] = set()
    substrate_imports: set[str] = set()
    dynamic_targets: set[str] = set()
    unresolved: set[str] = set()

    queue = [adapter_rel]
    scanned_roots: set[str] = set()
    while queue:
        rel = queue.pop(0)
        if rel in scanned_roots:
            continue
        scanned_roots.add(rel)

        out = census(root, [rel])
        substrate_imports.update(out["external_or_stdlib_substrate_imports"])
        new_paths = {
            str(row["path"])
            for row in out["brain_owned_transitive_files"]
            if isinstance(row, Mapping)
        }
        for p in sorted(new_paths):
            if p in provider_set:
                continue
            if p not in closure_paths:
                closure_paths.add(p)

        # Literal sibling loads are only inspected on member-owned files. Shared
        # provider files are theorem subjects and cannot contaminate member scope.
        for p in sorted(new_paths):
            if p in provider_set:
                continue
            full = _safe_file(root, p)

            # Recover concrete package-child imports omitted by the legacy
            # census, then recurse through those exact files too.
            for child in _canonical_from_import_children(full, root):
                child_rel = child.relative_to(root).as_posix()
                if child_rel not in scanned_roots:
                    queue.append(child_rel)

            targets, opens = _literal_sibling_loads(full)
            for item in opens:
                unresolved.add(p + ":" + item)
            for target in targets:
                try:
                    target_rel = target.relative_to(root).as_posix()
                except ValueError as exc:
                    raise MaterialCompileV2Error(
                        "DYNAMIC_TARGET_OUTSIDE_REPO:" + target.as_posix()
                    ) from exc
                dynamic_targets.add(target_rel)
                if target_rel not in scanned_roots:
                    queue.append(target_rel)

    materials = [
        _row_for(_safe_file(root, rel), root)
        for rel in sorted(closure_paths)
    ]
    return (
        materials,
        sorted(dynamic_targets),
        sorted(unresolved),
        sorted(substrate_imports),
    )


def compile_candidate(
    capability_id: str,
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cid = str(capability_id or "").strip()
    if not cid:
        raise MaterialCompileV2Error("CAPABILITY_ID_REQUIRED")

    registry_path, _registry, caps = _load_registry(root)
    entry = caps.get(cid)
    if not isinstance(entry, Mapping):
        raise MaterialCompileV2Error("BOUND_CAPABILITY_UNKNOWN:" + cid)
    if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise MaterialCompileV2Error("BOUND_CAPABILITY_NOT_VERIFIED:" + cid)
    if float(entry.get("incremental_spend_usd", 0)) != 0:
        raise MaterialCompileV2Error("BOUND_CAPABILITY_NONZERO_COST:" + cid)

    module_name = str(entry.get("adapter_module") or "").strip()
    if not module_name or not module_name.replace("_", "").isalnum():
        raise MaterialCompileV2Error("ADAPTER_MODULE_INVALID")
    adapter_rel = (
        "canonical/runtime/bound_capabilities/" + module_name + ".py"
    )
    adapter_path = _safe_file(root, adapter_rel)

    provider_rows = [
        _row_for(_safe_file(root, rel), root)
        for rel in PROVIDER_THEOREM_PATHS
    ]
    provider_root = material_closure_root(provider_rows)

    member_rows, dynamic_targets, unresolved, substrate_imports = (
        _member_closure(root, adapter_rel)
    )
    registry_row = _row_for(registry_path, root)
    # Registry is a member binding because it selects the exact row/adapter.
    member_by_path = {row["path"]: row for row in member_rows}
    member_by_path[registry_row["path"]] = registry_row
    member_rows = [member_by_path[k] for k in sorted(member_by_path)]
    member_root = material_closure_root(member_rows)

    source = entry.get("source") or {}
    if not isinstance(source, Mapping):
        raise MaterialCompileV2Error("BOUND_SOURCE_NOT_OBJECT")

    adapter_source = adapter_path.read_text(encoding="utf-8")
    signals = {
        "network_surface_detected": any(
            token in adapter_source
            for token in (
                "urllib.request",
                "urlopen(",
                "socket.",
                "http.client",
            )
        ),
        "subprocess_surface_detected": any(
            token in adapter_source
            for token in (
                "subprocess.",
                "os.system(",
                "Popen(",
            )
        ),
        "dynamic_literal_target_count": len(dynamic_targets),
        "unresolved_dynamic_load_count": len(unresolved),
    }

    return {
        "schema": SCHEMA,
        "status": (
            "MEMBER_MATERIAL_CLOSURE_CANDIDATE_COMPILED"
            if not unresolved
            else "OPEN__MEMBER_DYNAMIC_LOAD_UNRESOLVED"
        ),
        "capability_id": cid,
        "provider_theorem_required": True,
        "provider_theorem_subject": {
            "paths": list(PROVIDER_THEOREM_PATHS),
            "materials": provider_rows,
            "provider_code_root": provider_root,
            "recursive_member_dependency_interpretation": False,
            "claim": (
                "SEPARATE_THEOREM_MUST_PROVE_EXACT_BOUND_DISPATCH_AND_"
                "AUTHORITY_NONWIDENING_FOR_THESE_BYTES"
            ),
        },
        "member": {
            "registry_entry_sha256": _sha256_json(entry),
            "adapter_module": module_name,
            "adapter_path": adapter_rel,
            "adapter_git_blob_sha": _git_blob_sha(adapter_path.read_bytes()),
            "material_count": len(member_rows),
            "materials": member_rows,
            "member_material_closure_root": member_root,
            "dynamic_literal_targets": dynamic_targets,
            "unresolved_dynamic_loads": unresolved,
            "external_or_stdlib_substrate_imports": substrate_imports,
            "source_obligations": _source_obligations(source),
            "signals": signals,
        },
        "separation_invariant": (
            "PROVIDER_THEOREM_MAY_BE_REUSED_BUT_MEMBER_MATERIAL_CERTIFICATE_"
            "MUST_BIND_EACH_CAPABILITY_SEPARATELY"
        ),
        "d_finality_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
