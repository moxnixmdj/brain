from __future__ import annotations
import hashlib, io
from PIL import Image, ImageDraw
from canonical.runtime.osworld_v21_semantic_normalizer_v1 import normalize_instruction
from canonical.runtime.osworld_v21_workflow_policy_v9 import decide

STATE_NS="https://accessibility.ubuntu.example.org/ns/state"
COMP_NS="https://accessibility.ubuntu.example.org/ns/component"

def state(instruction, *, a11y=None, screenshot="s0", screenshot_bytes=None):
    return {"instruction":instruction,"a11y_tree":a11y,"ocr":None,"history":[],
            "screenshot_sha256":screenshot,"screenshot_bytes":screenshot_bytes}

def node(tag,label,x=100,y=100,w=80,h=30):
    return (f'<root xmlns:st="{STATE_NS}" xmlns:cp="{COMP_NS}">'
            f'<{tag} name="{label}" st:visible="true" st:showing="true" '
            f'cp:screencoord="({x}, {y})" cp:size="({w}, {h})" /></root>')

def action(out):
    assert len(out["actions"])==1
    return out["actions"][0]

def test_quote_preserving_control_normalization():
    out=normalize_instruction('Tap "Tap Here"')
    assert out["normalized"]=='click "Tap Here"'

def test_visit_reaches_navigation():
    out=decide(state("Visit https://example.com/docs"))
    assert action(out)=={"type":"BROWSER_OP","op":{"type":"NAVIGATE","url":"https://example.com/docs"}}

def test_activate_reaches_grounded_click():
    out=decide(state("Activate the Save button",a11y=node("button","Save",100,200,80,40)))
    assert action(out)=={"type":"CLICK","x":140,"y":220}

def test_fill_in_reaches_existing_field_fill():
    out=decide(state('Fill in Email with "person@test.invalid"',a11y=node("entry","Email")))
    a=action(out)
    assert a["type"]=="BROWSER_OP"
    assert a["op"]["type"]=="FILL_LABEL"
    assert a["op"]["label"]=="Email"
    assert a["op"]["value"]=="person@test.invalid"

def test_look_for_reaches_browser_observation():
    out=decide(state("Look for cats on the website"))
    assert action(out)=={"type":"BROWSER_OP","op":{"type":"OBSERVE"}}

def test_tap_reaches_visual_fallback():
    im=Image.new("RGB",(200,120),(255,255,255))
    ImageDraw.Draw(im).ellipse((20,30,60,70),fill=(220,45,45))
    b=io.BytesIO(); im.save(b,format="PNG"); data=b.getvalue()
    out=decide(state("Tap the red circle",screenshot=hashlib.sha256(data).hexdigest(),screenshot_bytes=data))
    a=action(out)
    assert a["type"]=="CLICK"
    assert 35<=a["x"]<=45 and 45<=a["y"]<=55
