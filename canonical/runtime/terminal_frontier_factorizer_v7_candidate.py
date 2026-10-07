from __future__ import annotations

DIRECT15 = (
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

DERIVED_INSIDE_ABC = (
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

TARGET_TUPLE_ATOMS = {
    "CODING_TB4_GE_66_4","CHARTOGRAPHY_TOOLS_GE_89","HLE_TOOLS_GE_67_7",
    "OSWORLD_2_1_PARTIAL_GE_81_8","FINANCE_AGENT_V2_GE_58_59",
    "CODING_FRONTIERCODE_GE_54_4","PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822","AUTOMATIONBENCH_GE_40",
    "MYSTERYMECHANISM_GE_49_55","FINANCE_ACCOUNTING_INDEX_GE_61",
    "CODING_CURSORBENCH_GE_57_8","TB_SCIENCE_GE_58_7",
}
EXTERNAL_RESULT_ATOMS = TARGET_TUPLE_ATOMS | {
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
}

def factorize():
    if set(DIRECT15) != EXTERNAL_RESULT_ATOMS:
        raise RuntimeError("DIRECT15_DRIFT")
    req={o:[] for o in DIRECT15}
    for o in TARGET_TUPLE_ATOMS:
        req[o].append("TARGET_TUPLE_BINDING")
    for o in DIRECT15:
        req[o].append("EXTERNAL_RESULT_OR_STRONGER_CERTIFICATE")
    missing=sorted(o for o,v in req.items() if not v)
    if missing:
        raise RuntimeError("UNMAPPED:"+",".join(missing))
    return {
      "status":"PASS__15_INDEPENDENT_ACCEPTANCE_CONJUNCTS__U4_AND_COMPOSITION_DERIVED_INSIDE_COMPLETE_ABC__META8_REFINEMENTS__D15_U0__ZERO_CREDIT",
      "direct_result_count":len(DIRECT15),
      "derived_inside_abc_count":len(DERIVED_INSIDE_ABC),
      "meta_refinement_count":len(META_REFINEMENTS),
      "independent_acceptance_conjunct_count":len(DIRECT15),
      "independent_obligation_interfaces":{k:sorted(v) for k,v in sorted(req.items())},
      "derived_inside_abc":list(DERIVED_INSIDE_ABC),
      "route_counts":{"D":15,"U":0,"J":0,"G":0,"T":0},
      "abc_closed":False,
      "terminal_credit_delta":0,
      "acceptance_credit_delta":0,
      "ownership_credit_delta":0,
    }

if __name__=="__main__":
    import json
    print(json.dumps(factorize(),indent=2,sort_keys=True))
