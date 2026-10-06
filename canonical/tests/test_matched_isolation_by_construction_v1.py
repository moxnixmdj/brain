from canonical.runtime.matched_isolation_by_construction_v1 import compile_isolation_by_construction,REQ

def good():
    x={k:True for k in REQ}
    x["case_ids"]=["a","b","c"]
    x["namespace_ids"]=["na","nb","nc"]
    return x

def test_good():
    o=compile_isolation_by_construction(good())
    assert o["pass"] is True
    assert o["matched_isolation_implied"] is True
    assert o["per_case_reset_equivalence_receipts_required"] is False

def test_each_structural_premise_is_load_bearing():
    for k in REQ:
        x=good(); x[k]=False
        o=compile_isolation_by_construction(x)
        assert o["pass"] is False
        assert k in o["missing"]

def test_namespace_reuse_fails():
    x=good(); x["namespace_ids"]=["n","n","m"]
    assert compile_isolation_by_construction(x)["pass"] is False

def test_case_id_reuse_fails():
    x=good(); x["case_ids"]=["a","a","b"]
    assert compile_isolation_by_construction(x)["pass"] is False
