"""Semantic truth proof-family dispatcher V1.

Preserves the existing selected-semantic truth certificate as the default path.
Adds one explicit proof family for proof-carrying domain-mapping relations.
Unknown declared truth kinds fail closed.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.domain_mapping_truth_certificate_v1 import (
    evaluate as evaluate_domain_mapping,
)
from canonical.runtime.regcap_loss_cushion_truth_certificate_v1 import (
    evaluate as evaluate_regcap_loss_cushion,
)

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
