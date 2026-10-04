import hashlib

from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_v3_lossless_scope_equivalence_v1 as proof


def test_scope_equivalence_theorem():
    out=proof.prove()
    assert out["status"]=="PASS__LOSSLESS_EQUIVALENCE_OVER_FROZEN_ADMISSIBLE_EVALUATOR_SCOPE"
    assert out["lossless"] is True
    assert out["scope_narrowing_of_admissible_cases"] is False
    assert out["generator_composition"]["successful_packet_rewrite"] is False


def test_successful_v3_packets_are_byte_semantically_identical_v2_packets():
    for i in range(32):
        beacon=f"SCOPE-EQUIVALENCE-{i:04d}-20261005"
        secret=hashlib.sha256(f"scope-secret-{i}".encode()).digest()
        v2=g2._generate(beacon=beacon,evaluator_secret=secret,namespace="SCOPE")
        v3=g3._generate(beacon=beacon,evaluator_secret=secret,namespace="SCOPE")
        assert v3==v2
        assert g3.validate_packet(v2)==v2


def test_rejection_classes_are_semantic_not_performance_filters():
    out=proof.prove()
    reasons=" ".join(out["validator_rejection_classes"].values())
    assert "SCORER" in reasons
    assert "HARNESS" in reasons
    assert "NONIDENTIFIABLE_REQUIRES_TWO_DECISION_DISTINCT_SURVIVORS" in reasons
    assert "FROZEN_UNDERSPECIFIED_CASE_REQUIRES_VALID_UNIQUE_MINIMUM_DISCRIMINATOR" in reasons


def test_no_credit_or_open_world_overclaim():
    out=proof.prove()
    assert out["accounting"]["acceptance_credit_delta"]==0
    assert out["accounting"]["capability_credit_delta"]==0
    assert any("NO_OPEN_WORLD" in x for x in out["hard_nonclaims"])
    assert any("INDEPENDENT_CONTENT_BOUND_VERIFICATION_REQUIRED" in x for x in out["hard_nonclaims"])
