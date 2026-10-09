from canonical.runtime.cursorbench_strict_externality_attempt_v1 import (
    classify_attempt,
    verify_current,
)

def base():
    return dict(
        public_score_nonidentifiable=True,
        scope_complete=True,
        stronger_policy_adequacy_route_state="INTERNAL_UNSOLVED",
        exact_protocol_admissible_world_pair_proved=False,
        all_internal_bypass_classes_falsified=False,
        proof_carrying_externality_certificate_present=False,
    )

def test_current_state_is_internal_unsolved_not_external():
    out=verify_current()
    assert out["pass"] is True, out
    assert out["current_classification"]=="INTERNAL_UNSOLVED"
    assert out["whole_predicate_externality_proved"] is False
    assert out["strict_gate_result"]["pass"] is False
    assert out["strict_gate_result"]["reason"]=="PROOF_CARRYING_EXTERNALITY_CERTIFICATE_REQUIRED"
    assert "ALTERNATIVE_ROUTE_NOT_FALSIFIED" in out["attempt"]["blockers"]
    assert out["terminal_credit_delta"]==0

def test_public_score_nonidentifiability_alone_is_not_whole_externality():
    out=classify_attempt(**base())
    assert out["externality_proved"] is False
    assert out["classification"]=="INTERNAL_UNSOLVED"

def test_open_stronger_route_blocks_externality_even_if_other_proofs_exist():
    x=base()
    x["exact_protocol_admissible_world_pair_proved"]=True
    x["all_internal_bypass_classes_falsified"]=True
    x["proof_carrying_externality_certificate_present"]=True
    out=classify_attempt(**x)
    assert not out["externality_proved"]
    assert out["blockers"]==["ALTERNATIVE_ROUTE_NOT_FALSIFIED"]

def test_incomplete_exact_protocol_world_pair_blocks_externality():
    x=base()
    x["stronger_policy_adequacy_route_state"]="PROVED_IMPOSSIBLE"
    x["all_internal_bypass_classes_falsified"]=True
    x["proof_carrying_externality_certificate_present"]=True
    out=classify_attempt(**x)
    assert not out["externality_proved"]
    assert "EXACT_CURSORBENCH_PROTOCOL_ADMISSIBLE_WORLD_PAIR_NOT_PROVED" in out["blockers"]

def test_internal_bypass_exhaustion_is_mandatory():
    x=base()
    x["stronger_policy_adequacy_route_state"]="PROVED_IMPOSSIBLE"
    x["exact_protocol_admissible_world_pair_proved"]=True
    x["proof_carrying_externality_certificate_present"]=True
    out=classify_attempt(**x)
    assert not out["externality_proved"]
    assert out["blockers"]==["INTERNAL_BYPASS_EXHAUSTION_NOT_PROVED"]

def test_externality_requires_every_strict_premise():
    x=base()
    x.update(
        stronger_policy_adequacy_route_state="PROVED_IMPOSSIBLE",
        exact_protocol_admissible_world_pair_proved=True,
        all_internal_bypass_classes_falsified=True,
        proof_carrying_externality_certificate_present=True,
    )
    out=classify_attempt(**x)
    assert out["externality_proved"] is True
    assert out["classification"]=="PROVEN_INFORMATION_THEORETICALLY_EXTERNAL"

def test_missing_public_nonidentifiability_also_blocks():
    x=base()
    x["public_score_nonidentifiable"]=False
    out=classify_attempt(**x)
    assert not out["externality_proved"]
    assert "PUBLIC_SCORE_NONIDENTIFIABILITY_NOT_PROVED" in out["blockers"]
