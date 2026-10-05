import json
from canonical.runtime.composition_current_upstream_bridge_fixed_point_verifier_v1 import ROOT, P

def test_fixed_point_document_is_zero_credit_and_4_of_12():
    d=json.loads((ROOT/P["fixed"]).read_text())
    assert d["fixed_point"]["scoped_proved_count"]==4
    assert d["fixed_point"]["open_count"]==8
    assert d["fixed_point"]["additional_component_credit_from_current_verified_owned_family_set"]==0
    assert d["accounting"]["acceptance_credit_delta"]==0
    assert d["fresh_reality_authority"] is False
