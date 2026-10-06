from canonical.runtime.dominance_preserving_transform_closure_v1 import (
    PrimitiveTransform, TransformClosureError, theorem_projection, verify_path
)

def test_identity_empty_path_preserves():
    x=verify_path([], "c0")
    assert x["pass"] and x["source_context"]=="c0" and x["target_context"]=="c0"

def test_well_typed_preserving_chain_preserves():
    xs=[
      PrimitiveTransform("T1","c0","c1",True),
      PrimitiveTransform("T2","c1","c2",True),
      PrimitiveTransform("T3","c2","c3",True),
    ]
    x=verify_path(xs,"c0")
    assert x["pass"] and x["target_context"]=="c3"

def test_nonpreserving_primitive_fails_closure():
    xs=[
      PrimitiveTransform("T1","c0","c1",True),
      PrimitiveTransform("BAD","c1","c2",False),
    ]
    x=verify_path(xs,"c0")
    assert not x["pass"] and x["reason"]=="NON_PRESERVING_PRIMITIVE:BAD"

def test_context_mismatch_fails_closed():
    try:
      verify_path([PrimitiveTransform("T","wrong","c1",True)],"c0")
    except TransformClosureError as e:
      assert str(e).startswith("CONTEXT_TYPE_MISMATCH:")
    else:
      raise AssertionError("expected context type mismatch")

def test_global_closure_requires_both_primitive_proofs_and_generator_completeness():
    ps=[PrimitiveTransform("T","c0","c1",True)]
    assert theorem_projection(ps,True)["finite_generated_composition_closure"]
    assert not theorem_projection(ps,False)["finite_generated_composition_closure"]
    bad=[PrimitiveTransform("T","c0","c1",False)]
    assert not theorem_projection(bad,True)["finite_generated_composition_closure"]

def test_zero_credit():
    assert theorem_projection([],True)["terminal_credit_delta"]==0
