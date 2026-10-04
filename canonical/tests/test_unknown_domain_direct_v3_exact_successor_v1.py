"""Regression and zero-reality qualification tests for Unknown-Domain V3."""
from copy import deepcopy

import pytest

from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3


CEX_BEACON = "CEX-00006-ABCDEFGHIJKLMNOP"


def _case(pop, index):
    return pop["visible_cases"][index], pop["hidden_records"][index]


def test_reachable_v2_add2_float_counterexample_is_repaired_exactly():
    old = g2.generate_qualification_fixture_population(beacon=CEX_BEACON)
    visible, hidden = _case(old, 10)
    old_out = harness.execute_case(
        candidate_step=c2.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    assert old_out["scorer_result"]["pass"] is False
    assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in old_out["scorer_result"]["errors"]
    assert 0 < abs(
        old_out["candidate_terminal_action"]["terminal_consequence"]
        - hidden["gold_terminal_consequence"]
    ) < 1e-12

    new = g3.generate_qualification_fixture_population(beacon=CEX_BEACON)
    visible3, hidden3 = _case(new, 10)
    new_out = harness.execute_case(
        candidate_step=c3.step,
        case_visible=visible3,
        hidden_record=hidden3,
    )
    assert new_out["scorer_result"]["pass"] is True
    assert new_out["candidate_terminal_action"]["terminal_consequence"] == hidden3["gold_terminal_consequence"]
    assert new_out["probe_count"] == 1


def test_add2_visible_sign_signatures_are_distinct_and_role_preserving():
    pop = g3.generate_qualification_fixture_population(beacon=CEX_BEACON)
    for index in (4, 10):
        visible, _ = _case(pop, index)
        receipt = visible["domain_a"]["earned_receipts"][0]
        r0 = c3._source_role_signature(visible, receipt, "r0")
        r1 = c3._source_role_signature(visible, receipt, "r1")
        assert r0 == (-1, 1, -1)
        assert r1 == (1, -1, 1)
        assert r0 != r1


def test_v3_identifier_guard_fails_closed_on_every_known_intra_packet_collision_class():
    pop = g3.generate_qualification_fixture_population(beacon=CEX_BEACON)
    visible, hidden = _case(pop, 4)

    bad = deepcopy(hidden)
    bad["distractor_feature_ids"][1] = bad["distractor_feature_ids"][0]
    with pytest.raises(g1.UnknownDomainGeneratorError, match="V3_DISTRACTOR_IDS_NOT_INJECTIVE"):
        g3._validate_transfer_packet(visible, bad)

    bad = deepcopy(hidden)
    keys = list(bad["domain_mapping"])
    bad["domain_mapping"][keys[1]] = bad["domain_mapping"][keys[0]]
    with pytest.raises(g1.UnknownDomainGeneratorError, match="V3_DOMAIN_MAPPING_NOT_INJECTIVE"):
        g3._validate_transfer_packet(visible, bad)

    bad_visible = deepcopy(visible)
    receipt = bad_visible["domain_a"]["earned_receipts"][0]
    keys = list(receipt["source_role_binding"])
    receipt["source_role_binding"][keys[1]] = receipt["source_role_binding"][keys[0]]
    with pytest.raises(g1.UnknownDomainGeneratorError, match="V3_SOURCE_MAPPING_NOT_INJECTIVE"):
        g3._validate_transfer_packet(bad_visible, hidden)


def test_v3_passes_multiple_zero_reality_qualification_populations():
    for i in range(32):
        beacon = f"V3-QUALIFICATION-{i:04d}-ABCDEFGHIJKLMNOP"
        pop = g3.generate_qualification_fixture_population(beacon=beacon)
        assert pop["production"] is False
        assert pop["case_count"] == 27
        for visible, hidden in zip(pop["visible_cases"], pop["hidden_records"]):
            out = harness.execute_case(
                candidate_step=c3.step,
                case_visible=visible,
                hidden_record=hidden,
            )
            assert out["scorer_result"]["pass"] is True
