"""Exact convergence gate for the flattened sound D_B region set.

This module does one deliberately narrow job: convert the current flattened sound
D_B regions into the exact creditable predicate-set input expected by the
selected-cover complement gate. It never infers executable membership predicates
from prose and never grants U-empty/ABC/terminal credit.

A region becomes complement-ready only when a content-addressed, independently
verified binding supplies:
  * a symbolic admission predicate,
  * a Brain-owned route,
  * an adequacy certificate, and
  * an admission-soundness receipt proving admission => route adequacy.

The output is therefore either the exact predicate set to send to the existing
complement gate, or the exact missing bindings. No benchmark/family detour is
created here.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.predicate_selected_cover_complement_gate_v1 import (
    predicate_set_digest,
)

SCHEMA = "PROJECT_BRAIN_EXACT_SOUND_DB_ADMISSION_CONVERGENCE_V1"
SCOPE_ID = "scope://opus55/observable-trace"

_REQUIRED_BINDING_TEXT = (
    "route_id",
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
_REQUIRED_TRUE = (
    "independent_verified",
    "exact_byte_bound",
    "brain_owned_route",
    "admission_implies_route_adequacy",
)


def _hex40(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(ch in "0123456789abcdef" for ch in value)
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


def compile_region_set(
    flattened: Mapping[str, Any],
    bindings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
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
            if not _hex40(row.get(field)):
                errors.append(f"INVALID_GIT_BLOB_SHA:{field}")
        for field in _REQUIRED_TRUE:
            if row.get(field) is not True:
                errors.append(f"NOT_PROVED:{field}")

        route_id = str(row.get("route_id") or "").strip()
        predicate_id = str(row.get("admission_predicate_id") or "").strip()
        if route_id and route_id in seen_route_ids:
            errors.append("ROUTE_ID_DUPLICATE")
        if predicate_id and predicate_id in seen_predicate_ids:
            errors.append("ADMISSION_PREDICATE_ID_DUPLICATE")

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
                "admission_predicate_id": predicate_id,
                "admission_predicate_blob_sha": row["admission_predicate_blob_sha"],
                "adequacy_certificate_blob_sha": row["adequacy_certificate_blob_sha"],
                "admission_soundness_receipt_blob_sha": row[
                    "admission_soundness_receipt_blob_sha"
                ],
                "source_path": source_by_region[rid],
                "source_artifact_blob_sha": row["source_artifact_blob_sha"],
                "route_blob_sha": row["route_blob_sha"],
                "admission_predicate_path": row["admission_predicate_path"],
                "adequacy_certificate_path": row["adequacy_certificate_path"],
                "admission_soundness_receipt_path": row[
                    "admission_soundness_receipt_path"
                ],
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
