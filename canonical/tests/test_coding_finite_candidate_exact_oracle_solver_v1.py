from canonical.runtime.coding_finite_candidate_exact_oracle_solver_v1 import solve

def rows(n=4):
    return [{"candidate_id":f"C{i}","value":i} for i in range(n)]

def test_finds_first_valid_member():
    out=solve(rows(),lambda c:c["value"]==2,max_checks=4)
    assert out["pass"] is True
    assert out["selected_candidate_id"]=="C2"
    assert out["check_calls"]==3

def test_last_member_witnesses_exhaustive_liveness_shape():
    out=solve(rows(7),lambda c:c["value"]==6,max_checks=7)
    assert out["pass"] is True
    assert out["selected_candidate_id"]=="C6"
    assert out["check_calls"]==7

def test_no_member_fails_closed():
    out=solve(rows(),lambda c:False,max_checks=4)
    assert out["pass"] is False
    assert out["reason"]=="NO_ACCEPTED_CANDIDATE"

def test_insufficient_budget_fails_before_checker():
    touched=[]
    out=solve(rows(),lambda c:touched.append(c) or True,max_checks=3)
    assert out["pass"] is False
    assert out["reason"]=="CHECK_BUDGET_INSUFFICIENT_FOR_EXHAUSTIVE_ENUMERATION"
    assert touched==[]

def test_checker_exception_and_nonboolean_fail_closed():
    def boom(c): raise RuntimeError("x")
    a=solve(rows(1),boom,max_checks=1)
    b=solve(rows(1),lambda c:1,max_checks=1)
    assert a["pass"] is False and a["reason"]=="CHECKER_EXCEPTION"
    assert b["pass"] is False and b["reason"]=="CHECKER_NONBOOLEAN_RESULT"

def test_duplicate_identity_fails_closed():
    out=solve([{"candidate_id":"X"},{"candidate_id":"X"}],lambda c:True,max_checks=2)
    assert out["pass"] is False
    assert out["reason"]=="CANDIDATE_ID_DUPLICATE"
