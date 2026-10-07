from canonical.runtime.credited_transform_certificate_compiler_v1 import compile_current


def test_registry_binds_exact_five_credited_families():
    out = compile_current()
    assert out["credited_family_count"] == 5
    assert out["declared_route_count"] == 5
    assert set(out["credited_families"]) == {
        "EXACT_SYMBOLIC_COMPUTATION",
        "LONG_HORIZON_MEMORY_AND_CONTINUITY",
        "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
        "SUBAGENT_DELEGATION_AND_COORDINATION",
        "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
    }


def test_exact_symbolic_is_first_complete_transform_certificate():
    out = compile_current()
    assert out["route_results"]["EXACT_SYMBOLIC_COMPUTATION"]["pass"] is True
    assert out["complete_transform_certificate_count"] == 1
    assert out["open_transform_certificate_count"] == 4


def test_uncertified_routes_fail_closed_and_c_remains_open():
    out = compile_current()
    for family in (
        "LONG_HORIZON_MEMORY_AND_CONTINUITY",
        "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
        "SUBAGENT_DELEGATION_AND_COORDINATION",
        "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
    ):
        assert out["route_results"][family]["pass"] is False
    assert out["c_closed"] is False
    assert out["b9_independent_escape_deleted"] is False
    assert out["terminal_credit_delta"] == 0
