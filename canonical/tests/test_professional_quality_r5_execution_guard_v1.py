from canonical.runtime import professional_quality_r5_execution_guard_v1 as g

def test_positive_path_requires_both_preflights():
    out=g.evaluate(evaluator_preflight_pass=True,root_binding_pass=True)
    assert out["pass"] is True
    assert out["ordinary_acceptance_path_allowed"] is True
    assert out["true_owner_evaluator_containment_proved"] is False

def test_every_known_r5_defeater_blocks_ordinary_path():
    assert len(g.KNOWN_R5_DEFEATERS)==16
    for did in g.KNOWN_R5_DEFEATERS:
        out=g.evaluate(evaluator_preflight_pass=True,root_binding_pass=True,
                       detected_defeater_ids=(did,))
        assert out["pass"] is False
        assert out["status"]=="ABSTAIN_OR_ESCALATE__KNOWN_R5_DEFEATER_ACTIVE"
        assert out["ordinary_acceptance_path_allowed"] is False

def test_every_r5_near_miss_escalates():
    assert len(g.NEAR_MISS_TO_TRIGGER)==16
    for signal,trigger in g.NEAR_MISS_TO_TRIGGER.items():
        out=g.evaluate(evaluator_preflight_pass=True,root_binding_pass=True,
                       near_miss_signals=(signal,))
        assert out["pass"] is False
        assert out["status"]=="ESCALATE__R5_NEAR_MISS_TRIGGER"
        assert trigger in out["active_escalation_triggers"]
        assert out["ordinary_acceptance_path_allowed"] is False

def test_unknown_and_unmapped_material_r5_defeaters_fail_closed():
    assert g.evaluate(evaluator_preflight_pass=True,root_binding_pass=True,
                      detected_defeater_ids=("C999_FRESH_R5_ATTACK",))["pass"] is False
    assert g.evaluate(evaluator_preflight_pass=True,root_binding_pass=True,
                      near_miss_signals=("fresh_signal",))["pass"] is False
    assert g.evaluate(evaluator_preflight_pass=True,root_binding_pass=True,
                      unmapped_material_defeater=True)["pass"] is False

def test_preflight_or_root_binding_failure_never_passes():
    assert g.evaluate(evaluator_preflight_pass=False,root_binding_pass=True)["pass"] is False
    assert g.evaluate(evaluator_preflight_pass=True,root_binding_pass=False)["pass"] is False
