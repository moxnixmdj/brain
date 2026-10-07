from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.p2_membership_residual_localizer_v1 import localize as localize_p2
from canonical.runtime.professional_source_authority_coverage_gate_v1 import verify as verify_structural
from canonical.runtime.source_positive_adequacy_db_admission_v1 import evaluate as evaluate_positive_adequacy

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_POSITIVE_ADEQUACY_ESCAPE_ROUTER_V1"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "selected_route": None,
        "full_semantic_manifest_required_for_selected_cell": None,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
    }
    out.update(extra)
    return out


def _raw_text(raw_source: str | bytes) -> str | None:
    if isinstance(raw_source, str):
        return raw_source
    if isinstance(raw_source, bytes):
        try:
            return raw_source.decode("utf-8")
        except UnicodeDecodeError:
            return None
    return None


def route(
    raw_source: str | bytes,
    *,
    source_id: str,
    structural_manifest: Mapping[str, Any],
    positive_adequacy_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    text = _raw_text(raw_source)
    if text is None or not text:
        return _fail("RAW_SOURCE_UTF8_TEXT_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        return _fail("SOURCE_ID_REQUIRED")
    if not isinstance(structural_manifest, Mapping):
        return _fail("STRUCTURAL_MANIFEST_REQUIRED")

    structural = verify_structural(structural_manifest)
    if structural.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED__DECLARED_STRUCTURAL_OMISSION",
            "pass": False,
            "selected_route": None,
            "structural_preflight": structural,
            "next_action": "REPAIR_ONLY_THE_FIRST_DECLARED_SOURCE_DIMENSION_OR_CONVENTION_OMISSION",
            "full_semantic_manifest_required_for_selected_cell": None,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "acceptance_credit_delta": 0,
        }

    membership = localize_p2(
        raw_source,
        source_id=source_id,
        structural_manifest=structural_manifest,
    )
    if membership.get("membership_proved") is True:
        return {
            "schema": SCHEMA,
            "status": "PASS__EXACT_P2_MEMBERSHIP_ROUTE",
            "pass": True,
            "selected_route": "EXACT_P2_MEMBERSHIP",
            "structural_preflight": structural,
            "membership": membership,
            "full_semantic_manifest_required_for_selected_cell": False,
            "reason": "EXACT_P2_MEMBERSHIP_ALREADY_PROVED",
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "acceptance_credit_delta": 0,
        }

    if positive_adequacy_payload is None:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED__TRY_POSITIVE_ADEQUACY_BEFORE_FULL_SEMANTIC_COMPLETION",
            "pass": False,
            "selected_route": None,
            "structural_preflight": structural,
            "membership": membership,
            "p2_first_residual_class": membership.get("first_residual_class"),
            "next_action": "PROVE_ONE_BRAIN_OWNED_POLICY_ADEQUATE_OVER_THE_SOURCE_COMPATIBLE_INTERPRETATION_OVERAPPROXIMATION_OR_LOCALIZE_THE_FIRST_POLICY_CHANGING_DISCRIMINATOR",
            "full_semantic_manifest_required_for_selected_cell": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "acceptance_credit_delta": 0,
        }

    if not isinstance(positive_adequacy_payload, Mapping):
        return _fail("POSITIVE_ADEQUACY_PAYLOAD_INVALID")
    payload = dict(positive_adequacy_payload)
    if payload.get("source_text") != text:
        return _fail("POSITIVE_ADEQUACY_SOURCE_TEXT_MISMATCH")
    if payload.get("source_id") != source_id:
        return _fail("POSITIVE_ADEQUACY_SOURCE_ID_MISMATCH")

    adequacy = evaluate_positive_adequacy(payload)
    if adequacy.get("db_admission_authorized") is True and adequacy.get("pass") is True:
        return {
            "schema": SCHEMA,
            "status": "PASS__SOURCE_POSITIVE_ADEQUACY_ESCAPE",
            "pass": True,
            "selected_route": "SOURCE_POSITIVE_ADEQUACY",
            "structural_preflight": structural,
            "membership": membership,
            "positive_adequacy": adequacy,
            "full_semantic_manifest_required_for_selected_cell": False,
            "reason": "SELECTED_BRAIN_OWNED_POLICY_IS_PROVED_ADEQUATE_ACROSS_THE_SOUND_SOURCE_COMPATIBLE_OVERAPPROXIMATION",
            "global_professional_scope_closed": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "acceptance_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "UNRESOLVED__P2_AND_POSITIVE_ADEQUACY_BOTH_OPEN",
        "pass": False,
        "selected_route": None,
        "structural_preflight": structural,
        "membership": membership,
        "positive_adequacy": adequacy,
        "p2_first_residual_class": membership.get("first_residual_class"),
        "positive_adequacy_status": adequacy.get("status"),
        "next_action": "LOCALIZE_ONLY_THE_FIRST_POLICY_CHANGING_SOURCE_SEMANTIC_OR_ADEQUACY_GAP;DO_NOT_REQUIRE_UNUSED_SEMANTIC_DETAIL",
        "full_semantic_manifest_required_for_selected_cell": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
    }
