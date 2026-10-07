from __future__ import annotations
import hashlib,json
from pathlib import Path
from canonical.runtime import terminal_frontier_factorizer_v6_candidate as f

ROOT=Path(__file__).resolve().parents[2]
THEOREM=ROOT/"canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json"

EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V10.json":"86d7cd3f96afc9330d5b474a33cc43018fc6ff6b",
 "canonical/runtime/terminal_frontier_factorizer_v6_candidate.py":"325113ade6a21cd271c9a279f1cdad4a4f7697f7",
 "canonical/governance/PUBLIC_FIXED_BAR_NECESSITY_FALSIFICATION_20261007_V1.json":"e9cd80eca9b5e22d79dc1df9840924e12e01c366",
 "canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json":"333bdc8306a19f005a600a47b415a4bd9cf9868c",
 "canonical/governance/META8_SELECTED_CONTEXT_ABC_ABSORPTION_20261007_V1.json":"1eb85b2b58ee53942716e70dbc7f523f08b3f302",
 "canonical/governance/COMPOSITION_TERMINAL_SUCCESS_DERIVATION_TRUTH_REPAIR_20261007_V1.json":"fb52ecf6e0ba703bbad9b0b626ba85057c438215",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V9.json":"1ec7f2c86534d046e51ddda00001ed287039fc0a",
}

FIXED13={
 "CODING_TB4_GE_66_4","CHARTOGRAPHY_TOOLS_GE_89","HLE_TOOLS_GE_67_7",
 "OSWORLD_2_1_PARTIAL_GE_81_8","FINANCE_AGENT_V2_GE_58_59",
 "CODING_FRONTIERCODE_GE_54_4","PROWORK_GDPVAL_GE_1846",
 "PROWORK_AA_BRIEFCASE_GE_1822","AUTOMATIONBENCH_GE_40",
 "MYSTERYMECHANISM_GE_49_55","FINANCE_ACCOUNTING_INDEX_GE_61",
 "CODING_CURSORBENCH_GE_57_8","TB_SCIENCE_GE_58_7",
}
OTHER2={"FINANCE_UNCOVERED_SCOPE_AUDIT","SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"}
STRUCTURAL4={
 "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
 "VISION_DENSE_NONCHART_SCOPE",
 "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
 "IF_SCOPE_BOUNDARY_NONINFERIOR",
}

def blob(rel:str)->str:
    p=ROOT/rel
    if not p.exists(): return ""
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def logical_collapse(*, rows:set[str], refinements_of_u:set[str], independent_score_identities:set[str]|None=None):
    independent_score_identities=set(independent_score_identities or ())
    if independent_score_identities:
        return {"pass":False,"reason":"INDEPENDENT_SCORE_IDENTITY_REOPENS:"+",".join(sorted(independent_score_identities))}
    missing=rows-refinements_of_u
    if missing:
        return {"pass":False,"reason":"ROW_NOT_BOUND_AS_U_REFINEMENT:"+",".join(sorted(missing))}
    return {"pass":True,"independent_l1_predicates":["COMPLETE_SELECTED_CONTEXT_ABC"],"refinement_row_count":len(rows)}

