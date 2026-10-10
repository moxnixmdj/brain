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
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
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
    "CODING_CURSORBENCH_GE_57_8",
    "TB_SCIENCE_GE_58_7",
}

EXTERNAL_RESULT_ATOMS = TARGET_TUPLE_ATOMS | {
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
}

UNIVERSAL_SCOPE_ATOMS = {
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "VISION_DENSE_NONCHART_SCOPE",
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
}

QUOTIENT_META = set(META) - {"CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META"}


class FactorizationError(RuntimeError):
    pass


def factorize() -> dict:
    obligations = list(ATOMIC) + list(META)
    req: dict[str, list[str]] = {o: [] for o in obligations}

    for o in TARGET_TUPLE_ATOMS:
        req[o].append("TARGET_TUPLE_BINDING")
    for o in EXTERNAL_RESULT_ATOMS:
        req[o].append("EXTERNAL_RESULT_OR_ACCESS")
    for o in UNIVERSAL_SCOPE_ATOMS:
        req[o].append("UNIVERSAL_SCOPE_AND_COMPOSITION")
    for o in QUOTIENT_META:
        req[o].append("BEHAVIORAL_QUOTIENT_AND_TRANSFER")
    req["CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META"].extend([
        "EXTERNAL_RESULT_OR_ACCESS",
        "UNIVERSAL_SCOPE_AND_COMPOSITION",
    ])

    missing = sorted(o for o, interfaces in req.items() if not interfaces)
    if missing:
        raise FactorizationError("UNMAPPED_OBLIGATIONS:" + ",".join(missing))

    unknown = sorted(set(req) - set(obligations))
    if unknown:
        raise FactorizationError("UNKNOWN_OBLIGATIONS:" + ",".join(unknown))

    interfaces: dict[str, list[str]] = {}
    for obligation, names in req.items():
        for name in names:
            interfaces.setdefault(name, []).append(obligation)

    return {
        "status": "PASS__30_CURRENT_TRUTH_OBLIGATIONS__TWO_VERIFIED_NONINDEPENDENT_TRUTHS_DELETED__FOUR_SHARED_CAUSAL_INTERFACES__ZERO_CREDIT",
        "atomic_count": len(ATOMIC),
        "meta_count": len(META),
        "truth_obligation_count": len(obligations),
        "interface_count": len(interfaces),
        "interfaces": {k: sorted(v) for k, v in sorted(interfaces.items())},
        "obligation_interfaces": {k: sorted(v) for k, v in sorted(req.items())},
        "truth_obligations_deleted": 2,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(factorize(), indent=2, sort_keys=True))
