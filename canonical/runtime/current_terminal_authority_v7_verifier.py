from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V7.json"
SOURCES={
"v6":("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V6.json","fafde6e942a423798c8cadd0d2a2ccfe140a9f53"),
"v6_audit":("canonical/verification/CURRENT_TERMINAL_AUTHORITY_V6_SOURCE_AUDIT_20261007_V1.json","86d9d058864e18916dc6c42226b3f27ce8f912c4"),
"factor28":("canonical/runtime/terminal_frontier_factorizer_v3_candidate.py","7fa597adec3df75145a501fb3090ffb3bca3026c"),
"verify28":("canonical/verification/TERMINAL_28_OBLIGATION_BASIS_WOLFRAM_VERIFICATION_20261007_V1.json","cb997726ba43ea44cc322df8d77ecaf3af3b30ff"),
"if_countermodel":("canonical/governance/IF_ZERO_CRITICAL_AUTHORITY_NECESSITY_COUNTERMODEL_20261007_V1.json","359bf94a129961a3899e7d7c485ffc29ff015880"),
"if_audit":("canonical/governance/IF_ZERO_CRITICAL_AUTHORITY_TERMINAL_BINDING_AUDIT_20261007_V1.json","8135c0ada40254b13cd18a22dec44b8d81281f3b"),
"pullback":("canonical/governance/EVALUATOR_PULLBACK_DOMINANCE_THEOREM_20261007_V1.json","5febbf7c34368dcce354da44201436a49f87c108"),
"pullback_verify":("canonical/verification/EVALUATOR_PULLBACK_DOMINANCE_VERIFICATION_20261007_V1.json","05d66cf13843578c9a34c929ba1c32509f075c44"),
"kernel":("canonical/governance/STOCHASTIC_KERNEL_TRANSFORM_UNIVERSALITY_20261007_V1.json","658f12eba91a85dbf67dac82b8fb1f6650cc3934"),
"kernel_verify":("canonical/verification/STOCHASTIC_KERNEL_TRANSFORM_UNIVERSALITY_WOLFRAM_VERIFICATION_20261007_V1.json","c55afa5aaae1587a6973908faf8b0e051cceb31a"),
"escape":("canonical/governance/TARGET_UNDOMINATED_ESCAPE_REDUCTION_20261007_V1.json","c6757e71f862dd592402199ac12afb8bca45c256"),
"escape_replay":("canonical/verification/TARGET_UNDOMINATED_ESCAPE_REPLAY_20261007_V1.json","5cc55a400b81db8aa356de811f46d24d8b26c83f"),
"escape_wolfram":("canonical/verification/TARGET_UNDOMINATED_ESCAPE_WOLFRAM_VERIFICATION_20261007_V1.json","54d1f2184548dba880adcd9006df31e6c4dc3f65"),
"escape_roles":("canonical/governance/TARGET_ROLE_ESCAPE_FRONTIER_20261007_V1.json","388dd2cb544b7b7bd7ded5779f51a06d3acb3ee3"),
}
def blob(p):
    b=(ROOT/p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def verify():
    errors=[]
    for name,(path,sha) in SOURCES.items():
        got=blob(path)
        if got!=sha: errors.append(f"BLOB_DRIFT:{name}:{got}")
    if errors:
        return {"pass":False,"errors":errors,"terminal":False}
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    v6=load(SOURCES["v6"][0])
    v6a=load(SOURCES["v6_audit"][0])
    v28=load(SOURCES["verify28"][0])
    ifc=load(SOURCES["if_countermodel"][0])
    ifa=load(SOURCES["if_audit"][0])
    kv=load(SOURCES["kernel_verify"][0])
    ew=load(SOURCES["escape_wolfram"][0])
    er=load(SOURCES["escape_replay"][0])
    roles=load(SOURCES["escape_roles"][0])
    if v6["preserved_truth"]["open_truth_obligations"]!=29: errors.append("V6_NOT_29")
    if "ONLY_C_SCHEDULING_REPRESENTATION" not in v6a["audit_conclusion"]: errors.append("V6_AUDIT_SCOPE")
    recompute=v28["independent_provider"]["recomputation"]
    if recompute["total"]!=28 or recompute["unique_count"]!=28: errors.append("VERIFY28_TOTAL")
    if recompute["deleted_predicate_present"] is not False: errors.append("VERIFY28_DELETED_PRESENT")
    if v28["deletion_basis"]["deleted_predicate"]!="IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS": errors.append("WRONG_DELETION")
    if "ABSOLUTE_ZERO_IS_NOT_LOGICALLY_NECESSARY" not in ifc["constructive_countermodel"]["logical_conclusion"]: errors.append("COUNTERMODEL_MISSING")
    if ifa["audit_conclusion"]["current_binding_class"]!="FROZEN_FAMILY_ACCEPTANCE_RULE__NOT_INDEPENDENTLY_BOUND_AS_A_SEPARATE_L2_ABSOLUTE_TERMINAL_GATE": errors.append("IF_AUDIT_BINDING_CLASS")
    if ifa["audit_conclusion"]["necessity_status"]!="NOT_ESTABLISHED_AS_LITERAL_ZERO": errors.append("IF_AUDIT_NOT_SUPPORTIVE")
    if kv["independent_provider"]["verified"]["two_by_two_row_stochastic_kernel_composition_remains_row_stochastic"] is not True: errors.append("KERNEL_COMPOSITION_NOT_VERIFIED")
    if kv["independent_provider"]["verified"]["pullback_of_evaluator_through_composed_kernel_equals_iterated_pullback"] is not True: errors.append("KERNEL_PULLBACK_NOT_VERIFIED")
    if ew["verified"]["u_subset_s_implies_target_dominance_iff_no_target_member_lies_in_s_minus_d_b"] is not True: errors.append("ESCAPE_EQUIVALENCE_NOT_VERIFIED")
    if ew["verified"]["full_superdomain_dominance_not_necessary"] is not True: errors.append("ESCAPE_FULL_SUPERDOMAIN_NECESSITY_NOT_FALSIFIED")
    if not er["status"].startswith("EXACT_REBASED_BRANCH_REPLAY_PASS__5_OF_5"): errors.append("ESCAPE_REPLAY_NOT_PASS")
    if len(roles["fully_accepted_roles"])!=4 or len(roles["structural_escape_roles"])!=6: errors.append("ESCAPE_ROLE_COUNTS")
    ct=a["current_truth"]
    if ct["open_truth_obligations"]!=28: errors.append("AUTH_TRUTH_COUNT")
    if ct["atomic_open"]!=20 or ct["meta_open"]!=8: errors.append("AUTH_ATOMIC_META")
    if ct["direct_external_result_atoms"]!=15 or ct["unresolved_zero_evidence_atoms_or_meta"]!=13: errors.append("AUTH_ROUTING_COUNTS")
    if ct["accepted_families"]!=5 or ct["open_families"]!=14: errors.append("AUTH_FAMILY_COUNTS")
    if ct["terminal"] is not False: errors.append("TERMINAL_DRIFT")
    if a["accounting"]["terminal_credit_delta"]!=0: errors.append("CREDIT_DRIFT")
    return {
      "schema":"PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_V7_VERIFIER_V1",
      "status":"PASS__V6_COMPOSED_WITH_VERIFIED_28_TRUTH_BASIS_AND_KERNEL_C_COMPRESSION__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "open_truth_obligations":28 if not errors else None,
      "accepted_families":5 if not errors else None,
      "open_families":14 if not errors else None,
      "terminal":False,
      "terminal_credit_delta":0,
    }
if __name__=="__main__":
    out=verify()
    print(json.dumps(out,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
