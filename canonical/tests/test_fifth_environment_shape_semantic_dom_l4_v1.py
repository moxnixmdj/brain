"""r83 -- FIFTH ENVIRONMENT SHAPE: semantic_dom (Layer 4), and the boundary that decides it.

Four defects stood between the L4 capability and a working skill. Each one returned
success while doing the wrong thing, which is the same failure class as r64's truncated
PNG and r80's ok:True with the file missing:

  1. a step tagged {"layer": "click"} matched neither the UI branch nor any executable
     branch, so elevate_trace_to_fastest_layer returned [] with dominant_layer "none"
     and no error at all;
  2. the demonstrated value "urgent" stayed a literal because it was not quoted in the
     goal, so the compiled skill would type "urgent" forever -- params: [], a recording;
  3. execute_compiled_steps never instantiated bindings, so a hole reached the wire as
     the literal string "?str_loose0" and every step receipt said ok:true;
  4. a CLICK_SEMANTIC step carrying a `value` was executed as a SUBMIT, dropping the
     value, so the page returned unfiltered and still reported ok:true.

And one boundary, which is the actual answer to "is this a skill?":
  a filter whose state lives in the URL is an EXACT postcondition and elevates to a
  skill; a filter whose state lives only in the DOM (onclick toggling row display) has
  no addressable state, the executor refuses loudly, and no skill may be claimed.
"""
import re
import urllib.request

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as TC

SRV = "http://127.0.0.1:8901/inbox"     # server-rendered: state is in the URL
JSRV = "http://127.0.0.1:8895/"         # client-side: state is only in the DOM

DOM = [
    {"role": "textbox", "name": "filter", "bbox": {"x": 34, "y": 120, "width": 300, "height": 40}},
    {"role": "button", "name": "APPLY", "bbox": {"x": 401, "y": 120, "width": 120, "height": 40}},
]
# What a browser produced in r82: click the box, type, click APPLY.
STEPS = [
    {"layer": "click", "x": 170, "y": 140},
    {"layer": "key", "text": "urgent", "x": 170, "y": 140},
    {"layer": "click", "x": 450, "y": 140},
]


def _up():
    try:
        urllib.request.urlopen(SRV, timeout=2).read()
        return True
    except Exception:
        return False


live = pytest.mark.skipif(not _up(), reason="L4 demo server not running on :8901")


def _skill():
    elev = TC.elevate_trace_to_fastest_layer({"steps": STEPS, "dom_elements": DOM})
    steps = [dict(s, url=SRV) for s in elev["elevated_steps"]]
    sk = TC.anti_unify_workflow("show only the urgent messages", steps,
                                {"dom_text_contains": "Inbox - 3 shown"})
    return elev, sk


def _shown(html):
    m = re.search(r"Inbox - (\d+) shown", html or "")
    return int(m.group(1)) if m else None


def _truth(token):
    html = urllib.request.urlopen(f"{SRV}?filter={token}", timeout=5).read().decode()
    return _shown(html)


# --- defect 1: a click step must be recognised as UI ------------------------- #
def test_a_click_step_is_a_ui_step():
    """`{"layer": "click"}` used to match nothing, so elevation returned [] silently."""
    elev = TC.elevate_trace_to_fastest_layer({"steps": STEPS, "dom_elements": DOM})
    assert len(elev["elevated_steps"]) == 3
    assert elev["dominant_layer"] == "semantic_dom"
    assert all(s["op"] == "CLICK_SEMANTIC" for s in elev["elevated_steps"])


# --- defect 2: the typed value must become a hole --------------------------- #
def test_the_typed_value_becomes_a_parameter_not_a_frozen_literal():
    """params == [] would make this a recording that types "urgent" forever."""
    _, sk = _skill()
    assert sk["param_order"] == ["?str_loose0"]
    assert "urgent" not in str(sk["abstract_steps"])
    assert "?str_loose0" in str(sk["abstract_steps"])


def test_the_hole_binds_from_goals_that_never_say_urgent():
    _, sk = _skill()
    for goal, want in (("show only the messages about refund", "refund"),
                       ("show only the messages from alice", "alice"),
                       ("show only the messages about invoice", "invoice"),
                       ("show only the urgent messages", "urgent")):
        assert TC.bind_goal_parameters(sk, goal) == {"?str_loose0": want}


def test_quoted_literals_still_parameterise_only_values_never_field_names():
    """A generic word scan once rewrote {"sku": "A-100"} into {"?str1": "?str0"}."""
    sk = TC.anti_unify_workflow(
        "place an order for sku A-100 with quantity 40",
        [{"layer": "http_request", "method": "POST", "url": "http://x/y",
          "form_body": {"sku": "A-100", "qty": "40"}}],
        {"http_status": 201})
    assert sk["abstract_steps"][0]["form_body"] == {"sku": "?str0", "qty": "?num0"}


# --- defect 3: an unbound hole must never reach the wire -------------------- #
def test_an_unbound_hole_is_refused_before_any_stage_runs():
    r = TC.execute_compiled_steps(
        [{"layer": "semantic_dom", "op": "CLICK_SEMANTIC", "url": SRV,
          "selector": {"role": "textbox", "name": "filter"}, "value": "?str_loose0"}],
        cwd="/tmp")
    assert r["ok"] is False
    assert r["reason"].startswith("UNBOUND_PARAMETERS")
    assert r["executed_steps"] == 0


# --- defect 4 + the end-to-end claim ---------------------------------------- #
@live
def test_one_demonstration_runs_four_unseen_goals_checked_against_an_oracle():
    _, sk = _skill()
    checked = 0
    for goal, token in (("show only the messages about refund", "refund"),
                        ("show only the messages from alice", "alice"),
                        ("show only the messages about invoice", "invoice"),
                        ("show only the urgent messages", "urgent")):
        b = TC.bind_goal_parameters(sk, goal)
        out = TC.execute_compiled_steps(sk["abstract_steps"], cwd="/tmp", bindings=b)
        assert out["ok"] is True, out.get("reason")
        got = _shown(out["step_receipts"][-1].get("response_preview"))
        assert got == _truth(token), f"{goal}: skill said {got}, oracle said {_truth(token)}"
        checked += 1
    assert checked == 4


# --- the boundary: where this is NOT a skill -------------------------------- #
def test_a_client_side_filter_has_no_addressable_postcondition():
    """:8895 filters by onclick over <tr>. No URL reproduces the state."""
    js = urllib.request.urlopen(JSRV, timeout=5).read().decode()
    assert "<form" not in js          # nothing for the semantic executor to submit
    out = TC.execute_compiled_steps(
        [{"layer": "semantic_dom", "op": "CLICK_SEMANTIC", "url": JSRV,
          "selector": {"role": "button", "name": "APPLY"}}], cwd="/tmp")
    assert out["ok"] is False
    assert out["reason"] == "NO_SEMANTIC_FORM_AT_URL"


def test_the_two_pages_are_distinguishable_by_one_probe():
    """The discriminator is addressability, not looks: same probe, opposite answers."""
    assert _truth("urgent") == 3 and _truth("invoice") == 1
    js = urllib.request.urlopen(JSRV + "?filter=urgent", timeout=5).read().decode()
    assert _shown(js) is None        # the JS page ignores the parameter entirely
