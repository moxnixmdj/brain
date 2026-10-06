from canonical.runtime.root3_e2_output_bypass_falsifier_v1 import evaluate

def test_current_output_bypass_falsifies_e2():
    out=evaluate()
    assert out["pass"] is True, out
    assert out["falsified_root"]=="E2_EFFECT_TOTALITY"
    assert len(out["direct_print_sites"])==7
    assert out["acceptance_credit_delta"]==0
    assert out["execution_authority"] is False
