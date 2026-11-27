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
from canonical.runtime.aa_briefcase_minimal_owner_attestation_v1 import (
    verify_minimal_owner_attestation,
)
from canonical.runtime.aa_briefcase_core_owner_attestation_v2 import (
    verify_core_owner_attestation,
)
from canonical.runtime.aa_briefcase_official_github_publication_v1 import (
    verify_official_github_publication,
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

    if mode == "OFFICIAL_GITHUB_PUBLICATION":
        publication = payload.get("publication")
        if not isinstance(publication, Mapping):
            raise NoninferiorityBridgeError("OFFICIAL_GITHUB_PUBLICATION_PAYLOAD_INVALID")
        result = verify_official_github_publication(
            current_target,
            publication,
        )
        passed = result["status"] == "PASS_OFFICIAL_GITHUB_PUBLICATION"
        route = "OFFICIAL_GITHUB_PUBLICATION"
        subject_sha256 = result["subject_sha256"]
        reference = result["current_owner_reference_elo_context_only"]
        observed_date = result["target_observed_date"]
        numeric_comparable_elo_used = False
        numeric_elo_reconstruction_required = False
        source_verdict_sha256 = result["verdict_sha256"]

    elif mode == "CORE_OWNER_ATTESTATION":
        statement = payload.get("statement")
        signature_bundle = payload.get("signature_bundle")
        if not isinstance(statement, Mapping) or not isinstance(signature_bundle, Mapping):
            raise NoninferiorityBridgeError("CORE_OWNER_ATTESTATION_PAYLOAD_INVALID")
        result = verify_core_owner_attestation(
            current_target,
            statement,
            signature_bundle,
        )
        passed = result["status"] == "PASS_CORE_OWNER_ATTESTATION"
        route = "CORE_OWNER_ATTESTATION"
        subject_sha256 = result["subject_sha256"]
        reference = result["current_owner_reference_elo_context_only"]
        observed_date = result["target_observed_date"]
        numeric_comparable_elo_used = False
        numeric_elo_reconstruction_required = False
        source_verdict_sha256 = result["verdict_sha256"]

    elif mode == "MATCHED_CURRENT_EPOCH_ELO":
        result = compile_current_epoch_bridge(current_target, payload)
        passed = all(bool(result["predicate_results"][pid]) for pid in PREDICATES)
        route = "MATCHED_CURRENT_EPOCH_ELO"
        subject_sha256 = result["subject_sha256"]
        reference = result["opus55_reference_score"]
        observed_date = result["target_observed_date"]
        numeric_comparable_elo_used = True
        numeric_elo_reconstruction_required = True
        source_verdict_sha256 = result["bridge_verdict_sha256"]

    elif mode == "MINIMAL_OWNER_ATTESTATION":
        statement = payload.get("statement")
        signature_bundle = payload.get("signature_bundle")
        if (
            not isinstance(statement, Mapping)
            or not isinstance(signature_bundle, Mapping)
        ):
            raise NoninferiorityBridgeError("OWNER_ATTESTATION_PAYLOAD_INVALID")
        result = verify_minimal_owner_attestation(
            current_target,
            statement,
            signature_bundle,
        )
        passed = result["status"] == "PASS_MINIMAL_OWNER_ATTESTATION"
        route = "MINIMAL_OWNER_ATTESTATION"
        subject_sha256 = result["subject_sha256"]
        reference = result["current_owner_reference_elo_context_only"]
        observed_date = result["target_observed_date"]
        numeric_comparable_elo_used = False
        numeric_elo_reconstruction_required = False
        source_verdict_sha256 = result["verdict_sha256"]

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
