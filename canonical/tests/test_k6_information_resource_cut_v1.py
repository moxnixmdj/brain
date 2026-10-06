from canonical.runtime.k6_information_resource_cut_v1 import bits_needed_for_distinct_worlds,can_guarantee_all_distinct_worlds,verify_cut

def test_exact_examples():
    assert bits_needed_for_distinct_worlds(1)==0
    assert bits_needed_for_distinct_worlds(2)==1
    assert bits_needed_for_distinct_worlds(3)==2
    assert bits_needed_for_distinct_worlds(4)==2
    assert bits_needed_for_distinct_worlds(5)==3

def test_insufficient_bits_fail():
    assert not can_guarantee_all_distinct_worlds(3,1)
    assert not can_guarantee_all_distinct_worlds(9,3)

def test_sufficient_bits_pass():
    assert can_guarantee_all_distinct_worlds(8,3)
    assert can_guarantee_all_distinct_worlds(9,4)

def test_verifier():
    assert verify_cut()["exact_pigeonhole_bound"] is True
