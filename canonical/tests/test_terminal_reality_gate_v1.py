from canonical.runtime.terminal_reality_gate_v1 import evaluate

TOP = [
    "COMPLETE_SELECTED_CONTEXT_ABC",
    "D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY",
]

def pointer(
    *,
    u,
    registry,
    abc,
    d,
    terminal,
    scope=True,
    router=True,
    deployed=True,
):
    return {
        "live_truth": {
            "independent_top_level_terminal_predicates": TOP,
            "fixed_authorized_target_trace_scope_closed": scope,
            "current_U_empty_proved": u,
            "router_registry_real_selected_cover_complete": registry,
            "complete_selected_context_ABC_closed": abc,
            "D_finality_closed": d,
            "router_mechanical_core_implemented": router,
            "router_deployed_runtime_binding_closed": deployed,
            "terminal": terminal,
            "complete_selected_context_ABC_normal_form": "U_IS_EMPTY",
            "known_sound_D_B_certificate_record_count": 15,
        }
    }

def test_gate_passes_only_on_full_terminal_conjunction():
    out = evaluate(pointer(u=True, registry=True, abc=True, d=True, terminal=True))
    assert out["terminal_real"] is True
    assert out["blockers"] == []

def test_gate_fails_closed_on_live_remaining_blockers():
    out = evaluate(pointer(u=False, registry=False, abc=False, d=False, terminal=False))
    assert out["terminal_real"] is False
    assert "U_NOT_PROVED_EMPTY" in out["blockers"]
    assert "ROUTER_REGISTRY_SELECTED_COVER_INCOMPLETE" in out["blockers"]
    assert "COMPLETE_SELECTED_CONTEXT_ABC_OPEN" in out["blockers"]
    assert "D_FINALITY_OPEN" in out["blockers"]

def test_gate_rejects_missing_deployed_binding():
    out = evaluate(
        pointer(
            u=True,
            registry=True,
            abc=True,
            d=True,
            terminal=False,
            deployed=False,
        )
    )
    assert out["terminal_real"] is False
    assert "ROUTER_DEPLOYED_RUNTIME_BINDING_OPEN" in out["blockers"]

def test_gate_rejects_false_terminal_declaration():
    out = evaluate(pointer(u=False, registry=False, abc=False, d=False, terminal=True))
    assert out["terminal_real"] is False
    assert "DECLARED_TERMINAL_INCONSISTENT_WITH_REQUIRED_PREDICATES" in out["blockers"]
