from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime.aa_briefcase_current_epoch_result_bridge_v2 import (
    PREDICATES,
    compile_current_epoch_bridge,
)
from canonical.runtime.aa_briefcase_scope_complete_dominance_v1 import (
    verify_scope_complete_dominance,
)

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_CURRENT_EPOCH_NONINFERIORITY_BRIDGE_V3"


class NoninferiorityBridgeError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def compile_current_epoch_noninferiority(
    current_target: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise NoninferiorityBridgeError("EVIDENCE_INVALID")
    mode = evidence.get("mode")
    payload = evidence.get("payload")
    if not isinstance(payload, Mapping):
        raise NoninferiorityBridgeError("EVIDENCE_PAYLOAD_INVALID")

    if mode == "MATCHED_CURRENT_EPOCH_ELO":
        result = compile_current_epoch_bridge(current_target, payload)
        passed = all(bool(result["predicate_results"][pid]) for pid in PREDICATES)
        route = "MATCHED_CURRENT_EPOCH_ELO"
        subject_sha256 = result["subject_sha256"]
        reference = result["opus55_reference_score"]
        observed_date = result["target_observed_date"]
        numeric_comparable_elo_used = True
        numeric_elo_reconstruction_required = True
        source_verdict_sha256 = result["bridge_verdict_sha256"]

    elif mode == "SCOPE_COMPLETE_DIRECT_DOMINANCE":
        result = verify_scope_complete_dominance(current_target, payload)
        passed = result["status"] == "PASS_SCOPE_COMPLETE_CURRENT_EPOCH_DOMINANCE"
        route = "SCOPE_COMPLETE_DIRECT_DOMINANCE"
        subject_sha256 = result["subject_sha256"]
        reference = result["current_owner_reference_elo_context_only"]
        observed_date = result["target_observed_date"]
        numeric_comparable_elo_used = False
        numeric_elo_reconstruction_required = False
        source_verdict_sha256 = result["verdict_sha256"]

    else:
        raise NoninferiorityBridgeError("UNKNOWN_EVIDENCE_MODE")

    material = {
        "schema": SCHEMA,
        "status": "PASS_CURRENT_TARGET_NONINFERIORITY" if passed else "FAIL_CURRENT_TARGET_NONINFERIORITY",
        "comparison_route": route,
        "target_observed_date": observed_date,
        "current_owner_reference_elo_context_only": float(reference),
        "subject_sha256": subject_sha256,
        "predicate_results": {pid: passed for pid in PREDICATES},
        "single_result_reused_across_predicates": True,
        "historical_1822_predicate_ids_preserved": True,
        "historical_epoch_rewritten": False,
        "official_owner_elo_claimed": False,
        "numeric_comparable_elo_used": numeric_comparable_elo_used,
        "numeric_elo_reconstruction_required": numeric_elo_reconstruction_required,
        "source_verdict_sha256": source_verdict_sha256,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
    }
    return {**material, "bridge_verdict_sha256": _sha256(material)}
