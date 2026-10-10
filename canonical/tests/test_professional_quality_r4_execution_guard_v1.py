from canonical.runtime import professional_quality_r4_execution_guard_v1 as g

def test_positive_measurement_path_only_when_clear():
    out=g.evaluate(measurement_pass=True)
    assert out["pass"] is True
    assert out["ordinary_acceptance_path_allowed"] is True
    assert out["detection_completeness_proved"] is False
    assert out["semantic_leaf_authority"] is False

def test_every_known_r4_defeater_blocks_ordinary_path():
    assert len(g.KNOWN_R4_DEFEATERS)==7
    for did in g.KNOWN_R4_DEFEATERS:
        out=g.evaluate(measurement_pass=True,detected_defeater_ids=(did,))
        assert out["pass"] is False
        assert out["status"]=="ABSTAIN_OR_ESCALATE__KNOWN_R4_DEFEATER_ACTIVE"
        assert out["ordinary_acceptance_path_allowed"] is False

def test_every_near_miss_escalates():
    assert len(g.NEAR_MISS_TO_TRIGGER)==7
    for signal,trigger in g.NEAR_MISS_TO_TRIGGER.items():
        out=g.evaluate(measurement_pass=True,near_miss_signals=(signal,))
        assert out["pass"] is False
        assert trigger in out["active_escalation_triggers"]

def test_unknown_and_unmapped_fail_closed():
    assert g.evaluate(measurement_pass=True,detected_defeater_ids=("C999_FRESH_R4_ATTACK",))["pass"] is False
    assert g.evaluate(measurement_pass=True,near_miss_signals=("fresh_signal",))["pass"] is False
    assert g.evaluate(measurement_pass=True,unmapped_material_defeater=True)["pass"] is False

def test_failed_measurement_never_passes():
    out=g.evaluate(measurement_pass=False)
    assert out["pass"] is False
    assert out["ordinary_acceptance_path_allowed"] is False
