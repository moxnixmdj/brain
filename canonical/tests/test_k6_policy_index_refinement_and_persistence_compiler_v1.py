from canonical.runtime.k6_policy_index_refinement_and_persistence_compiler_v1 import compile_policy_index

def test_universal_policy_needs_zero_label_bits_and_zero_discriminators():
    out=compile_policy_index(worlds=["w0","w1"],policies=["p"],adequate={"w0":["p"],"w1":["p"]},discriminators=[],commitment_deadline=0,separator_reacquirable_after_restart_before_deadline=False)
    assert out["tau"]==1 and out["minimum_policy_index_bits"]==0
    assert out["selected_discriminators"]==[]

def test_disjoint_two_worlds_require_one_bit_and_separator():
    d=[{"id":"bit","observations":{"w0":0,"w1":1},"cost":1,"arrival":0,"authorized":True,"owned_operator":True}]
    out=compile_policy_index(worlds=["w0","w1"],policies=["p0","p1"],adequate={"w0":["p0"],"w1":["p1"]},discriminators=d,commitment_deadline=0,separator_reacquirable_after_restart_before_deadline=False)
    assert out["tau"]==2 and out["minimum_policy_index_bits"]==1
    assert out["selected_discriminators"]==["bit"]
    assert out["persistent_policy_index_bits_lower_bound"]==1

def test_reacquirable_separator_zeroes_persistent_lower_bound():
    d=[{"id":"bit","observations":{"w0":0,"w1":1},"cost":1,"arrival":0,"authorized":True,"owned_operator":True}]
    out=compile_policy_index(worlds=["w0","w1"],policies=["p0","p1"],adequate={"w0":["p0"],"w1":["p1"]},discriminators=d,commitment_deadline=0,separator_reacquirable_after_restart_before_deadline=True)
    assert out["minimum_policy_index_bits"]==1
    assert out["persistent_policy_index_bits_lower_bound"]==0

def test_policy_cover_bits_can_be_smaller_than_world_identifier_bits():
    worlds=["w0","w1","w2","w3"]
    adequate={"w0":["p0"],"w1":["p0"],"w2":["p1"],"w3":["p1"]}
    d=[{"id":"group","observations":{"w0":0,"w1":0,"w2":1,"w3":1},"cost":1,"arrival":0,"authorized":True,"owned_operator":True}]
    out=compile_policy_index(worlds=worlds,policies=["p0","p1"],adequate=adequate,discriminators=d,commitment_deadline=0,separator_reacquirable_after_restart_before_deadline=False)
    assert out["tau"]==2 and out["minimum_policy_index_bits"]==1

def test_minimum_cost_separator_selected():
    ds=[
      {"id":"expensive","observations":{"w0":0,"w1":1},"cost":9,"arrival":0,"authorized":True,"owned_operator":True},
      {"id":"cheap","observations":{"w0":"a","w1":"b"},"cost":1,"arrival":0,"authorized":True,"owned_operator":True},
    ]
    out=compile_policy_index(worlds=["w0","w1"],policies=["p0","p1"],adequate={"w0":["p0"],"w1":["p1"]},discriminators=ds,commitment_deadline=0,separator_reacquirable_after_restart_before_deadline=True)
    assert out["selected_discriminators"]==["cheap"]

def test_late_or_nonowned_separator_rejected():
    ds=[
      {"id":"late","observations":{"w0":0,"w1":1},"cost":0,"arrival":2,"authorized":True,"owned_operator":True},
      {"id":"borrowed","observations":{"w0":0,"w1":1},"cost":0,"arrival":0,"authorized":True,"owned_operator":False},
    ]
    out=compile_policy_index(worlds=["w0","w1"],policies=["p0","p1"],adequate={"w0":["p0"],"w1":["p1"]},discriminators=ds,commitment_deadline=1,separator_reacquirable_after_restart_before_deadline=False)
    assert out["status"]=="NONIDENTIFIABLE_WITH_ADMISSIBLE_PRECOMMITMENT_INFORMATION"

def test_pairwise_overlap_does_not_fake_global_common_policy():
    worlds=["w0","w1","w2"]
    policies=["p1","p2","p3"]
    adequate={"w0":["p1","p2"],"w1":["p2","p3"],"w2":["p1","p3"]}
    d=[{"id":"w","observations":{"w0":0,"w1":1,"w2":2},"cost":1,"arrival":0,"authorized":True,"owned_operator":True}]
    out=compile_policy_index(worlds=worlds,policies=policies,adequate=adequate,discriminators=d,commitment_deadline=0,separator_reacquirable_after_restart_before_deadline=True)
    assert out["tau"]==2
    assert out["selected_discriminators"]==["w"]

def test_fail_closed_returns_witness_cell():
    out=compile_policy_index(worlds=["w0","w1"],policies=["p0","p1"],adequate={"w0":["p0"],"w1":["p1"]},discriminators=[],commitment_deadline=0,separator_reacquirable_after_restart_before_deadline=False)
    assert out["status"]=="NONIDENTIFIABLE_WITH_ADMISSIBLE_PRECOMMITMENT_INFORMATION"
    assert out["witness_cells"]==[["w0","w1"]]
