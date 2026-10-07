from canonical.runtime.credited_transform_certificate_compiler_v1 import compile_current


CREDITED = {
    "EXACT_SYMBOLIC_COMPUTATION",
    "LONG_HORIZON_MEMORY_AND_CONTINUITY",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
    "SUBAGENT_DELEGATION_AND_COORDINATION",
    "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
}

CERTIFIED = CREDITED - {"LONG_HORIZON_MEMORY_AND_CONTINUITY"}


def test_registry_binds_exact_five_credited_families():
    out = compile_current()
    assert out["credited_family_count"] == 5
    assert out["declared_route_count"] == 5
    assert set(out["credited_families"]) == CREDITED


def test_four_current_routes_have_complete_transform_certificates():
    out = compile_current()
    assert out["complete_transform_certificate_count"] == 4
    assert out["open_transform_certificate_count"] == 1
    for family in CERTIFIED:
        assert out["route_results"][family]["pass"] is True, (family, out)


def test_continuity_fails_closed_until_current_child_seam_is_requalified():
    out = compile_current()
    assert out["route_results"]["LONG_HORIZON_MEMORY_AND_CONTINUITY"]["pass"] is False
    assert out["c_closed"] is False
    assert out["b9_independent_escape_deleted"] is False
    assert out["terminal_credit_delta"] == 0
