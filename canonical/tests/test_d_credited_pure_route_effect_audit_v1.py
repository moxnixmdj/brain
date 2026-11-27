from canonical.runtime.d_credited_pure_route_effect_audit_v1 import audit
def test_four_current_selected_routes_effect_free():
 x=audit()
 assert x["pass"],x
 assert set(x["routes"])=={"accepted.delegation","accepted.recovery","accepted.tool_discovery","accepted.exact_symbolic"}
 assert all(v["pass"] for v in x["routes"].values())
 assert all(v["material_effect_ids"]==[] for v in x["routes"].values())
 assert x["proof_obligation_id"]=="D_CREDITED_ROUTE_EFFECT_TOTALITY"
 assert x["terminal_credit_delta"]==0
