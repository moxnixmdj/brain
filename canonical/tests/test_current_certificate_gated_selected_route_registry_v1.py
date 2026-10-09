from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v5 as v5


def test_live_registry_is_current_pointer_resolved_and_unique_match():
    registry = v5.load_registry()
    assert registry["schema"] == v5.REGISTRY_SCHEMA
    assert registry["selection_rule"] == "UNIQUE_MATCH_REQUIRED__ANY_OVERLAP_FAILS_CLOSED"
    assert set(v5.verified_route_ids(registry)) == {"router-deployment-canary"}
