from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUBJECT = ROOT / "canonical/governance/ABC_V12_PRIMITIVE_ESCAPE_NORMAL_FORM_20261007_V1.json"
AUTH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V12.json"
ROLE = ROOT / "canonical/governance/TARGET_ROLE_ESCAPE_FRONTIER_20261007_V1.json"
B9 = ROOT / "canonical/governance/B9_COMPOSITION_DERIVATIVE_REDUCTION_20261007_V1.json"
DRED = ROOT / "canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json"

PRIMITIVE = {
    "B0_INPUT_PERCEPTION_AND_GROUNDING",
    "B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT",
    "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING",
    "B4_EXTERNAL_ACTION_PLANNING_AND_ENVIRONMENT_CONTROL",
    "B7_OUTPUT_COMMUNICATION_SYNTHESIS_AND_ARTIFACT_CONSTRUCTION",
}
ACCEPTED = {
    "B3_TEMPORAL_STATE_MEMORY_AND_CONTINUITY",
    "B5_TOOL_DISCOVERY_SELECTION_AND_LEARNING",
    "B6_DELEGATION_AND_COORDINATION",
    "B8_SELF_VERIFICATION_FAILURE_LOCALIZATION_AND_RECOVERY",
}

def load(path: Path) -> dict:
    v = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(v, dict):
        raise ValueError(path)
    return v

def verify() -> dict:
    errors = []
    s, a, r, b9, d = map(load, (SUBJECT, AUTH, ROLE, B9, DRED))
    st = s.get("structural_reduction", {})

    if a.get("current_truth", {}).get("target_universe_scope_superset_closed") is not True:
        errors.append("SCOPE")
    if a.get("current_truth", {}).get("independent_top_level_terminal_predicate_count") != 2:
        errors.append("TOP_LEVEL")
    if set(st.get("primitive_escape_overapprox", [])) != PRIMITIVE:
        errors.append("PRIMITIVE")
    if set(st.get("fully_accepted_coarse_roles", [])) != ACCEPTED:
        errors.append("ACCEPTED")
    if set(r.get("fully_accepted_roles", [])) != ACCEPTED:
        errors.append("ROLE_SOURCE")
    if st.get("dependent_composition_residual", {}).get("independent_semantic_primitive") is not False:
        errors.append("B9")
    if "B9_MULTI_ROLE_COMPOSITION_IS_NOT_AN_INDEPENDENT_TARGET_DOMINANCE" not in b9.get("theorem", {}).get("statement", ""):
        errors.append("B9_SOURCE")
    if st.get("shared_semantic_frontier", {}).get("count") != 1:
        errors.append("FRONTIER")
    if d.get("current_D_effect_frontier", {}).get("current_accepted_family_effect_mediator_residual_count") != 0:
        errors.append("D_CURRENT")

    return {
        "pass": not errors,
        "errors": errors,
        "target_scope_closed": True if not errors else None,
        "primitive_escape_role_count": 5 if not errors else None,
        "shared_semantic_frontier_count": 1 if not errors else None,
        "b9_independent_semantic_primitive": False if not errors else None,
        "complete_selected_context_abc_closed": False,
        "global_d_finality_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
