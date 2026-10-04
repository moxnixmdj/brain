"""Deterministic falsifier for the revoked Unknown-Domain V2 universal promotion.

The V2 candidate can identify the correct ADD2 support while lexicographic role
orientation changes the exact IEEE-754 result by one ulp.  The frozen scorer
compares terminal consequence exactly, so one reachable failing case is enough
to falsify a FOR-EVERY-population theorem.
"""
import hashlib

from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator


def test_v2_universal_promotion_has_reachable_exact_float_counterexample():
    secret=hashlib.sha256(b"secret0").digest()
    beacon="beacon-qualification-0000000000000000"
    visible,hidden=generator._transfer_case(secret,beacon,4,namespace="REVOCATION")

    out=harness.execute_case(
        candidate_step=candidate.step,
        case_visible=visible,
        hidden_record=hidden,
    )

    assert out["scorer_result"]["pass"] is False
    assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in out["scorer_result"]["errors"]
    assert set(out["candidate_terminal_action"]["support_feature_ids"]) == set(hidden["transfer_relevant_feature_ids"])

    got=out["candidate_terminal_action"]["terminal_consequence"]
    gold=hidden["gold_terminal_consequence"]
    assert got != gold
    assert 0 < abs(got-gold) < 1e-12
    assert out["probe_count"] == 1
