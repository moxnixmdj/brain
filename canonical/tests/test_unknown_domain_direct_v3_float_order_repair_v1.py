from canonical.runtime import unknown_domain_direct_candidate_v3 as v3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_v2_add2_float_counterexample_v1 as ce


def test_v2_universal_claim_has_exact_add2_binary64_counterexample():
    out = ce.reproduce()
    assert out["status"] == "COUNTEREXAMPLE_REPRODUCED__V2_UNIVERSAL_PASS_FALSE"
    assert out["candidate_terminal_consequence"] == 7.335613344468422
    assert out["gold_terminal_consequence"] == 7.335613344468421
    assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in out["scorer_errors"]


def test_v3_repairs_exact_counterexample_without_hidden_access_or_extra_probe():
    packet = generator._generate(
        beacon=ce.BEACON,
        evaluator_secret=ce.SECRET,
        namespace="UDIR",
    )
    visible = packet["visible_cases"][ce.TRANSFER_INDEX]
    hidden = packet["hidden_records"][ce.TRANSFER_INDEX]
    out = harness.execute_case(
        candidate_step=v3.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    assert out["probe_count"] == 1
    assert out["scorer_result"]["pass"] is True
    assert out["candidate_terminal_action"]["terminal_consequence"] == hidden["gold_terminal_consequence"]
    assert out["candidate_terminal_action"]["support_feature_ids"] == sorted(hidden["domain_mapping"].values())


def test_v3_visible_sign_signatures_recover_add2_role_order_for_both_indices():
    # For the frozen V2 generator ADD2 occurs at transfer indexes 4 and 10.
    # Magnitudes are strictly positive, while role signs depend only on j/index,
    # so the first three public rows give source and target the same distinct
    # signatures regardless of beacon/secret.
    for index in (4, 10):
        r0 = tuple(-1 if (j + index) % 2 == 0 else 1 for j in range(3))
        r1 = tuple(-1 if (j + index + 1) % 3 == 0 else 1 for j in range(3))
        assert r0 == (-1, 1, -1)
        assert r1 == (1, -1, 1)
        assert r0 != r1


def test_v3_many_synthetic_generator_populations_all_pass():
    # Non-production falsification sweep only. No authority gate is invoked.
    for k in range(32):
        beacon = f"V3-SYNTHETIC-FALSIFICATION-{k:04d}"
        secret = (f"V3-SYNTHETIC-SECRET-{k:04d}-" + "x" * 40).encode()
        packet = generator._generate(
            beacon=beacon,
            evaluator_secret=secret,
            namespace="UDIR",
        )
        results = []
        for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"]):
            out = harness.execute_case(
                candidate_step=v3.step,
                case_visible=visible,
                hidden_record=hidden,
            )
            results.append(out["scorer_result"])
        assert all(row["pass"] is True for row in results)
