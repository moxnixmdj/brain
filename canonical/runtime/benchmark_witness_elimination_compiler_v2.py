from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Mapping

VALID_TYPES = {
    "THRESHOLD_LOWER_BOUND",
    "TASK_CONDITIONED_DOMINANCE",
    "SCOPE_SUPERSET",
}
VALID_RELATION_TYPES = {
    "EXACT_IDENTITY",
    "SOUND_THRESHOLD_IMPLICATION",
    "SOUND_DOMINANCE_IMPLICATION",
}
VALID_RELATION_STATUSES = {
    "PROVED_EXACT",
    "PROVED_SOUND_IMPLICATION",
}
VALID_EVIDENCE_CLASSES = {
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
TARGET_SCOPE = "FROZEN_TARGET_EVALUATOR_HARNESS_FALLBACK"

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

def _evaluator_relation_error(certificate: Mapping[str, Any]) -> str | None:
    relation = certificate.get("evaluator_relation")
    if not isinstance(relation, Mapping):
        return "EVALUATOR_RELATION_OBJECT_MISSING"
    if relation.get("status") not in VALID_RELATION_STATUSES:
        return "EVALUATOR_RELATION_STATUS_NOT_PROVED"
    if relation.get("relation_type") not in VALID_RELATION_TYPES:
        return "EVALUATOR_RELATION_TYPE_INVALID"
    if relation.get("target_scope") != TARGET_SCOPE:
        return "EVALUATOR_RELATION_TARGET_SCOPE_NOT_FROZEN_EXACT"
    evidence_class = relation.get("evidence_class")
    if evidence_class in FORBIDDEN_SUBSTITUTE_EVIDENCE_CLASSES:
        return "EVALUATOR_RELATION_FORBIDDEN_SUBSTITUTE_EVIDENCE"
    if evidence_class not in VALID_EVIDENCE_CLASSES:
        return "EVALUATOR_RELATION_EVIDENCE_CLASS_INVALID"
    if not _binding(relation.get("target_tuple_binding")):
        return "EVALUATOR_RELATION_TARGET_BINDING_NOT_CONTENT_ADDRESSED"
    if not _receipt_list(relation.get("receipts")):
        return "EVALUATOR_RELATION_RECEIPTS_NOT_CONTENT_ADDRESSED"
    return None

def evaluate_certificate(spec: Dict[str, Any]) -> Verdict:
    pid = str(spec.get("predicate_id", "UNKNOWN"))
    c = spec.get("certificate", {})
    ctype = c.get("type")
    if ctype not in VALID_TYPES:
        return Verdict(pid, str(ctype), False, "UNKNOWN_CERTIFICATE_TYPE")
    if not spec.get("exact_target_tuple_bound", False):
        return Verdict(pid, ctype, False, "TARGET_TUPLE_NOT_EXACTLY_BOUND")
    if not _binding(spec.get("target_tuple_binding")):
        return Verdict(pid, ctype, False, "TARGET_TUPLE_BINDING_NOT_CONTENT_ADDRESSED")
    if not _receipt_list(c.get("receipts")):
        return Verdict(pid, ctype, False, "CERTIFICATE_RECEIPTS_NOT_CONTENT_ADDRESSED")

    relation_error = _evaluator_relation_error(c)
    if relation_error:
        return Verdict(pid, ctype, False, relation_error)

    if ctype == "THRESHOLD_LOWER_BOUND":
        if not c.get("score_decomposition_exact", False):
            return Verdict(pid, ctype, False, "SCORE_DECOMPOSITION_NOT_EXACT")
        lower = c.get("proved_lower_bound")
        target = c.get("target_threshold")
        if lower is None or target is None:
            return Verdict(pid, ctype, False, "LOWER_BOUND_OR_TARGET_MISSING")
        if lower < target:
            return Verdict(pid, ctype, False, "PROVED_LOWER_BOUND_BELOW_TARGET")
        return Verdict(pid, ctype, True, "THRESHOLD_SOUNDLY_IMPLIED")

    if ctype == "TASK_CONDITIONED_DOMINANCE":
        required = (
            "domain_subset_proved",
            "resource_semantics_preserved",
            "universal_success_proved",
        )
        missing = [k for k in required if not c.get(k, False)]
        if missing:
            return Verdict(pid, ctype, False, "MISSING_" + "_".join(missing).upper())
        return Verdict(pid, ctype, True, "FROZEN_TARGET_SCORE_DOMINATED_BY_TASK_CONDITIONED_PROOF")

    required = (
        "published_contract_upper_bounds_hidden_scope",
        "resource_semantics_preserved",
        "universal_success_proved",
        "no_target_outcome_leakage",
    )
    missing = [k for k in required if not c.get(k, False)]
    if missing:
        return Verdict(pid, ctype, False, "MISSING_" + "_".join(missing).upper())
    return Verdict(pid, ctype, True, "HIDDEN_TARGET_SOUNDLY_COVERED_BY_SCOPE_SUPERSET")

def compile_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    verdicts = [evaluate_certificate(x) for x in manifest.get("targets", [])]
    admitted = [v for v in verdicts if v.admissible]
    return {
        "schema": "PROJECT_BRAIN_BENCHMARK_WITNESS_ELIMINATION_COMPILATION_V2",
        "candidate_count": len(verdicts),
        "admitted_count": len(admitted),
        "admitted_predicates": [v.predicate_id for v in admitted],
        "verdicts": [asdict(v) for v in verdicts],
        "hard_nonclaim": "V2_ADMISSION_IS_STILL_ONLY_A_PROOF_CARRYING_CERTIFICATE_SHAPE_CHECK__TERMINAL_CREDIT_REQUIRES_INDEPENDENT_SEMANTIC_VERIFICATION_AND_GOVERNANCE_PROMOTION",
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
