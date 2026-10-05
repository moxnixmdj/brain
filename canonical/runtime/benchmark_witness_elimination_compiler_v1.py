from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict

VALID_TYPES = {
    "THRESHOLD_LOWER_BOUND",
    "TASK_CONDITIONED_DOMINANCE",
    "SCOPE_SUPERSET",
}

@dataclass
class Verdict:
    predicate_id: str
    certificate_type: str
    admissible: bool
    reason: str
    terminal_credit: int = 0

def evaluate_certificate(spec: Dict[str, Any]) -> Verdict:
    pid = str(spec.get("predicate_id", "UNKNOWN"))
    c = spec.get("certificate", {})
    ctype = c.get("type")
    if ctype not in VALID_TYPES:
        return Verdict(pid, str(ctype), False, "UNKNOWN_CERTIFICATE_TYPE")
    if not spec.get("exact_target_tuple_bound", False):
        return Verdict(pid, ctype, False, "TARGET_TUPLE_NOT_EXACTLY_BOUND")
    if not c.get("receipts", []):
        return Verdict(pid, ctype, False, "NO_CONTENT_ADDRESSED_RECEIPTS")

    if ctype == "THRESHOLD_LOWER_BOUND":
        if not c.get("score_decomposition_exact", False):
            return Verdict(pid, ctype, False, "SCORE_DECOMPOSITION_NOT_EXACT")
        lower = c.get("proved_lower_bound")
        target = c.get("target_threshold")
        if lower is None or target is None:
            return Verdict(pid, ctype, False, "LOWER_BOUND_OR_TARGET_MISSING")
        if lower < target:
            return Verdict(pid, ctype, False, "PROVED_LOWER_BOUND_BELOW_TARGET")
        if not c.get("evaluator_relation_proved", False):
            return Verdict(pid, ctype, False, "EVALUATOR_RELATION_NOT_PROVED")
        return Verdict(pid, ctype, True, "THRESHOLD_SOUNDLY_IMPLIED")

    if ctype == "TASK_CONDITIONED_DOMINANCE":
        required = (
            "domain_subset_proved",
            "evaluator_relation_proved",
            "resource_semantics_preserved",
            "universal_success_proved",
        )
        missing = [k for k in required if not c.get(k, False)]
        if missing:
            return Verdict(pid, ctype, False, "MISSING_" + "_".join(missing).upper())
        return Verdict(pid, ctype, True, "FROZEN_TARGET_SCORE_DOMINATED_BY_TASK_CONDITIONED_PROOF")

    required = (
        "published_contract_upper_bounds_hidden_scope",
        "evaluator_relation_proved",
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
        "schema": "PROJECT_BRAIN_BENCHMARK_WITNESS_ELIMINATION_COMPILATION_V1",
        "candidate_count": len(verdicts),
        "admitted_count": len(admitted),
        "admitted_predicates": [v.predicate_id for v in admitted],
        "verdicts": [asdict(v) for v in verdicts],
        "hard_nonclaim": "ADMISSION_BY_THIS_COMPILER_IS_ONLY_A_CERTIFICATE_SHAPE_CHECK__TERMINAL_CREDIT_REQUIRES_INDEPENDENT_VERIFICATION_AND_GOVERNANCE_PROMOTION",
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
