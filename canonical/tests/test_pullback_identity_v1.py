from fractions import Fraction as Q
from canonical.runtime.pullback_identity_v1 import exp,pull,push,identity

def test_deterministic_pullback_identity():
    p=[Q(1,3),Q(2,3)]
    k=[[1,0],[0,1]]
    g=[2,5]
    assert identity(p,k,g)

def test_stochastic_pullback_identity():
    p=[Q(1,4),Q(3,4)]
    k=[[Q(1,2),Q(1,2)],[Q(1,3),Q(2,3)]]
    g=[1,7]
    assert identity(p,k,g)

def test_source_pullback_dominance_implies_target_dominance():
    mu=[Q(3,4),Q(1,4)]
    nu=[Q(1,4),Q(3,4)]
    k=[[1,0],[0,1]]
    g=[4,1]
    kg=pull(k,g)
    assert exp(mu,kg)>=exp(nu,kg)
    assert exp(push(mu,k),g)>=exp(push(nu,k),g)

def test_bad_kernel_fails_closed():
    try: pull([[1,1]],[1,2])
    except ValueError as e: assert str(e)=="KERNEL"
    else: raise AssertionError("expected failure")
