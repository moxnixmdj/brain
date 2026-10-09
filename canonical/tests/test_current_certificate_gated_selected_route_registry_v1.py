from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v3 as r


def test_live_registry_is_pointer_resolved_not_version_hardcoded():
    registry = r.load_registry()
    assert registry["schema"] == r.REGISTRY_SCHEMA
    assert "REGISTRY_V1" not in r.CURRENT_REGISTRY_POINTER_PATH.name
    assert "REGISTRY_V2" not in r.CURRENT_REGISTRY_POINTER_PATH.name
    assert set(r.verified_route_ids(registry)) == {"router-deployment-canary"}
