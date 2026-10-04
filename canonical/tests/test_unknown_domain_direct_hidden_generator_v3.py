from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer


BEACON = "V3-COLLISION-TOTAL-QUALIFICATION-BEACON"


def test_v3_is_byte_preserving_on_the_ordinary_noncollision_fixture():
    v2 = g2.generate_qualification_fixture_population(beacon=BEACON)
    v3 = g3.generate_qualification_fixture_population(beacon=BEACON)
    assert v3["visible_cases"] == v2["visible_cases"]
    assert v3["hidden_records"] == v2["hidden_records"]


def test_surface_ids_are_injective_even_under_total_raw_token_collision(monkeypatch):
    def constant_token(secret, beacon, *parts, width=14):
        return "0" * width

    monkeypatch.setattr(g1, "_token", constant_token)
    secret = b"X" * 32
    mapping, distractors = g3._surface_ids(
        secret, BEACON, 4, "QUALONLY_B", ["r0", "r1"]
    )
    ids = list(mapping.values()) + list(distractors)
    assert len(ids) == 4
    assert len(set(ids)) == 4
    assert set(mapping.values()).isdisjoint(distractors)


def test_nonidentifiable_and_underspecified_semantics_survive_total_token_collision(monkeypatch):
    def constant_token(secret, beacon, *parts, width=14):
        return "a" * width

    monkeypatch.setattr(g1, "_token", constant_token)
    secret = b"Y" * 32

    non_v, non_h = g3._abstention_case(secret, BEACON, 5, namespace="QUALONLY")
    assert non_h["identifiability_status"] == "NONIDENTIFIABLE"
    assert len({x["hypothesis_id"] for x in non_v["hypotheses"]}) == 2
    assert len({x["terminal_consequence"] for x in non_v["hypotheses"]}) == 2

    under_v, under_h = g3._abstention_case(secret, BEACON, 10, namespace="QUALONLY")
    assert under_h["identifiability_status"] == "UNDERSPECIFIED"
    pids = [x["probe_id"] for x in under_v["allowed_probes"]]
    assert len(pids) == len(set(pids)) == 2
    assert under_h["minimum_discriminator_id"] == pids[0]


def test_candidate_passes_all_27_when_every_raw_opaque_token_is_forced_to_collide(monkeypatch):
    def constant_token(secret, beacon, *parts, width=14):
        return "f" * width

    monkeypatch.setattr(g1, "_token", constant_token)
    population = g3.generate_qualification_fixture_population(beacon=BEACON)
    assert population["case_count"] == 27
    assert len({x["case_id"] for x in population["visible_cases"]}) == 27

    results = []
    for visible, hidden in zip(population["visible_cases"], population["hidden_records"]):
        execution = harness.execute_case(
            candidate_step=candidate.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        assert execution["scorer_result"]["pass"] is True, execution
        results.append(execution["scorer_result"])

    aggregate = scorer.aggregate(results)
    assert aggregate["all_27_cases_pass"] is True
    assert aggregate["status"] == "TWO_FROZEN_LEAVES_PASS"
