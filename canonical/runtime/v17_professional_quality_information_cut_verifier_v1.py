from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATHS = {
    "governance": "canonical/governance/V17_PROFESSIONAL_QUALITY_INFORMATION_CUT_REALITY_WAKE_20261007_V1.json",
    "v17": "canonical/governance/TERMINAL_NOW_V17_LIVE_REBASE_20261007_V1.json",
    "prewave": "canonical/governance/PROFESSIONAL_ARTIFACT_INTERNAL_PREWAVE_BINDING_V1.json",
    "terminal_binding": "canonical/governance/P2_PROFESSIONAL_QUALITY_T1_MULTIPLEX_TERMINAL_BINDING_V1.json",
    "artifact_residual": "canonical/governance/ARTIFACT_PROFESSIONAL_RESIDUAL_REDUCTION_20261007_V1.json",
    "bounded_cell": "canonical/governance/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_20261007_V1.json",
}
EXPECTED = {
    PATHS["governance"]: "d2640079672542b974e391722e8ae4163fd8c78a",
    PATHS["v17"]: "75b6dd8b7095644f2aeca2c71de4e41d87e0e21b",
    PATHS["prewave"]: "89083d0a7039f4e3e9ac0f9fbdd392836eb11f25",
    PATHS["terminal_binding"]: "8d5888a8299d1b8addd629be01fe9a6dc46b1a7d",
    PATHS["artifact_residual"]: "afaf6e9c4dfe13873b732d49a468329fc9510ffe",
    PATHS["bounded_cell"]: "0ccc3ecbdbf2636b8f1e7f0daf959a48350cb82e",
}

def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def verify() -> dict:
    errors = []
    for path, expected in EXPECTED.items():
        p = ROOT / path
        if not p.is_file():
            errors.append("MISSING:" + path)
        elif blob(p.read_bytes()) != expected:
            errors.append("DRIFT:" + path)

    if errors:
        return {"pass": False, "status": "FAIL_CLOSED__SOURCE_DRIFT", "errors": errors,
                "terminal": False, "terminal_credit_delta": 0}

    gov = load(PATHS["governance"])
    v17 = load(PATHS["v17"])
    prewave = load(PATHS["prewave"])
    binding = load(PATHS["terminal_binding"])
    bounded = load(PATHS["bounded_cell"])

    pq = next((x for x in v17.get("live_positive_frontier", [])
               if x.get("id") == "PROFESSIONAL_QUALITY_OUTSIDE_CACHED_CELLS"), None)
    if pq is None:
        errors.append("V17_PROFESSIONAL_RESIDUAL_MISSING")
    elif "DO_NOT_INFER_OPEN_ENDED_QUALITY_FROM_SYNTHETIC_GENERATOR_OPTIMALITY" not in pq.get("rule", ""):
        errors.append("V17_SCOPE_RULE_DRIFT")

    audit = prewave.get("uncovered_scope_audit", {})
    if audit.get("authoritative_scope_equivalent_now") is not False:
        errors.append("PREWAVE_SCOPE_EQUIVALENCE_NOT_FALSE")
    if audit.get("no_scope_inheritance") is not True:
        errors.append("PREWAVE_SCOPE_INHERITANCE_GUARD_MISSING")
    if not audit.get("authoritative_unresolved_dimensions"):
        errors.append("PREWAVE_UNRESOLVED_DIMENSIONS_EMPTY")

    info = prewave.get("information_boundary", {})
    if info.get("candidate_receives_hidden_oracle") is not False:
        errors.append("HIDDEN_ORACLE_LEAK")
    if not info.get("hidden_oracle"):
        errors.append("HIDDEN_ORACLE_FIELDS_EMPTY")

    forbidden = set(binding.get("candidate_must_not_receive", []))
    if not binding.get("hidden_evaluator_information"):
        errors.append("TERMINAL_HIDDEN_EVALUATOR_SET_EMPTY")
    if "GOLD_EDIT_QUALITY_SCORES" not in forbidden:
        errors.append("GOLD_QUALITY_NOT_FORBIDDEN")
    if binding.get("terminal_acceptance", {}).get("standalone_synthetic_whole_domain_score_forbidden") is not True:
        errors.append("SYNTHETIC_WHOLE_DOMAIN_GUARD_MISSING")

    consequence = bounded.get("abc_consequence", {})
    if consequence.get("professional_quality_global_closed") is not False:
        errors.append("BOUNDED_CELL_GLOBAL_OVERCLAIM")

    # Same visible state in both worlds forces one shared action distribution.
    # W1 requires p=1 to match its informed optimum; W2 requires p=0.
    p_for_w1 = Fraction(1, 1)
    p_for_w2 = Fraction(0, 1)
    universal_visible_policy_exists = p_for_w1 == p_for_w2
    minimax = Fraction(1, 2)

    cut = gov.get("two_world_information_cut", {})
    if cut.get("feasible") is not False:
        errors.append("GOVERNANCE_FEASIBILITY_DRIFT")
    if cut.get("minimax_visible_only_success") != "1/2":
        errors.append("GOVERNANCE_MINIMAX_DRIFT")
    if universal_visible_policy_exists:
        errors.append("TWO_WORLD_COUNTERMODEL_COLLAPSED")

    deduction = gov.get("deduction", {})
    if deduction.get("current_zero_reality_bytes_prove_full_professional_quality_universal_dominance") is not False:
        errors.append("ZERO_REALITY_OVERCLAIM")
    if deduction.get("repeating_current_bounded_p2_generator_proofs_can_change_this_deduction") is not False:
        errors.append("REPROOF_LOOP_NOT_DELETED")

    return {
        "pass": not errors,
        "status": "PASS__CURRENT_BOUND_PROFESSIONAL_QUALITY_PREMISES_HIT_INFORMATION_CUT"
                  if not errors else "FAIL_CLOSED__SEMANTIC_BINDING_ERROR",
        "errors": errors,
        "professional_quality_global_scope_equivalent_now": False,
        "bounded_p2_cell_remains_valid": True,
        "universal_visible_policy_exists_for_opposed_hidden_worlds": universal_visible_policy_exists,
        "minimax_visible_only_success": str(minimax),
        "new_information_or_new_structural_restriction_required": not errors,
        "fresh_target_case_executed": False,
        "abc_closed": False,
        "d_finality_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
