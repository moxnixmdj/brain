from canonical.runtime.k6_adaptive_decision_refinement_v2 import compile_adaptive
from canonical.runtime.k6_policy_index_refinement_and_persistence_compiler_v1 import compile_policy_index

def probe(i,obs,cost=1,arrival=0,owned=True):
    return {"id":i,"observations":obs,"cost":cost,"arrival":arrival,"authorized":True,"owned_operator":owned}

def test_common_policy_needs_no_probe():
    out=compile_adaptive(worlds=["x","y"],adequate={"x":["p"],"y":["p"]},discriminators=[],commitment_deadline=0)
    assert out["worst_case_cost"]==0

def test_adaptive_strictly_beats_static_countermodel():
    W=["00","01","10","11"]
    A={w:["a"+w] for w in W}
    D=[
      probe("r",{"00":0,"01":0,"10":1,"11":1}),
      probe("l",{"00":0,"01":1,"10":0,"11":0}),
      probe("q",{"00":0,"01":0,"10":0,"11":1}),
    ]
    a=compile_adaptive(worlds=W,adequate=A,discriminators=D,commitment_deadline=0)
    s=compile_policy_index(worlds=W,policies=["a"+w for w in W],adequate=A,discriminators=D,commitment_deadline=0,separator_reacquirable_after_restart_before_deadline=True)
    assert a["worst_case_cost"]==2
    assert s["total_discriminator_cost"]==3

def test_deadline_semantics_preserved():
    D=[probe("late",{"x":0,"y":1},arrival=2)]
    out=compile_adaptive(worlds=["x","y"],adequate={"x":["a"],"y":["b"]},discriminators=D,commitment_deadline=1)
    assert out["status"].startswith("NONIDENTIFIABLE")

def test_unowned_probe_not_admitted():
    D=[probe("borrowed",{"x":0,"y":1},owned=False)]
    out=compile_adaptive(worlds=["x","y"],adequate={"x":["a"],"y":["b"]},discriminators=D,commitment_deadline=1)
    assert out["status"].startswith("NONIDENTIFIABLE")
