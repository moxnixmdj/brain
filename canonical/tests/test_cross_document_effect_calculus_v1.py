from __future__ import annotations
from hashlib import sha256
import json
import pytest
from canonical.runtime import cross_document_effect_calculus_v1 as c
from canonical.runtime import cross_document_effect_calculus_verify_v1 as v

def _sha(x):
    return sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def _e(eid,cls,value,*,cond=None,start=None,sup=None):
    return {"effect_id":eid,"target_id":"threshold","effect_class":cls,"value":value,
            "conditions":cond or {},"valid_from":start,"valid_until":None,
            "supersedes":sup or [],"source_locator":"section:"+eid}

def _d(did,effects):
    return {"schema":c.DOC_SCHEMA,"document_id":did,"effects":effects}

def _fixture():
    docs={
      "A.json":_d("A",[_e("A.t","DEFINE","10")]),
      "B.json":_d("B",[_e("B.t","REPLACE","12",start="2026-07-01",sup=["A.t"])]),
      "C.json":_d("C",[_e("C.t","EXCEPTION","8",cond={"small":True},start="2026-07-01",sup=["B.t"])])
    }
    return docs

def _case(docs,context,when="2026-08-01"):
    return {"schema":c.CASE_SCHEMA,"case_id":"abc",
            "documents":[{"path":p,"sha256":_sha(d)} for p,d in reversed(list(docs.items()))],
            "query":{"target_id":"threshold","as_of":when,"context":context}}

def test_define_replace_exception_composes():
    docs=_fixture(); case=_case(docs,{"small":True})
    out=c.compute(case,docs)
    assert out["pass"] and out["effective_value"]=="8"
    assert out["surviving_effect_ids"]==["C.t"]
    assert v.verify(case,docs,out)["verified"]

def test_exception_false_falls_back_to_replacement():
    docs=_fixture(); case=_case(docs,{"small":False})
    out=c.compute(case,docs)
    assert out["pass"] and out["effective_value"]=="12"
    assert out["surviving_effect_ids"]==["B.t"]

def test_before_amendment_uses_definition():
    docs=_fixture(); case=_case(docs,{"small":True},"2026-06-30")
    out=c.compute(case,docs)
    assert out["pass"] and out["effective_value"]=="10"

def test_incomparable_different_values_remain_open():
    docs={"A.json":_d("A",[_e("A.t","DEFINE","10")]),
          "B.json":_d("B",[_e("B.t","DEFINE","11")])}
    case=_case(docs,{})
    out=c.compute(case,docs)
    assert not out["pass"]
    assert out["status"]=="OPEN__INCOMPARABLE_EFFECTS_REQUIRE_DISCRIMINATOR"
    assert v.verify(case,docs,out)["verified"]

def test_incomparable_same_value_closes_without_fake_disambiguation():
    docs={"A.json":_d("A",[_e("A.t","DEFINE","10")]),
          "B.json":_d("B",[_e("B.t","DEFINE","10")])}
    case=_case(docs,{})
    out=c.compute(case,docs)
    assert out["pass"] and out["effective_value"]=="10"
    assert out["decision_ambiguity_irrelevant"] is True

def test_cycle_and_hash_drift_fail_closed():
    cyc={"A.json":_d("A",[
        _e("A.t","REPLACE","10",sup=["B.t"]),
        _e("B.t","REPLACE","11",sup=["A.t"])])}
    with pytest.raises(ValueError,match="SUPERSESSION_CYCLE"):
        c.compute(_case(cyc,{}),cyc)
    docs=_fixture(); case=_case(docs,{"small":True})
    case["documents"][0]["sha256"]="0"*64
    with pytest.raises(ValueError,match="DOCUMENT_CONTENT_ADDRESS_MISMATCH"):
        c.compute(case,docs)
