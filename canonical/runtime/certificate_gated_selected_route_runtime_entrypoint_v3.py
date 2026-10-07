"""Certificate-gated selected-route runtime V3 with symbolic admission predicates.

V1 established content-addressed exact-context routing. V2 added exact payload
membership validation for creditable routes. V3 adds content-addressed symbolic
admission predicates over context regions. Global selected-cover completeness is
never a manual flag: it is derived only from the exact creditable predicate set
plus an independent complement proof.
"""
from __future__ import annotations

import importlib.util
import sys
from typing import Any, Mapping

from canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v1 import (
    ROOT,
    RuntimeBindingFailClosed,
    _canonical_path,
    _load_json,
    context_digest,
    git_blob_sha,
)
from canonical.runtime.predicate_selected_cover_complement_gate_v1 import (
    evaluate as evaluate_complement_cover,
)

SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_ENTRYPOINT_V3"
REGISTRY_SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V2"
REGISTRY_PATH = ROOT / "canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V2.json"
MATCH_MODES = {"EXACT_DIGEST", "SYMBOLIC_PREDICATE"}


def _load_callable(path, callable_name: str, module_prefix: str):
    name = str(callable_name or "").strip()
    if not name:
        raise RuntimeBindingFailClosed("CALLABLE_MISSING")
    module_name = module_prefix + "_" + git_blob_sha(path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeBindingFailClosed("IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    fn = getattr(module, name, None)
    if not callable(fn):
        raise RuntimeBindingFailClosed("CALLABLE_INVALID:" + name)
    return fn


def load_registry() -> Mapping[str, Any]:
    reg = _load_json(REGISTRY_PATH)
    if reg.get("schema") != REGISTRY_SCHEMA:
        raise RuntimeBindingFailClosed("REGISTRY_SCHEMA_INVALID")
    if reg.get("default") != "FAIL_CLOSED":
        raise RuntimeBindingFailClosed("REGISTRY_DEFAULT_NOT_FAIL_CLOSED")
    if reg.get("selected_cover_authority") != (
        "DERIVED_ONLY_FROM_EXACT_PREDICATE_SET_PLUS_INDEPENDENT_COMPLEMENT_PROOF"
    ):
        raise RuntimeBindingFailClosed("SELECTED_COVER_AUTHORITY_INVALID")
    if not isinstance(reg.get("scope_id"), str) or not reg.get("scope_id"):
        raise RuntimeBindingFailClosed("REGISTRY_SCOPE_ID_INVALID")
    if not isinstance(reg.get("routes"), list):
        raise RuntimeBindingFailClosed("REGISTRY_ROUTES_NOT_LIST")
    return reg


def _verified_rows(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_routes: set[str] = set()
    seen_predicates: set[str] = set()

    for index, row in enumerate(registry.get("routes") or []):
        if not isinstance(row, Mapping):
            raise RuntimeBindingFailClosed(f"ROUTE_ROW_NOT_OBJECT:{index}")
        mode = str(row.get("match_mode") or "")
        if mode not in MATCH_MODES:
            raise RuntimeBindingFailClosed(f"MATCH_MODE_INVALID:{index}")
        if row.get("scope_id") != registry.get("scope_id"):
            raise RuntimeBindingFailClosed(f"ROUTE_SCOPE_MISMATCH:{index}")
        if type(row.get("admitted")) is not bool:
            raise RuntimeBindingFailClosed(f"ROUTE_ADMISSION_NOT_LITERAL_BOOL:{index}")
        if type(row.get("creditable")) is not bool:
            raise RuntimeBindingFailClosed(f"ROUTE_CREDITABLE_NOT_LITERAL_BOOL:{index}")

        cell_id = str(row.get("cell_id") or "").strip()
        route_id = str(row.get("route_id") or "").strip()
        if not cell_id or not route_id or route_id in seen_routes:
            raise RuntimeBindingFailClosed(f"ROUTE_IDENTITY_INVALID:{index}")
        seen_routes.add(route_id)

        route_path = _canonical_path(row.get("route_path"), prefixes=("canonical/runtime/",))
        adequacy_path = _canonical_path(
            row.get("adequacy_certificate_path"),
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        admission_path = _canonical_path(
            row.get("admission_certificate_path"),
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        if row.get("route_blob_sha") != git_blob_sha(route_path):
            raise RuntimeBindingFailClosed(f"ROUTE_BLOB_DRIFT:{index}")
        if row.get("adequacy_certificate_blob_sha") != git_blob_sha(adequacy_path):
            raise RuntimeBindingFailClosed(f"ADEQUACY_CERTIFICATE_BLOB_DRIFT:{index}")
        if row.get("admission_certificate_blob_sha") != git_blob_sha(admission_path):
            raise RuntimeBindingFailClosed(f"ADMISSION_CERTIFICATE_BLOB_DRIFT:{index}")

        adequacy = _load_json(adequacy_path)
        admission = _load_json(admission_path)
        for cert, name in ((adequacy, "ADEQUACY"), (admission, "ADMISSION")):
            if cert.get("scope_id") != registry.get("scope_id"):
                raise RuntimeBindingFailClosed(f"{name}_SCOPE_MISMATCH:{index}")
            if cert.get("cell_id") != cell_id:
                raise RuntimeBindingFailClosed(f"{name}_CELL_ID_MISMATCH:{index}")
            if cert.get("route_id") != route_id:
                raise RuntimeBindingFailClosed(f"{name}_ROUTE_ID_MISMATCH:{index}")
            if cert.get("route_blob_sha") != row.get("route_blob_sha"):
                raise RuntimeBindingFailClosed(f"{name}_ROUTE_BLOB_MISMATCH:{index}")
            if cert.get("creditable") is not row.get("creditable"):
                raise RuntimeBindingFailClosed(f"{name}_CREDITABLE_MISMATCH:{index}")

        normalized = dict(row)
        if mode == "EXACT_DIGEST":
            digest = str(row.get("context_digest") or "").strip()
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise RuntimeBindingFailClosed(f"CONTEXT_DIGEST_INVALID:{index}")
            if admission.get("context_digest_sha256") != digest:
                raise RuntimeBindingFailClosed(f"ADMISSION_CONTEXT_DIGEST_MISMATCH:{index}")
        else:
            pid = str(row.get("admission_predicate_id") or "").strip()
            if not pid or pid in seen_predicates:
                raise RuntimeBindingFailClosed(f"PREDICATE_ID_INVALID_OR_DUPLICATE:{index}")
            seen_predicates.add(pid)
            predicate_path = _canonical_path(
                row.get("admission_predicate_path"), prefixes=("canonical/runtime/",)
            )
            if row.get("admission_predicate_blob_sha") != git_blob_sha(predicate_path):
                raise RuntimeBindingFailClosed(f"PREDICATE_BLOB_DRIFT:{index}")
            for cert, name in ((adequacy, "ADEQUACY"), (admission, "ADMISSION")):
                if cert.get("admission_predicate_id") != pid:
                    raise RuntimeBindingFailClosed(f"{name}_PREDICATE_ID_MISMATCH:{index}")
                if cert.get("admission_predicate_blob_sha") != row.get("admission_predicate_blob_sha"):
                    raise RuntimeBindingFailClosed(f"{name}_PREDICATE_BLOB_MISMATCH:{index}")
            normalized["_predicate_path"] = predicate_path

        if admission.get("admitted") is not row.get("admitted"):
            raise RuntimeBindingFailClosed(f"ADMISSION_BOOLEAN_MISMATCH:{index}")

        if row.get("creditable") is True:
            if mode != "SYMBOLIC_PREDICATE":
                raise RuntimeBindingFailClosed(f"CREDITABLE_ROW_MUST_USE_SYMBOLIC_PREDICATE:{index}")
            if (
                adequacy.get("independent_verified") is not True
                or adequacy.get("exact_byte_bound") is not True
                or adequacy.get("adequate_for_predicate_region") is not True
                or admission.get("independent_verified") is not True
                or admission.get("exact_byte_bound") is not True
                or admission.get("admission_implies_route_adequacy") is not True
            ):
                raise RuntimeBindingFailClosed(f"CREDITABLE_SOUNDNESS_UNPROVED:{index}")
            sr = row.get("admission_soundness_receipt")
            if not isinstance(sr, Mapping):
                raise RuntimeBindingFailClosed(f"ADMISSION_SOUNDNESS_RECEIPT_REQUIRED:{index}")
            if not isinstance(row.get("admission_soundness_receipt_blob_sha"), str):
                raise RuntimeBindingFailClosed(f"ADMISSION_SOUNDNESS_BLOB_REQUIRED:{index}")

        normalized["_route_path"] = route_path
        out.append(normalized)
    return out


def _selected_cover_state(registry: Mapping[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    creditable = [r for r in rows if r.get("creditable") is True]
    receipt = registry.get("complement_coverage_receipt")
    if not creditable or not isinstance(receipt, Mapping):
        return {
            "authorized": False,
            "gate_status": "NO_CREDITABLE_EXACT_PREDICATE_SET_OR_COMPLEMENT_RECEIPT",
        }

    gate_rows = []
    for row in creditable:
        gate_rows.append({
            "cell_id": row["cell_id"],
            "route_id": row["route_id"],
            "admission_predicate_id": row["admission_predicate_id"],
            "admission_predicate_blob_sha": row["admission_predicate_blob_sha"],
            "adequacy_certificate_blob_sha": row["adequacy_certificate_blob_sha"],
            "admission_soundness_receipt_blob_sha": row["admission_soundness_receipt_blob_sha"],
            "admission_soundness_receipt": row["admission_soundness_receipt"],
        })
    gate = evaluate_complement_cover({
        "scope_id": registry["scope_id"],
        "routes": gate_rows,
        "complement_coverage_receipt": dict(receipt),
    })
    return {
        "authorized": gate.get("selected_cover_complete_authorized") is True,
        "gate_status": gate.get("status"),
        "gate": gate,
    }


def preflight() -> dict[str, Any]:
    try:
        registry = load_registry()
        rows = _verified_rows(registry)
        cover = _selected_cover_state(registry, rows)
        return {
            "schema": SCHEMA,
            "status": "PASS__CONTENT_ADDRESSED_SYMBOLIC_ROUTE_RUNTIME_VALID",
            "pass": True,
            "route_count": len(rows),
            "symbolic_route_count": sum(r.get("match_mode") == "SYMBOLIC_PREDICATE" for r in rows),
            "creditable_route_count": sum(r.get("creditable") is True for r in rows),
            "selected_cover_complete": cover["authorized"],
            "selected_cover_gate_status": cover["gate_status"],
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "selected_cover_complete": False,
            "terminal_credit_delta": 0,
        }


def dispatch(context: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(context, Mapping):
        raise RuntimeBindingFailClosed("CONTEXT_MAPPING_REQUIRED")
    if not isinstance(payload, Mapping):
        raise RuntimeBindingFailClosed("PAYLOAD_MAPPING_REQUIRED")

    registry = load_registry()
    rows = _verified_rows(registry)
    actual_digest = context_digest(context)
    matches: list[dict[str, Any]] = []

    for row in rows:
        if row.get("admitted") is not True:
            continue
        mode = row.get("match_mode")
        matched = False
        if mode == "EXACT_DIGEST":
            matched = row.get("context_digest") == actual_digest
        else:
            fn = _load_callable(
                row["_predicate_path"],
                row.get("admission_predicate_callable"),
                "project_brain_admission_predicate",
            )
            result = fn(dict(context))
            if type(result) is not bool:
                raise RuntimeBindingFailClosed("ADMISSION_PREDICATE_MUST_RETURN_LITERAL_BOOL")
            matched = result
        if matched:
            matches.append(row)

    if not matches:
        raise RuntimeBindingFailClosed("NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT")

    matches.sort(key=lambda r: (
        str(r.get("admission_certificate_blob_sha") or ""),
        str(r.get("adequacy_certificate_blob_sha") or ""),
        str(r.get("route_blob_sha") or ""),
        str(r.get("cell_id") or ""),
        str(r.get("route_id") or ""),
    ))
    selected = matches[0]
    route_fn = _load_callable(
        selected["_route_path"],
        selected.get("callable"),
        "project_brain_selected_route_v3",
    )
    result = route_fn(dict(payload))
    if not isinstance(result, Mapping):
        raise RuntimeBindingFailClosed("ROUTE_RESULT_NOT_MAPPING")

    cover = _selected_cover_state(registry, rows)
    return {
        "schema": SCHEMA,
        "status": "PASS__CERTIFICATE_GATED_SYMBOLIC_ROUTE_EXECUTED",
        "actual_context_digest": actual_digest,
        "selected_cell_id": selected["cell_id"],
        "selected_route_id": selected["route_id"],
        "match_mode": selected["match_mode"],
        "admission_predicate_id": selected.get("admission_predicate_id"),
        "route_blob_sha": selected["route_blob_sha"],
        "adequacy_certificate_blob_sha": selected["adequacy_certificate_blob_sha"],
        "admission_certificate_blob_sha": selected["admission_certificate_blob_sha"],
        "creditable": selected.get("creditable") is True,
        "result": dict(result),
        "selected_cover_complete": cover["authorized"],
        "selected_cover_gate_status": cover["gate_status"],
        "terminal_credit_delta": 0,
        "rule": (
            "SYMBOLIC_REGION_ROUTE_EXECUTES_ONLY_AFTER_CONTENT_ADDRESSED_PREDICATE_"
            "ROUTE_AND_CERTIFICATE_BINDING__GLOBAL_COVER_ONLY_FROM_INDEPENDENT_COMPLEMENT_PROOF"
        ),
    }
