from fractions import Fraction
from typing import Mapping, Sequence, Any

class QuotientError(ValueError):
    pass

def _q(x: Any) -> Fraction:
    if isinstance(x, Fraction):
        return x
    if isinstance(x, bool):
        return Fraction(int(x),1)
    return Fraction(x)

def _normalize_kernel(kernel, source_states, target_states):
    X=tuple(map(str,source_states)); Y=tuple(map(str,target_states))
    if not X or not Y:
        raise QuotientError("EMPTY_STATE_DOMAIN")
    out={}
    for x in X:
        row=kernel.get(x)
        if not isinstance(row,Mapping):
            raise QuotientError("MISSING_KERNEL_ROW:"+x)
        vals={y:_q(row.get(y,0)) for y in Y}
        if any(v<0 for v in vals.values()) or sum(vals.values(),Fraction(0))!=1:
            raise QuotientError("INVALID_KERNEL_ROW:"+x)
        out[x]=vals
    return out

def _factorization_counterexamples(values, quotient, states):
    groups={}
    for s in map(str,states):
        if s not in quotient:
            raise QuotientError("QUOTIENT_MISSING:"+s)
        groups.setdefault(str(quotient[s]),[]).append(s)
    bad=[]
    for qid,members in groups.items():
        first=values[members[0]]
        for s in members[1:]:
            if values[s]!=first:
                bad.append((qid,members[0],s,first,values[s]))
    return bad

def certify_state_quotients(
    *,
    source_states: Sequence[str],
    target_states: Sequence[str],
    kernel: Mapping[str,Mapping[str,Any]],
    source_quotient: Mapping[str,str],
    target_quotient: Mapping[str,str],
    evaluators: Mapping[str,Mapping[str,Any]],
    hard_constraints: Mapping[str,Mapping[str,Any]],
):
    X=tuple(map(str,source_states)); Y=tuple(map(str,target_states))
    K=_normalize_kernel(kernel,X,Y)
    if not evaluators and not hard_constraints:
        raise QuotientError("NO_LOAD_BEARING_FUNCTIONALS")
    target_bad=[]
    source_bad=[]
    all_fns={**dict(evaluators),**dict(hard_constraints)}
    for name,raw in all_fns.items():
        vals={y:_q(raw[y]) for y in Y}
        tb=_factorization_counterexamples(vals,target_quotient,Y)
        target_bad.extend((name,*x) for x in tb)
        pb={x:sum((K[x][y]*vals[y] for y in Y),Fraction(0)) for x in X}
        sb=_factorization_counterexamples(pb,source_quotient,X)
        source_bad.extend((name,*x) for x in sb)
    ok=not target_bad and not source_bad
    return {
        "status":"PASS__LOAD_BEARING_STATE_QUOTIENT_SUFFICIENT" if ok else "FAIL_CLOSED",
        "pass":ok,
        "target_factorization_counterexamples":target_bad,
        "source_pullback_factorization_counterexamples":source_bad,
        "evaluator_count":len(evaluators),
        "hard_constraint_count":len(hard_constraints),
        "terminal_credit_delta":0,
    }
