from canonical.runtime.k6_decision_refinement_compiler_v1 import compile_refinement

def test_no_information_needed_when_common_action_exists():
    out=compile_refinement(
      worlds=["w0","w1"],
      acceptable_actions={"w0":["a"],"w1":["a"]},
      discriminators=[],
      commitment_deadline=0,
    )
    assert out["status"]=="SUFFICIENT_DECISION_PARTITION_FOUND"
    assert out["selected_discriminators"]==[]

def test_one_separator_solves_disjoint_worlds():
    out=compile_refinement(
      worlds=["w0","w1"],
      acceptable_actions={"w0":["a0"],"w1":["a1"]},
      discriminators=[{"id":"d","observations":{"w0":0,"w1":1},"cost":2,"arrival":0,"authorized":True,"owned_operator":True}],
      commitment_deadline=0,
    )
    assert out["selected_discriminators"]==["d"]

def test_minimum_cost_sufficient_subset_selected():
    ds=[
      {"id":"expensive","observations":{"w0":0,"w1":1},"cost":10,"arrival":0,"authorized":True,"owned_operator":True},
      {"id":"cheap","observations":{"w0":"x","w1":"y"},"cost":1,"arrival":0,"authorized":True,"owned_operator":True},
    ]
    out=compile_refinement(worlds=["w0","w1"],acceptable_actions={"w0":["a0"],"w1":["a1"]},discriminators=ds,commitment_deadline=0)
    assert out["selected_discriminators"]==["cheap"]
    assert out["total_cost"]==1

def test_late_or_unauthorized_information_cannot_close_cell():
    ds=[
      {"id":"late","observations":{"w0":0,"w1":1},"cost":0,"arrival":2,"authorized":True,"owned_operator":True},
      {"id":"borrowed","observations":{"w0":0,"w1":1},"cost":0,"arrival":0,"authorized":True,"owned_operator":False},
    ]
    out=compile_refinement(worlds=["w0","w1"],acceptable_actions={"w0":["a0"],"w1":["a1"]},discriminators=ds,commitment_deadline=1)
    assert out["status"]=="NONIDENTIFIABLE_WITH_ADMISSIBLE_PRECOMMITMENT_INFORMATION"

def test_owned_prior_is_just_zero_cost_discriminator_record():
    ds=[{"id":"owned_prior_bit","observations":{"w0":0,"w1":1},"cost":0,"arrival":0,"authorized":True,"owned_operator":True}]
    out=compile_refinement(worlds=["w0","w1"],acceptable_actions={"w0":["a0"],"w1":["a1"]},discriminators=ds,commitment_deadline=0)
    assert out["selected_discriminators"]==["owned_prior_bit"]

def test_abstention_common_action_stops_without_separator():
    out=compile_refinement(worlds=["w0","w1"],acceptable_actions={"w0":["wait","a0"],"w1":["wait","a1"]},discriminators=[],commitment_deadline=0)
    assert out["selected_discriminators"]==[]
    assert out["policy"][0]["action"] in {"wait"}

def test_two_bits_can_be_jointly_required():
    worlds=["00","01","10","11"]
    acc={w:["a"+w] for w in worlds}
    ds=[
      {"id":"b0","observations":{w:w[0] for w in worlds},"cost":1,"arrival":0,"authorized":True,"owned_operator":True},
      {"id":"b1","observations":{w:w[1] for w in worlds},"cost":1,"arrival":0,"authorized":True,"owned_operator":True},
    ]
    out=compile_refinement(worlds=worlds,acceptable_actions=acc,discriminators=ds,commitment_deadline=0)
    assert out["selected_discriminators"]==["b0","b1"]

def test_failure_returns_exact_witness_cell():
    out=compile_refinement(worlds=["w0","w1"],acceptable_actions={"w0":["a0"],"w1":["a1"]},discriminators=[],commitment_deadline=0)
    assert out["status"]=="NONIDENTIFIABLE_WITH_ADMISSIBLE_PRECOMMITMENT_INFORMATION"
    assert out["witness_cells"]==[["w0","w1"]]
