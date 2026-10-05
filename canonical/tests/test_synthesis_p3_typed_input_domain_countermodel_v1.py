from pathlib import Path

from canonical.runtime.verify_synthesis_p3_typed_input_domain_countermodel_v1 import verify


def test_live_tree_source_bound_countermodel_passes():
    out = verify(Path("."))
    assert out["status"] == "PASS", out
    assert out["universal_current_p3_v3_totality_falsified"] is True
    assert out["constructive_residual_class_count"] == 7
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["acceptance_credit_delta"] == 0
