from canonical.runtime.semantic_target_exclusion_cut_v1 import target_exclusion_cut,certify_target_support,find_assignment_for_target_support

def test_two_unsplittable_worlds_need_only_exclude_one_for_zero_message():
    worlds=("w0","w1"); policies=("p0","p1")
    adequate={"w0":("p0",),"w1":("p1",)}
    queries={"q":{"w0":"same","w1":"same"}}
    cut=target_exclusion_cut(worlds,policies,adequate,queries)
    assert cut["excluded_count"]==1
    assert certify_target_support(worlds,policies,adequate,queries,("w0",))["certified"] is True
    assert find_assignment_for_target_support(worlds,policies,adequate,queries,("w0","w1"))["certified"] is False

def test_exact_identity_is_not_required_when_target_support_subset_has_common_policy():
    worlds=("a","b","c"); policies=("p0","p1")
    adequate={"a":("p0",),"b":("p0",),"c":("p1",)}
    queries={"q":{"a":0,"b":0,"c":0}}
    out=find_assignment_for_target_support(worlds,policies,adequate,queries,("a","b"))
    assert out["certified"] is True
    assert out["exact_target_identity_required"] is False
    assert out["excluded"]==("c",)

def test_query_separation_can_make_exclusion_cut_empty():
    worlds=("w0","w1"); policies=("p0","p1")
    adequate={"w0":("p0",),"w1":("p1",)}
    queries={"q":{"w0":0,"w1":1}}
    cut=target_exclusion_cut(worlds,policies,adequate,queries)
    assert cut["excluded_count"]==0
