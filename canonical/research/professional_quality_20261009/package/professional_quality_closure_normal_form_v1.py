from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_CLOSURE_NORMAL_FORM_VERIFIER_V1"
EXPECTED_ROOTS = {
    "R1_TARGET_SPECIFICATION",
    "R2_CANDIDATE_SEARCH",
    "R3_REALIZATION_OBSERVATION",
    "R4_MEASUREMENT_CONSTRUCT",
    "R5_EVALUATOR_REFERENCE",
    "R6_EVIDENCE_GROUNDING_DEPENDENCE",
    "R7_CAUSAL_PRESCRIPTIVE",
    "R8_POPULATION_CONTEXT_OPERATOR",
    "R9_TEMPORAL_DEPLOYMENT",
    "R10_ANALYSIS_DECISION",
    "R11_ADAPTIVE_INTEGRITY_SECURITY",
    "R12_META_COMPOSITION_CLOSURE",
}
REQUIRED_P1_STEPS = {
    "COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS",
    "GENERATE_DIVERSE_CANDIDATE_BRANCHES_WITH_INCUMBENT_PRESERVATION",
    "RUN_DETERMINISTIC_FACT_STRUCTURE_FORMAT_AND_GROUNDING_CHECKS",
    "RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS",
    "RUN_CRITERION_SPECIFIC_PLUS_HOLISTIC_COMPARATIVE_EVALUATION",
    "ATTACK_FINALISTS_WITH_RELEVANT_INVARIANCE_DEFEATER_AND_HIDDEN_CHANNEL_PROBES",
    "FREEZE_WINNER_AND_USE_FRESH_OR_SELECTION_AWARE_TERMINAL_EVIDENCE",
    "ISSUE_SCOPED_CERTIFICATE_OR_ABSTAIN_WITH_MINIMUM_BLOCKING_CUT",
}
SAFE_CHALLENGE_BEHAVIORS = {"FAIL", "ABSTAIN", "INVESTIGATE"}

def verify(normal_form: Mapping[str, Any], matrix: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    roots = normal_form.get("roots")
    if not isinstance(roots, list):
        roots = []
        errors.append("ROOTS_INVALID")
    root_ids = [r.get("id") for r in roots if isinstance(r, Mapping)]
    if len(root_ids) != len(set(root_ids)):
        errors.append("ROOT_ID_DUPLICATE")
    if set(root_ids) != EXPECTED_ROOTS:
        errors.append("ROOT_SET_MISMATCH")
    if any(not isinstance(r.get("contract"), str) or not r.get("contract").strip() for r in roots if isinstance(r, Mapping)):
        errors.append("ROOT_CONTRACT_MISSING")

    profile = normal_form.get("p1_default_profile")
    if not isinstance(profile, Mapping):
        errors.append("P1_PROFILE_MISSING")
        steps = set()
        triggers = []
    else:
        steps = set(profile.get("steps") or [])
        triggers = profile.get("escalation_triggers") or []
    if not REQUIRED_P1_STEPS.issubset(steps):
        errors.append("P1_REQUIRED_STEP_MISSING")
    if not triggers:
        errors.append("P1_ESCALATION_TRIGGER_MISSING")

    challenges = matrix.get("challenges")
    if not isinstance(challenges, list) or not challenges:
        challenges = []
        errors.append("CHALLENGES_MISSING")
    seen: set[str] = set()
    covered: set[str] = set()
    for row in challenges:
        if not isinstance(row, Mapping):
            errors.append("CHALLENGE_NOT_OBJECT")
            continue
        cid = row.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append("CHALLENGE_ID_MISSING")
            continue
        if cid in seen:
            errors.append("CHALLENGE_ID_DUPLICATE:" + cid)
        seen.add(cid)
        refs = row.get("root_ids")
        if not isinstance(refs, list) or not refs:
            errors.append("CHALLENGE_ROOT_MISSING:" + cid)
            continue
        unknown = set(refs) - EXPECTED_ROOTS
        if unknown:
            errors.append("CHALLENGE_UNKNOWN_ROOT:" + cid)
        covered.update(set(refs) & EXPECTED_ROOTS)
        expected = set(row.get("expected_terminal_behavior") or [])
        if not expected or not expected.issubset(SAFE_CHALLENGE_BEHAVIORS):
            errors.append("CHALLENGE_BEHAVIOR_UNSAFE:" + cid)
        if row.get("terminal_pass_forbidden") is not True:
            errors.append("CHALLENGE_PASS_NOT_FORBIDDEN:" + cid)

    if covered != EXPECTED_ROOTS:
        errors.append("ROOT_WITHOUT_ADVERSARIAL_CHALLENGE")
    if normal_form.get("closure_rule", {}).get("current_result") == "PROVED":
        errors.append("UNAUTHORIZED_COMPLETENESS_CLAIM")
    if normal_form.get("accounting", {}).get("terminal_credit_delta") not in (0, None):
        errors.append("UNAUTHORIZED_TERMINAL_CREDIT")
    if matrix.get("accounting", {}).get("terminal_credit_delta") not in (0, None):
        errors.append("UNAUTHORIZED_MATRIX_TERMINAL_CREDIT")

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": "STRUCTURAL_PASS_ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "root_count": len(root_ids),
        "challenge_count": len(challenges),
        "covered_root_count": len(covered),
        "professional_quality_closed": False,
        "terminal_credit_delta": 0,
    }
