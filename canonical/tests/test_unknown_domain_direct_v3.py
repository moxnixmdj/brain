import hashlib

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer


def test_v3_repairs_exact_add2_float_counterexample_from_v2():
    secret = hashlib.sha256(b"secret0").digest()
    beacon = "beacon-qualification-0000000000000000"
    visible, hidden = g2._transfer_case(secret, beacon, 4, namespace="REVOCATION")
    out = harness.execute_case(
        candidate_step=c3.step, case_visible=visible, hidden_record=hidden
    )
    assert out["scorer_result"]["pass"] is True
    assert out["candidate_terminal_action"]["terminal_consequence"] == hidden["gold_terminal_consequence"]
    assert out["probe_count"] == 1


def test_v3_opaque_ids_are_structurally_unique_and_cross_domain_disjoint():
    for k in range(64):
        secret = hashlib.sha256(f"id-totality-{k}".encode()).digest()
        beacon = "TOTALITY-" + hashlib.sha256(str(k).encode()).hexdigest()[:24]
        for index in range(12):
            visible, hidden = g3._transfer_case(secret, beacon, index, namespace=f"T{k}")
            a = visible["domain_a"]
            b = visible["domain_b"]
            a_ids = set(a["tasks"][0]["inputs"])
            b_ids = set(b["tasks"][0]["inputs"])
            assert len(a_ids) == len(a["tasks"][0]["inputs"])
            assert len(b_ids) == len(b["tasks"][0]["inputs"])
            assert not (a_ids & b_ids)
            assert len(hidden["transfer_relevant_feature_ids"]) == len(
                set(hidden["transfer_relevant_feature_ids"])
            )
            assert len(hidden["distractor_feature_ids"]) == len(
                set(hidden["distractor_feature_ids"])
            )


def test_v3_end_to_end_falsification_sweep():
    for k in range(64):
        secret = hashlib.sha256(f"v3-secret-{k}".encode()).digest()
        beacon = "V3-VERIFY-" + hashlib.sha256(f"beacon-{k}".encode()).hexdigest()[:24]
        packet = g3._generate(beacon=beacon, evaluator_secret=secret, namespace=f"V3T{k}")
        results = []
        for visible, hidden in zip(
            packet["visible_cases"], packet["hidden_records"], strict=True
        ):
            out = harness.execute_case(
                candidate_step=c3.step, case_visible=visible, hidden_record=hidden
            )
            assert out["scorer_result"]["pass"] is True, (
                k, visible["case_id"], out["scorer_result"]
            )
            results.append(out["scorer_result"])
        assert scorer.aggregate(results)["all_27_cases_pass"] is True



def test_v3_all_critical_id_scopes_survive_total_token_collision(monkeypatch):
    # Stronger than suffix-collision testing: every token call collides. The
    # generator must remain well-formed because unique finite slot ordinals,
    # not token uniqueness, carry identity.
    monkeypatch.setattr(g3.v1, "_token", lambda *args, **kwargs: "COLLISION")

    packet = g3._generate(
        beacon="TOTAL-TOKEN-COLLISION-BEACON-0001",
        evaluator_secret=b"X" * 32,
        namespace="ALLCOLLIDE",
    )
    assert packet["case_count"] == 27
    assert len({x["case_id"] for x in packet["visible_cases"]}) == 27

    results = []
    receipt_ids = []
    for visible, hidden in zip(
        packet["visible_cases"], packet["hidden_records"], strict=True
    ):
        assert visible["case_id"] == hidden["case_id"]

        if visible["leaf_id"] == g3.v1.TRANSFER:
            receipts = visible["domain_a"]["earned_receipts"]
            assert len(receipts) == 1
            receipt_ids.append(receipts[0]["receipt_id"])

            probe_ids = [
                row["probe_id"] for row in visible["domain_b"]["allowed_probes"]
            ]
            assert len(probe_ids) == len(set(probe_ids)) == 2
            assert set(probe_ids) == set(hidden["allowed_probe_outcome_table"])

            relevant = hidden["transfer_relevant_feature_ids"]
            distractors = hidden["distractor_feature_ids"]
            assert len(relevant) == len(set(relevant))
            assert len(distractors) == len(set(distractors)) == 2
            assert set(relevant).isdisjoint(distractors)
        else:
            hypothesis_ids = [
                row["hypothesis_id"] for row in visible["hypotheses"]
            ]
            assert len(hypothesis_ids) == len(set(hypothesis_ids)) == 2

            status = hidden["identifiability_status"]
            consequences = [
                row["terminal_consequence"] for row in visible["hypotheses"]
            ]
            if status == "IDENTIFIABLE":
                assert len(set(consequences)) == 1
            else:
                assert len(set(consequences)) == 2

            probe_ids = [row["probe_id"] for row in visible["allowed_probes"]]
            assert len(probe_ids) == len(set(probe_ids))
            assert set(probe_ids) == set(hidden["allowed_probe_outcome_table"])

        out = harness.execute_case(
            candidate_step=c3.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        assert out["scorer_result"]["pass"] is True, (
            visible["case_id"],
            out["scorer_result"],
        )
        results.append(out["scorer_result"])

    assert len(receipt_ids) == len(set(receipt_ids)) == 12
    assert scorer.aggregate(results)["all_27_cases_pass"] is True
