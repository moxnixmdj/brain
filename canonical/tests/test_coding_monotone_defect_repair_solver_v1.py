from canonical.runtime.coding_monotone_defect_repair_solver_v1 import solve

def test_monotone_repairs_reach_zero_defects():
    universe=["a","b","c","d"]
    def verifier(c):
        ds=list(c["defects"])
        return {"pass":not ds,"defects":ds}
    def repair(c,d):
        return {"candidate_id":c["candidate_id"],"defects":[x for x in c["defects"] if x!=d]}
    out=solve({"candidate_id":"x","defects":universe},universe,verifier,repair,
              max_verifier_calls=5,max_repairs=4)
    assert out["pass"] is True
    assert out["repair_calls"]==4
    assert out["verifier_calls"]==5
    assert out["trace"][-1]["defects"]==[]

def test_can_remove_multiple_defects_per_repair():
    universe=["a","b","c","d"]
    def verifier(c):
        ds=list(c["defects"]); return {"pass":not ds,"defects":ds}
    def repair(c,d):
        return {"defects":[]}
    out=solve({"defects":universe},universe,verifier,repair,
              max_verifier_calls=5,max_repairs=4)
    assert out["pass"] is True
    assert out["repair_calls"]==1
    assert out["verifier_calls"]==2

def test_nonmonotone_reintroduction_fails_closed():
    universe=["a","b"]
    states=[["a","b"],["a","b"]]
    def verifier(c):
        ds=states.pop(0); return {"pass":False,"defects":ds}
    def repair(c,d): return dict(c)
    out=solve({"candidate_id":"x"},universe,verifier,repair,
              max_verifier_calls=3,max_repairs=2)
    assert out["pass"] is False
    assert out["reason"]=="DEFECT_SET_DID_NOT_STRICTLY_DECREASE"

def test_unknown_defect_fails_closed():
    out=solve({"x":1},["a"],lambda c:{"pass":False,"defects":["z"]},
              lambda c,d:c,max_verifier_calls=2,max_repairs=1)
    assert out["pass"] is False
    assert out["reason"].startswith("VERIFIER_DEFECT_OUTSIDE_DECLARED_UNIVERSE")

def test_budget_insufficient_fails_before_callbacks():
    touched=[]
    out=solve({"x":1},["a","b"],lambda c:touched.append("v") or {"pass":True,"defects":[]},
              lambda c,d:touched.append("r") or c,max_verifier_calls=2,max_repairs=2)
    assert out["pass"] is False
    assert out["reason"]=="VERIFIER_BUDGET_INSUFFICIENT_FOR_WORST_CASE"
    assert touched==[]

def test_malformed_verifier_and_repair_fail_closed():
    a=solve({"x":1},["a"],lambda c:{"pass":False,"defects":[]},
            lambda c,d:c,max_verifier_calls=2,max_repairs=1)
    b=solve({"x":1},["a"],lambda c:{"pass":False,"defects":["a"]},
            lambda c,d:7,max_verifier_calls=2,max_repairs=1)
    assert a["pass"] is False and a["reason"]=="FAIL_WITH_EMPTY_DEFECT_SET"
    assert b["pass"] is False and b["reason"]=="REPAIR_RESULT_NOT_OBJECT"
