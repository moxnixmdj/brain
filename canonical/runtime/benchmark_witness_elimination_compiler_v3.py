from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Mapping

VALID_TYPES = {
    "THRESHOLD_LOWER_BOUND",
    "TASK_CONDITIONED_DOMINANCE",
    "SCOPE_SUPERSET",
}

VALID_PROOF_STATUSES = {
    "PROVED_EXACT",
    "PROVED_SOUND_IMPLICATION",
}

VALID_PROOF_TYPES = {
    "EXACT_IDENTITY",
    "DETERMINISTIC_DERIVATION",
    "SOUND_IMPLICATION",
    "EXHAUSTIVE_ENUMERATION",
    "UNIVERSAL_PROOF",
    "INDEPENDENT_VERIFICATION",
    "PROVENANCE_PROOF",
}

VALID_PREMISE_EVIDENCE_CLASSES = {
    "DETERMINISTIC_FORMAL_PROOF",
    "CONTENT_ADDRESSED_EXACT_SOURCE",
    "INDEPENDENT_VERIFICATION",
    "OWNER_FROZEN_TARGET_RECEIPT",
    "SCOPE_COMPLETE_CONTRACT_PROOF",
    "UNIVERSAL_EXECUTION_PROOF",
    "PROVENANCE_AUDIT",
}

VALID_RELATION_TYPES = {
    "EXACT_IDENTITY",
    "SOUND_THRESHOLD_IMPLICATION",
    "SOUND_DOMINANCE_IMPLICATION",
}

VALID_RELATION_EVIDENCE_CLASSES = {
    "EXACT_FROZEN_TARGET_HARNESS",
    "SOUND_EVALUATOR_IMPLICATION",
    "INDEPENDENT_MATCHED_COMPARISON",
    "OWNER_FROZEN_TARGET_RESULT_RELATION",
}

FORBIDDEN_SUBSTITUTE_EVIDENCE_CLASSES = {
    "GENERIC_PROTOCOL_ONLY",
    "PUBLIC_CALIBRATION_ONLY",
    "PUBLIC_LEADERBOARD_CALIBRATION",
    "RESOURCE_COMPATIBILITY_ONLY",
    "CARRIER_RUNTIME_ONLY",
}

EVALUATOR_TARGET_SCOPE = "FROZEN_TARGET_EVALUATOR_HARNESS_FALLBACK"

PREMISE_SCOPES = {
    "SCORE_DECOMPOSITION_EXACT": "FROZEN_TARGET_SCORING_RULE",
    "LOWER_BOUND_GE_TARGET": "FROZEN_TARGET_SCORE_THRESHOLD",
    "DOMAIN_SUBSET": "FROZEN_TARGET_TASK_DOMAIN",
    "RESOURCE_SEMANTICS": "FROZEN_TARGET_RESOURCE_SEMANTICS",
    "UNIVERSAL_SUCCESS": "CERTIFICATE_CLAIM_DOMAIN",
    "HIDDEN_SCOPE_UPPER_BOUND": "FROZEN_HIDDEN_TARGET_SCOPE",
    "NO_TARGET_OUTCOME_LEAKAGE": "CERTIFICATE_EVIDENCE_PROVENANCE",
}

@dataclass
class Verdict:
    predicate_id: str
    certificate_type: str
    admissible: bool
    reason: str
    terminal_credit: int = 0

def _sha1(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(c in "0123456789abcdef" for c in value)
    )

def _binding(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value["path"].strip())
        and _sha1(value.get("git_blob_sha"))
    )

def _receipt_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_binding(x) for x in value)

