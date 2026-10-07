from copy import deepcopy
from canonical.runtime.c_acceptance_ledger_transport_gate_v2 import verify_acceptance_c_gate

BASE=[{
  "predicate_id":"A","state":"PROVED","proof_kind":"RECEIPT",
  "source_path":"r.json","source_sha":"abc","basis":"direct",
  "scope_complete":True,"independent_or_objective":True,
}]

def cert(ok=True):
    return {
      "implementation_content_addressed":True,
      "load_bearing_state_quotient_complete":True,
      "target_evaluator_pullbacks_complete":ok,
      "hard_constraint_preimages_complete":True,
      "independent_or_objective_verified":True,
    }

def test_exact_baseline_row_is_grandfathered():
    out=verify_acceptance_c_gate(deepcopy(BASE),BASE)
    assert out["pass"] is True
    assert out["grandfathered_exact_baseline_count"]==1

def test_mutated_old_receipt_cannot_hide_as_grandfathered():
    rows=deepcopy(BASE)
    rows[0]["basis"]="mutated"
    out=verify_acceptance_c_gate(rows,BASE)
    assert out["pass"] is False
    assert any("EXPLICIT_C_ROUTE_KIND" in e for e in out["errors"])

def test_new_receipt_kind_still_requires_explicit_route_kind():
    rows=deepcopy(BASE)+[{
      "predicate_id":"B","state":"PROVED","proof_kind":"RECEIPT",
      "source_path":"b.json","source_sha":"def","basis":"new",
      "scope_complete":True,"independent_or_objective":True,
    }]
    assert verify_acceptance_c_gate(rows,BASE)["pass"] is False
    rows[-1]["c_route_kind"]="DIRECT"
    out=verify_acceptance_c_gate(rows,BASE)
    assert out["pass"] is True and out["new_or_mutated_direct_count"]==1

def test_transport_requires_proved_parent_and_complete_local_c():
    rows=deepcopy(BASE)+[{
      "predicate_id":"B","state":"PROVED","proof_kind":"DERIVED_TRANSFER",
      "source_path":"b.json","source_sha":"def","basis":"transport",
      "scope_complete":True,"independent_or_objective":True,
      "c_route_kind":"TRANSPORT","c_parent_predicate_id":"A",
      "c_transform_certificate":cert(False),
    }]
    assert verify_acceptance_c_gate(rows,BASE)["pass"] is False
    rows[-1]["c_transform_certificate"]=cert(True)
    out=verify_acceptance_c_gate(rows,BASE)
    assert out["pass"] is True and out["transported_count"]==1

def test_new_direct_must_not_carry_parent_or_transform():
    rows=deepcopy(BASE)+[{
      "predicate_id":"B","state":"PROVED","proof_kind":"UNIVERSAL",
      "source_path":"b.json","source_sha":"def","basis":"direct",
      "scope_complete":True,"independent_or_objective":True,
      "c_route_kind":"DIRECT","c_parent_predicate_id":"A",
    }]
    assert verify_acceptance_c_gate(rows,BASE)["pass"] is False
