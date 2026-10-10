from canonical.runtime import regcap_four_way_governing_requirement_discriminator_v1 as d
from canonical.runtime import regcap_necessary_property_authority_v1 as r
from canonical.runtime import mrel_necessary_property_authority_v1 as m

def _ok(domain, digest):
    return {"pass": True, "semantic_truth_authority": True, "candidate_domain": domain, "authority_sha256": digest}

def test_four_way_composition_and_guards():
    def pair(pid, repo_root=None):
        return _ok([r.CCOB,m.MREL],"a") if pid=="CCOB_MREL" else _ok([r.CCYB,m.MREL],"b")
    def tm(repo_root=None):
        return _ok([r.TLAC,m.MREL],"c")
    out=d.verify_authority(ccob_mrel_authority=pair,ccyb_mrel_authority=pair,tlac_mrel_authority=tm)
    assert out["pass"] is True
    assert sorted(out["candidate_domain"])==sorted(d.DOMAIN)
    assert len(set(out["outcomes"].values()))==4
    assert out["open_world_ontology_complete"] is False
    assert out["terminal_authority"] is False

    def bad(pid, repo_root=None):
        return {"pass": False}
    out=d.verify_authority(ccob_mrel_authority=bad,ccyb_mrel_authority=pair,tlac_mrel_authority=tm)
    assert out["pass"] is False

    def drift(pid, repo_root=None):
        return _ok([r.CCOB,m.MREL],"x")
    out=d.verify_authority(ccob_mrel_authority=pair,ccyb_mrel_authority=drift,tlac_mrel_authority=tm)
    assert out["pass"] is False and "DOMAIN_DRIFT" in out["reason"]
