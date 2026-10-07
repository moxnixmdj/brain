from __future__ import annotations

DIRECT = (
    "CODING_TB4_GE_66_4",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "HLE_TOOLS_GE_67_7",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "FINANCE_AGENT_V2_GE_58_59",
    "CODING_FRONTIERCODE_GE_54_4",
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "AUTOMATIONBENCH_GE_40",
    "MYSTERYMECHANISM_GE_49_55",
    "FINANCE_ACCOUNTING_INDEX_GE_61",
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
    "CODING_CURSORBENCH_GE_57_8",
    "TB_SCIENCE_GE_58_7",
)

ABC_STRUCTURAL_REFINEMENTS = (
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "VISION_DENSE_NONCHART_SCOPE",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
)

DERIVED_INSIDE_ABC = (
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
)

META_REFINEMENTS = (
    "CYBERSECURITY",
    "BIOLOGY_RESEARCH_AND_DEVELOPMENT",
    "AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT",
    "HEALTHCARE",
    "MATHEMATICAL_REASONING_ARXIVMATH",
    "MULTILINGUAL_PERFORMANCE",
    "LONG_CONTEXT",
    "CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META",
)

EXPECTED_STRUCTURAL = {
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "VISION_DENSE_NONCHART_SCOPE",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
}

ABC_REFINEMENT_RULES = {
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION":
        "AGENCY_CELLS_INCLUDE_SAFETY_SCOPE_INVALID_ACTION_AND_UNRECOVERED_FAILURE_EVALUATORS_OR_HARD_CONSTRAINTS",
    "VISION_DENSE_NONCHART_SCOPE":
        "VISION_CELLS_COVER_DENSE_DOCUMENTS_SCREENSHOTS_DIAGRAMS_AND_COMPLEX_REAL_WORLD_IMAGERY_WITH_B0_ADEQUACY",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR":
        "AGENCY_CELLS_INCLUDE_FROZEN_TERMINAL_TASK_SUCCESS_SEMANTICS_AND_TARGET_RELATIVE_DISTRIBUTIONAL_DOMINANCE",
    "IF_SCOPE_BOUNDARY_NONINFERIOR":
        "IF_CELLS_INCLUDE_FROZEN_SCOPE_BOUNDARY_SUCCESS_AUTHORITY_SCOPE_ABSTENTION_AND_FAIL_CLOSED_SEMANTICS",
}

def factorize() -> dict:
    direct = set(DIRECT)
    structural = set(ABC_STRUCTURAL_REFINEMENTS)
    if len(DIRECT) != 15 or len(direct) != 15:
        raise RuntimeError("DIRECT15_DRIFT")
    if structural != EXPECTED_STRUCTURAL:
        raise RuntimeError("STRUCTURAL4_DRIFT")
    if set(ABC_REFINEMENT_RULES) != EXPECTED_STRUCTURAL:
        raise RuntimeError("STRUCTURAL4_RULE_DRIFT")
    if direct & structural:
        raise RuntimeError("DIRECT_STRUCTURAL_OVERLAP")
    if set(DERIVED_INSIDE_ABC) & (direct | structural):
        raise RuntimeError("DERIVED_OVERLAP")
    return {
        "status": (
            "PASS__15_INDEPENDENT_ACCEPTANCE_CONJUNCTS__"
            "STRUCTURAL4_INSIDE_ABC__COMPOSITION_DERIVED_INSIDE_ABC__"
            "META8_REFINEMENTS__ZERO_CREDIT"
        ),
        "independent_acceptance_conjunct_count": 15,
        "direct_result_count": 15,
        "structural_independent_count": 0,
        "structural_abc_refinement_count": 4,
        "composition_derived_inside_abc_count": 1,
        "meta_refinement_count": 8,
        "verified_independent_truth_deletions_if_promoted": 9,
        "route_counts": {"D": 15, "U": 0, "J": 0, "G": 0, "T": 0},
        "independent_acceptance_conjuncts": sorted(direct),
        "abc_structural_refinements": {
            k: ABC_REFINEMENT_RULES[k] for k in sorted(ABC_REFINEMENT_RULES)
        },
        "derived_inside_abc": list(DERIVED_INSIDE_ABC),
        "meta_refinements": list(META_REFINEMENTS),
        "terminal_global_surfaces_still_required": [
            "ABC_SELECTED_CONTEXT_COVER",
            "D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE",
        ],
        "terminal": False,
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
    }

if __name__ == "__main__":
    import json
    print(json.dumps(factorize(), indent=2, sort_keys=True))
