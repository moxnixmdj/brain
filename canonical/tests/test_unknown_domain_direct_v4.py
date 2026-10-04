import hashlib

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer


def _run(packet):
    results = []
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"], strict=True):
        out = harness.execute_case(candidate_step=c3.step, case_visible=visible, hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True, (visible["case_id"], out)
        results.append(out["scorer_result"])
    assert scorer.aggregate(results)["all_27_cases_pass"] is True


def test_v4_survives_forced_total_token_collision_end_to_end():
    original = g1._token
    try:
        g1._token = lambda *args, **kwargs: "COLLISION"
        packet = g4._generate(
            beacon="FORCED-COLLISION-000000000000",
            evaluator_secret=b"x" * 32,
            namespace="COLLIDE",
        )
        assert len({x["case_id"] for x in packet["visible_cases"]}) == 27
        _run(packet)
    finally:
        g1._token = original


def test_v4_all_visible_identifier_sets_are_unique_where_semantically_distinct():
    for k in range(32):
        secret = hashlib.sha256(f"total-{k}".encode()).digest()
        beacon = "TOTAL-" + hashlib.sha256(str(k).encode()).hexdigest()[:24]
        packet = g4._generate(beacon=beacon, evaluator_secret=secret, namespace=f"T{k}")
        for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"], strict=True):
            if visible["leaf_id"] == g1.TRANSFER:
                inputs = visible["domain_b"]["tasks"][0]["inputs"]
                assert len(inputs) == len(set(inputs))
                pids = [p["probe_id"] for p in visible["domain_b"]["allowed_probes"]]
                assert len(pids) == len(set(pids)) == 2
                rel = hidden["transfer_relevant_feature_ids"]
                dis = hidden["distractor_feature_ids"]
                assert len(rel) == len(set(rel))
                assert len(dis) == len(set(dis))
                assert not (set(rel) & set(dis))
            else:
                hids = [h["hypothesis_id"] for h in visible["hypotheses"]]
                assert len(hids) == len(set(hids)) == 2
                pids = [p["probe_id"] for p in visible["allowed_probes"]]
                assert len(pids) == len(set(pids))


def test_v4_end_to_end_falsification_sweep():
    for k in range(128):
        secret = hashlib.sha256(f"v4-secret-{k}".encode()).digest()
        beacon = "V4-VERIFY-" + hashlib.sha256(f"beacon-{k}".encode()).hexdigest()[:24]
        _run(g4._generate(beacon=beacon, evaluator_secret=secret, namespace=f"V4T{k}"))
