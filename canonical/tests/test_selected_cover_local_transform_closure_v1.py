from canonical.runtime.selected_cover_local_transform_closure_v1 import certify_selected_cover

def base():
    return dict(
      target_contexts={"c0","c1"},
      context_to_route={"c0":"r0","c1":"r1"},
      route_primitive_dominance={"r0":True,"r1":True},
      route_local_c_closure={"r0":True,"r1":True},
      route_transforms={"r0":["t0"],"r1":["t1"]},
      known_transforms={"t0","t1","bad_unused"},
    )

def test_unused_bad_transform_does_not_block():
    out=certify_selected_cover(**base())
    assert out["pass"] is True
    assert "bad_unused" in out["unused_transforms"]
    assert out["global_all_transform_closure_required"] is False

def test_selected_route_with_open_local_c_fails():
    d=base(); d["route_local_c_closure"]["r1"]=False
    out=certify_selected_cover(**d)
    assert out["pass"] is False
    assert "SELECTED_ROUTE_LOCAL_C_OPEN" in out["errors"]

def test_uncovered_target_context_fails():
    d=base(); del d["context_to_route"]["c1"]
    out=certify_selected_cover(**d)
    assert out["pass"] is False
    assert "UNCOVERED_TARGET_CONTEXT" in out["errors"]

def test_unknown_transform_on_selected_route_fails():
    d=base(); d["route_transforms"]["r1"]=["t_unknown"]
    out=certify_selected_cover(**d)
    assert out["pass"] is False
    assert out["unknown_selected_transforms"]

def test_bad_unselected_route_is_irrelevant():
    d=base()
    d["route_primitive_dominance"]["r_bad"]=False
    d["route_local_c_closure"]["r_bad"]=False
    d["route_transforms"]["r_bad"]=["bad_unused"]
    out=certify_selected_cover(**d)
    assert out["pass"] is True
