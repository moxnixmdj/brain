"""Regression and successor tests for Unknown-Domain direct V3."""
import hashlib
import itertools

from canonical.runtime import unknown_domain_direct_candidate_v3 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as generator
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v3_semantics_v1 as sem


def _secret(label: bytes) -> bytes:
    return hashlib.sha256(label).digest()


def test_v3_add2_is_exactly_role_permutation_invariant():
    program = {
        "dsl": "UDIR_V1",
        "op": "ADD2",
        "roles": ["r0", "r1"],
        "params": {"bias": -1.2345678901234567},
    }
    values = [0.10000000000000002, 3.141592653589793]
    a = sem.eval_program(program, {"r0": values[0], "r1": values[1]})
    b = sem.eval_program(program, {"r0": values[1], "r1": values[0]})
    assert a == b


def test_v3_repairs_the_reachable_v2_one_ulp_fixture():
    secret = _secret(b"secret13")
    beacon = "beacon-0000000000000013-xxxxxxxx"
    visible, hidden = generator._transfer_case(
        secret, beacon, 4, namespace="V3REG"
    )
    assert hidden["primitive_family"] == "COMPOSITIONAL_REWRITE"

    out = harness.execute_case(
        candidate_step=candidate.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    assert out["scorer_result"]["pass"] is True
    assert out["candidate_terminal_action"]["terminal_consequence"] == hidden[
        "gold_terminal_consequence"
    ]
    assert out["probe_count"] <= 2

    mapping = dict(hidden["domain_mapping"])
    swapped = {"r0": mapping["r1"], "r1": mapping["r0"]}
    query = visible["domain_b"]["query_inputs"]
    true_values = {role: query[fid] for role, fid in mapping.items()}
    swap_values = {role: query[fid] for role, fid in swapped.items()}
    assert sem.eval_program(hidden["latent_primitive_program"], true_values) == sem.eval_program(
        hidden["latent_primitive_program"], swap_values
    )


def test_v3_full_27_case_fixture_passes_unchanged_frozen_scorer():
    packet = generator.generate_test_fixture_population()
    assert packet["case_count"] == 27
    results = []
    for visible, hidden in zip(
        packet["visible_cases"], packet["hidden_records"], strict=True
    ):
        out = harness.execute_case(
            candidate_step=candidate.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        result = out["scorer_result"]
        assert result["pass"] is True, result
        results.append(result)

    aggregate = scorer.aggregate(results)
    assert aggregate["all_27_cases_pass"] is True
    assert aggregate["transfer_leaf_pass"] is True
    assert aggregate["abstention_leaf_pass"] is True


def test_rank_is_a_bijection_for_every_frozen_cardinality():
    secret = _secret(b"rank-proof-regression")
    beacon = "rank-proof-beacon-000000000000"
    for count in range(1, 28):
        ranks = [
            generator._rank(secret, beacon, "TEST", i, count)
            for i in range(count)
        ]
        assert sorted(ranks) == list(range(count))


def test_surface_identifier_uniqueness_does_not_depend_on_hmac_suffix(monkeypatch):
    monkeypatch.setattr(generator, "_opaque_suffix", lambda *args: "COLLISION")
    secret = _secret(b"forced-suffix-collision")
    beacon = "forced-collision-beacon-000000000"

    for roles in (["r0"], ["r0", "r1"]):
        mapping, distractors = generator._surface_ids_total(
            secret, beacon, 4, "DOMAIN", list(roles)
        )
        ids = list(mapping.values()) + list(distractors)
        assert len(ids) == len(set(ids))
        assert len(ids) == len(roles) + 2


def test_case_and_probe_identity_totality_survives_forced_suffix_collision(monkeypatch):
    monkeypatch.setattr(generator, "_opaque_suffix", lambda *args: "COLLISION")
    packet = generator._generate(
        beacon="forced-totality-beacon-00000000000",
        evaluator_secret=_secret(b"forced-totality"),
        namespace="TOTALITY",
    )
    case_ids = [row["case_id"] for row in packet["visible_cases"]]
    assert len(case_ids) == 27
    assert len(set(case_ids)) == 27

    for visible in packet["visible_cases"]:
        if visible["leaf_id"] == generator.TRANSFER:
            ids = list(visible["domain_b"]["tasks"][0]["inputs"])
            assert len(ids) == len(set(ids))
            probe_ids = [p["probe_id"] for p in visible["domain_b"]["allowed_probes"]]
            assert len(probe_ids) == len(set(probe_ids)) == 2
        else:
            hypotheses = [h["hypothesis_id"] for h in visible["hypotheses"]]
            assert len(hypotheses) == len(set(hypotheses)) == 2
            probe_ids = [p["probe_id"] for p in visible["allowed_probes"]]
            assert len(probe_ids) == len(set(probe_ids))


def test_add2_permutation_invariance_is_exact_over_representative_v2_domain_values():
    program = {
        "dsl": "UDIR_V1",
        "op": "ADD2",
        "roles": ["r0", "r1"],
        "params": {"bias": 1.9375},
    }
    values = (-3.5, -0.25, 0.25, 1.0, 3.5)
    for a, b in itertools.product(values, repeat=2):
        left = sem.eval_program(program, {"r0": a, "r1": b})
        right = sem.eval_program(program, {"r0": b, "r1": a})
        assert left == right
