from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXPECTED={
"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V12.json":"3ab55ad2e9df6a7f94acb2e1950569bdc18c8136",
"canonical/governance/K6_CURRENT_AUTHORITY_RECONCILIATION_V3.json":"d03edf08098059811d91f26b174e8e76858bc23d",
"canonical/governance/K6_PROOF_ROUTE_NECESSITY_FALSIFICATION_20261007_V1.json":"bd8faec07728d40424a5a4b968f81d0faf11aa87",
"canonical/verification/K6_PROOF_ROUTE_NECESSITY_WOLFRAM_VERIFICATION_20261007_V1.json":"54dc6bfb945f37e80c34a460df2701b6b6433c82",
"canonical/governance/K6_TARGET_RELATIVE_DECISION_QUOTIENT_THEOREM_20261006_V1.json":"03baddc27d5ee9dd73656fdd801251e1f4fd8cc6",
"canonical/verification/K6_TARGET_RELATIVE_DECISION_QUOTIENT_SPRITE_VERIFICATION_20261006_V1.json":"51a449b74550894a04519ec8e17f008e468506c4",
"canonical/governance/MINIMUM_CAPABILITY_KERNEL_INFORMATION_CUT_20261006_V1.json":"2b6c8150db5c635eb34c35c4041b99c7fc9c5dd5",
"canonical/capabilities/opus55/FINITE_IDENTIFIABILITY_KERNEL_001.json":"1d3a556f15380dfe3aef1e6120c94563df2ef126",
"canonical/capabilities/opus55/SHARED_BOUNDED_DECISION_PRIMITIVES_001.json":"dac3d653df1ed65a3a5249950b8568abce7be62e",
"canonical/governance/TARGET_INFORMATION_CEILING_DOMINANCE_THEOREM_20261005_V1.json":"948123227a5c84a32a1035268f9db395c5d77bc1",
"canonical/verification/TARGET_INFORMATION_CEILING_DOMINANCE_WOLFRAM_VERIFICATION_20261005_V1.json":"a4e9cd8389c5572e7abcd7296b93eccdfa258c77",
}
def blob(b:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def prior_activation(*,selected_context:bool,complete_semantics:bool,empty_intersection:bool,direct_certificate:bool,verifier_available:bool,discriminator_available:bool,uncertainty_acceptable:bool,opus_separator_bound:bool,minimum_prior_localized:bool):
 if not selected_context or not complete_semantics or not empty_intersection:return False
 if direct_certificate or verifier_available or discriminator_available or uncertainty_acceptable:return False
 return opus_separator_bound and minimum_prior_localized
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("SOURCE_MISSING:"+p); continue
  if blob(q.read_bytes())!=w: errors.append("SOURCE_DRIFT:"+p)
 v12=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V12.json")
 k=load("canonical/governance/K6_CURRENT_AUTHORITY_RECONCILIATION_V3.json")
 opt=load("canonical/verification/K6_PROOF_ROUTE_NECESSITY_WOLFRAM_VERIFICATION_20261007_V1.json")
 dqv=load("canonical/verification/K6_TARGET_RELATIVE_DECISION_QUOTIENT_SPRITE_VERIFICATION_20261006_V1.json")
 info=load("canonical/governance/MINIMUM_CAPABILITY_KERNEL_INFORMATION_CUT_20261006_V1.json")
 ident=load("canonical/capabilities/opus55/FINITE_IDENTIFIABILITY_KERNEL_001.json")
 dec=load("canonical/capabilities/opus55/SHARED_BOUNDED_DECISION_PRIMITIVES_001.json")
 a=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json")
 if (v12.get("current_truth") or {}).get("target_universe_scope_superset_closed") is not True: errors.append("V12_SCOPE_NOT_CLOSED")
 cs=k.get("current_state") or {}
 if cs.get("preproof_generic_implementation_generator_count")!=0: errors.append("GENERIC_K6_IMPL_RESIDUAL_NONZERO")
 if cs.get("active_context_specific_k6_work_item") is not None: errors.append("ACTIVE_K6_CONTEXT_EXISTS")
 if cs.get("certificate_form_logically_mandatory") is not False: errors.append("K6_FALSELY_MANDATORY")
 if opt.get("boolean_model",{}).get("countermodel_exists") is not True: errors.append("K6_OPTIONALITY_NOT_VERIFIED")
 if not str(dqv.get("status","")).startswith("INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS"): errors.append("DECISION_QUOTIENT_NOT_VERIFIED")
 if "P_OWNED_PRIOR" not in [x.get("id") for x in (info.get("information_cut") or {}).get("minimum_alternatives",[])]: errors.append("LOWER_BOUND_PRIOR_ROUTE_LOST")
 if not str(ident.get("status","")).startswith("VERIFIED_BRAIN_OWNED"): errors.append("IDENTIFIABILITY_NOT_OWNED")
 if ident.get("donor_runtime_required") is not False: errors.append("IDENTIFIABILITY_DONOR_REQUIRED")
 if not str(dec.get("status","")).startswith("VERIFIED_BRAIN_OWNED"): errors.append("DECISION_PRIMITIVES_NOT_OWNED")
 if dec.get("donor_runtime_required") is not False: errors.append("DECISION_PRIMITIVES_DONOR_REQUIRED")
 ct=a.get("current_truth") or {}
 if ct.get("generic_preproof_semantic_implementation_residual_count")!=0: errors.append("V13_GENERIC_IMPL_NONZERO")
 if ct.get("active_context_specific_k6_work_item") is not None: errors.append("V13_ACTIVE_K6_CONTEXT")
 if ct.get("active_authority_bound_p_only_witness") is not None: errors.append("V13_P_WITNESS_INVENTED")
 if ct.get("persistent_prior_gap_active") is not False: errors.append("V13_PRIOR_GAP_FALSELY_ACTIVE")
 if ct.get("abc_closed") is not False or ct.get("terminal") is not False: errors.append("FALSE_CLOSURE")
 # Lower-bound canary: exact two-world P-only witness activates prior.
 if not prior_activation(selected_context=True,complete_semantics=True,empty_intersection=True,direct_certificate=False,verifier_available=False,discriminator_available=False,uncertainty_acceptable=False,opus_separator_bound=True,minimum_prior_localized=True):
  errors.append("P_ONLY_WITNESS_FAILS_TO_ACTIVATE")
 # Current state has no active selected witness and must not activate.
 if prior_activation(selected_context=False,complete_semantics=True,empty_intersection=True,direct_certificate=False,verifier_available=False,discriminator_available=False,uncertainty_acceptable=False,opus_separator_bound=True,minimum_prior_localized=True):
  errors.append("PRIOR_ACTIVATED_WITHOUT_SELECTED_CONTEXT")
 return {"schema":"PROJECT_BRAIN_ABC_SELECTED_CONTEXT_SEPARATOR_FRONTIER_VERIFIER_V1","status":"PASS__ZERO_GENERIC_K6_OR_PRIOR_BUILD__P_ONLY_GATE_PRESERVED__ABC_OPEN__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"generic_preproof_semantic_implementation_residual_count":0 if not errors else None,"active_persistent_prior_gap":False,"abc_closed":False,"terminal":False,"terminal_credit_delta":0}
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
