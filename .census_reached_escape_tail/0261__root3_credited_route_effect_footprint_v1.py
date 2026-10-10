from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

MANIFEST_SCHEMA = "PROJECT_BRAIN_CREDITED_ROUTE_EFFECT_FOOTPRINT_MANIFEST_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_CREDITED_ROUTE_EFFECT_REACHABILITY_RECEIPT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_CREDITED_ROUTE_EFFECT_FOOTPRINT_OUTPUT_V1"
REQUIRED_PREDICATES = frozenset({
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
})
_EFFECT_ID = re.compile(r"^[A-Za-z0-9_.:/-]{1,200}$")


class EffectFootprintError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _bound_file(root: Path, spec: Mapping[str, Any], label: str) -> dict[str, str]:
    if not isinstance(spec, Mapping) or set(spec) != {"path", "git_blob_sha"}:
        raise EffectFootprintError(label + "_BINDING_FIELDS_INVALID")
    rel = spec.get("path")
    expected = spec.get("git_blob_sha")
    if not isinstance(rel, str) or not rel or "\x00" in rel:
        raise EffectFootprintError(label + "_PATH_INVALID")
    if (
        not isinstance(expected, str)
        or len(expected) != 40
        or any(ch not in "0123456789abcdef" for ch in expected)
    ):
        raise EffectFootprintError(label + "_GIT_BLOB_SHA_INVALID")
    path = (root / rel).resolve()
    if not _inside(path, root):
        raise EffectFootprintError(label + "_PATH_ESCAPES_ROOT")
    if not path.is_file():
        raise EffectFootprintError(label + "_FILE_MISSING:" + rel)
    actual = git_blob_sha(path.read_bytes())
    if actual != expected:
        raise EffectFootprintError(label + "_BLOB_DRIFT:" + rel + ":" + actual)
    return {"path": rel.replace("\\", "/"), "git_blob_sha": actual}


def _binding_set(
    root: Path,
    raw: Any,
    label: str,
    *,
    allow_empty: bool = False,
) -> list[dict[str, str]]:
    if not isinstance(raw, list) or (not raw and not allow_empty):
        raise EffectFootprintError(label + "_LIST_INVALID")
    out = [_bound_file(root, x, label) for x in raw]
    paths = [x["path"] for x in out]
    if len(paths) != len(set(paths)):
        raise EffectFootprintError(label + "_DUPLICATE_PATH")
    return sorted(out, key=lambda x: x["path"])


def _load_bound_json(root: Path, spec: Mapping[str, Any], label: str) -> dict[str, Any]:
    bound = _bound_file(root, spec, label)
    path = root / bound["path"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise EffectFootprintError(label + "_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise EffectFootprintError(label + "_JSON_OBJECT_REQUIRED")
    return value


def _effect_ids(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        raise EffectFootprintError("MATERIAL_EFFECT_IDS_LIST_REQUIRED")
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str) or _EFFECT_ID.fullmatch(item) is None:
            raise EffectFootprintError("MATERIAL_EFFECT_ID_INVALID")
        out.append(item)
    if len(out) != len(set(out)):
        raise EffectFootprintError("MATERIAL_EFFECT_ID_DUPLICATE")
    return sorted(out)


def compile_footprint(
    manifest: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise EffectFootprintError("MANIFEST_NOT_OBJECT")
    if set(manifest) != {
        "schema",
        "effect_ontology_bindings",
        "credited_routes",
    }:
        raise EffectFootprintError("MANIFEST_FIELDS_INVALID")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise EffectFootprintError("MANIFEST_SCHEMA_INVALID")

    root = Path(repo_root).resolve(strict=True)
    ontology = _binding_set(
        root,
        manifest.get("effect_ontology_bindings"),
        "EFFECT_ONTOLOGY",
    )
    ontology_sha = sha256_json(ontology)

    routes = manifest.get("credited_routes")
    if not isinstance(routes, list) or not routes:
        raise EffectFootprintError("CREDITED_ROUTES_REQUIRED")

    route_ids: set[str] = set()
    all_effects: set[str] = set()
    compiled_routes: list[dict[str, Any]] = []

    for raw_route in routes:
        if not isinstance(raw_route, Mapping) or set(raw_route) != {
            "route_id",
            "route_bindings",
            "reachability_receipt",
        }:
            raise EffectFootprintError("ROUTE_FIELDS_INVALID")
        route_id = raw_route.get("route_id")
        if (
            not isinstance(route_id, str)
            or not route_id
            or _EFFECT_ID.fullmatch(route_id) is None
        ):
            raise EffectFootprintError("ROUTE_ID_INVALID")
        if route_id in route_ids:
            raise EffectFootprintError("DUPLICATE_ROUTE_ID:" + route_id)
        route_ids.add(route_id)

        route_bindings = _binding_set(
            root,
            raw_route.get("route_bindings"),
            "ROUTE_BINDING",
        )
        route_binding_sha = sha256_json(route_bindings)

        receipt_spec = raw_route.get("reachability_receipt")
        receipt_bound = _bound_file(root, receipt_spec, "REACHABILITY_RECEIPT")
        receipt = _load_bound_json(
            root,
            receipt_spec,
            "REACHABILITY_RECEIPT",
        )
        if receipt.get("schema") != RECEIPT_SCHEMA:
            raise EffectFootprintError("RECEIPT_SCHEMA_INVALID")
        if receipt.get("route_id") != route_id:
            raise EffectFootprintError("RECEIPT_ROUTE_ID_MISMATCH:" + route_id)
        if receipt.get("route_binding_sha256") != route_binding_sha:
            raise EffectFootprintError("RECEIPT_ROUTE_BINDING_MISMATCH:" + route_id)
        if receipt.get("effect_ontology_binding_sha256") != ontology_sha:
            raise EffectFootprintError("RECEIPT_ONTOLOGY_BINDING_MISMATCH:" + route_id)

        for key in (
            "scope_complete",
            "conservative",
            "fail_closed_outside_footprint",
            "independent_or_objective",
        ):
            if receipt.get(key) is not True:
                raise EffectFootprintError(
                    "RECEIPT_" + key.upper() + "_NOT_TRUE:" + route_id
                )
        predicates = frozenset(
            str(x) for x in (receipt.get("predicate_ids") or [])
        )
        if not REQUIRED_PREDICATES.issubset(predicates):
            raise EffectFootprintError(
                "RECEIPT_PREDICATE_SCOPE_INCOMPLETE:" + route_id
            )

        effects = _effect_ids(receipt.get("material_effect_ids"))
        all_effects.update(effects)
        compiled_routes.append({
            "route_id": route_id,
            "route_bindings": route_bindings,
            "route_binding_sha256": route_binding_sha,
            "reachability_receipt": receipt_bound,
            "material_effect_ids": effects,
        })

    compiled_routes.sort(key=lambda x: x["route_id"])
    footprint = sorted(all_effects)
    output_core = {
        "effect_ontology_bindings": ontology,
        "effect_ontology_binding_sha256": ontology_sha,
        "credited_routes": compiled_routes,
        "material_effect_ids": footprint,
    }
    return {
        "schema": OUTPUT_SCHEMA,
        "status": "PASS__CREDITED_ROUTE_EFFECT_FOOTPRINT_COMPILED",
        **output_core,
        "credited_route_count": len(compiled_routes),
        "material_effect_count": len(footprint),
        "footprint_sha256": sha256_json(output_core),
        "scope_complete_claim_from_receipts": True,
        "fail_closed_outside_footprint_required": True,
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def compile_manifest_file(
    manifest_path: str | Path,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    path = Path(manifest_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    return compile_footprint(value, repo_root=repo_root)
