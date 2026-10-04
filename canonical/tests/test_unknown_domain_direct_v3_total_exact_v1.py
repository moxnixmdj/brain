import hashlib

from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proof


def _run_population(packet):
    rows = []
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"]):
        rows.append(
            harness.execute_case(
                candidate_step=c3.step,
                case_visible=visible,
                hidden_record=hidden,
            )["scorer_result"]
        )
    return scorer.aggregate(rows)


def test_v3_candidate_repairs_the_exact_v2_add2_counterexample():
    secret = hashlib.sha256(b"secret0").digest()
    beacon = "beacon-qualification-0000000000000000"
    visible, hidden = g2._transfer_case(secret, beacon, 4, namespace="REVOCATION")

    old = harness.execute_case(
        candidate_step=c2.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    assert old["scorer_result"]["pass"] is False
    assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in old["scorer_result"]["errors"]

    new = harness.execute_case(
        candidate_step=c3.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    assert new["scorer_result"]["pass"] is True
    assert (
        new["candidate_terminal_action"]["terminal_consequence"]
        == hidden["gold_terminal_consequence"]
    )
    assert set(new["candidate_terminal_action"]["support_feature_ids"]) == set(
        hidden["transfer_relevant_feature_ids"]
    )
    assert new["probe_count"] < hidden["full_rediscovery_probe_floor"]


def test_v3_identifier_totality_survives_total_ranking_digest_collision(monkeypatch):
    monkeypatch.setattr(
        g3,
        "_rank_digest",
        lambda secret, beacon, scope, label: b"\x00" * 32,
    )
    packet = g3._generate(
        beacon="FORCED-DIGEST-TIE-BEACON-0001",
        evaluator_secret=b"X" * 32,
        namespace="TIECASE",
    )
    assert packet["case_count"] == 27
    assert len({x["case_id"] for x in packet["visible_cases"]}) == 27

    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"]):
        if visible["leaf_id"] == g3.v1.TRANSFER:
            relevant = hidden["transfer_relevant_feature_ids"]
            distractors = hidden["distractor_feature_ids"]
            assert len(relevant) == len(set(relevant))
            assert len(distractors) == len(set(distractors)) == 2
            assert set(relevant).isdisjoint(distractors)

    aggregate = _run_population(packet)
    assert aggregate["all_27_cases_pass"] is True


def test_v3_passes_varied_zero_reality_populations():
    for i in range(8):
        packet = g3._generate(
            beacon=f"QUALIFICATION-V3-{i:04d}-BEACON",
            evaluator_secret=hashlib.sha256(f"secret-{i}".encode()).digest(),
            namespace=f"Q{i}",
        )
        aggregate = _run_population(packet)
        assert aggregate["all_27_cases_pass"] is True


def test_v3_content_bound_universal_proof_candidate():
    out = proof.prove()
    assert out["status"] == "PASS__UNIVERSAL_PROOF_CANDIDATE_OVER_EXACT_V3_EMITTED_DOMAIN"
    assert out["identifier_totality_proof"]["identifier_totality"] is True
    assert out["identifier_totality_proof"][
        "uniqueness_depends_on_hash_collision_resistance"
    ] is False
    assert out["add2_exact_orientation_proof"][
        "candidate_generator_add2_eval_exactly_aligned"
    ] is True
    assert out["support_rejection_proof"][
        "all_six_families_wrong_support_rejected"
    ] is True
    assert out["accounting"]["terminal_cases_consumed"] == 0
