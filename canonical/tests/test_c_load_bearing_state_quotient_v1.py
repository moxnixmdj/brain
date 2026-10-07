from fractions import Fraction
from canonical.runtime.c_load_bearing_state_quotient_v1 import certify_state_quotients

def base():
    return dict(
      source_states=("x0","x1","x2"),
      target_states=("y0","y1","y2"),
      kernel={
        "x0":{"y0":1,"y1":0,"y2":0},
        "x1":{"y0":1,"y1":0,"y2":0},
        "x2":{"y0":0,"y1":1,"y2":0},
      },
      source_quotient={"x0":"q0","x1":"q0","x2":"q1"},
      target_quotient={"y0":"r0","y1":"r1","y2":"r1"},
      evaluators={"g":{"y0":1,"y1":0,"y2":0}},
      hard_constraints={"h":{"y0":1,"y1":0,"y2":0}},
    )

def test_valid_quotient_passes():
    out=certify_state_quotients(**base())
    assert out["pass"] is True
    assert out["terminal_credit_delta"]==0

def test_source_merge_with_different_pullback_fails():
    d=base()
    d["source_quotient"]={"x0":"q0","x1":"q0","x2":"q0"}
    out=certify_state_quotients(**d)
    assert out["pass"] is False
    assert out["source_pullback_factorization_counterexamples"]

def test_target_merge_with_different_evaluator_fails():
    d=base()
    d["target_quotient"]={"y0":"r0","y1":"r0","y2":"r0"}
    out=certify_state_quotients(**d)
    assert out["pass"] is False
    assert out["target_factorization_counterexamples"]

def test_hidden_target_distinction_is_allowed_when_load_bearing_functions_agree():
    d=base()
    d["target_quotient"]={"y0":"r0","y1":"r1","y2":"r1"}
    d["evaluators"]["g2"]={"y0":2,"y1":5,"y2":5}
    d["hard_constraints"]["h2"]={"y0":0,"y1":1,"y2":1}
    out=certify_state_quotients(**d)
    assert out["pass"] is True
