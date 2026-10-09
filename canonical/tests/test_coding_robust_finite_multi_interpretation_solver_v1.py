import itertools
from canonical.runtime.coding_robust_finite_multi_interpretation_solver_v1 import solve

def candidates(n):
    return [{"candidate_id":f"C{i}","value":i} for i in range(n)]

def worlds(m):
    return [{"interpretation_id":f"M{j}","value":j} for j in range(m)]

def test_exhaustive_boolean_matrices_through_three_by_three():
    checked=0
    for n in range(1,4):
        for m in range(1,4):
            for bits in itertools.product((False,True),repeat=n*m):
                out=solve(
                    candidates(n),worlds(m),
                    lambda c,w,bits=bits,m=m:bits[c["value"]*m+w["value"]],
                    max_checks=n*m,
                )
                robust=[all(bits[i*m+j] for j in range(m)) for i in range(n)]
                checked+=1
                if any(robust):
                    first=robust.index(True)
                    assert out["pass"] is True
                    assert out["selected_candidate_index"]==first
                    assert out["check_calls"]<=n*m
                else:
                    assert out["pass"] is False
                    assert out["reason"]=="NO_ROBUST_ACCEPTED_CANDIDATE"
                    assert out["detail"]["check_calls"]<=n*m
    assert checked==682

def test_single_interpretation_reduces_to_exact_oracle_shape():
    out=solve(candidates(4),worlds(1),lambda c,w:c["value"]==2,max_checks=4)
    assert out["pass"] is True
    assert out["selected_candidate_id"]=="C2"

def test_budget_fails_before_checker():
    touched=[]
    out=solve(candidates(2),worlds(3),lambda c,w:touched.append((c,w)) or True,max_checks=5)
    assert out["pass"] is False
    assert out["reason"]=="CHECK_BUDGET_INSUFFICIENT_FOR_WORST_CASE"
    assert touched==[]

def test_duplicate_candidate_or_interpretation_identity_fails_closed():
    a=solve([{"candidate_id":"X"},{"candidate_id":"X"}],worlds(1),lambda c,w:True,max_checks=2)
    b=solve(candidates(1),[{"interpretation_id":"Y"},{"interpretation_id":"Y"}],lambda c,w:True,max_checks=2)
    assert a["pass"] is False and a["reason"]=="CANDIDATE_ID_DUPLICATE"
    assert b["pass"] is False and b["reason"]=="INTERPRETATION_ID_DUPLICATE"

def test_checker_exception_and_nonboolean_fail_closed():
    def boom(c,w): raise RuntimeError("x")
    a=solve(candidates(1),worlds(1),boom,max_checks=1)
    b=solve(candidates(1),worlds(1),lambda c,w:1,max_checks=1)
    assert a["pass"] is False and a["reason"]=="CHECKER_EXCEPTION"
    assert b["pass"] is False and b["reason"]=="CHECKER_NONBOOLEAN_RESULT"
