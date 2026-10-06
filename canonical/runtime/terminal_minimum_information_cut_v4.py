from __future__ import annotations

from canonical.runtime.terminal_frontier_factorizer_v3_candidate import ATOMIC,META

FIXED_THRESHOLD_DECISION = {
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

DIRECT_HIDDEN_ORACLE = {
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
}

BRAIN_FIRST_BINARY_MATCHED = {
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}

RELATIVE_SCOPE_OR_QUALITY = {
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "VISION_DENSE_NONCHART_SCOPE",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
}

META_TRANSFER = set(META)

def compile_cut() -> dict:
    classes={
        "FIXED_THRESHOLD_DECISION":set(FIXED_THRESHOLD_DECISION),
        "DIRECT_HIDDEN_ORACLE":set(DIRECT_HIDDEN_ORACLE),
        "BRAIN_FIRST_BINARY_MATCHED":set(BRAIN_FIRST_BINARY_MATCHED),
        "RELATIVE_SCOPE_OR_QUALITY":set(RELATIVE_SCOPE_OR_QUALITY),
        "META_TRANSFER":set(META_TRANSFER),
    }
    errors=[]
    keys=list(classes)
    for i,a in enumerate(keys):
        for b in keys[i+1:]:
            overlap=classes[a]&classes[b]
            if overlap:
                errors.append("OVERLAP:"+a+":"+b+":"+",".join(sorted(overlap)))
    union=set().union(*classes.values())
    current=set(ATOMIC)|set(META)
    if union!=current:
        errors.append("PARTITION_MISMATCH:missing="+",".join(sorted(current-union))+";extra="+",".join(sorted(union-current)))
    if len(FIXED_THRESHOLD_DECISION)!=13: errors.append("FIXED_THRESHOLD_COUNT")
    if len(DIRECT_HIDDEN_ORACLE)!=1: errors.append("DIRECT_ORACLE_COUNT")
    if len(BRAIN_FIRST_BINARY_MATCHED)!=3: errors.append("BRAIN_FIRST_COUNT")
    if len(RELATIVE_SCOPE_OR_QUALITY)!=3: errors.append("RELATIVE_SCOPE_COUNT")
    if len(META_TRANSFER)!=8: errors.append("META_COUNT")
    ok=not errors
    return {
      "schema":"PROJECT_BRAIN_TERMINAL_MINIMUM_INFORMATION_CUT_V4",
      "status":"PASS__28_TRUTHS_PARTITIONED_BY_MINIMUM_PROOF_INFORMATION_CLASS__ZERO_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":errors,
      "truth_count":len(current),
      "classes":{k:sorted(v) for k,v in classes.items()},
      "counts":{k:len(v) for k,v in classes.items()},
      "opus_execution_best_case":{
        "FIXED_THRESHOLD_DECISION":0,
        "DIRECT_HIDDEN_ORACLE":0,
        "BRAIN_FIRST_BINARY_MATCHED":0,
        "RELATIVE_SCOPE_OR_QUALITY":"UNPROVED",
        "META_TRANSFER":0,
      },
      "semantic_external_verdict_requirements":{
        "FIXED_THRESHOLD_DECISION":"ONE_AUTHENTICATED_BOUND_PASS_FAIL_VERDICT_PER_SURVIVING_PREDICATE_UNLESS_STRONGER_INTERNAL_PROOF_CLOSES_IT",
        "DIRECT_HIDDEN_ORACLE":"TWO_FROZEN_FINANCE_DIRECT_ORACLE_LEAF_VERDICTS_FOR_THE_ONE_SCOPE_AUDIT",
        "BRAIN_FIRST_BINARY_MATCHED":"ZERO_OPUS_CASE_OUTPUTS_IF_BRAIN_PASSES_COMPLETE_FROZEN_SCOPE__ELSE_ONLY_BRAIN_FAILURE_RESIDUAL",
        "RELATIVE_SCOPE_OR_QUALITY":"STRONGER_ABSOLUTE_SCOPE_COMPLETE_THEOREM_OR_TARGET_RELATIVE_EVIDENCE",
        "META_TRANSFER":"SCOPE_AND_TRANSFER_THEOREMS__NO_BENCHMARK_RESULT_REQUIRED_BY_CLASSIFICATION",
      },
      "terminal_credit_delta":0,
      "execution_authority":False,
      "fresh_reality_authority":False,
      "promotion_authority":False,
    }

if __name__=="__main__":
    import json
    out=compile_cut()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
