import hashlib

from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2


def _exact_add2_float_order_counterexample():
    secret=hashlib.sha256(b"secret0").digest()
    beacon="beacon-qualification-0000000000000000"
    return g2._transfer_case(secret,beacon,4,namespace="QUALONLY")


def test_v2_has_exact_float_order_counterexample():
    visible,hidden=_exact_add2_float_order_counterexample()
    out=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
    assert out["scorer_result"]["pass"] is False
    assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in out["scorer_result"]["errors"]
    got=out["candidate_terminal_action"]["terminal_consequence"]
    gold=hidden["gold_terminal_consequence"]
    assert got != gold
    assert 0 < abs(got-gold) < 1e-12
    # This is an exact-order issue, not a support failure.
    assert set(out["candidate_terminal_action"]["support_feature_ids"]) == set(hidden["transfer_relevant_feature_ids"])


def test_v3_repairs_same_counterexample_without_extra_probe_or_hidden_access():
    visible,hidden=_exact_add2_float_order_counterexample()
    out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
    assert out["scorer_result"]["pass"] is True, out["scorer_result"]
    assert out["candidate_terminal_action"]["terminal_consequence"] == hidden["gold_terminal_consequence"]
    assert set(out["candidate_terminal_action"]["support_feature_ids"]) == set(hidden["transfer_relevant_feature_ids"])
    assert out["probe_count"] == 1


def test_frozen_v2_add2_public_signatures_uniquely_orient_roles():
    for index in (4,10):
        # The V2 generator's public target rows j=0..2 have fixed nonzero sign
        # signatures because ADD2 indices are both congruent to 4 mod 6.
        r0=tuple(-1 if (j+index)%2==0 else 1 for j in range(3))
        r1=tuple(-1 if (j+index+1)%3==0 else 1 for j in range(3))
        assert r0 == c3.ADD2_R0_SIG
        assert r1 == c3.ADD2_R1_SIG
        assert r0 != r1