def _common_proof_error(
    proof: Any,
    *,
    claim_id: str,
    target_scope: str,
    target_tuple_binding: Mapping[str, Any],
) -> str | None:
    if not isinstance(proof, Mapping):
        return "PREMISE_PROOF_OBJECT_MISSING:" + claim_id
    if proof.get("claim_id") != claim_id:
        return "PREMISE_PROOF_CLAIM_ID_MISMATCH:" + claim_id
    if proof.get("status") not in VALID_PROOF_STATUSES:
        return "PREMISE_PROOF_STATUS_NOT_PROVED:" + claim_id
    if proof.get("proof_type") not in VALID_PROOF_TYPES:
        return "PREMISE_PROOF_TYPE_INVALID:" + claim_id
    if proof.get("target_scope") != target_scope:
        return "PREMISE_PROOF_TARGET_SCOPE_MISMATCH:" + claim_id
    evidence_class = proof.get("evidence_class")
    if evidence_class in FORBIDDEN_SUBSTITUTE_EVIDENCE_CLASSES:
        return "PREMISE_PROOF_FORBIDDEN_SUBSTITUTE_EVIDENCE:" + claim_id
    if evidence_class not in VALID_PREMISE_EVIDENCE_CLASSES:
        return "PREMISE_PROOF_EVIDENCE_CLASS_INVALID:" + claim_id
    if not _binding(proof.get("target_tuple_binding")):
        return "PREMISE_PROOF_TARGET_BINDING_NOT_CONTENT_ADDRESSED:" + claim_id
    if dict(proof.get("target_tuple_binding") or {}) != dict(target_tuple_binding):
        return "PREMISE_PROOF_TARGET_BINDING_MISMATCH:" + claim_id
    if not _receipt_list(proof.get("receipts")):
        return "PREMISE_PROOF_RECEIPTS_NOT_CONTENT_ADDRESSED:" + claim_id
    return None

def _premise_error(
    certificate: Mapping[str, Any],
    *,
    claim_id: str,
    target_tuple_binding: Mapping[str, Any],
) -> str | None:
    proofs = certificate.get("premise_proofs")
    if not isinstance(proofs, Mapping):
        return "PREMISE_PROOFS_MAP_MISSING"
    return _common_proof_error(
        proofs.get(claim_id),
        claim_id=claim_id,
        target_scope=PREMISE_SCOPES[claim_id],
        target_tuple_binding=target_tuple_binding,
    )

def _evaluator_relation_error(
    certificate: Mapping[str, Any],
    *,
    target_tuple_binding: Mapping[str, Any],
) -> str | None:
    relation = certificate.get("evaluator_relation")
    if not isinstance(relation, Mapping):
        return "EVALUATOR_RELATION_OBJECT_MISSING"
    if relation.get("status") not in VALID_PROOF_STATUSES:
        return "EVALUATOR_RELATION_STATUS_NOT_PROVED"
    if relation.get("relation_type") not in VALID_RELATION_TYPES:
        return "EVALUATOR_RELATION_TYPE_INVALID"
    if relation.get("target_scope") != EVALUATOR_TARGET_SCOPE:
        return "EVALUATOR_RELATION_TARGET_SCOPE_NOT_FROZEN_EXACT"
    evidence_class = relation.get("evidence_class")
    if evidence_class in FORBIDDEN_SUBSTITUTE_EVIDENCE_CLASSES:
        return "EVALUATOR_RELATION_FORBIDDEN_SUBSTITUTE_EVIDENCE"
    if evidence_class not in VALID_RELATION_EVIDENCE_CLASSES:
        return "EVALUATOR_RELATION_EVIDENCE_CLASS_INVALID"
    if not _binding(relation.get("target_tuple_binding")):
        return "EVALUATOR_RELATION_TARGET_BINDING_NOT_CONTENT_ADDRESSED"
    if dict(relation.get("target_tuple_binding") or {}) != dict(target_tuple_binding):
        return "EVALUATOR_RELATION_TARGET_BINDING_MISMATCH"
    if not _receipt_list(relation.get("receipts")):
        return "EVALUATOR_RELATION_RECEIPTS_NOT_CONTENT_ADDRESSED"
    return None

def _require_premises(
    certificate: Mapping[str, Any],
    *,
    claim_ids: tuple[str, ...],
    target_tuple_binding: Mapping[str, Any],
) -> str | None:
    for claim_id in claim_ids:
        error = _premise_error(
            certificate,
            claim_id=claim_id,
            target_tuple_binding=target_tuple_binding,
        )
        if error:
            return error
    return None

