from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GOV="canonical/governance/V13_FINANCE_UNCOVERED_SCOPE_ROUTING_TRUTH_REPAIR_20261007_V1.json"
SOURCES={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json":"0d18488b51a222e5da414329ccd9d33cbc1fc31c",
 "canonical/governance/MAXIMAL_CONTEXT_LAW_SPACE_COMPLETENESS_THEOREM_20261007_V1.json":"54f5495fc7a6990400bc9195b15be895b75c62d0",
 "canonical/runtime/terminal_frontier_factorizer_v6_candidate.py":"325113ade6a21cd271c9a279f1cdad4a4f7697f7",
 "canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json":"84973ca473cbb8f6160b45c025567c56f8a3d4ba",
 "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"f8b661abf7cb1b628aa14d966658394b80093879",
}
STRUCTURAL_LEGACY={
 "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
 "VISION_DENSE_NONCHART_SCOPE",
 "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
 "IF_SCOPE_BOUNDARY_NONINFERIOR",
}
FIN="FINANCE_UNCOVERED_SCOPE_AUDIT"

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def route_sets():
    ns={}
    exec((ROOT/"canonical/runtime/terminal_frontier_factorizer_v6_candidate.py").read_text(encoding="utf-8"),ns)
    atomic=set(ns["ATOMIC"])
    legacy_external=set(ns["EXTERNAL_RESULT_ATOMS"])
    benchmark_or_target_relative=legacy_external-{FIN}
    objective_or_structural=(atomic-benchmark_or_target_relative)
    return atomic,legacy_external,benchmark_or_target_relative,objective_or_structural

def verify():
    errors=[]
    for rel,want in SOURCES.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("SOURCE_MISSING:"+rel); continue
        got=blob(p.read_bytes())
        if got!=want:
            errors.append("SOURCE_DRIFT:"+rel+":"+got)

    gov=load(GOV)
    v13=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json")
    maxk=load("canonical/governance/MAXIMAL_CONTEXT_LAW_SPACE_COMPLETENESS_THEOREM_20261007_V1.json")
    fin=load("canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json")
    protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
    atomic,legacy_external,targetlike,objective=route_sets()

    if FIN not in legacy_external:
        errors.append("LEGACY_MISROUTING_NO_LONGER_PRESENT")
    if len(atomic)!=19 or len(legacy_external)!=15:
        errors.append("LEGACY_COUNT_DRIFT")
    if len(targetlike)!=14 or len(objective)!=5:
        errors.append("REPAIRED_COUNT_WRONG")
    if objective != STRUCTURAL_LEGACY|{FIN}:
        errors.append("OBJECTIVE_SET_WRONG:"+",".join(sorted(objective)))

    if (v13.get("abc_normal_form") or {}).get("target_law_information",{}).get("query_rule") != "TARGET_INFORMATION_IS_LOAD_BEARING_ONLY_WHEN_IT_CAN_EXCLUDE_A_SURVIVING_MEMBER_OF_K_c_minus":
        errors.append("V13_TARGET_INFORMATION_RULE_DRIFT")
    sched=set(maxk.get("scheduler_effect") or [])
    if "FIRST_TEST_OR_PROVE_TOP_ELEMENT_BRAIN_DOMINANCE_ON_L_c." not in sched:
        errors.append("MAXIMAL_LAW_TOP_FIRST_RULE_MISSING")

    if fin.get("objective","").startswith("Prove only the Financial Analysis leaves") is not True:
        errors.append("FINANCE_DIRECT_OBJECTIVE_DRIFT")
    admission=fin.get("candidate_admission") or {}
    if "BRAIN_OWNED" not in str(admission.get("rule","")):
        errors.append("FINANCE_BRAIN_OWNED_ROUTE_NOT_REQUIRED")
    if "OPAQUE_EXTERNAL_FINANCIAL_ANALYSIS_PROVIDER_IS_SPECIMEN_ONLY" not in str(admission.get("rule","")):
        errors.append("FINANCE_EXTERNAL_CAPABILITY_NOT_FORBIDDEN")
    leaves=fin.get("leaves") or []
    if {x.get("id") for x in leaves}!={
        "SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE",
        "DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE",
    }:
        errors.append("FINANCE_LEAF_SET_DRIFT")
    if any("OPUS" in json.dumps(x).upper() for x in leaves):
        errors.append("FINANCE_HIDDEN_EVALUATOR_CONTAINS_OPUS_DEPENDENCY")

    fp=[p for p in protocols.get("protocols",[]) if p.get("family")=="FINANCIAL_ANALYSIS"]
    if len(fp)!=1:
        errors.append("FINANCIAL_PROTOCOL_COUNT")
    else:
        acc=fp[0].get("acceptance") or []
        if not any("structured quantitative-method" in str(x) for x in acc):
            errors.append("UNCOVERED_SCOPE_LEAVES_NOT_EXPLICIT")

    r=gov.get("routing_repair") or {}
    if (r.get("legacy_counts") or {}).get("external_result_or_access")!=15:
        errors.append("GOV_LEGACY_COUNT_DRIFT")
    if (r.get("repaired_minimum_counts") or {}).get("benchmark_or_target_relative_result_interfaces")!=14:
        errors.append("GOV_REPAIRED_TARGETLIKE_COUNT_DRIFT")
    if (r.get("repaired_minimum_counts") or {}).get("objective_or_structural_abc_interfaces")!=5:
        errors.append("GOV_REPAIRED_OBJECTIVE_COUNT_DRIFT")

    return {
      "schema":"PROJECT_BRAIN_V13_FINANCE_UNCOVERED_SCOPE_ROUTING_VERIFIER_V1",
      "status":"PASS__FINANCE_UNCOVERED_SCOPE_ROUTED_TO_OBJECTIVE_ABC_DIRECT_PROOF__TARGETLIKE_14_OBJECTIVE_5__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "legacy_external_count":len(legacy_external),
      "benchmark_or_target_relative_count":len(targetlike),
      "objective_or_structural_count":len(objective),
      "moved_interface":FIN,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
    raise SystemExit(0 if verify()["pass"] else 1)
