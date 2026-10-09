"""Certificate-gated selected-route runtime entrypoint V3.

V3 removes registry-version identity from the live runtime. It resolves one
content-addressed current-registry pointer and supports both exact-context and
content-addressed symbolic-predicate rows. Selection is globally unique:
any overlap fails closed instead of being resolved by lexical order.

V2 remains immutable historical evidence for its exact-context/payload-binding
contract. V3 preserves the same creditable payload-attestation requirement.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_ENTRYPOINT_V3"
POINTER_SCHEMA = "PROJECT_BRAIN_CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY_POINTER_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V3"
CURRENT_REGISTRY_POINTER_PATH = ROOT / "canonical/governance/CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY.json"
MATCH_MODES = {"EXACT_CONTEXT_DIGEST", "SYMBOLIC_PREDICATE_CALLABLE"}


class RuntimeBindingFailClosed(RuntimeError):
    pass


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _canonical_json_digest(value: Mapping[str, Any], *, label: str) -> str:
    if not isinstance(value, Mapping):
        raise RuntimeBindingFailClosed(label + "_MAPPING_REQUIRED")
    try:
        raw = json.dumps(
            dict(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RuntimeBindingFailClosed(label + "_NOT_CANONICAL_JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def context_digest(context: Mapping[str, Any]) -> str:
    return _canonical_json_digest(context, label="CONTEXT")


def payload_digest(payload: Mapping[str, Any]) -> str:
    return _canonical_json_digest(payload, label="PAYLOAD")


def _canonical_path(raw: Any, *, prefixes: tuple[str, ...]) -> Path:
    value = str(raw or "").strip()
    p = Path(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise RuntimeBindingFailClosed("NONCANONICAL_PATH")
    if not any(value.startswith(prefix) for prefix in prefixes):
        raise RuntimeBindingFailClosed("PATH_OUTSIDE_ALLOWED_CANONICAL_SCOPE")
    full = ROOT / p
    if not full.is_file():
        raise RuntimeBindingFailClosed("BOUND_FILE_MISSING:" + value)
    return full


def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeBindingFailClosed(
            "BOUND_JSON_INVALID:" + str(path.relative_to(ROOT) if ROOT in path.parents else path)
        ) from exc
    if not isinstance(value, Mapping):
        raise RuntimeBindingFailClosed("BOUND_JSON_NOT_OBJECT")
    return value


def _load_callable(path: Path, callable_name: str, *, module_prefix: str):
    if not callable_name:
        raise RuntimeBindingFailClosed("CALLABLE_MISSING")
    blob = git_blob_sha(path)
    module_name = module_prefix + blob
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeBindingFailClosed("IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    fn = getattr(module, callable_name, None)
    if not callable(fn):
        raise RuntimeBindingFailClosed("CALLABLE_INVALID")
    return fn


def load_registry(pointer_path: str | Path = CURRENT_REGISTRY_POINTER_PATH) -> Mapping[str, Any]:
    pointer = _load_json(Path(pointer_path))
    if pointer.get("schema") != POINTER_SCHEMA:
        raise RuntimeBindingFailClosed("CURRENT_REGISTRY_POINTER_SCHEMA_INVALID")
    if pointer.get("status") != "ACTIVE_CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY":
        raise RuntimeBindingFailClosed("CURRENT_REGISTRY_POINTER_NOT_ACTIVE")
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
    if target.get("schema") != registry.get("schema") or registry.get("schema") != REGISTRY_SCHEMA:
        raise RuntimeBindingFailClosed("CURRENT_REGISTRY_TARGET_SCHEMA_INVALID")
    if registry.get("default") != "FAIL_CLOSED":
        raise RuntimeBindingFailClosed("REGISTRY_DEFAULT_NOT_FAIL_CLOSED")
    if registry.get("selection_rule") != "UNIQUE_MATCH_REQUIRED__ANY_EXACT_SYMBOLIC_OR_SYMBOLIC_SYMBOLIC_OVERLAP_FAILS_CLOSED":
        raise RuntimeBindingFailClosed("REGISTRY_SELECTION_RULE_INVALID")
    if type(registry.get("selected_cover_complete")) is not bool:
        raise RuntimeBindingFailClosed("REGISTRY_SELECTED_COVER_FLAG_INVALID")
    if not isinstance(registry.get("routes"), list):
        raise RuntimeBindingFailClosed("REGISTRY_ROUTES_NOT_LIST")
    return registry


def _verify_payload_attestation(
    attestation: Mapping[str, Any],
    *,
    cell_id: str,
    actual_context_digest: str,
    actual_payload_digest: str,
) -> None:
    if not isinstance(attestation, Mapping):
        raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_NOT_MAPPING")
    if attestation.get("admitted") is not True:
        raise RuntimeBindingFailClosed("PAYLOAD_NOT_ADMITTED_TO_SELECTED_CELL")
    if attestation.get("cell_id") != cell_id:
        raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_CELL_MISMATCH")
    if attestation.get("context_digest_sha256") != actual_context_digest:
        raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_CONTEXT_MISMATCH")
    if attestation.get("payload_sha256") != actual_payload_digest:
        raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_DIGEST_MISMATCH")


def _validate_creditable_payload(
    row: Mapping[str, Any],
    *,
    cell_id: str,
    context: Mapping[str, Any],
    payload: Mapping[str, Any],
    actual_context_digest: str,
) -> str:
    required = (
        "payload_validator_path",
        "payload_validator_blob_sha",
        "payload_validator_callable",
    )
    if any(not row.get(key) for key in required):
        raise RuntimeBindingFailClosed("CREDITABLE_PAYLOAD_VALIDATOR_BINDING_MISSING")
    validator_path = _canonical_path(
        row.get("payload_validator_path"),
        prefixes=("canonical/runtime/",),
    )
    if row.get("payload_validator_blob_sha") != git_blob_sha(validator_path):
        raise RuntimeBindingFailClosed("PAYLOAD_VALIDATOR_BLOB_DRIFT")
    fn = _load_callable(
        validator_path,
        str(row.get("payload_validator_callable") or ""),
        module_prefix="project_brain_payload_validator_v3_",
    )
    actual_payload_digest = payload_digest(payload)
    attestation = fn(dict(context), dict(payload))
    _verify_payload_attestation(
        attestation,
        cell_id=cell_id,
        actual_context_digest=actual_context_digest,
        actual_payload_digest=actual_payload_digest,
    )
    return actual_payload_digest


def _verify_common_row(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise RuntimeBindingFailClosed(f"ROUTE_ROW_NOT_OBJECT:{index}")
    mode = str(row.get("match_mode") or "")
    if mode not in MATCH_MODES:
        raise RuntimeBindingFailClosed(f"ROUTE_MATCH_MODE_INVALID:{index}")
    if type(row.get("admitted")) is not bool:
        raise RuntimeBindingFailClosed(f"ROUTE_ADMISSION_NOT_LITERAL_BOOL:{index}")
    if type(row.get("creditable")) is not bool:
        raise RuntimeBindingFailClosed(f"ROUTE_CREDITABLE_NOT_LITERAL_BOOL:{index}")

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
        if cert.get("cell_id") != row.get("cell_id"):
            raise RuntimeBindingFailClosed(f"{name}_CELL_ID_MISMATCH:{index}")
        if cert.get("route_id") != row.get("route_id"):
            raise RuntimeBindingFailClosed(f"{name}_ROUTE_ID_MISMATCH:{index}")

    if admission.get("admitted") is not row.get("admitted"):
        raise RuntimeBindingFailClosed(f"ADMISSION_BOOLEAN_MISMATCH:{index}")
    if adequacy.get("creditable") is not row.get("creditable"):
        raise RuntimeBindingFailClosed(f"ADEQUACY_CREDITABLE_MISMATCH:{index}")
    if admission.get("creditable") is not row.get("creditable"):
        raise RuntimeBindingFailClosed(f"ADMISSION_CREDITABLE_MISMATCH:{index}")

    out = dict(row)
    out["_route_path_obj"] = route_path
    out["_adequacy"] = adequacy
    out["_admission"] = admission
    return out


def _verify_exact_row(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    out = _verify_common_row(row, index)
    digest = str(row.get("context_digest") or "")
    if len(digest) != 64:
        raise RuntimeBindingFailClosed(f"EXACT_CONTEXT_DIGEST_INVALID:{index}")
    if out["_admission"].get("context_digest_sha256") != digest:
        raise RuntimeBindingFailClosed(f"ADMISSION_CONTEXT_DIGEST_MISMATCH:{index}")
    return out


def _verify_symbolic_row(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    out = _verify_common_row(row, index)
    for key in ("scope_id", "admission_predicate_id", "admission_predicate_path",
                "admission_predicate_blob_sha", "admission_predicate_callable"):
        if not str(row.get(key) or "").strip():
            raise RuntimeBindingFailClosed(f"SYMBOLIC_BINDING_MISSING:{index}:{key}")
    predicate_path = _canonical_path(
        row.get("admission_predicate_path"),
        prefixes=("canonical/runtime/",),
    )
    if row.get("admission_predicate_blob_sha") != git_blob_sha(predicate_path):
        raise RuntimeBindingFailClosed(f"SYMBOLIC_PREDICATE_BLOB_DRIFT:{index}")
    for cert, name in ((out["_adequacy"], "ADEQUACY"), (out["_admission"], "ADMISSION")):
        if cert.get("scope_id") != row.get("scope_id"):
            raise RuntimeBindingFailClosed(f"{name}_SCOPE_MISMATCH:{index}")
        if cert.get("admission_predicate_id") != row.get("admission_predicate_id"):
            raise RuntimeBindingFailClosed(f"{name}_PREDICATE_ID_MISMATCH:{index}")
        if cert.get("admission_predicate_blob_sha") != row.get("admission_predicate_blob_sha"):
            raise RuntimeBindingFailClosed(f"{name}_PREDICATE_BLOB_MISMATCH:{index}")
    if row.get("creditable") is True:
        if out["_adequacy"].get("independent_verified") is not True:
            raise RuntimeBindingFailClosed(f"CREDITABLE_SYMBOLIC_ADEQUACY_NOT_INDEPENDENT:{index}")
        if out["_admission"].get("independent_verified") is not True:
            raise RuntimeBindingFailClosed(f"CREDITABLE_SYMBOLIC_ADMISSION_NOT_INDEPENDENT:{index}")
        if out["_admission"].get("admission_implies_route_adequacy") is not True:
            raise RuntimeBindingFailClosed(f"CREDITABLE_SYMBOLIC_SOUNDNESS_UNPROVED:{index}")
    out["_predicate_path_obj"] = predicate_path
    return out


def _verified_rows(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    identities: set[tuple[str, str, str]] = set()
    for index, row in enumerate(registry.get("routes") or []):
        mode = str(row.get("match_mode") or "") if isinstance(row, Mapping) else ""
        if mode == "EXACT_CONTEXT_DIGEST":
            bound = _verify_exact_row(row, index)
        elif mode == "SYMBOLIC_PREDICATE_CALLABLE":
            bound = _verify_symbolic_row(row, index)
        else:
            raise RuntimeBindingFailClosed(f"ROUTE_MATCH_MODE_INVALID:{index}")
        identity = (mode, str(bound.get("cell_id") or ""), str(bound.get("route_id") or ""))
        if identity in identities:
            raise RuntimeBindingFailClosed("DUPLICATE_RUNTIME_ROUTE_IDENTITY")
        identities.add(identity)
        verified.append(bound)
    return verified


def verified_route_ids(registry: Mapping[str, Any] | None = None) -> list[str]:
    reg = registry if registry is not None else load_registry()
    return sorted({
        str(row.get("route_id"))
        for row in _verified_rows(reg)
        if row.get("admitted") is True
    })


def _row_matches(row: Mapping[str, Any], context: Mapping[str, Any], actual_digest: str) -> bool:
    if row.get("admitted") is not True:
        return False
    mode = row.get("match_mode")
    if mode == "EXACT_CONTEXT_DIGEST":
        return row.get("context_digest") == actual_digest
    if mode == "SYMBOLIC_PREDICATE_CALLABLE":
        fn = _load_callable(
            row["_predicate_path_obj"],
            str(row.get("admission_predicate_callable") or ""),
            module_prefix="project_brain_symbolic_predicate_v3_",
        )
        result = fn(dict(context))
        if type(result) is not bool:
            raise RuntimeBindingFailClosed("SYMBOLIC_PREDICATE_RESULT_NOT_LITERAL_BOOL")
        return result
    raise RuntimeBindingFailClosed("ROUTE_MATCH_MODE_UNIMPLEMENTED")


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
    matches = [row for row in rows if _row_matches(row, context, actual_digest)]
    if not matches:
        raise RuntimeBindingFailClosed("NO_CERTIFIED_ROUTE_MATCH")
    if len(matches) != 1:
        detail = ",".join(
            str(row.get("match_mode")) + ":" + str(row.get("cell_id")) + ":" + str(row.get("route_id"))
            for row in matches
        )
        raise RuntimeBindingFailClosed("AMBIGUOUS_CERTIFIED_ROUTE_MATCH:" + detail)
    return matches[0]


def preflight() -> dict[str, Any]:
    try:
        registry = load_registry()
        rows = _verified_rows(registry)
        return {
            "schema": SCHEMA,
            "status": "PASS__CURRENT_CONTENT_ADDRESSED_MULTI_MATCH_REGISTRY_VALID",
            "pass": True,
            "route_row_count": len(rows),
            "route_id_count": len({str(row.get("route_id")) for row in rows if row.get("admitted") is True}),
            "match_modes": sorted({str(row.get("match_mode")) for row in rows}),
            "selected_cover_complete": registry.get("selected_cover_complete") is True,
            "terminal_credit_delta": 0,
        }
    except RuntimeBindingFailClosed as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_credit_delta": 0,
        }


def dispatch(context: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise RuntimeBindingFailClosed("PAYLOAD_MAPPING_REQUIRED")
    actual_context_digest = context_digest(context)
    row = select_route(context)
    bound_payload_digest = None
    if row.get("creditable") is True:
        bound_payload_digest = _validate_creditable_payload(
            row,
            cell_id=str(row.get("cell_id") or ""),
            context=context,
            payload=payload,
            actual_context_digest=actual_context_digest,
        )
    fn = _load_callable(
        row["_route_path_obj"],
        str(row.get("callable") or ""),
        module_prefix="project_brain_selected_route_v3_",
    )
    result = fn(dict(payload))
    if not isinstance(result, Mapping):
        raise RuntimeBindingFailClosed("ROUTE_RESULT_NOT_MAPPING")
    return {
        "schema": SCHEMA,
        "status": "PASS__CERTIFICATE_GATED_ROUTE_EXECUTED",
        "actual_context_digest": actual_context_digest,
        "payload_sha256": bound_payload_digest,
        "selected_match_mode": row.get("match_mode"),
        "selected_cell_id": row.get("cell_id"),
        "selected_route_id": row.get("route_id"),
        "route_blob_sha": row.get("route_blob_sha"),
        "adequacy_certificate_blob_sha": row.get("adequacy_certificate_blob_sha"),
        "admission_certificate_blob_sha": row.get("admission_certificate_blob_sha"),
        "creditable": row.get("creditable") is True,
        "result": dict(result),
        "selected_cover_complete": False,
        "terminal_credit_delta": 0,
        "rule": "ONE_CURRENT_CONTENT_ADDRESSED_REGISTRY__UNIQUE_MATCH_ONLY__OVERLAP_FAILS_CLOSED",
    }
