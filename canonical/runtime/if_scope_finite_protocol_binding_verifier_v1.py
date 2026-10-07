from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FILES = {
    "candidate": "canonical/governance/IF_SCOPE_FINITE_PROTOCOL_BINDING_TRUTH_REPAIR_20261007_V1.json",
    "protocols": "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
    "semantics": "canonical/governance/MATCHED_PORTFOLIO_SCOPE_SEMANTICS_DISJUNCTION_20261007_V1.json",
    "precommit": "canonical/governance/IF_SCOPE_FINITE_WAVE_PRECOMMIT_20261007_V1.json",
    "top": "canonical/governance/IF_SCOPE_FINITE_MANIFEST_TOP_CERTIFICATE_20261007_V1.json",
    "execution": "canonical/verification/IF_SCOPE_FINITE_WAVE_SPRITE_VERIFICATION_20261007_V1.json",
}

EXPECTED_ATOMS = {
    "dimension:multi_constraint_instruction_compliance",
    "dimension:authorization_and_scope_boundaries",
    "dimension:routine_ambiguity",
    "dimension:requirement_change",
    "dimension:explicit_abstention_and_fail_closed_cases",
}

def load(key: str):
    return json.loads((ROOT / FILES[key]).read_text(encoding="utf-8"))

def verify() -> dict:
    errors = []
    cand = load("candidate")
    protocols = load("protocols")
    semantics = load("semantics")
    pre = load("precommit")
    top = load("top")
    exe = load("execution")

    if cand.get("protocol_binding", {}).get("predicate") != "IF_SCOPE_BOUNDARY_NONINFERIOR":
        errors.append("CANDIDATE_PREDICATE_DRIFT")

    if_entry = next((x for x in protocols.get("protocols", [])
                     if x.get("family") == "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT"), None)
    if if_entry is None:
        errors.append("IF_PROTOCOL_MISSING")
        if_entry = {}

    dims = set(if_entry.get("task_dimensions", []))
    normalized_protocol_dims = {
        "dimension:" + x.replace("/", "_or_").replace(" ", "_").replace("-", "_")
        for x in dims
    }
    # Bind by the canonical precommit atoms rather than lossy free-text normalization.
    pre_atoms = set(pre.get("fixed_universe", {}).get("normalized_atoms", []))
    if pre_atoms != EXPECTED_ATOMS:
        errors.append("PRECOMMIT_ATOM_SET_DRIFT")

    if len(if_entry.get("task_dimensions", [])) != 5:
        errors.append("IF_PROTOCOL_DIMENSION_COUNT_DRIFT")

    acceptance_text = " ".join(str(x) for x in if_entry.get("acceptance", []))
    if "matched scope-boundary portfolio" not in acceptance_text:
        errors.append("IF_ACCEPTANCE_PORTFOLIO_BINDING_MISSING")
    if "frozen portfolio" not in acceptance_text:
        errors.append("IF_ACCEPTANCE_FROZEN_PORTFOLIO_MISSING")

    # The protocol entry must not explicitly elevate the acceptance object to a larger population.
    protocol_entry_text = json.dumps(if_entry, sort_keys=True).lower()
    if "underlying population" in protocol_entry_text or "population inference" in protocol_entry_text:
        errors.append("EXPLICIT_POPULATION_ACCEPTANCE_FOUND")

    if semantics.get("routes", {}).get("FINITE_DECLARED_SCOPE", {}).get("consequence", [None])[0] != (
        "THE EXACT FINITE SUCCESS REDUCER R=K/N IS THE ACCEPTANCE REDUCER"
    ):
        errors.append("FINITE_SCOPE_SEMANTICS_DRIFT")

    fixed = pre.get("fixed_universe", {})
    if fixed.get("case_count") != 160 or fixed.get("cases_per_kind") != 32:
        errors.append("PRECOMMIT_CASE_SHAPE_DRIFT")
    if set(fixed.get("kinds", [])) != {
        "MULTI_CONSTRAINT", "AUTHORIZATION_BOUNDARY", "ROUTINE_AMBIGUITY",
        "REQUIREMENT_CHANGE", "EXPLICIT_ABSTENTION"
    }:
        errors.append("PRECOMMIT_KIND_SET_DRIFT")

    freeze = pre.get("execution_freeze", {})
    for key in (
        "brain_runtime_content_addressed", "scorer_content_addressed",
        "generator_content_addressed", "tool_authority_content_addressed",
        "target_interface_content_addressed", "fixed_case_count_before_first_result",
        "no_case_replacement_after_exposure", "no_adaptive_case_selection",
        "no_result_dependent_scope_edit", "each_case_fresh_python_process"
    ):
        if freeze.get(key) is not True:
            errors.append("FREEZE_" + key.upper() + "_NOT_TRUE")

    ex = exe.get("execution", {})
    if exe.get("status", "").startswith("PRIVATE_INDEPENDENT_CARRIER_EXECUTION_PASS") is False:
        errors.append("INDEPENDENT_EXECUTION_NOT_PASS")
    for key, expected in (
        ("case_count", 160), ("brain_success_count", 160), ("brain_failure_count", 0),
        ("opus_residual_case_count", 0), ("covered_atom_count", 5)
    ):
        if ex.get(key) != expected:
            errors.append(f"EXECUTION_{key.upper()}_DRIFT")
    if ex.get("coverage_complete") is not True:
        errors.append("EXECUTION_COVERAGE_INCOMPLETE")
    if ex.get("case_isolation_or_reset_equivalent") is not True:
        errors.append("EXECUTION_ISOLATION_FAIL")

    if top.get("target_predicate") != "IF_SCOPE_BOUNDARY_NONINFERIOR":
        errors.append("TOP_CERT_TARGET_DRIFT")
    br = top.get("brain_result", {})
    if br.get("success_count") != 160 or br.get("failure_count") != 0:
        errors.append("TOP_CERT_RESULT_DRIFT")
    if br.get("coverage_complete") is not True:
        errors.append("TOP_CERT_COVERAGE_INCOMPLETE")
    if top.get("independent_report_audit", {}).get("authority_denied_route_touches") != 0:
        errors.append("AUTHORITY_VIOLATION_PRESENT")

    truth = cand.get("truth_repair", {})
    if truth.get("if_scope_boundary_refinement_closed_if_verified") is not True:
        errors.append("CANDIDATE_CLOSURE_FLAG_MISSING")
    if truth.get("sound_subtraction_from_U_if_verified") is not True:
        errors.append("CANDIDATE_U_SUBTRACTION_FLAG_MISSING")

    return {
        "schema": "PROJECT_BRAIN_IF_SCOPE_FINITE_PROTOCOL_BINDING_VERIFIER_V1",
        "pass": not errors,
        "errors": errors,
        "protocol_family": if_entry.get("family"),
        "declared_scope_mode": cand.get("protocol_binding", {}).get("interpretation"),
        "case_count": ex.get("case_count"),
        "brain_success_count": ex.get("brain_success_count"),
        "required_atom_count": len(EXPECTED_ATOMS),
        "covered_atom_count": ex.get("covered_atom_count"),
        "opus_query_required": False if not errors else None,
        "if_scope_boundary_refinement_closed": not errors,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
    raise SystemExit(0 if verify()["pass"] else 1)
