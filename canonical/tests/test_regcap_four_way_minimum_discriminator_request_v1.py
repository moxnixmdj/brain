from canonical.runtime import regcap_four_way_minimum_discriminator_request_v1 as q
from canonical.runtime import regcap_four_way_governing_requirement_discriminator_v1 as d

def test_minimum_four_way_request_is_exact_and_fail_closed():
    def ok(repo_root=None):
        return {"pass":True,"semantic_truth_authority":True,"outcomes":dict(d.OUTCOMES),"authority_sha256":"abc"}
    out=q.compile_request(list(d.DOMAIN),authority_verifier=ok)
    assert out["pass"] is True
    assert out["minimum_observation_count"]==1
    assert out["absence_is_not_negative_evidence"] is True
    assert out["independent_verification_required"] is True
    assert len(set(out["allowed_outcomes"].values()))==4
    assert out["concept_identity_authority"] is False
    assert out["terminal_authority"] is False

    out=q.compile_request(list(d.DOMAIN)[:-1],authority_verifier=ok)
    assert out["pass"] is False

    def bad(repo_root=None):
        return {"pass":False}
    out=q.compile_request(list(d.DOMAIN),authority_verifier=bad)
    assert out["pass"] is False