def verify():
    errors=[]
    for rel,want in EXPECTED.items():
        if blob(rel)!=want:
            errors.append("SOURCE_DRIFT:"+rel)

    theorem=json.loads(THEOREM.read_text(encoding="utf-8"))
    fixed=load("canonical/governance/PUBLIC_FIXED_BAR_NECESSITY_FALSIFICATION_20261007_V1.json")
    trace=load("canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json")
    meta=load("canonical/governance/META8_SELECTED_CONTEXT_ABC_ABSORPTION_20261007_V1.json")
    comp=load("canonical/governance/COMPOSITION_TERMINAL_SUCCESS_DERIVATION_TRUTH_REPAIR_20261007_V1.json")
    reg=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")

    rows=set(f.ATOMIC)
    expected19=FIXED13|OTHER2|STRUCTURAL4
    if rows!=expected19:
        errors.append("CURRENT19_SET_MISMATCH")
    if len(rows)!=19:
        errors.append("CURRENT19_COUNT_MISMATCH")
    if set(f.EXTERNAL_RESULT_ATOMS)!=(FIXED13|OTHER2):
        errors.append("DIRECT15_CLASSIFICATION_MISMATCH")
    if set(f.STRUCTURAL_ATOMS)!=STRUCTURAL4:
        errors.append("STRUCTURAL4_CLASSIFICATION_MISMATCH")

    if set(fixed.get("current_13_fixed_bar_atoms") or [])!=FIXED13:
        errors.append("FIXED13_REPAIR_SET_MISMATCH")
    tr=fixed.get("truth_repair") or {}
    if tr.get("delete_only")!="FIXED_SCORE_IDENTITY_AS_AN_INDEPENDENT_NECESSARY_TERMINAL_TRUTH":
        errors.append("FIXED_SCORE_IDENTITY_NOT_DELETED")
    rc=fixed.get("routing_consequence") or {}
    if rc.get("target_tuple_binding_is_not_logically_mandatory") is not True:
        errors.append("TARGET_TUPLE_STILL_MANDATORY")
    if rc.get("external_result_or_access_is_not_logically_mandatory_for_these_13_SCOPES") is not True:
        errors.append("EXTERNAL_RESULT_STILL_MANDATORY")

    th=trace.get("theorem") or {}
    if th.get("scope_superset_not_domain_enumeration") is not True:
        errors.append("TRACE_SCOPE_SUPERSET_MISSING")
    critical=trace.get("critical_split") or {}
    if critical.get("current_acceptance_basis_universal_dominance_state")!="OPEN":
        errors.append("TRACE_THEOREM_FALSELY_CLOSES_DOMINANCE")

    pred={str(x.get("id")):x for x in reg.get("predicates") or []}
    if pred.get("FINANCE_UNCOVERED_SCOPE_AUDIT",{}).get("kind")!="DIRECT_SCOPE_AUDIT":
        errors.append("FINANCE_SCOPE_KIND_DRIFT")
    if pred.get("SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",{}).get("kind")!="MATCHED_NONINFERIORITY":
        errors.append("SYNTHESIS_SCOPE_KIND_DRIFT")

    if comp.get("truth_repair",{}).get("delete_as_independent_truth_variable")!="COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR":
        errors.append("COMPOSITION_NOT_DERIVED")
    if int(meta.get("candidate_basis_effect",{}).get("current_meta_count",-1))!=8:
        errors.append("META8_COUNT_DRIFT")

    trows=theorem.get("current_19_refinements") or {}
    theorem_rows=set(trows.get("fixed_bar_successor_scopes") or [])|set(trows.get("other_scope_or_quality_refinements") or [])|set(trows.get("structural_abc_refinements") or [])
    if theorem_rows!=rows:
        errors.append("THEOREM_ROW_SET_MISMATCH")

    collapse=logical_collapse(rows=rows,refinements_of_u=theorem_rows)
    if not collapse["pass"]:
        errors.append("LOGICAL_COLLAPSE_FAIL:"+collapse["reason"])

    nf=theorem.get("normal_form_effect_if_verified") or {}
    if nf.get("independent_L1_predicates")!=["COMPLETE_SELECTED_CONTEXT_ABC"]:
        errors.append("L1_NORMAL_FORM_NOT_ONE_PREDICATE")
    if nf.get("D_ownership_effect_closure")!="REMAINS_SEPARATE_AND_OPEN":
        errors.append("D_FALSELY_ABSORBED")

    return {
      "schema":"PROJECT_BRAIN_L1_UNIVERSAL_ABC_NORMAL_FORM_VERIFIER_V1",
      "status":"PASS__19_ROWS_ARE_ABC_REFINEMENT_PARTITIONS__ONE_INDEPENDENT_L1_PREDICATE__D_SEPARATE__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "current_row_count":19 if not errors else None,
      "fixed_bar_scope_refinements":13 if not errors else None,
      "other_scope_quality_refinements":2 if not errors else None,
      "structural_abc_refinements":4 if not errors else None,
      "independent_l1_predicate_count":1 if not errors else None,
      "independent_l1_predicates":["COMPLETE_SELECTED_CONTEXT_ABC"] if not errors else None,
      "D_remains_separate":True if not errors else None,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
