from __future__ import annotations
import hashlib, io
from PIL import Image, ImageDraw
from canonical.runtime.osworld_v21_visual_relational_grounding_v1 import route_relational_visual
from canonical.runtime.osworld_v21_workflow_policy_v10 import decide

RED=(220,45,45)
WHITE=(255,255,255)

def img(circles):
    im=Image.new("RGB",(240,140),WHITE)
    d=ImageDraw.Draw(im)
    for box in circles:
        d.ellipse(box,fill=RED)
    b=io.BytesIO(); im.save(b,format="PNG")
    return b.getvalue()

def state(instruction,data):
    return {
        "instruction":instruction,
        "a11y_tree":None,
        "ocr":None,
        "history":[],
        "screenshot_bytes":data,
        "screenshot_sha256":hashlib.sha256(data).hexdigest(),
    }

def action(out):
    assert len(out["actions"])==1
    return out["actions"][0]

def test_largest_selects_unique_larger_region():
    data=img([(20,40,50,70),(140,20,210,90)])
    out=route_relational_visual(state("Click the largest red circle",data))
    a=action(out)
    assert a["type"]=="CLICK"
    assert a["x"]>120

def test_smallest_selects_unique_smaller_region():
    data=img([(20,40,50,70),(140,20,210,90)])
    out=route_relational_visual(state("Click the smallest red circle",data))
    a=action(out)
    assert a["type"]=="CLICK"
    assert a["x"]<100

def test_leftmost_and_rightmost_select_extrema():
    data=img([(20,40,60,80),(160,40,200,80)])
    left=route_relational_visual(state("Click the leftmost red circle",data))
    right=route_relational_visual(state("Click the rightmost red circle",data))
    assert action(left)["x"]<100
    assert action(right)["x"]>120

def test_topmost_and_bottommost_select_extrema():
    data=img([(100,10,140,50),(100,90,140,130)])
    top=route_relational_visual(state("Click the topmost red circle",data))
    bottom=route_relational_visual(state("Click the bottommost red circle",data))
    assert action(top)["y"]<70
    assert action(bottom)["y"]>70

def test_equal_size_largest_tie_fails_closed():
    data=img([(20,40,60,80),(160,40,200,80)])
    out=route_relational_visual(state("Click the largest red circle",data))
    assert action(out)=={"type":"WAIT"}
    assert out["_policy_receipt"]["reason"]=="TIED_EXTREME"

def test_multiple_relations_do_not_guess():
    data=img([(20,40,50,70),(140,20,210,90)])
    out=route_relational_visual(state("Click the largest leftmost red circle",data))
    assert out is None

def test_v15_workflow_uses_comparative_fallback_after_v14_wait():
    data=img([(20,40,50,70),(140,20,210,90)])
    out=decide(state("Tap the largest red circle",data))
    a=action(out)
    assert a["type"]=="CLICK"
    assert a["x"]>120
