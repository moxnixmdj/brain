from __future__ import annotations

B0="B0_INPUT_PERCEPTION_AND_GROUNDING"
B1="B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT"
B2="B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING"
B4="B4_EXTERNAL_ACTION_PLANNING_AND_ENVIRONMENT_CONTROL"
B7="B7_OUTPUT_COMMUNICATION_SYNTHESIS_AND_ARTIFACT_CONSTRUCTION"
D="D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE"
ACTIVE=(B0,B1,B2,B4,B7)

ROWS={
"CODING_TB4_GE_66_4":(B2,B4),
"CHARTOGRAPHY_TOOLS_GE_89":(B0,),
"HLE_TOOLS_GE_67_7":(B2,),
"OSWORLD_2_1_PARTIAL_GE_81_8":(B0,B4),
"FINANCE_AGENT_V2_GE_58_59":(B2,B4),
"CODING_FRONTIERCODE_GE_54_4":(B2,B4),
"PROWORK_GDPVAL_GE_1846":(B1,B2,B7),
"PROWORK_AA_BRIEFCASE_GE_1822":(B1,B2,B7),
"AUTOMATIONBENCH_GE_40":(B1,B4),
"MYSTERYMECHANISM_GE_49_55":(B2,),
"AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION":(B1,B4),
"VISION_DENSE_NONCHART_SCOPE":(B0,),
"IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS":(B1,D),
"AGENCY_MATCHED_SUCCESS_NONINFERIOR":(B4,),
"IF_SCOPE_BOUNDARY_NONINFERIOR":(B0,B1),
"COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR":(B0,B1,B2,B4,B7),
"FINANCE_ACCOUNTING_INDEX_GE_61":(B2,),
"FINANCE_UNCOVERED_SCOPE_AUDIT":(B2,),
"SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR":(B1,B2,B7),
"CODING_CURSORBENCH_GE_57_8":(B2,B4),
"TB_SCIENCE_GE_58_7":(B2,),
"CYBERSECURITY":(B2,B4),
"BIOLOGY_RESEARCH_AND_DEVELOPMENT":(B2,B7),
"AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT":(B2,B4),
"HEALTHCARE":(B0,B1,B2,B4,B7),
"MATHEMATICAL_REASONING_ARXIVMATH":(B2,),
"MULTILINGUAL_PERFORMANCE":(B0,B1,B2,B4,B7),
"LONG_CONTEXT":(B0,B1,B2,B4,B7),
"CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META":(B0,B7),
}

ATOMIC=(
"CODING_TB4_GE_66_4","CHARTOGRAPHY_TOOLS_GE_89","HLE_TOOLS_GE_67_7",
"OSWORLD_2_1_PARTIAL_GE_81_8","FINANCE_AGENT_V2_GE_58_59",
"CODING_FRONTIERCODE_GE_54_4","PROWORK_GDPVAL_GE_1846",
"PROWORK_AA_BRIEFCASE_GE_1822","AUTOMATIONBENCH_GE_40",
"MYSTERYMECHANISM_GE_49_55","AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
"VISION_DENSE_NONCHART_SCOPE","IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
"AGENCY_MATCHED_SUCCESS_NONINFERIOR","IF_SCOPE_BOUNDARY_NONINFERIOR",
"COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR","FINANCE_ACCOUNTING_INDEX_GE_61",
"FINANCE_UNCOVERED_SCOPE_AUDIT","SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
"CODING_CURSORBENCH_GE_57_8","TB_SCIENCE_GE_58_7",
)
META=(
"CYBERSECURITY","BIOLOGY_RESEARCH_AND_DEVELOPMENT",
"AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT","HEALTHCARE",
"MATHEMATICAL_REASONING_ARXIVMATH","MULTILINGUAL_PERFORMANCE","LONG_CONTEXT",
"CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META",
)

def compile_matrix()->dict:
    canonical=set(ATOMIC)|set(META)
    mapped=set(ROWS)
    if canonical!=mapped:
        missing=sorted(canonical-mapped)
        extra=sorted(mapped-canonical)
        raise RuntimeError(f"ROW_SET_MISMATCH:missing={missing}:extra={extra}")
    allowed=set(ACTIVE)|{D}
    invalid=sorted((row,role) for row,roles in ROWS.items() for role in roles if role not in allowed)
    if invalid:
        raise RuntimeError("INVALID_ROLE_MAPPING:"+repr(invalid))
    empty=sorted(row for row,roles in ROWS.items() if not roles)
    if empty:
        raise RuntimeError("EMPTY_ROLE_MAPPING:"+",".join(empty))
    counts={role:0 for role in ACTIVE}
    d_overlap=[]
    role_rows={role:[] for role in ACTIVE}
    for row,roles in ROWS.items():
        for role in ACTIVE:
            if role in roles:
                counts[role]+=1
                role_rows[role].append(row)
        if D in roles:
            d_overlap.append(row)
    ranking=sorted(ACTIVE,key=lambda r:(-counts[r],r))
    return {
      "schema":"PROJECT_BRAIN_V9_ABC_RESIDUAL_ROLE_MATRIX_V1",
      "status":"PASS__29_OF_29_PRESERVED__FIVE_ACTIVE_PRIMITIVE_ABC_ROLES__CONSERVATIVE_SEARCH_PROJECTION__ZERO_CREDIT",
      "truth_row_count":len(canonical),
      "atomic_count":len(ATOMIC),
      "meta_count":len(META),
      "active_abc_roles":list(ACTIVE),
      "active_role_count":len(ACTIVE),
      "role_row_counts":counts,
      "role_rows":{k:sorted(v) for k,v in role_rows.items()},
      "priority_order_by_shared_row_reach":ranking,
      "d_overlap_rows":sorted(d_overlap),
      "d_overlap_count":len(d_overlap),
      "rows":{k:list(v) for k,v in sorted(ROWS.items())},
      "semantic_rows_deleted":0,
      "terminal_credit_delta":0,
      "boundary":"CONSERVATIVE_ROLE_LEVEL_SEARCH_SCHEDULER_ONLY__WITHIN_ROLE_TARGET_LAW_AND_UTILITY_DISTINCTIONS_REMAIN_LOAD_BEARING__A_ROW_MAY_MAP_TO_MULTIPLE_ROLES",
    }

if __name__=="__main__":
    import json
    print(json.dumps(compile_matrix(),indent=2,sort_keys=True))
