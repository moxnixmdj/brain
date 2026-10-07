from __future__ import annotations
import hashlib,json,importlib.util,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CELL=ROOT/"canonical/governance/V13_DB_LIVEBENCH_ACTIVE15_SELECTED_CELL_20261007_V1.json"

EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json":"0d18488b51a222e5da414329ccd9d33cbc1fc31c",
 "canonical/governance/DIRECT_END_TO_END_SELECTED_CELL_CERTIFICATE_THEOREM_20261007_V1.json":"ecb52ca25fa14a60b7c34206fea25d8d3cfdcf0d",
 "canonical/governance/MAXIMAL_CONTEXT_LAW_SPACE_COMPLETENESS_THEOREM_20261007_V1.json":"54f5495fc7a6990400bc9195b15be895b75c62d0",
 "canonical/verification/LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_PROMOTION_INDEPENDENT_VERIFICATION_20261005_V1.json":"57e27e3c56372b57a1d4e0255f49340d4a4c8588",
 "canonical/governance/LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_PROMOTION_PRECOMMIT_20261005_V1.json":"e0c84402955425aca64b20562f3400287e8792fc",
 "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":"0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
 "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":"7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
 "canonical/runtime/livebench_legacy15_contract_composer_v2.py":"d73ec366b32252996258eae6d10d67d4d6a5e042",
 "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":"71e637c70edf1c582e28ea38b3b798965c803a06",
 "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py":"09a5d7810fd46713aaf06cf1d204fe140d1d8045",
 "canonical/runtime/livebench_pointwise_minimum_cut_v1.py":"3552ceb0c9bdf80e8666460931f20f06f580a0f2",
 "canonical/runtime/livebench_post_sacrifice_parametric_reduction_v1.py":"fd1ad043fb9fe461b6593f5b8130093be0028c22",
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def _invoke_route():
    p=ROOT/"canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py"
    spec=importlib.util.spec_from_file_location("brain_livebench_selected_route",p)
    if spec is None or spec.loader is None:
        raise RuntimeError("ROUTE_LOAD_FAILED")
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m.run({"contracts":[{"instruction_id":"detectable_format:title","slots":{}}]})

def verify():
    errors=[]
    for rel,want in EXPECTED.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("SOURCE_MISSING:"+rel); continue
        got=blob(p)
        if got!=want: errors.append("SOURCE_DRIFT:"+rel+":"+got)

    cell=json.loads(CELL.read_text(encoding="utf-8"))
    proof=load("canonical/verification/LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_PROMOTION_INDEPENDENT_VERIFICATION_20261005_V1.json")
    pre=load("canonical/governance/LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_PROMOTION_PRECOMMIT_20261005_V1.json")

    if cell["cell"]["complete_semantics"] is not True: errors.append("CELL_SEMANTICS_NOT_COMPLETE")
    if cell["cell"]["route_identity_exact"] is not True: errors.append("CELL_ROUTE_NOT_EXACT")
    app=cell["theorem_application"]
    for k in ("route_is_final_selected_route_for_cell","semantics_complete_for_cell","e2e_directly_proves_final_route_law","brain_law_is_top_on_cell","maximal_K_minus_empty","abc_selected_cell_closed","add_cell_to_D_B"):
        if app.get(k) is not True: errors.append("CELL_APPLICATION_FALSE:"+k)

    if proof.get("status")!="INDEPENDENT_PUBLIC_RUNNER_PASS__CLEAN_SCOPE_COMPLETE_POINTWISE_DOMINANCE_FORCES_LIVEBENCH_IF_GE_65_7__ZERO_TARGET_ROWS":
        errors.append("PROOF_STATUS_DRIFT")
    rp=proof.get("recomputed_proof") or {}
    if rp.get("exact_frozen_population_count")!=200: errors.append("POPULATION_DRIFT")
    if rp.get("active_instruction_identity_count")!=15: errors.append("ACTIVE15_DRIFT")
    if rp.get("full_cross_exact_pointwise_matches")!=712704 or rp.get("full_cross_total_cases")!=712704:
        errors.append("POINTWISE_COVERAGE_DRIFT")
    brain=float(rp.get("brain_mean_lower_bound_percent"))
    opus=float(rp.get("public_opus55_raw_if_mean_percent"))
    threshold=float(rp.get("required_threshold_percent"))
    if not (brain>=opus>=threshold): errors.append("DOMINANCE_ARITHMETIC_FAIL")

    fw=proof.get("contamination_firewall") or {}
    for key in ("terminal_rows_read","terminal_kwargs_read","target_responses_read","target_scores_read"):
        if fw.get(key)!=0: errors.append("TARGET_DATA_USED:"+key)

    exact=proof.get("exact_subject_blobs") or {}
    for path,want in cell["selected_route"]["route_blobs"].items():
        name=Path(path).stem
        mapping={
          "livebench_legacy15_composition_archetypes_v1":"composition_archetypes",
          "livebench_legacy15_slot_feasibility_v1":"slot_feasibility",
          "livebench_legacy15_contract_composer_v2":"composer_v2",
          "livebench_legacy15_pointwise_optimal_v1":"pointwise_planner",
        }
        k=mapping[name]
        if exact.get(k)!=want: errors.append("PROOF_ROUTE_BINDING_MISMATCH:"+path)

    if pre.get("target_predicate")!="LIVEBENCH_IF_GE_65_7": errors.append("PRECOMMIT_TARGET_DRIFT")

    try:
        out=_invoke_route()
        if out.get("status")!="CANDIDATE_POINTWISE_OPTIMAL": errors.append("ROUTE_EXEC_STATUS")
        if out.get("model_dependency_count")!=0: errors.append("ROUTE_MODEL_DEPENDENCY")
        if not isinstance(out.get("response"),str) or not out.get("response"): errors.append("ROUTE_EMPTY_RESPONSE")
    except Exception as exc:
        errors.append("ROUTE_EXEC_FAILED:"+type(exc).__name__+":"+str(exc))

    return {
      "schema":"PROJECT_BRAIN_V13_DB_LIVEBENCH_ACTIVE15_SELECTED_CELL_VERIFIER_V1",
      "status":"PASS__ACTIVE15_CELL_IN_D_B__D_DELTA_STILL_REQUIRED__ZERO_NEW_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "cell_id":"LIVEBENCH_ACTIVE15_FROZEN_PUBLIC_GRAMMAR_CELL",
      "add_cell_to_D_B":not errors,
      "D_delta_required":True,
      "family_credit_delta":0,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
