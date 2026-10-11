"""Semantic truth proof-family dispatcher V1.

Preserves the existing selected-semantic truth certificate as the default path.
Adds explicit proof families for proof-carrying domain-mapping relations and
bounded source-aligned regulatory-capital contextual atoms. Unknown declared
truth kinds fail closed.
"""
from __future__ import annotations

from typing import Any, Mapping

def evaluate_domain_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.domain_mapping_truth_certificate_v1 import evaluate
    return evaluate(payload)


def evaluate_regcap_loss_cushion(payload: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.regcap_loss_cushion_truth_certificate_v6 import evaluate
    return evaluate(payload)


def evaluate_regcap_context_atom(payload: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.regcap_context_atom_truth_certificate_v2 import evaluate
    return evaluate(payload)


def evaluate_margin_context_identity(payload: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.margin_context_identity_truth_certificate_v1 import evaluate
    return evaluate(payload)


def evaluate_regcap_facet_role(payload: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.regcap_facet_role_truth_certificate_v1 import evaluate
    return evaluate(payload)


def evaluate_regcap_buffer_reference(payload: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.regcap_buffer_reference_truth_certificate_v1 import evaluate
    return evaluate(payload)


def evaluate_spread_relation_identity(payload: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.spread_relation_identity_truth_certificate_v1 import evaluate
    return evaluate(payload)


def evaluate_rwa_capital_measurement(payload: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.rwa_capital_measurement_truth_certificate_v1 import evaluate
    return evaluate(payload)


SCHEMA = "PROJECT_BRAIN_SEMANTIC_TRUTH_DISPATCH_V1"


def evaluate_legacy(payload: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.selected_semantic_truth_certificate_v1 import (
        evaluate as legacy_evaluate,
    )
    return legacy_evaluate(payload)


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "PAYLOAD_MAPPING_REQUIRED",
            "predicate_truth": "UNKNOWN",
            "truthful_precommitment_observation": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    kind = payload.get("truth_kind")
    if kind is None:
        return evaluate_legacy(payload)
    if kind == "DOMAIN_MAPPING_RELATION":
        return evaluate_domain_mapping(payload)
    if kind == "REGCAP_LOSS_CUSHION_GROUNDING":
        return evaluate_regcap_loss_cushion(payload)
    if kind == "REGCAP_CONTEXT_ATOM":
        return evaluate_regcap_context_atom(payload)
    if kind == "MARGIN_CONTEXT_IDENTITY":
        return evaluate_margin_context_identity(payload)
    if kind == "REGCAP_FACET_ROLE":
        return evaluate_regcap_facet_role(payload)
    if kind == "REGCAP_BUFFER_REFERENCE_IDENTITY":
        return evaluate_regcap_buffer_reference(payload)
    if kind == "SPREAD_RELATION_IDENTITY":
        return evaluate_spread_relation_identity(payload)
    if kind == "RWA_CAPITAL_MEASUREMENT_FRAME":
        return evaluate_rwa_capital_measurement(payload)
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": "TRUTH_KIND_UNSUPPORTED:" + str(kind),
        "predicate_truth": "UNKNOWN",
        "truthful_precommitment_observation": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
