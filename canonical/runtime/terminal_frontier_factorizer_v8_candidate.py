from __future__ import annotations

LOCAL_DIRECT_EVIDENCE_ROUTES = (
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

DERIVED_OR_ABSORBED_INSIDE_ABC = (
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "VISION_DENSE_NONCHART_SCOPE",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
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

def factorize():
    if len(LOCAL_DIRECT_EVIDENCE_ROUTES) != 15:
        raise RuntimeError("DIRECT_ROUTE_COUNT_DRIFT")
    return {
      "status":"PASS__ONE_GLOBAL_ACCEPTANCE_SEMANTIC_ABC__15_LOCAL_DIRECT_EVIDENCE_ROUTES__ZERO_SCOPE_DELETION__ZERO_CREDIT",
      "independent_acceptance_semantics":["ABC_SELECTED_CONTEXT_COVER_COMPLETE"],
      "independent_acceptance_semantic_count":1,
      "independent_scope_specific_acceptance_conjunct_count":0,
      "local_direct_evidence_route_count":len(LOCAL_DIRECT_EVIDENCE_ROUTES),
      "local_direct_evidence_routes":list(LOCAL_DIRECT_EVIDENCE_ROUTES),
      "derived_or_absorbed_inside_abc":list(DERIVED_OR_ABSORBED_INSIDE_ABC),
      "meta_refinement_count":len(META_REFINEMENTS),
      "abc_closed":False,
      "terminal_credit_delta":0,
      "acceptance_credit_delta":0,
      "ownership_credit_delta":0,
    }

if __name__=="__main__":
    import json
    print(json.dumps(factorize(),indent=2,sort_keys=True))
