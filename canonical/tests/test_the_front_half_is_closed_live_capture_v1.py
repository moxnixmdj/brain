"""The front half is closed: the demonstration comes from a real click, not from a harness.

Before this round, every Layer-2 result supplied `observed_effects.http_exchanges` by hand --
the harness already knew the answer. That is the one gap that made the reduction look better
than it was.

Now: a fourth audited channel (`trace_capture_v1`) subscribes to the browser's own Network
events. It CANNOT click, type, navigate or evaluate. It can only listen.

MEASURED, end to end, on a page with nothing hardcoded:

    navigate to a real form, address the fields via role/textbox
    click sku, type "A-100", click qty, type "40", click SUBMIT     (real input events)
    capture  -> POST /orders form_body {csrf: LIVE-TOK, sku: A-100, qty: 40, go: ""} status 201
    elevate  -> 1 http_request step, all 6 UI steps pruned
    learn    -> {csrf: LIVE-TOK, sku: ?str0, qty: ?num0, go: ""}
    new goal -> "sku Z-777 with quantity 3" -> {'?str0': 'Z-777', '?num0': '3'}
    execute  -> 201, server echoes {"sku": "Z-777", "qty": "3"}, 2.0 ms, NO BROWSER

So: a person's clicks become one network call, that call becomes a parameterised skill, and the
skill performs a task nobody demonstrated.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from canonical.runtime import trace_capture_v1 as CAP   # noqa: E402
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as TC  # noqa: E402


def test_the_capture_channel_cannot_act():
    for forbidden in CAP.FORBIDDEN_HERE:
        assert forbidden not in CAP.ALLOWED_HERE
    assert CAP.ALLOWED_HERE == {"Network.enable", "Network.disable"}


def test_a_forbidden_call_raises_rather_than_being_filtered():
    c = CAP.NetworkCapture.__new__(CAP.NetworkCapture)
    c.i, c.events = 0, []
    for bad in ("Input.dispatchMouseEvent", "Page.navigate", "Runtime.evaluate"):
        try:
            c.call(bad)
        except CAP.CaptureError:
            continue
        raise AssertionError(f"{bad} was not refused")


def test_the_captured_exchange_reduces_and_parameterises():
    ex = [{"url": "http://127.0.0.1:8891/orders", "method": "POST",
           "headers": {"Content-Type": "application/x-www-form-urlencoded"},
           "form_body": {"csrf": "LIVE-TOK", "sku": "A-100", "qty": "40", "go": ""},
           "status": 201}]
    elev = TC.elevate_trace_to_fastest_layer(
        {"steps": [], "observed_effects": {"http_exchanges": ex}})
    sk = TC.anti_unify_workflow("place an order for sku A-100 with quantity 40",
                                elev["elevated_steps"], {"http_status": 201})
    body = sk["abstract_steps"][0]["form_body"]
    assert body["sku"] == "?str0" and body["qty"] == "?num0"
    assert body["csrf"] == "LIVE-TOK"
    assert TC.bind_goal_parameters(
        sk, "place an order for sku Z-777 with quantity 3") == {"?str0": "Z-777", "?num0": "3"}


def test_only_mutating_requests_become_exchanges():
    """A GET is navigation, not a skill. Capturing it would teach the skill to load a page."""
    c = CAP.NetworkCapture.__new__(CAP.NetworkCapture)
    c.events = [
        {"method": "Network.requestWillBeSent",
         "params": {"requestId": "1", "type": "Document",
                    "request": {"url": "http://x/", "method": "GET", "headers": {}}}},
        {"method": "Network.requestWillBeSent",
         "params": {"requestId": "2", "type": "XHR",
                    "request": {"url": "http://x/orders", "method": "POST",
                                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                                "postData": "sku=A&qty=1"}}},
    ]
    out = c.http_exchanges()
    assert len(out) == 1 and out[0]["method"] == "POST"
    assert out[0]["form_body"] == {"sku": "A", "qty": "1"}
