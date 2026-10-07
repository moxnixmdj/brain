from canonical.runtime.credited_transform_certificate_compiler_v1 import compile_current


CREDITED = {
    "EXACT_SYMBOLIC_COMPUTATION",
    "LONG_HORIZON_MEMORY_AND_CONTINUITY",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
    "SUBAGENT_DELEGATION_AND_COORDINATION",
    "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
}


def test_registry_binds_exact_five_credited_families():
    out = compile_current()
    assert out["credited_family_count"] == 5
    assert out["declared_route_count"] == 5
    assert set(out["credited_families"]) == CREDITED


def test_all_current_credited_routes_have_complete_transform_certificates():
    out = compile_current()
    assert out["complete_transform_certificate_count"] == 5
    assert out["open_transform_certificate_count"] == 0
    for family in CREDITED:
        assert out["route_results"][family]["pass"] is True, (family, out)


def test_current_c_route_set_closes_fail_closed():
    out = compile_current()
    assert out["c_closed"] is True
    assert out["b9_independent_escape_deleted"] is True
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
