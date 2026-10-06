from canonical.runtime.k6_positive_adequacy_cover_certificate_v1 import (
    certify_positive_cover,
    finite_countermodel,
)


def bit_discriminator():
    return [{
        "id": "bit",
        "observations": {"w0": 0, "w1": 1},
        "cost": 1,
        "arrival": 0,
        "authorized": True,
        "owned_operator": True,
    }]


def test_partial_positive_relation_can_soundly_certify_route():
    out = finite_countermodel()
    assert out["status"] == "CERTIFIED_SUFFICIENT_POSITIVE_POLICY_COVER"
    assert out["relation_mode"] == "SOUND_POSITIVE_SUBRELATION"
    assert out["certified_cover_number_hat_tau"] == 2
    assert out["hat_tau_semantics"] == "UPPER_BOUND_ON_TRUE_MINIMUM"
    assert out["true_minimum_tau_claimed"] is False
    assert out["sound_under_additional_true_adequacy_edges"] is True


def test_empty_certified_world_is_unknown_when_adequacy_incomplete():
    out = certify_positive_cover(
        worlds=("w0", "w1"),
        policies=("p0", "p1"),
        certified_adequate={"w0": ("p0",), "w1": ()},
        discriminators=[],
        commitment_deadline=0,
        separator_reacquirable_after_restart_before_deadline=False,
        adequacy_relation_complete=False,
        discriminator_universe_complete=False,
    )
    assert out["status"] == "UNKNOWN__POSITIVE_ADEQUACY_BINDING_INCOMPLETE"
    assert out["capability_gap_candidate"] is False


def test_empty_world_becomes_capability_gap_candidate_only_with_complete_relation():
    out = certify_positive_cover(
        worlds=("w0", "w1"),
        policies=("p0", "p1"),
        certified_adequate={"w0": ("p0",), "w1": ()},
        discriminators=[],
        commitment_deadline=0,
        separator_reacquirable_after_restart_before_deadline=False,
        adequacy_relation_complete=True,
        discriminator_universe_complete=True,
    )
    assert out["status"] == "NO_ADEQUATE_POLICY_IN_COMPLETE_DECLARED_POLICY_UNIVERSE"
    assert out["capability_gap_candidate"] is True
    assert out["absolute_terminal_claim"] is False


def test_partial_relation_no_separator_is_unknown_not_nonidentifiability():
    out = certify_positive_cover(
        worlds=("w0", "w1"),
        policies=("p0", "p1", "p2"),
        certified_adequate={"w0": ("p0",), "w1": ("p1",)},
        discriminators=[],
        commitment_deadline=0,
        separator_reacquirable_after_restart_before_deadline=False,
        adequacy_relation_complete=False,
        discriminator_universe_complete=False,
    )
    assert out["status"] == "UNKNOWN__ADEQUACY_OR_DISCRIMINATOR_BINDING_INCOMPLETE"


def test_nonidentifiability_requires_both_complete_relations():
    out = certify_positive_cover(
        worlds=("w0", "w1"),
        policies=("p0", "p1"),
        certified_adequate={"w0": ("p0",), "w1": ("p1",)},
        discriminators=[],
        commitment_deadline=0,
        separator_reacquirable_after_restart_before_deadline=False,
        adequacy_relation_complete=True,
        discriminator_universe_complete=True,
    )
    assert out["status"] == "PROVED_NONIDENTIFIABLE_IN_COMPLETE_DECLARED_MODEL"
    assert out["absolute_terminal_claim"] is False


def test_complete_relation_allows_exact_declared_tau_claim():
    out = certify_positive_cover(
        worlds=("w0", "w1"),
        policies=("p0", "p1"),
        certified_adequate={"w0": ("p0",), "w1": ("p1",)},
        discriminators=bit_discriminator(),
        commitment_deadline=0,
        separator_reacquirable_after_restart_before_deadline=True,
        adequacy_relation_complete=True,
        discriminator_universe_complete=True,
    )
    assert out["status"] == "CERTIFIED_SUFFICIENT_POSITIVE_POLICY_COVER"
    assert out["hat_tau_semantics"] == "EXACT_FOR_DECLARED_COMPLETE_RELATION"
    assert out["true_minimum_tau_claimed"] is True
    assert out["terminal_credit_delta"] == 0


def test_theorem_source_bindings_fail_closed_and_pass_current_branch():
    from canonical.runtime.k6_positive_adequacy_cover_theorem_verifier_v1 import verify
    out = verify()
    assert out["pass"] is True, out
    assert out["terminal_credit_delta"] == 0
