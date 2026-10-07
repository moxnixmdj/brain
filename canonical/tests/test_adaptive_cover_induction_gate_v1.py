from canonical.runtime.adaptive_cover_induction_gate_v1 import evaluate
R={"path":"canonical/verification/R.json","git_blob_sha":"0"*40,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success"}
def rr(**x): return {**R,**x}
def base():
    return {"initial_state_id":"TOP","top_initialization":{"alpha_total_on_scope":True,"true_context_preserved_in_gamma_top":True,"receipt":rr(alpha_total_on_scope=True,true_context_preserved_in_gamma_top=True)},"states":[
      {"state_id":"TOP","terminal":False,"refinement_policy_id":"q0","refinement_soundness_receipt":rr(true_context_preserved_in_every_actual_successor=True),"refinement_safety_receipt":rr(refinement_safe_on_entire_concretization=True),"outcome_completeness_receipt":rr(outcome_model_complete=True),"outcomes":[{"outcome_id":"a","successor_state_id":"T0","cost_units":2},{"outcome_id":"b","successor_state_id":"M","cost_units":1}]},
      {"state_id":"M","terminal":False,"refinement_policy_id":"q1","refinement_soundness_receipt":rr(true_context_preserved_in_every_actual_successor=True),"refinement_safety_receipt":rr(refinement_safe_on_entire_concretization=True),"outcome_completeness_receipt":rr(outcome_model_complete=True),"outcomes":[{"outcome_id":"done","successor_state_id":"T1","cost_units":3}]},
      {"state_id":"T0","terminal":True,"terminal_policy_id":"p0","terminal_cost_units":5,"terminal_adequacy_receipt":rr(policy_adequate_on_entire_concretization=True),"terminal_safety_receipt":rr(policy_safe_on_entire_concretization=True)},
      {"state_id":"T1","terminal":True,"terminal_policy_id":"p1","terminal_cost_units":4,"terminal_adequacy_receipt":rr(policy_adequate_on_entire_concretization=True),"terminal_safety_receipt":rr(policy_safe_on_entire_concretization=True)}]}
def test_mechanizes_rank_budget_and_cover():
    o=evaluate(base()); assert o["pass"] and o["derived_rank"]=={"M":1,"T0":0,"T1":0,"TOP":2} and o["initial_worst_case_resource_bound_units"]==8.0 and not o["u_empty_authorized"]
def test_cycle_fails():
    p=base();p["states"][1]["outcomes"][0]["successor_state_id"]="TOP";o=evaluate(p);assert not o["pass"] and o["reason"]=="WELL_FOUNDED_RANK_IMPOSSIBLE_CYCLE"
def test_outcome_completeness_is_load_bearing():
    p=base();p["states"][0]["outcome_completeness_receipt"]["outcome_model_complete"]=False;o=evaluate(p);assert not o["pass"] and o["reason"]=="OUTCOME_COMPLETENESS_UNPROVED"
def test_terminal_safety_is_load_bearing():
    p=base();p["states"][2]["terminal_safety_receipt"]["policy_safe_on_entire_concretization"]=False;o=evaluate(p);assert not o["pass"] and o["reason"]=="TERMINAL_SAFETY_UNPROVED"
