"""Fail-closed reducer for the Composition P2 ingress-only provenance theorem.

The theorem is deliberately conditional.  It proves that once the composition
runtime is content-bound and no-bypass, load-bearing provenance completeness can
be reduced to certificates on external-evidence ingress action types plus
certificates that pure action types perform no external evidence reads.

It grants no acceptance credit by itself.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_COMPOSITION_P2_INGRESS_ONLY_CERTIFICATE_V1"
OUT_SCHEMA = "PROJECT_BRAIN_COMPOSITION_P2_INGRESS_ONLY_REDUCTION_V1"
_SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class ReductionError(ValueError):
    pass


def _true(obj: Mapping[str, Any], key: str) -> None:
    if obj.get(key) is not True:
        raise ReductionError("REQUIRED_TRUE:" + key)


def _sha(obj: Mapping[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ReductionError("INVALID_CONTENT_HASH:" + key)
    return value


def _token(obj: Mapping[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReductionError("INVALID_TOKEN:" + key)
    return value.strip()


def reduce_certificate(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise ReductionError("CERTIFICATE_NOT_OBJECT")
        if cert.get("schema") != SCHEMA:
            raise ReductionError("SCHEMA_MISMATCH")
        scope_id = _token(cert, "exact_scope_id")
        _sha(cert, "runtime_scope_sha")
        _true(cert, "verified_initial_inputs_content_bound")
        _true(cert, "external_nondeterminism_is_evidence_ingress")

        route = cert.get("runtime_route_totality")
        if not isinstance(route, Mapping):
            raise ReductionError("RUNTIME_ROUTE_TOTALITY_INVALID")
        _true(route, "all_admissible_composition_macrosteps_use_declared_action_types")
        _true(route, "capsule_v2_no_bypass")
        _true(route, "action_type_set_complete")
        _sha(route, "independent_scope_receipt_sha")

        rows = cert.get("action_types")
        if (
            not isinstance(rows, Sequence)
            or isinstance(rows, (str, bytes, bytearray))
            or not rows
        ):
            raise ReductionError("ACTION_TYPES_INVALID")

        seen: set[str] = set()
        ingress: list[str] = []
        pure: list[str] = []
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise ReductionError(f"ACTION_TYPE_{index}_INVALID")
            action_type = _token(row, "action_type")
            if action_type in seen:
                raise ReductionError("DUPLICATE_ACTION_TYPE:" + action_type)
            seen.add(action_type)
            _sha(row, "implementation_blob_sha")
            _sha(row, "independent_receipt_sha")
            _true(row, "capsule_v2_bound")
            _true(row, "output_lineage_binds_exact_action_result")

            cls = row.get("class")
            if cls == "PURE":
                _true(row, "no_external_evidence_reads")
                pure.append(action_type)
            elif cls == "INGRESS":
                _true(row, "external_evidence_input_totality")
                _true(row, "source_identity_content_bound")
                _true(row, "payload_content_bound")
                _true(row, "no_unreturned_load_bearing_evidence")
                ingress.append(action_type)
            else:
                raise ReductionError("UNKNOWN_ACTION_CLASS:" + str(cls))

        return {
            "schema": OUT_SCHEMA,
            "status": "PASS__P2_FOLLOWS_FOR_EXACT_SCOPE_IF_RECEIPTS_ARE_INDEPENDENT_AND_SEMANTICALLY_VALID",
            "exact_scope_id": scope_id,
            "action_type_count": len(rows),
            "ingress_action_types": sorted(ingress),
            "pure_action_types": sorted(pure),
            "proof": [
                "BASE__VERIFIED_INITIAL_INPUTS_ARE_CONTENT_BOUND",
                "INDUCTION_PURE__PURE_ACTION_READS_ONLY_PROVENANCE_COMPLETE_CAPSULE_STATE__EXACT_ACTION_AND_RESULT_ARE_BOUND__OUTPUT_LINEAGE_INHERITS_COMPLETE_PROVENANCE",
                "INDUCTION_INGRESS__ALL_EXTERNAL_LOAD_BEARING_EVIDENCE_IS_RETURNED_WITH_CONTENT_BOUND_SOURCE_IDENTITY_AND_PAYLOAD__EXACT_ACTION_AND_RESULT_ARE_BOUND__OUTPUT_LINEAGE_EXTENDS_COMPLETE_PROVENANCE",
                "CLOSURE__EVERY_ADMISSIBLE_MACROSTEP_IS_ONE_OF_THE_CERTIFIED_ACTION_TYPES_AND_CAPSULE_V2_HAS_NO_BYPASS",
                "THEREFORE__EVERY_LOAD_BEARING_OUTPUT_IN_THE_EXACT_SCOPE_HAS_COMPLETE_PROVENANCE_TO_VERIFIED_INITIAL_INPUTS_OR_CONTENT_BOUND_EXTERNAL_INGRESS_EVIDENCE",
            ],
            "p2_load_bearing_provenance_completeness": True,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
    except Exception as exc:
        return {
            "schema": OUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "p2_load_bearing_provenance_completeness": False,
            "acceptance_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
