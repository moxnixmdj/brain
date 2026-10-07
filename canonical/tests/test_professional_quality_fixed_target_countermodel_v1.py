from fractions import Fraction
from canonical.runtime.professional_quality_fixed_target_countermodel_v1 import (
    target_success_pair, brain_success_pair, noninferior, verify
)

def test_fixed_target_success_pair():
    assert target_success_pair(Fraction(1,3)) == (Fraction(1,3), Fraction(2,3))

def test_target_relative_constraints_force_match():
    q=Fraction(7,11)
    assert noninferior(q,q)
    assert not noninferior(Fraction(8,11),q)
    assert not noninferior(Fraction(6,11),q)

def test_no_fixed_target_is_omniscient_in_both_opposed_worlds():
    for n in range(101):
        q=Fraction(n,100)
        assert target_success_pair(q) != (Fraction(1),Fraction(1))

def test_verifier_fail_closed_noncredit():
    out=verify()
    assert out["pass"] is True
    assert out["professional_quality_covered"] is False
    assert out["u_empty"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
