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
    root=None,
):
    live = {
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
        "known_sound_D_B_certificate_record_count": 17,
    }
    if root is not None:
        live["current_terminal_root_predicate"] = root
    return {"live_truth": live}


def test_gate_passes_on_full_terminal_conjunction():
    out = evaluate(pointer(u=True, registry=True, abc=True, d=True, terminal=True))
    assert out["terminal_real"] is True
    assert out["phase"] == "TERMINAL"
    assert out["blockers"] == []


def test_open_u_is_one_live_research_root_not_four_parallel_blockers():
    root = "PROVE_RESIDUAL_COMPLEMENT_UNSAT_OVER_EXACT_SOUND_ADMISSION_PREDICATE_SET"
    out = evaluate(
        pointer(
            u=False,
            registry=False,
            abc=False,
            d=False,
            terminal=False,
            root=root,
        )
    )
    assert out["terminal_real"] is False
    assert out["phase"] == "RESEARCH_ROOT"
    assert out["blockers"] == [root]
    assert out["live_research_blockers"] == [root]
    assert "REAL_SELECTED_COVER_INCOMPLETE_DERIVED_FROM_OPEN_U" in out["derived_pending"]
    assert "COMPLETE_SELECTED_CONTEXT_ABC_OPEN_DERIVED_FROM_OPEN_U" in out["derived_pending"]
    assert out["finalization_pending"] == ["D_FINALITY_DEFERRED_UNTIL_ABC"]


def test_post_u_promotion_is_one_derived_transition_not_new_research():
    out = evaluate(pointer(u=True, registry=False, abc=False, d=False, terminal=False))
    assert out["terminal_real"] is False
    assert out["phase"] == "POST_U_DERIVED_TRANSITION"
    assert out["live_research_blockers"] == []
    assert out["blockers"] == [
        "POST_U_SELECTED_COVER_PROMOTION_OR_ABC_RECOMPUTE_PENDING"
    ]


def test_d_is_post_abc_finalization_not_parallel_research():
    out = evaluate(pointer(u=True, registry=True, abc=True, d=False, terminal=False))
    assert out["terminal_real"] is False
    assert out["phase"] == "POST_ABC_FINALIZATION"
    assert out["live_research_blockers"] == []
    assert out["blockers"] == ["POST_ABC_FINALIZATION_PENDING"]


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


def test_manual_terminal_false_does_not_block_derived_terminal_truth():
    out = evaluate(pointer(u=True, registry=True, abc=True, d=True, terminal=False))
    assert out["terminal_real"] is True
    assert out["blockers"] == []
    assert out["declaration_warnings"] == [
        "DECLARED_TERMINAL_FALSE_BUT_DERIVED_TERMINAL_TRUE__METADATA_OUT_OF_SYNC"
    ]


def test_gate_rejects_false_positive_terminal_declaration():
    out = evaluate(pointer(u=False, registry=False, abc=False, d=False, terminal=True))
    assert out["terminal_real"] is False
    assert "DECLARED_TERMINAL_INCONSISTENT_WITH_REQUIRED_PREDICATES" in out["blockers"]
