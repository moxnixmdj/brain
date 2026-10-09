"""Certificate-gated selected-route runtime V5.

V5 is the current-pointer successor to V4. It preserves V4's mandatory
content-addressed payload-membership validator for every creditable route,
removes registry-version identity from the live runtime, and makes route
selection globally unique: any overlap fails closed.

The current registry may contain exact-digest and symbolic-predicate admission
rows. Global selected-cover completeness remains derived only from creditable
sound predicates plus an independent complement proof.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v2 import (
    ROOT,
    RuntimeBindingFailClosed,
    _canonical_path,
    _load_callable,
    _load_json,
    _validate_creditable_payload,
    context_digest,
    git_blob_sha,
)
from canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v3 import (
    _selected_cover_state,
)

SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_ENTRYPOINT_V5"
POINTER_SCHEMA = "PROJECT_BRAIN_CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY_POINTER_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V3"
CURRENT_REGISTRY_POINTER_PATH = (
    ROOT / "canonical/governance/CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY.json"
)
MATCH_MODES = {"EXACT_DIGEST", "SYMBOLIC_PREDICATE"}


def load_registry(
    pointer_path: str | Path = CURRENT_REGISTRY_POINTER_PATH,
) -> Mapping[str, Any]:
    pointer = _load_json(Path(pointer_path))
    if pointer.get("schema") != POINTER_SCHEMA:
        raise RuntimeBindingFailClosed("CURRENT_REGISTRY_POINTER_SCHEMA_INVALID")
    if pointer.get("status") != "ACTIVE_CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY":
        raise RuntimeBindingFailClosed("CURRENT_REGISTRY_POINTER_NOT_ACTIVE")
    if pointer.get("selection_rule") != "UNIQUE_MATCH_REQUIRED__ANY_OVERLAP_FAILS_CLOSED":
        raise RuntimeBindingFailClosed("CURRENT_REGISTRY_POINTER_SELECTION_RULE_INVALID")
    target = pointer.get("target")
    if not isinstance(target, Mapping):
        raise RuntimeBindingFailClosed("CURRENT_REGISTRY_POINTER_TARGET_MISSING")
    registry_path = _canonical_path(
        target.get("path"),
        prefixes=("canonical/governance/",),
    )
    if target.get("git_blob_sha") != git_blob_sha(registry_path):
        raise RuntimeBindingFailClosed("CURRENT_REGISTRY_TARGET_BLOB_DRIFT")
    registry = _load_json(registry_path)
    if registry.get("schema") != target.get("schema") or registry.get("schema") != REGISTRY_SCHEMA:
        raise RuntimeBindingFailClosed("CURRENT_REGISTRY_TARGET_SCHEMA_INVALID")
    if registry.get("default") != "FAIL_CLOSED":
        raise RuntimeBindingFailClosed("REGISTRY_DEFAULT_NOT_FAIL_CLOSED")
    if registry.get("selection_rule") != "UNIQUE_MATCH_REQUIRED__ANY_OVERLAP_FAILS_CLOSED":
        raise RuntimeBindingFailClosed("REGISTRY_SELECTION_RULE_INVALID")
    if registry.get("selected_cover_authority") != (
        "DERIVED_ONLY_FROM_EXACT_PREDICATE_SET_PLUS_INDEPENDENT_COMPLEMENT_PROOF"
    ):
        raise RuntimeBindingFailClosed("SELECTED_COVER_AUTHORITY_INVALID")
    if not isinstance(registry.get("scope_id"), str) or not registry.get("scope_id"):
        raise RuntimeBindingFailClosed("REGISTRY_SCOPE_ID_INVALID")
    if not isinstance(registry.get("routes"), list):
        raise RuntimeBindingFailClosed("REGISTRY_ROUTES_NOT_LIST")
    return registry


def _verify_common_row(
    registry: Mapping[str, Any],
    row: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
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
    if not cell_id or not route_id:
        raise RuntimeBindingFailClosed(f"ROUTE_IDENTITY_INVALID:{index}")

    route_path = _canonical_path(
        row.get("route_path"), prefixes=("canonical/runtime/",)
    )
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
        if cert.get("cell_id") != cell_id:
            raise RuntimeBindingFailClosed(f"{name}_CELL_ID_MISMATCH:{index}")
        if cert.get("route_id") != route_id:
            raise RuntimeBindingFailClosed(f"{name}_ROUTE_ID_MISMATCH:{index}")
        if cert.get("creditable") is not row.get("creditable"):
            raise RuntimeBindingFailClosed(f"{name}_CREDITABLE_MISMATCH:{index}")

    if admission.get("admitted") is not row.get("admitted"):
        raise RuntimeBindingFailClosed(f"ADMISSION_BOOLEAN_MISMATCH:{index}")

    normalized = dict(row)
    normalized["_route_path"] = route_path
    normalized["_adequacy"] = adequacy
    normalized["_admission"] = admission
    return normalized


def _verify_creditable_payload_binding(row: Mapping[str, Any], index: int) -> None:
    if row.get("creditable") is not True:
        return
    required = (
        "payload_validator_path",
        "payload_validator_blob_sha",
        "payload_validator_callable",
    )
    if any(not row.get(key) for key in required):
        raise RuntimeBindingFailClosed(
            f"CREDITABLE_PAYLOAD_VALIDATOR_BINDING_MISSING:{index}"
        )
    validator_path = _canonical_path(
        row.get("payload_validator_path"),
        prefixes=("canonical/runtime/",),
    )
    if row.get("payload_validator_blob_sha") != git_blob_sha(validator_path):
        raise RuntimeBindingFailClosed(f"PAYLOAD_VALIDATOR_BLOB_DRIFT:{index}")
    admission = row["_admission"]
    for key in required:
        if admission.get(key) != row.get(key):
            raise RuntimeBindingFailClosed(
                f"ADMISSION_PAYLOAD_VALIDATOR_BINDING_MISMATCH:{index}:{key}"
            )


def _verify_exact_row(
    registry: Mapping[str, Any],
    row: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    out = _verify_common_row(registry, row, index)
    digest = str(row.get("context_digest") or "").strip()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise RuntimeBindingFailClosed(f"CONTEXT_DIGEST_INVALID:{index}")
    if out["_admission"].get("context_digest_sha256") != digest:
        raise RuntimeBindingFailClosed(f"ADMISSION_CONTEXT_DIGEST_MISMATCH:{index}")
    if row.get("creditable") is True:
        raise RuntimeBindingFailClosed(
            f"CREDITABLE_ROW_MUST_USE_SYMBOLIC_PREDICATE:{index}"
        )
    return out


def _verify_symbolic_row(
    registry: Mapping[str, Any],
    row: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    out = _verify_common_row(registry, row, index)
    pid = str(row.get("admission_predicate_id") or "").strip()
    if not pid:
        raise RuntimeBindingFailClosed(f"PREDICATE_ID_INVALID:{index}")
    predicate_path = _canonical_path(
        row.get("admission_predicate_path"),
        prefixes=("canonical/runtime/",),
    )
    if row.get("admission_predicate_blob_sha") != git_blob_sha(predicate_path):
        raise RuntimeBindingFailClosed(f"PREDICATE_BLOB_DRIFT:{index}")
    for cert, name in ((out["_adequacy"], "ADEQUACY"), (out["_admission"], "ADMISSION")):
        if cert.get("scope_id") != registry.get("scope_id"):
            raise RuntimeBindingFailClosed(f"{name}_SCOPE_MISMATCH:{index}")
        if cert.get("route_blob_sha") != row.get("route_blob_sha"):
            raise RuntimeBindingFailClosed(f"{name}_ROUTE_BLOB_MISMATCH:{index}")
        if cert.get("admission_predicate_id") != pid:
            raise RuntimeBindingFailClosed(f"{name}_PREDICATE_ID_MISMATCH:{index}")
        if cert.get("admission_predicate_blob_sha") != row.get("admission_predicate_blob_sha"):
            raise RuntimeBindingFailClosed(f"{name}_PREDICATE_BLOB_MISMATCH:{index}")

    if row.get("creditable") is True:
        if (
            out["_adequacy"].get("independent_verified") is not True
            or out["_adequacy"].get("exact_byte_bound") is not True
            or out["_adequacy"].get("adequate_for_predicate_region") is not True
            or out["_admission"].get("independent_verified") is not True
            or out["_admission"].get("exact_byte_bound") is not True
            or out["_admission"].get("admission_implies_route_adequacy") is not True
        ):
            raise RuntimeBindingFailClosed(f"CREDITABLE_SOUNDNESS_UNPROVED:{index}")
        sr = row.get("admission_soundness_receipt")
        if not isinstance(sr, Mapping):
            raise RuntimeBindingFailClosed(
                f"ADMISSION_SOUNDNESS_RECEIPT_REQUIRED:{index}"
            )
        if not isinstance(row.get("admission_soundness_receipt_blob_sha"), str):
            raise RuntimeBindingFailClosed(
                f"ADMISSION_SOUNDNESS_BLOB_REQUIRED:{index}"
            )
        _verify_creditable_payload_binding(out, index)

    out["_predicate_path"] = predicate_path
    return out


def _verified_rows(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    identities: set[tuple[str, str, str, str]] = set()
    predicate_ids: set[str] = set()
    for index, row in enumerate(registry.get("routes") or []):
        mode = str(row.get("match_mode") or "") if isinstance(row, Mapping) else ""
        if mode == "EXACT_DIGEST":
            normalized = _verify_exact_row(registry, row, index)
            discriminator = str(row.get("context_digest") or "")
        elif mode == "SYMBOLIC_PREDICATE":
            normalized = _verify_symbolic_row(registry, row, index)
            pid = str(row.get("admission_predicate_id") or "")
            if pid in predicate_ids:
                raise RuntimeBindingFailClosed(
                    f"PREDICATE_ID_INVALID_OR_DUPLICATE:{index}"
                )
            predicate_ids.add(pid)
            discriminator = pid
        else:
            raise RuntimeBindingFailClosed(f"MATCH_MODE_INVALID:{index}")
        identity = (
            mode,
            str(normalized.get("cell_id") or ""),
            str(normalized.get("route_id") or ""),
            discriminator,
        )
        if identity in identities:
            raise RuntimeBindingFailClosed(
                f"DUPLICATE_RUNTIME_ROUTE_IDENTITY:{index}"
            )
        identities.add(identity)
        out.append(normalized)
    return out


def verified_route_ids(registry: Mapping[str, Any] | None = None) -> list[str]:
    reg = registry if registry is not None else load_registry()
    return sorted({
        str(row.get("route_id"))
        for row in _verified_rows(reg)
        if row.get("admitted") is True
    })


def _row_matches(
    row: Mapping[str, Any],
    context: Mapping[str, Any],
    actual_digest: str,
) -> bool:
    if row.get("admitted") is not True:
        return False
    if row.get("match_mode") == "EXACT_DIGEST":
        return row.get("context_digest") == actual_digest
    fn = _load_callable(
        row["_predicate_path"],
        str(row.get("admission_predicate_callable") or ""),
        module_prefix="project_brain_admission_predicate_v5_",
    )
    result = fn(dict(context))
    if type(result) is not bool:
        raise RuntimeBindingFailClosed(
            "ADMISSION_PREDICATE_MUST_RETURN_LITERAL_BOOL"
        )
    return result


def select_route(
    context: Mapping[str, Any],
    *,
    registry: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    if not isinstance(context, Mapping):
        raise RuntimeBindingFailClosed("CONTEXT_MAPPING_REQUIRED")
    reg = registry if registry is not None else load_registry()
    rows = _verified_rows(reg)
    actual_digest = context_digest(context)
    matches = [
        row for row in rows
        if _row_matches(row, context, actual_digest)
    ]
    if not matches:
        raise RuntimeBindingFailClosed("NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT")
    if len(matches) != 1:
        detail = ",".join(
            str(row.get("match_mode")) + ":"
            + str(row.get("cell_id")) + ":"
            + str(row.get("route_id"))
            for row in matches
        )
        raise RuntimeBindingFailClosed(
            "AMBIGUOUS_CERTIFIED_ROUTE_MATCH:" + detail
        )
    return matches[0]


def preflight() -> dict[str, Any]:
    try:
        registry = load_registry()
        rows = _verified_rows(registry)
        cover = _selected_cover_state(registry, rows)
        return {
            "schema": SCHEMA,
            "status": "PASS__CURRENT_POINTER_UNIQUE_MATCH_ROUTE_RUNTIME_VALID",
            "pass": True,
            "route_row_count": len(rows),
            "route_id_count": len({
                str(row.get("route_id"))
                for row in rows if row.get("admitted") is True
            }),
            "exact_route_count": sum(
                row.get("match_mode") == "EXACT_DIGEST" for row in rows
            ),
            "symbolic_route_count": sum(
                row.get("match_mode") == "SYMBOLIC_PREDICATE" for row in rows
            ),
            "creditable_route_count": sum(
                row.get("creditable") is True for row in rows
            ),
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


def dispatch(
    context: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(context, Mapping):
        raise RuntimeBindingFailClosed("CONTEXT_MAPPING_REQUIRED")
    if not isinstance(payload, Mapping):
        raise RuntimeBindingFailClosed("PAYLOAD_MAPPING_REQUIRED")

    registry = load_registry()
    selected = select_route(context, registry=registry)
    actual_context_digest = context_digest(context)
    bound_payload_digest = None
    if selected.get("creditable") is True:
        bound_payload_digest = _validate_creditable_payload(
            selected,
            cell_id=str(selected["cell_id"]),
            context=context,
            payload=payload,
            actual_context_digest=actual_context_digest,
        )

    route_fn = _load_callable(
        selected["_route_path"],
        str(selected.get("callable") or ""),
        module_prefix="project_brain_selected_route_v5_",
    )
    result = route_fn(dict(payload))
    if not isinstance(result, Mapping):
        raise RuntimeBindingFailClosed("ROUTE_RESULT_NOT_MAPPING")

    rows = _verified_rows(registry)
    cover = _selected_cover_state(registry, rows)
    return {
        "schema": SCHEMA,
        "status": "PASS__CERTIFICATE_GATED_ROUTE_EXECUTED_UNIQUE_MATCH",
        "actual_context_digest": actual_context_digest,
        "payload_sha256": bound_payload_digest,
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
            "CURRENT_CONTENT_ADDRESSED_REGISTRY__UNIQUE_MATCH_ONLY__"
            "CREDITABLE_PAYLOAD_BINDING_REQUIRED__ANY_OVERLAP_FAILS_CLOSED"
        ),
    }
