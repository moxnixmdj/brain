from canonical.runtime.certified_deontic_rule_fragment_v1 import parse_deontic_rule
import canonical.runtime.source_aligned_deontic_extension_v1 as ext

def dclaim(text):
    p=parse_deontic_rule(text,source="s");s=p.get("scope")
    return p,{"claim_id":"d","kind":"DEONTIC_RULE","rule_id":p["rule_id"],"relation":p["relation"],
              "subject_span":p["subject_span"],"action_span":p["action_span"],
              "scope_id":s.get("scope_id") if s else None,
              "scope_relation":s.get("relation") if s else None,
              "condition_span":s.get("condition_span") if s else None}

def test_current_v6_arguments_forward_unchanged(monkeypatch):
    seen={}
    def fake(source_text,**kwargs):
        seen["source_text"]=source_text;seen.update(kwargs)
        return {"status":"PROOF_CHECKED","accepted_claims":[],"rejected_claims":[],
                "proved_constraints":[{"op":"ATOM","id":"BASE"}]}
    monkeypatch.setattr(ext,"verify_v6",fake)
    out=ext.verify_proof("source",source_id="sid",claims=[{"claim_id":"base","kind":"BASE"}],
                         typed_context={"x":1},expected_typed_context_sha256="d"*64,
                         fact_source=b"facts",fact_source_id="fid")
    assert out["status"]=="PROOF_CHECKED"
    assert seen["fact_source"]==b"facts" and seen["fact_source_id"]=="fid"
    assert seen["typed_context"]=={"x":1} and seen["expected_typed_context_sha256"]=="d"*64

def test_scoped_deontic_claim_and_corruption(monkeypatch):
    monkeypatch.setattr(ext,"verify_v6",lambda source_text,**kwargs:{"status":"PROOF_CHECKED","accepted_claims":[],"rejected_claims":[],"proved_constraints":[]})
    text="If the input is complete, The operator must archive the record.";p,c=dclaim(text)
    assert ext.verify_proof(text,source_id="s",claims=[c])["status"]=="PROOF_CHECKED"
    bad=dict(c);bad["scope_relation"]="UNLESS"
    out=ext.verify_proof(text,source_id="s",claims=[bad])
    assert out["status"]=="PROOF_CHECKED_WITH_REJECTIONS" and out["proved_constraints"]==[]

def test_wrong_relation_cannot_mint_constraint(monkeypatch):
    monkeypatch.setattr(ext,"verify_v6",lambda source_text,**kwargs:{"status":"PROOF_CHECKED","accepted_claims":[],"rejected_claims":[],"proved_constraints":[]})
    text="The operator must not publish the draft.";p,c=dclaim(text);c["relation"]="REQUIRED"
    assert ext.verify_proof(text,source_id="s",claims=[c])["proved_constraints"]==[]
