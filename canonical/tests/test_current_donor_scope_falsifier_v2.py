from canonical.runtime.current_donor_scope_falsifier_v2 import (
    compile_falsification,
    old_roots,
    scope_counterexample,
)


def test_old_verified_audit_does_not_include_current_model_paths():
    roots = set(old_roots())
    assert len(roots) == 9
    assert "harbor_brain_agent" not in roots
    assert "astra_runtime" not in roots


def test_current_model_path_constructs_scope_counterexample():
    out = scope_counterexample()
    assert out["harbor_calls_planner"] is True
    assert out["harbor_model_dependency"] is True
    assert out["astra_remote_fallback"] is True
    assert out["astra_local_only_guard"] is True
    assert out["scope_gap_proved"] is True


def test_falsifier_preserves_old_receipt_but_denies_current_uplift():
    out = compile_falsification()
    assert out["status"].startswith("PASS__")
    assert out["old_receipt_preserved_for_old_scope"] is True
    assert out["current_whole_witness_donor_independence_proved"] is False
    assert out["terminal_credit"] is False
    assert out["ownership_credit"] is False
