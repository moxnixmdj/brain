from canonical.runtime.direct_e2e_selected_cell_certificate_v1 import cell_certified,verify

def test_direct_e2e_can_certify_without_internal_decomposition():
    assert cell_certified(complete_semantics=True,exact_route=True,e2e=True,primitive=False,local_c=False)

def test_existing_local_c_route_still_works():
    assert cell_certified(complete_semantics=True,exact_route=True,e2e=False,primitive=True,local_c=True)

def test_incomplete_semantics_fail():
    assert not cell_certified(complete_semantics=False,exact_route=True,e2e=True,primitive=False,local_c=False)

def test_route_drift_fails():
    assert not cell_certified(complete_semantics=True,exact_route=False,e2e=True,primitive=False,local_c=False)

def test_partial_decomposition_fails():
    assert not cell_certified(complete_semantics=True,exact_route=True,e2e=False,primitive=True,local_c=False)

def test_source_bound_candidate_verifies():
    assert verify()["pass"] is True
