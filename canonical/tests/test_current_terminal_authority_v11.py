from canonical.runtime.current_terminal_authority_v11_verifier_v1 import verify, logical_normal_form, TOP

def test_current_v11_passes():
    x=verify()
    assert x["pass"] is True,x
    assert x["independent_top_level_terminal_predicate_count"]==2
    assert x["current_positive_frontier"]=="COMPLETE_SELECTED_CONTEXT_ABC"
    assert x["global_D_closed"] is False

def test_false_d_closure_fails():
    x=logical_normal_form(top=TOP,abc_closed=False,d_closed=True,l1_independent_count=1,current_d_residual=0)
    assert x["pass"] is False
    assert "D_FALSELY_CLOSED" in x["errors"]

def test_resurrecting_19_l1_fails():
    x=logical_normal_form(top=TOP,abc_closed=False,d_closed=False,l1_independent_count=19,current_d_residual=0)
    assert x["pass"] is False
    assert "L1_NOT_COLLAPSED_TO_ONE_ABC" in x["errors"]

def test_nonzero_current_d_residual_fails():
    x=logical_normal_form(top=TOP,abc_closed=False,d_closed=False,l1_independent_count=1,current_d_residual=1)
    assert x["pass"] is False
    assert "CURRENT_ACCEPTED_D_RESIDUAL_NOT_ZERO" in x["errors"]
