from canonical.runtime.current_accepted_five_d_reduction_verifier_v1 import verify, reduce_current_d

def test_current_exact_sources_pass():
    x=verify()
    assert x["pass"] is True,x
    assert x["current_accepted_family_effect_mediator_residual_count"]==0
    assert x["global_D_closed"] is False

def test_provider_dependency_fails():
    x=reduce_current_d(effect_free_count=4,continuity_owned=False,continuity_confined=True,raw_subprocess_reachable=False,downstream_separate=True)
    assert x["pass"] is False
    assert "CONTINUITY_NOT_OWNED" in x["errors"]

def test_escape_fails():
    x=reduce_current_d(effect_free_count=4,continuity_owned=True,continuity_confined=False,raw_subprocess_reachable=False,downstream_separate=True)
    assert x["pass"] is False
    assert "CONTINUITY_EFFECT_ESCAPE" in x["errors"]

def test_scope_conflation_fails():
    x=reduce_current_d(effect_free_count=4,continuity_owned=True,continuity_confined=True,raw_subprocess_reachable=False,downstream_separate=False)
    assert x["pass"] is False
    assert "DOWNSTREAM_SCOPE_CONFLATION" in x["errors"]
