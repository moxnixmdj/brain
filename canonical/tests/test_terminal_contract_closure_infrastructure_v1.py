from canonical.runtime import terminal_contract_closer_v1 as c
from canonical.runtime import terminal_authority_consistency_guard_v1 as g

def env():
    return {
      "required_dimensions":["A","B","C"],
      "verified_envelopes":[{"id":"E","covers":["A"],"receipt":"r://a","proof_kind":"FORMAL_PROOF","authority_verified":True}],
      "verified_failures":[],
      "verified_implications":[{"if_proved":["B"],"then_proved":["C"],"receipt":"r://b-c","authority_verified":True}],
    }

def test_closer_preserves_irreducible_residual_and_never_grants_terminal_credit():
    out=c.evaluate({"contracts":[{"contract_id":"X","envelope_input":env(),
      "scope_gate_v2_independent_pass":True,
      "terminal_population_binding_frozen":True,
      "terminal_population_binding_independent_pass":True,
      "terminal_acceptance_mode_frozen":True}]})
    assert out["status"]=="PREWAVE_RESIDUAL_OPEN"
    assert out["contracts"][0]["minimum_residual_proof_basis"]==["B"]
    assert out["terminal_credit_delta"]==0
    assert out["execution_authority"] is False

def test_closer_admits_only_fully_verified_preconditions():
    e=env()
    e["verified_envelopes"].append({"id":"E2","covers":["B"],"receipt":"r://b","proof_kind":"FORMAL_PROOF","authority_verified":True})
    row={"contract_id":"X","envelope_input":e,"scope_gate_v2_independent_pass":True,
         "terminal_population_binding_frozen":True,"terminal_population_binding_independent_pass":True,
         "terminal_acceptance_mode_frozen":True}
    out=c.evaluate({"contracts":[row]})
    assert out["status"]=="ALL_PREWAVE_ROUTES_ADMISSIBLE"
    assert out["contracts"][0]["prewave_route_admissible"] is True
    assert out["execution_authority"] is False

def test_consistency_guard_detects_admissible_marked_missing():
    basis={"contracts":[{"behavior_id":"A","proof_state":"TERMINAL_ROUTE_FROZEN_ADMISSIBLE"}],
           "admissible_frozen_terminal_route_count":1,"active_contract_count":1,"execution_authority":False}
    gap={"missing_active_contracts":[{"behavior_id":"A"}],"source_bindings":{"registry":{"active_count":1}}}
    preq={"execution_authority":False}
    out=g.evaluate(basis,gap,preq)
    assert out["status"]=="FAIL_CLOSED_STALE_OR_CONTRADICTORY_STATE"
    assert out["terminal_credit_delta"]==0
