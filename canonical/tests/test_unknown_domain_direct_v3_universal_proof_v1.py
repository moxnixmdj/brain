import itertools

from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proof


def test_every_possible_fisher_yates_swap_path_is_bijective_through_size_7():
    paths = 0
    for n in range(1, 8):
        labels = tuple(f"L{i}" for i in range(n))
        domains = [range(i + 1) for i in range(n - 1, 0, -1)]
        sequences = itertools.product(*domains) if domains else [()]
        for swaps in sequences:
            ranks = g3._rank_from_swaps(labels, tuple(swaps))
            assert set(ranks) == set(labels)
            assert set(ranks.values()) == set(range(n))
            paths += 1
    assert paths == 5913


def test_zero_draw_path_still_has_distinct_semantic_slots(monkeypatch):
    monkeypatch.setattr(g3, "_draw", lambda *args, **kwargs: 0)
    secret = b"0" * 32
    mapping, distractors = g3._surface_ids(
        secret, "B" * 16, 4, "UDIR3_B", ["r0", "r1"]
    )
    values = list(mapping.values()) + list(distractors)
    assert len(values) == len(set(values)) == 4

    visible, hidden = g3._abstention_case(
        secret, "B" * 16, 6, namespace="TESTV3"
    )
    consequences = [h["terminal_consequence"] for h in visible["hypotheses"]]
    assert hidden["identifiability_status"] == "NONIDENTIFIABLE"
    assert len(set(consequences)) == 2


def test_qualification_fixture_end_to_end_all_27_pass_without_production():
    packet = g3.generate_qualification_fixture_population(
        beacon="V3-QUALIFICATION-BEACON-0001"
    )
    assert packet["production"] is False
    results = []
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"]):
        run = harness.execute_case(
            candidate_step=candidate.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        results.append(run["scorer_result"])
    aggregate = scorer.aggregate(results)
    assert aggregate["all_27_cases_pass"] is True


def test_universal_certificate_consumes_zero_reality_and_closes_collision_assumption():
    out = proof.prove()
    assert out["status"] == "PASS__UNIVERSAL_COLLISION_TOTAL_OVER_EXACT_V3_GENERATOR_DOMAIN"
    assert out["identifier_totality_proof"]["all_possible_swap_paths_proved"] == 5913
    assert out["identifier_totality_proof"]["hmac_collision_resistance_required_for_uniqueness"] is False
    assert out["scope"]["identifier_collision_cases_excluded"] == 0
    assert out["scope"]["terminal_or_production_cases_generated"] == 0
    assert out["production_execution_information_gain"] == 0
    assert out["accounting"]["acceptance_credit_delta"] == 0
    assert out["accounting"]["capability_credit_delta"] == 0


def test_v3_is_semantic_totalization_not_open_world_claim():
    out = proof.prove()
    eq = out["semantic_equivalence_to_v2"]
    assert eq["only_change"].startswith("OPAQUE_IDENTIFIER_CONSTRUCTOR")
    assert "CANDIDATE_V2" in eq["unchanged"]
    assert "HIDDEN_SCORER_V1" in eq["unchanged"]
    assert any("NO_OPEN_WORLD" in x for x in out["hard_nonclaims"])
