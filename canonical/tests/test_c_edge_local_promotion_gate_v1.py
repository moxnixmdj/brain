import pytest
from canonical.runtime.c_edge_local_promotion_gate_v1 import (
    CPromotionError,prospective_promotion_allowed,verify_credited_proof_graph
)

def direct(rid):
    return {
        "route_id":rid,"proof_kind":"DIRECT","direct_mode":"UNIVERSAL",
        "direct_scope_complete_verified":True,"direct_independent_verified":True,
        "parent_route_id":None,"transform_certificate":None,
    }

def transport(rid,parent,**overrides):
    cert={
        "implementation_content_addressed":True,
        "load_bearing_state_quotient_complete":True,
        "target_evaluator_pullbacks_complete":True,
        "hard_constraint_preimages_complete":True,
        "independent_or_objective_verified":True,
    }
    cert.update(overrides)
    return {"route_id":rid,"proof_kind":"TRANSPORT","parent_route_id":parent,"transform_certificate":cert}

def test_direct_proof_needs_no_c_transport_edge():
    out=verify_credited_proof_graph([direct("A")])
    assert out["pass"] is True
    assert out["direct_root_count"]==1
    assert out["transport_edge_count"]==0

def test_transport_requires_complete_local_c_certificate():
    rows=[direct("A"),transport("B","A")]
    out=verify_credited_proof_graph(rows)
    assert out["transport_edges"]==(("A","B"),)
    bad=transport("C","B",target_evaluator_pullbacks_complete=False)
    assert prospective_promotion_allowed(current_rows=rows,candidate=bad) is False

def test_uncredited_future_transform_is_not_preproof_requirement():
    out=verify_credited_proof_graph([direct("A")])
    assert out["uninstantiated_or_uncredited_transforms_required_preproof"] is False

def test_future_transport_can_be_promoted_after_local_certificate():
    rows=[direct("A")]
    assert prospective_promotion_allowed(current_rows=rows,candidate=transport("B","A")) is True

def test_missing_parent_and_cycle_fail_closed():
    assert prospective_promotion_allowed(current_rows=[direct("A")],candidate=transport("B","MISSING")) is False
    with pytest.raises(CPromotionError):
        verify_credited_proof_graph([
            {"route_id":"A","proof_kind":"TRANSPORT","parent_route_id":"B","transform_certificate":transport("x","x")["transform_certificate"]},
            {"route_id":"B","proof_kind":"TRANSPORT","parent_route_id":"A","transform_certificate":transport("x","x")["transform_certificate"]},
        ])
