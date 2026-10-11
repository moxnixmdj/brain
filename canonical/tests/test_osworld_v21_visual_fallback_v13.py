from __future__ import annotations

import hashlib
import inspect
import io

from PIL import Image, ImageDraw

from canonical.runtime.osworld_v21_brain_subject_v13 import SUBJECT_ID, build_subject
from canonical.runtime.osworld_v21_visual_policy_overlay_v1 import route_visual
from canonical.runtime.osworld_v21_visual_region_grounding_v1 import ground_visual_region
from canonical.runtime.osworld_v21_workflow_policy_v8 import decide


RED=(220,45,45)
WHITE=(255,255,255)


def image_bytes(circles=()):
    im=Image.new("RGB",(200,120),WHITE)
    draw=ImageDraw.Draw(im)
    for box in circles:
        draw.ellipse(box,fill=RED)
    out=io.BytesIO(); im.save(out,format="PNG")
    return out.getvalue()


def state(instruction, screenshot, history=None):
    return {
        "instruction":instruction,
        "history":list(history or []),
        "a11y_tree":None,
        "ocr":None,
        "screenshot_bytes":screenshot,
        "screenshot_sha256":hashlib.sha256(screenshot).hexdigest(),
    }


def action(out):
    assert len(out["actions"])==1
    return out["actions"][0]


def test_unique_explicit_red_circle_grounded_without_model():
    img=image_bytes([(20,30,60,70)])
    out=ground_visual_region(img,color="red",shape="circle")
    assert out["pass"] is True
    assert out["candidate_count"]==1
    p=out["click_point"]
    assert 35<=p["x"]<=45 and 45<=p["y"]<=55


def test_duplicate_visual_targets_fail_closed_without_spatial_discriminator():
    img=image_bytes([(20,30,60,70),(140,30,180,70)])
    out=ground_visual_region(img,color="red",shape="circle")
    assert out["pass"] is False
    assert out["reason"]=="AMBIGUOUS_MATCH"
    routed=route_visual(state("Click the red circle",img))
    assert routed["actions"]==[{"type":"WAIT"}]
    assert routed["_policy_receipt"]["route"]=="VISUAL_GROUNDING_UNRESOLVED"


def test_spatial_discriminator_selects_left_target():
    img=image_bytes([(20,30,60,70),(140,30,180,70)])
    out=ground_visual_region(img,color="red",shape="circle",spatial="left")
    assert out["pass"] is True
    assert out["click_point"]["x"]<100
    routed=route_visual(state("Click the red circle on the left",img))
    assert action(routed)["type"]=="CLICK"
    assert action(routed)["x"]<100


def test_same_screenshot_suppresses_repeated_visual_click():
    img=image_bytes([(20,30,60,70)])
    first=route_visual(state("Click the red circle",img))
    row={
        "screenshot_sha256":hashlib.sha256(img).hexdigest(),
        "policy_receipt":first["_policy_receipt"],
    }
    second=route_visual(state("Click the red circle",img,[row]))
    assert second["actions"]==[{"type":"WAIT"}]
    assert second["_policy_receipt"]["route"]=="VISUAL_NO_PROGRESS_FAIL_CLOSED"


def test_changed_screenshot_after_explicit_visual_click_is_completion_evidence():
    before=image_bytes([(20,30,60,70)])
    after=image_bytes([])
    first=route_visual(state("Click the red circle",before))
    row={
        "screenshot_sha256":hashlib.sha256(before).hexdigest(),
        "policy_receipt":first["_policy_receipt"],
    }
    second=route_visual(state("Click the red circle",after,[row]))
    assert second["actions"]==[{"type":"DONE"}]
    assert second["_policy_receipt"]["route"]=="VISUAL_CLICK_TRANSITION_VERIFIED"


def test_visual_then_file_workflow_composes_across_receipts():
    before=image_bytes([(20,30,60,70)])
    after=image_bytes([])
    instruction='Click the red circle; then create "done.txt" containing "yes"'
    first=decide(state(instruction,before))
    assert action(first)["type"]=="CLICK"
    h1={
        "screenshot_sha256":hashlib.sha256(before).hexdigest(),
        "actions":["pyautogui.click(...)"],
        "policy_receipt":first["_policy_receipt"],
    }
    second=decide(state(instruction,after,[h1]))
    assert action(second)["type"]=="STATE_OPS"
    assert action(second)["ops"][0]=={
        "type":"WRITE_TEXT","path":"/home/oai/share/done.txt","text":"yes"
    }


def test_v13_subject_and_visual_stack_remain_model_independent():
    subject=build_subject()
    assert subject.policy_id==SUBJECT_ID
    import canonical.runtime.osworld_v21_visual_region_grounding_v1 as g
    import canonical.runtime.osworld_v21_visual_policy_overlay_v1 as p
    import canonical.runtime.osworld_v21_unified_policy_v13 as u
    import canonical.runtime.osworld_v21_workflow_policy_v8 as w
    source="\n".join(inspect.getsource(x).casefold() for x in (g,p,u,w))
    for forbidden in ("openai","anthropic","gemini","qwen","reference_trajectory","task_001"):
        assert forbidden not in source
