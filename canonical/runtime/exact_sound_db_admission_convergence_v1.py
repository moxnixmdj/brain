"""Compile the flattened sound D_B regions into one exact admission predicate set.

This gate is deliberately fail-closed. A region is complement-ready only when the
source, Brain-owned route, executable admission predicate, adequacy certificate,
and independent admission-soundness receipt all exist inside the repository and
match their declared Git blob SHAs. Semantic soundness is read from the bound
receipt bytes, never from caller-supplied booleans.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.content_bound_artifact_v1 import load_bound_json, resolve_bound_file
from canonical.runtime.predicate_selected_cover_complement_gate_v1 import predicate_set_digest

SCHEMA = "PROJECT_BRAIN_EXACT_SOUND_DB_ADMISSION_CONVERGENCE_V1"
SCOPE_ID = "scope://opus55/observable-trace"
ROOT = Path(__file__).resolve().parents[2]

_REQUIRED_BINDING_TEXT = (
    "route_id",
    "route_path",
    "admission_predicate_id",
    "admission_predicate_path",
    "adequacy_certificate_path",
    "admission_soundness_receipt_path",
)
_REQUIRED_BINDING_SHA = (
    "source_artifact_blob_sha",
    "route_blob_sha",
    "admission_predicate_blob_sha",
    "adequacy_certificate_blob_sha",
    "admission_soundness_receipt_blob_sha",
)


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "complement_ready": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _receipt_errors(
    receipt: Mapping[str, Any],
    *,
    region_id: str,
    route_id: str,
    predicate_id: str,
    route_blob_sha: str,
    predicate_blob_sha: str,
    adequacy_blob_sha: str,
) -> list[str]:
    errors: list[str] = []
    if receipt.get("independent_verified") is not True:
        errors.append("RECEIPT_INDEPENDENT_VERIFICATION_MISSING")
    if receipt.get("exact_byte_bound") is not True:
        errors.append("RECEIPT_EXACT_BYTE_BINDING_MISSING")
    if receipt.get("conclusion") != "success":
        errors.append("RECEIPT_SUCCESS_CONCLUSION_MISSING")
    if receipt.get("admission_implies_route_adequacy") is not True:
        errors.append("RECEIPT_ADMISSION_SOUNDNESS_MISSING")
    if receipt.get("brain_owned_route") is not True:
        errors.append("RECEIPT_BRAIN_OWNERSHIP_MISSING")
    if str(receipt.get("scope_id") or "") != SCOPE_ID:
        errors.append("RECEIPT_SCOPE_MISMATCH")

    receipt_region = str(receipt.get("region_id") or receipt.get("cell_id") or "")
    if receipt_region != region_id:
        errors.append("RECEIPT_REGION_MISMATCH")
    if str(receipt.get("route_id") or "") != route_id:
        errors.append("RECEIPT_ROUTE_MISMATCH")
    if str(receipt.get("admission_predicate_id") or "") != predicate_id:
        errors.append("RECEIPT_PREDICATE_MISMATCH")
    if receipt.get("route_blob_sha") != route_blob_sha:
        errors.append("RECEIPT_ROUTE_BLOB_MISMATCH")
    if receipt.get("admission_predicate_blob_sha") != predicate_blob_sha:
        errors.append("RECEIPT_PREDICATE_BLOB_MISMATCH")
    if receipt.get("adequacy_certificate_blob_sha") != adequacy_blob_sha:
        errors.append("RECEIPT_ADEQUACY_BLOB_MISMATCH")
    return errors


def compile_region_set(
    flattened: Mapping[str, Any],
    bindings: Sequence[Mapping[str, Any]],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = repo_root or ROOT

    if not isinstance(flattened, Mapping):
        return _fail("FLATTENED_ROOT_INPUT_MAPPING_REQUIRED")
    if flattened.get("schema") != "PROJECT_BRAIN_EXACT_SOUND_DB_REGION_SET_ROOT_INPUT_V1":
        return _fail("FLATTENED_ROOT_INPUT_SCHEMA_INVALID")

    regions = flattened.get("regions")
    if not isinstance(regions, list) or not regions:
        return _fail("FLATTENED_REGIONS_REQUIRED")

    region_ids: list[str] = []
    source_by_region: dict[str, str] = {}
    for index, row in enumerate(regions):
        if not isinstance(row, Mapping):
            return _fail("REGION_NOT_MAPPING", index=index)
        rid = str(row.get("id") or "").strip()
        source = str(row.get("source_path") or "").strip()
        if not rid or not source:
            return _fail("REGION_ID_OR_SOURCE_MISSING", index=index)
        if rid in source_by_region:
            return _fail("REGION_ID_DUPLICATE", region_id=rid)
        region_ids.append(rid)
        source_by_region[rid] = source

    declared_count = (flattened.get("flattening_checks") or {}).get("region_count")
    if declared_count != len(region_ids):
        return _fail(
            "DECLARED_REGION_COUNT_MISMATCH",
            declared=declared_count,
            actual=len(region_ids),
        )

    if not isinstance(bindings, Sequence) or isinstance(bindings, (str, bytes)):
        return _fail("BINDINGS_SEQUENCE_REQUIRED")

    binding_by_region: dict[str, Mapping[str, Any]] = {}
    unknown: list[str] = []
    duplicate: list[str] = []
    for row in bindings:
        if not isinstance(row, Mapping):
            return _fail("BINDING_NOT_MAPPING")
        rid = str(row.get("region_id") or "").strip()
        if rid not in source_by_region:
            unknown.append(rid or "<missing>")
            continue
        if rid in binding_by_region:
            duplicate.append(rid)
            continue
        binding_by_region[rid] = row

    if unknown:
        return _fail("UNKNOWN_REGION_BINDING", region_ids=sorted(set(unknown)))
    if duplicate:
        return _fail("DUPLICATE_REGION_BINDING", region_ids=sorted(set(duplicate)))

    missing: list[dict[str, Any]] = []
    normalized_routes: list[dict[str, Any]] = []
    seen_route_ids: set[str] = set()
    seen_predicate_ids: set[str] = set()

    for rid in region_ids:
        row = binding_by_region.get(rid)
        if row is None:
            missing.append(
                {
                    "region_id": rid,
                    "source_path": source_by_region[rid],
                    "missing": ["BINDING"],
                }
            )
            continue

        errors: list[str] = []
        if str(row.get("scope_id") or "") != SCOPE_ID:
            errors.append("SCOPE_ID_INVALID")
        if str(row.get("source_path") or "") != source_by_region[rid]:
            errors.append("SOURCE_PATH_MISMATCH")

        for field in _REQUIRED_BINDING_TEXT:
            if not isinstance(row.get(field), str) or not str(row.get(field)).strip():
                errors.append(f"MISSING:{field}")
        for field in _REQUIRED_BINDING_SHA:
            value = row.get(field)
            if not isinstance(value, str) or len(value) != 40 or any(
                ch not in "0123456789abcdef" for ch in value
            ):
                errors.append(f"INVALID_GIT_BLOB_SHA:{field}")

        route_id = str(row.get("route_id") or "").strip()
        predicate_id = str(row.get("admission_predicate_id") or "").strip()
        if route_id and route_id in seen_route_ids:
            errors.append("ROUTE_ID_DUPLICATE")
        if predicate_id and predicate_id in seen_predicate_ids:
            errors.append("ADMISSION_PREDICATE_ID_DUPLICATE")

        exact_files = (
            ("source_artifact", source_by_region[rid], row.get("source_artifact_blob_sha")),
            ("route", row.get("route_path"), row.get("route_blob_sha")),
            (
                "admission_predicate",
                row.get("admission_predicate_path"),
                row.get("admission_predicate_blob_sha"),
            ),
            (
                "adequacy_certificate",
                row.get("adequacy_certificate_path"),
                row.get("adequacy_certificate_blob_sha"),
            ),
            (
                "admission_soundness_receipt",
                row.get("admission_soundness_receipt_path"),
                row.get("admission_soundness_receipt_blob_sha"),
            ),
        )
        if not errors:
            for name, path_value, blob_sha in exact_files:
                _, error = resolve_bound_file(path_value, blob_sha, root)
                if error is not None:
                    errors.append(f"UNBOUND:{name}:{error}")

        receipt: Mapping[str, Any] | None = None
        if not errors:
            receipt, error = load_bound_json(
                row.get("admission_soundness_receipt_path"),
                row.get("admission_soundness_receipt_blob_sha"),
                root,
            )
            if error is not None:
                errors.append(f"UNBOUND:admission_soundness_receipt:{error}")
            elif receipt is not None:
                errors.extend(
                    _receipt_errors(
                        receipt,
                        region_id=rid,
                        route_id=route_id,
                        predicate_id=predicate_id,
                        route_blob_sha=str(row["route_blob_sha"]),
                        predicate_blob_sha=str(row["admission_predicate_blob_sha"]),
                        adequacy_blob_sha=str(row["adequacy_certificate_blob_sha"]),
                    )
                )

        if errors:
            missing.append(
                {
                    "region_id": rid,
                    "source_path": source_by_region[rid],
                    "missing": sorted(set(errors)),
                }
            )
            continue

        seen_route_ids.add(route_id)
        seen_predicate_ids.add(predicate_id)
        normalized_routes.append(
            {
                "cell_id": rid,
                "route_id": route_id,
                "route_path": row["route_path"],
                "route_blob_sha": row["route_blob_sha"],
                "admission_predicate_id": predicate_id,
                "admission_predicate_path": row["admission_predicate_path"],
                "admission_predicate_blob_sha": row["admission_predicate_blob_sha"],
                "adequacy_certificate_path": row["adequacy_certificate_path"],
                "adequacy_certificate_blob_sha": row["adequacy_certificate_blob_sha"],
                "admission_soundness_receipt_path": row[
                    "admission_soundness_receipt_path"
                ],
                "admission_soundness_receipt_blob_sha": row[
                    "admission_soundness_receipt_blob_sha"
                ],
                "source_path": source_by_region[rid],
                "source_artifact_blob_sha": row["source_artifact_blob_sha"],
            }
        )

    if missing:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "INCOMPLETE__EXACT_BINDINGS_REQUIRED",
            "scope_id": SCOPE_ID,
            "region_count": len(region_ids),
            "bound_region_count": len(normalized_routes),
            "missing_region_count": len(missing),
            "missing_bindings": missing,
            "complement_ready": False,
            "u_empty_authorized": False,
            "abc_closed_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "scheduler_rule": (
                "WORK_ONLY_THE_LISTED_MISSING_BINDINGS__DO_NOT_REOPEN_FAMILY_OR_"
                "BENCHMARK_PROGRAMS_UNLESS_ONE_IS_REQUIRED_TO_PRODUCE_A_LISTED_BINDING"
            ),
        }

    digest = predicate_set_digest(SCOPE_ID, normalized_routes)
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__EXACT_SOUND_ADMISSION_PREDICATE_SET_READY_FOR_COMPLEMENT_PROOF",
        "scope_id": SCOPE_ID,
        "region_count": len(region_ids),
        "bound_region_count": len(normalized_routes),
        "missing_region_count": 0,
        "routes": sorted(
            normalized_routes,
            key=lambda x: (x["admission_predicate_id"], x["route_id"], x["cell_id"]),
        ),
        "predicate_set_sha256": digest,
        "complement_ready": True,
        "next_only_action": (
            "PROVE_S_TRACE_AND_NOT_ANY_SOUND_ADMISSION_PREDICATE_UNSAT_OR_RETURN_"
            "ONE_CONSTRUCTIVE_COUNTEREXAMPLE"
        ),
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
