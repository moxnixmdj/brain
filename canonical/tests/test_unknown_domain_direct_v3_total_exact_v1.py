"""Regression tests for the Unknown-Domain V3 total/exact successor."""
import hashlib

from canonical.runtime import unknown_domain_direct_candidate_v3 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer


def _run_population(pop):
    results = []
    for visible, hidden in zip(pop["visible_cases"], pop["hidden_records"], strict=True):
        out = harness.execute_case(
            candidate_step=candidate.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        results.append(out["scorer_result"])
    return scorer.aggregate(results)


def test_v3_candidate_repairs_reachable_v2_add2_exact_float_counterexample():
    secret = hashlib.sha256(b"secret0").digest()
    beacon = "beacon-qualification-0000000000000000"
    visible, hidden = g2._transfer_case(secret, beacon, 4, namespace="REVOCATION")

    out = harness.execute_case(
        candidate_step=candidate.step,
        case_visible=visible,
        hidden_record=hidden,
    )

    assert out["scorer_result"]["pass"] is True
    assert out["candidate_terminal_action"]["terminal_consequence"] == hidden[
        "gold_terminal_consequence"
    ]
    assert set(out["candidate_terminal_action"]["support_feature_ids"]) == set(
        hidden["transfer_relevant_feature_ids"]
    )
    assert out["probe_count"] == 1


def test_v3_add2_orientation_is_derived_from_source_signatures_not_labels():
    secret = hashlib.sha256(b"orientation-proof").digest()
    beacon = "orientation-beacon-000000000000000000"
    for index in (4, 10):
        visible, hidden = g3._transfer_case(secret, beacon, index, namespace="ORIENT")
        receipt = visible["domain_a"]["earned_receipts"][0]
        support = hidden["transfer_relevant_feature_ids"]
        mapping = candidate._orient_add2(visible, receipt, support)
        assert mapping == hidden["domain_mapping"]


def test_v3_structural_totality_survives_forced_token_collision(monkeypatch):
    # Strong falsifier: make every opaque token identical. V2 could merge roles
    # or distractors under this condition; V3's bijective slot tags must not.
    monkeypatch.setattr(g1, "_token", lambda *args, **kwargs: "COLLIDE")
    pop = g3._generate(
        beacon="forced-collision-beacon-000000000000",
        evaluator_secret=b"x" * 32,
        namespace="COLLIDE",
    )

    assert pop["case_count"] == 27
    case_ids = [x["case_id"] for x in pop["visible_cases"]]
    assert len(case_ids) == len(set(case_ids)) == 27

    all_feature_ids = set()
    for visible, hidden in zip(pop["visible_cases"], pop["hidden_records"], strict=True):
        if visible["leaf_id"] == g1.TRANSFER:
            relevant = list(hidden["transfer_relevant_feature_ids"])
            distractors = list(hidden["distractor_feature_ids"])
            assert len(relevant) == len(set(relevant))
            assert len(distractors) == len(set(distractors)) == 2
            assert set(relevant).isdisjoint(distractors)
            source_ids = set(visible["domain_a"]["tasks"][0]["inputs"])
            target_ids = set(visible["domain_b"]["tasks"][0]["inputs"])
            assert len(source_ids) in (3, 4)
            assert len(target_ids) in (3, 4)
            assert source_ids.isdisjoint(target_ids)
            case_feature_ids = source_ids | target_ids
            assert all_feature_ids.isdisjoint(case_feature_ids)
            all_feature_ids.update(case_feature_ids)
        else:
            hyps = visible["hypotheses"]
            assert hyps[0]["hypothesis_id"] != hyps[1]["hypothesis_id"]
            if hidden["identifiability_status"] != "IDENTIFIABLE":
                assert hyps[0]["terminal_consequence"] != hyps[1]["terminal_consequence"]
            probe_ids = [p["probe_id"] for p in visible["allowed_probes"]]
            assert len(probe_ids) == len(set(probe_ids))


def test_v3_full_qualification_populations_pass_exact_scorer():
    for beacon in (
        "v3-qualification-alpha-000000000000",
        "v3-qualification-beta-0000000000000",
        "v3-qualification-gamma-000000000000",
    ):
        pop = g3.generate_qualification_fixture_population(beacon=beacon)
        aggregate = _run_population(pop)
        assert aggregate["status"] == "TWO_FROZEN_LEAVES_PASS"
        assert aggregate["all_27_cases_pass"] is True
