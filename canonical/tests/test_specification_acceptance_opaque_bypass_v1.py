import itertools
from canonical.runtime.specification_acceptance_opaque_bypass_v1 import evaluate, PREMISES


def good():
    return {key: True for key in PREMISES}


def test_all_premises_pass_and_only_shrink_dependency_shape():
    out = evaluate(good())
    assert out["pass"] is True
    assert out["explicit_complete_semantic_hypothesis_enumeration_required"] is False
    assert out["explicit_intermediate_consequence_model_materialization_required"] is False
    assert out["remaining_load_bearing_residual"] == (
        "SOURCE_BOUND_SCOPE_SOUND_POLICY_ADEQUACY_OR_DIRECT_END_TO_END_ACCEPTANCE"
    )
    assert out["semantic_interpretation_solved"] is False
    assert out["policy_adequacy_proved"] is False
    assert out["benchmark_acceptance_proved"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_every_premise_is_individually_load_bearing():
    for key in PREMISES:
        p = good()
        p[key] = False
        out = evaluate(p)
        assert out["pass"] is False
        assert key in out["missing_premises"]


def test_exhaustive_boolean_premise_space_has_exactly_one_pass():
    passed = []
    for bits in itertools.product((False, True), repeat=len(PREMISES)):
        p = dict(zip(PREMISES, bits))
        out = evaluate(p)
        if out["pass"]:
            passed.append(bits)
    assert passed == [(True,) * len(PREMISES)]


def test_non_mapping_fails_closed():
    out = evaluate(None)
    assert out["pass"] is False
    assert out["reason"] == "PAYLOAD_MAPPING_REQUIRED"
