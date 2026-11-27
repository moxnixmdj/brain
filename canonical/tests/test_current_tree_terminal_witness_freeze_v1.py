from canonical.runtime.current_tree_terminal_witness_freeze_v1 import witness_policy


def test_default_denies_architecture_growth():
    out = witness_policy()
    assert out["new_implementation_authorized"] is False
    assert out["next_action"] == "FALSIFY_OR_PROVE_CURRENT_WITNESS"
    assert out["terminal_credit"] is False


def test_only_irreducible_terminal_counterexample_reopens_implementation():
    out = witness_policy({
        "terminal_relevant": True,
        "causally_localized": True,
        "not_closed_by_existing_owned_composition_or_configuration": True,
    })
    assert out["new_implementation_authorized"] is True
    assert out["next_action"] == "MINIMAL_CAUSAL_REPAIR"


def test_nonlocalized_failure_does_not_authorize_new_capability():
    out = witness_policy({
        "terminal_relevant": True,
        "causally_localized": False,
        "not_closed_by_existing_owned_composition_or_configuration": True,
    })
    assert out["new_implementation_authorized"] is False
