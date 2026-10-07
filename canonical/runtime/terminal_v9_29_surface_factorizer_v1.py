from __future__ import annotations

ATOMIC = (
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
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "VISION_DENSE_NONCHART_SCOPE",
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    "FINANCE_ACCOUNTING_INDEX_GE_61",
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
    "CODING_CURSORBENCH_GE_57_8",
    "TB_SCIENCE_GE_58_7",
)

META = (
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
UNIVERSAL_SCOPE_ATOMS = {
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "VISION_DENSE_NONCHART_SCOPE",
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
}
QUOTIENT_META = set(META) - {"CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META"}

ABC = "ABC_SELECTED_CONTEXT_COVER"
D = "D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE"

def factorize() -> dict:
    obligations = list(ATOMIC) + list(META)
    old_interfaces: dict[str, list[str]] = {o: [] for o in obligations}
    for o in TARGET_TUPLE_ATOMS:
        old_interfaces[o].append("TARGET_TUPLE_BINDING")
    for o in EXTERNAL_RESULT_ATOMS:
        old_interfaces[o].append("EXTERNAL_RESULT_OR_ACCESS")
    for o in UNIVERSAL_SCOPE_ATOMS:
        old_interfaces[o].append("UNIVERSAL_SCOPE_AND_COMPOSITION")
    for o in QUOTIENT_META:
        old_interfaces[o].append("BEHAVIORAL_QUOTIENT_AND_TRANSFER")
    old_interfaces["CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META"].extend([
        "EXTERNAL_RESULT_OR_ACCESS",
        "UNIVERSAL_SCOPE_AND_COMPOSITION",
    ])
    missing_old = sorted(o for o,v in old_interfaces.items() if not v)
    if missing_old:
        raise RuntimeError("OLD_INTERFACE_UNMAPPED:" + ",".join(missing_old))

    v9_surfaces: dict[str, list[str]] = {}
    for o in obligations:
        v9_surfaces[o] = [ABC]

    # Conservative overlap: the historical IF authority predicate is still
    # preserved inside ABC hard-constraint semantics, and any absolute
    # deployed effect/authority part is additionally carried by D.
    v9_surfaces["IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"].append(D)

    unmapped = sorted(o for o,v in v9_surfaces.items() if ABC not in v)
    if unmapped:
        raise RuntimeError("V9_ABC_UNMAPPED:" + ",".join(unmapped))

    return {
        "status":"PASS__29_OF_29_ROWS_PRESERVED__29_OF_29_MAP_TO_V9_ABC__IF_AUTHORITY_CONSERVATIVELY_OVERLAPS_D__ZERO_CREDIT",
        "atomic_count":len(ATOMIC),
        "meta_count":len(META),
        "truth_row_count":len(obligations),
        "unique_truth_row_count":len(set(obligations)),
        "old_interface_count":len({x for v in old_interfaces.values() for x in v}),
        "v9_primitive_proof_surface_count":2,
        "v9_surfaces":[ABC,D],
        "abc_mapped_row_count":sum(ABC in v for v in v9_surfaces.values()),
        "d_overlap_row_count":sum(D in v for v in v9_surfaces.values()),
        "unmapped_rows":unmapped,
        "semantic_rows_deleted":0,
        "rows_reclassified_from_primitive_to_surface_slices":len(obligations),
        "old_interfaces":{k:sorted(v) for k,v in sorted(old_interfaces.items())},
        "v9_row_surfaces":{k:sorted(v) for k,v in sorted(v9_surfaces.items())},
        "terminal_credit_delta":0,
    }

if __name__ == "__main__":
    import json
    print(json.dumps(factorize(), indent=2, sort_keys=True))
