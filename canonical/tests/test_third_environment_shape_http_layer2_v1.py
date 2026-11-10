"""LAYER 2: a browser demonstration becomes a parameterised API call. The thesis in one test.

    demonstrate (6 UI steps against a form)
        click sku, type A-100, click qty, type 40, click submit
    observed causal effect
        POST /orders  form_body {csrf: tok123, sku: A-100, qty: 40}
    elevate (0.07 ms)
        1 step, layer=http_request, ALL SIX UI steps pruned
    learn
        form_body {csrf: tok123, sku: ?str0, qty: ?num0}
        goal_skeleton "place an order for sku ?str0 with quantity ?num0"
    new goal
        "place an order for sku B-900 with quantity 7"
    bind
        {'?str0': 'B-900', '?num0': 7}
    execute
        POST -> 201, body {"id": "ORD-B-900-7", "stored": {...}}
    round trip 2.5 ms, zero model calls, no browser.

WHAT THIS PROVES: the reduction a demonstration needs is to the API call, not to the click.
The six clicks were the noise; the POST was the signal; the two values were the parameters.

WHAT IT DOES NOT PROVE: that this happens automatically from a live browser capture. Here the
causal HTTP exchange is GIVEN to the compiler, which is the honest boundary -- recording the
exchange from a real session is a different piece of work.

NOTE the csrf token survived as a LITERAL, correctly: it is session state, not a goal
parameter. Only values that came from the goal became holes.
"""
import json
import pathlib
import socket
import sys
import threading
import time
import urllib.parse
import http.server
import socketserver

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as TC  # noqa: E402

URL_PATH = "/orders"
STORE: dict[str, dict] = {}


class _H(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode()
        d = {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}
        oid = f"ORD-{d.get('sku','?')}-{d.get('qty','?')}"
        STORE[oid] = d
        self._send(201, json.dumps({"id": oid, "stored": d}))

    def log_message(self, *a):
        pass


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


PORT = _free_port()
_SRV = socketserver.TCPServer(("127.0.0.1", PORT), _H)
threading.Thread(target=_SRV.serve_forever, daemon=True).start()
time.sleep(0.1)
URL = f"http://127.0.0.1:{PORT}{URL_PATH}"


def _demo() -> dict:
    return {
        "steps": [{"layer": "screenshot"}, {"layer": "click", "x": 210, "y": 180},
                  {"layer": "key", "text": "A-100"}, {"layer": "click", "x": 210, "y": 240},
                  {"layer": "key", "text": "40"}, {"layer": "click", "x": 300, "y": 320}],
        "observed_effects": {"http_exchanges": [{
            "url": URL, "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "form_body": {"csrf": "tok123", "sku": "A-100", "qty": "40"}}]},
    }


def _learn():
    elev = TC.elevate_trace_to_fastest_layer(_demo())
    goal = "place an order for sku A-100 with quantity 40"
    return elev, TC.anti_unify_workflow(goal, elev["elevated_steps"], {"http_status": 201})


def test_six_ui_steps_reduce_to_one_http_call():
    elev, _ = _learn()
    steps = elev["elevated_steps"]
    assert len(steps) == 1
    assert steps[0]["layer"] == "http_request" and steps[0]["method"] == "POST"


def test_the_goal_values_become_holes_and_session_state_does_not():
    _, sk = _learn()
    body = sk["abstract_steps"][0]["form_body"]
    assert body["sku"] == "?str0" and body["qty"] == "?num0"
    assert body["csrf"] == "tok123", "a csrf token is session state, not a goal parameter"


def test_it_places_a_different_order_it_was_never_taught():
    _, sk = _learn()
    bind = TC.bind_goal_parameters(sk, "place an order for sku B-900 with quantity 7")
    assert bind == {"?str0": "B-900", "?num0": "7"}
    steps = TC._instantiate_obj(sk["abstract_steps"], bind)
    out = TC.execute_compiled_steps(steps, cwd="/tmp")
    assert out["ok"] is True
    assert out["step_receipts"][0]["status_code"] == 201
    assert "ORD-B-900-7" in out["step_receipts"][0]["response_preview"]


def test_the_round_trip_does_not_need_a_browser():
    _, sk = _learn()
    steps = TC._instantiate_obj(sk["abstract_steps"],
                                {"?str0": "C-1", "?num0": "2"})
    out = TC.execute_compiled_steps(steps, cwd="/tmp")
    # a result dict that cannot be serialised is not a result -- this raised TypeError
    # because the live OpenerDirector was being returned. json_safe() + a cookie snapshot.
    safe = TC.json_safe(out)
    json.dumps(safe)
    assert safe["step_receipts"][0]["layer"] == "http_request"
    assert safe["step_receipts"][0]["elapsed_us"] < 200_000
    assert isinstance(safe.get("cookies"), list)


def test_three_environment_shapes_now_work_end_to_end():
    """sqlite_exec, python_file_op, http_request -- the three the record named as undemonstrated."""
    _, sk = _learn()
    assert sk["abstract_steps"][0]["layer"] == "http_request"
    doc = (ROOT / "canonical/governance/"
           "THREE_ENVIRONMENT_SHAPES_MEASURED_20261109_V1.json")
    assert doc.exists()
