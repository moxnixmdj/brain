from __future__ import annotations
from fractions import Fraction
import json

def target_success_pair(q: Fraction) -> tuple[Fraction, Fraction]:
    if q < 0 or q > 1:
        raise ValueError("Q_OUT_OF_RANGE")
    return q, 1-q

def brain_success_pair(p: Fraction) -> tuple[Fraction, Fraction]:
    if p < 0 or p > 1:
        raise ValueError("P_OUT_OF_RANGE")
    return p, 1-p

def noninferior(p: Fraction, q: Fraction) -> bool:
    bp=brain_success_pair(p); tp=target_success_pair(q)
    return bp[0] >= tp[0] and bp[1] >= tp[1]

def verify() -> dict:
    errors=[]
    # Exact algebra: p>=q and 1-p>=1-q iff p=q.
    for den in range(1,65):
        for num in range(den+1):
            q=Fraction(num,den)
            matching=[Fraction(n,den) for n in range(den+1) if noninferior(Fraction(n,den),q)]
            if matching != [q]:
                errors.append(("GRID_NONINFERIORITY_NOT_EQUALITY",q,matching))
    # A single fixed q cannot attain success 1 in both opposed worlds.
    oracle_pair_possible=False
    for den in range(1,65):
        for num in range(den+1):
            q=Fraction(num,den)
            if target_success_pair(q)==(Fraction(1),Fraction(1)):
                oracle_pair_possible=True
    if oracle_pair_possible:
        errors.append(("FIXED_TARGET_ORACLE_PAIR_UNEXPECTED",))
    passed=not errors
    return {
      "schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_FIXED_TARGET_COUNTERMODEL_VERIFY_V1",
      "pass":passed,
      "status":"PASS__FIXED_TARGET_TWO_WORLD_REDUCTION__ZERO_CREDIT" if passed else "FAIL_CLOSED",
      "exact_symbolic_claims":[
        "TARGET_SUCCESS_PAIR_FOR_FIXED_q_IS_(q,1-q)",
        "BRAIN_TARGET_RELATIVE_NONINFERIORITY_IN_BOTH_OPPOSED_WORLDS_IFF_p=q",
        "NO_FIXED_q_CAN_PRODUCE_TARGET_SUCCESS_PAIR_(1,1)"
      ],
      "grid_denominators_checked":"1..64",
      "professional_quality_covered":False,
      "u_empty":False,
      "terminal":False,
      "terminal_credit_delta":0,
      "errors":[repr(x) for x in errors]
    }

if __name__=="__main__":
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