def evaluate_certificate(spec: Dict[str, Any]) -> Verdict:
    pid = str(spec.get("predicate_id", "UNKNOWN"))
    c = spec.get("certificate", {})
    ctype = c.get("type")

    if ctype not in VALID_TYPES:
        return Verdict(pid, str(ctype), False, "UNKNOWN_CERTIFICATE_TYPE")
    if not spec.get("exact_target_tuple_bound", False):
        return Verdict(pid, ctype, False, "TARGET_TUPLE_NOT_EXACTLY_BOUND")

    target_binding = spec.get("target_tuple_binding")
    if not _binding(target_binding):
        return Verdict(pid, ctype, False, "TARGET_TUPLE_BINDING_NOT_CONTENT_ADDRESSED")
    if not _receipt_list(c.get("receipts")):
        return Verdict(pid, ctype, False, "CERTIFICATE_RECEIPTS_NOT_CONTENT_ADDRESSED")

    relation_error = _evaluator_relation_error(
        c,
        target_tuple_binding=target_binding,
    )
    if relation_error:
        return Verdict(pid, ctype, False, relation_error)

    if ctype == "THRESHOLD_LOWER_BOUND":
        premise_error = _require_premises(
            c,
            claim_ids=("SCORE_DECOMPOSITION_EXACT", "LOWER_BOUND_GE_TARGET"),
            target_tuple_binding=target_binding,
        )
        if premise_error:
            return Verdict(pid, ctype, False, premise_error)

        lower = c.get("proved_lower_bound")
        target = c.get("target_threshold")
        if not isinstance(lower, (int, float)) or isinstance(lower, bool):
            return Verdict(pid, ctype, False, "PROVED_LOWER_BOUND_NOT_NUMERIC")
        if not isinstance(target, (int, float)) or isinstance(target, bool):
            return Verdict(pid, ctype, False, "TARGET_THRESHOLD_NOT_NUMERIC")

        lower_proof = c["premise_proofs"]["LOWER_BOUND_GE_TARGET"]
        if lower_proof.get("claim_value") != lower:
            return Verdict(pid, ctype, False, "LOWER_BOUND_PROOF_VALUE_MISMATCH")
        if lower_proof.get("target_value") != target:
            return Verdict(pid, ctype, False, "LOWER_BOUND_PROOF_TARGET_MISMATCH")
        if lower < target:
            return Verdict(pid, ctype, False, "PROVED_LOWER_BOUND_BELOW_TARGET")
        return Verdict(pid, ctype, True, "THRESHOLD_SOUNDLY_IMPLIED")

    if ctype == "TASK_CONDITIONED_DOMINANCE":
        premise_error = _require_premises(
            c,
            claim_ids=("DOMAIN_SUBSET", "RESOURCE_SEMANTICS", "UNIVERSAL_SUCCESS"),
            target_tuple_binding=target_binding,
        )
        if premise_error:
            return Verdict(pid, ctype, False, premise_error)
        return Verdict(
            pid,
            ctype,
            True,
            "FROZEN_TARGET_SCORE_DOMINATED_BY_PROOF_CARRYING_TASK_CONDITIONED_PROOF",
        )

    premise_error = _require_premises(
        c,
        claim_ids=(
            "HIDDEN_SCOPE_UPPER_BOUND",
            "RESOURCE_SEMANTICS",
            "UNIVERSAL_SUCCESS",
            "NO_TARGET_OUTCOME_LEAKAGE",
        ),
        target_tuple_binding=target_binding,
    )
    if premise_error:
        return Verdict(pid, ctype, False, premise_error)
    return Verdict(
        pid,
        ctype,
        True,
        "HIDDEN_TARGET_SOUNDLY_COVERED_BY_PROOF_CARRYING_SCOPE_SUPERSET",
    )

def compile_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    verdicts = [evaluate_certificate(x) for x in manifest.get("targets", [])]
    admitted = [v for v in verdicts if v.admissible]
    return {
        "schema": "PROJECT_BRAIN_BENCHMARK_WITNESS_ELIMINATION_COMPILATION_V3",
        "candidate_count": len(verdicts),
        "admitted_count": len(admitted),
        "admitted_predicates": [v.predicate_id for v in admitted],
        "verdicts": [asdict(v) for v in verdicts],
        "hard_nonclaim": (
            "V3_ADMISSION_IS_ONLY_A_PROOF_CARRYING_CERTIFICATE_STRUCTURE_CHECK__"
            "SEMANTIC_TRUTH_AND_TERMINAL_CREDIT_REQUIRE_INDEPENDENT_VERIFICATION_AND_GOVERNANCE_PROMOTION"
        ),
    }

if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    args = parser.parse_args()
    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    print(json.dumps(compile_manifest(manifest), indent=2, sort_keys=True))
