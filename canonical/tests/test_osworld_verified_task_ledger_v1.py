"""Hard fail-closed tests for the external verified task ledger.

The receipt-producing tests run real guest subprocesses through the pinned state-op
compiler and the admitted sensor bridge; no receipt is hand-written as PASS.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import pytest

from canonical.runtime import osworld_verified_task_ledger_v1 as L
from canonical.runtime.osworld_sensor_request_bridge_v1 import AdmittedSensorGuestOps
from canonical.runtime.osworld_v21_host_guest_ops_v1 import OSWorldHostGuestOps
from canonical.runtime.osworld_v21_host_web_app_ops_v1 import OSWorldHostWebAppOps


class Controller:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root

    def execute_python_command(self, program: str) -> dict[str, Any]:
        done = subprocess.run(
            [sys.executable, "-c", program], cwd=str(self.root),
            capture_output=True, text=True, timeout=120,
        )
        return {
            "status": "success" if done.returncode == 0 else "error",
            "output": done.stdout,
            "error": done.stderr or None,
        }


class Environment:
    def __init__(self, root: pathlib.Path) -> None:
        self.controller = Controller(root)


class NoBrowser:
    """The ledger tests exercise guest ops only; no CDP endpoint is available."""

    def bind_environment(self, environment: Any) -> None:
        return None

    def run(self, op: Mapping[str, Any]) -> dict[str, Any]:
        raise AssertionError("unexpected browser operation: " + str(op))


def _state(instruction: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"instruction": instruction, "history": rows, "screenshot_sha256": "a" * 64}


def _done(_: Mapping[str, Any]) -> dict[str, Any]:
    return {"response": "finish", "actions": [{"type": "DONE"}]}


def _wait(_: Mapping[str, Any]) -> dict[str, Any]:
    return {"response": "working", "actions": [{"type": "WAIT"}]}


def _row(ops: list[dict[str, Any]], result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "screenshot_sha256": "a" * 64,
        "action_fingerprint": "x",
        "actions": ["WAIT"],
        "response": "state ops",
        "submitted_operations": ops,
        "guest_result": dict(result),
    }


def test_explicit_directory_receipt_from_real_guest_allows_done() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-ledger-dir-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "reports"
        instruction = f"Create a directory {target}"
        requirements, errors = L.compile_requirements(instruction)
        assert errors == []
        assert requirements == [{
            "kind": "DIRECTORY_SENSOR", "path": str(target),
            "op": "ASSERT_SENSOR_REQUEST",
            "ops": ["ASSERT_PATH_EXISTS", "ASSERT_SENSOR_REQUEST"],
        }]
        assert L.assertion_ops(requirements[0]) == [
            {"type": "ASSERT_PATH_EXISTS", "path": str(target)},
            {"type": "ASSERT_SENSOR_REQUEST", "path": str(target)},
        ]

        ops = [
            {"type": "MKDIR", "path": str(target)},
            {"type": "ASSERT_PATH_EXISTS", "path": str(target)},
            {"type": "ASSERT_SENSOR_REQUEST", "path": str(target)},
        ]
        bridge = AdmittedSensorGuestOps()
        bridge.bind_environment(Environment(root))
        result = bridge.run({"ops": ops})
        assert result["ok"] is True
        assert "SENSOR_REQUEST:PASS:" in result["output"]
        assert result["admission"]["source"] == "fresh_measurement"

        out = L.decide(_state(instruction, [_row(ops, result)]), _done)
        assert out["actions"] == [{"type": "DONE"}]
        assert out["_policy_receipt"]["verified"] is True


def test_file_text_receipt_from_real_guest_allows_done() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-ledger-file-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "notes.txt"
        instruction = f'Write "Q4" into {target}'
        requirements, errors = L.compile_requirements(instruction)
        assert errors == []
        assert requirements[0]["kind"] == "TEXT_CONTAINS"
        assert requirements[0]["text"] == "Q4"

        ops = [
            {"type": "WRITE_TEXT", "path": str(target), "text": "Q4 report"},
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(target), "text": "Q4"},
        ]
        guest = OSWorldHostGuestOps()
        guest.bind_environment(Environment(root))
        result = guest.run({"ops": ops})
        assert "ASSERT_TEXT_CONTAINS:PASS:" + str(target) in result["output"]

        out = L.decide(_state(instruction, [_row(ops, result)]), _done)
        assert out["actions"] == [{"type": "DONE"}]

        # The same verified ledger lets a stalled base policy finish honestly.
        out_wait = L.decide(_state(instruction, [_row(ops, result)]), _wait)
        assert out_wait["actions"] == [{"type": "DONE"}]


def test_done_is_withheld_until_assertion_receipt_exists() -> None:
    instruction = "/tmp/brain-ledger-unseen-target"
    out = L.decide(_state(instruction, []), _done)
    assert out["actions"] == [{
        "type": "STATE_OPS",
        "ops": [{"type": "ASSERT_PATH_EXISTS", "path": instruction}],
    }]
    assert out["_policy_receipt"]["withheld_reason"] == "FRESH_PASS_REQUIRED"


def test_later_mutation_invalidates_older_pass() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-ledger-stale-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "notes.txt"
        instruction = f'Write "Q4" into {target}'
        ops = [
            {"type": "WRITE_TEXT", "path": str(target), "text": "Q4 report"},
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(target), "text": "Q4"},
        ]
        guest = OSWorldHostGuestOps()
        guest.bind_environment(Environment(root))
        result = guest.run({"ops": ops})
        mutation = {"type": "WRITE_TEXT", "path": str(target), "text": "changed"}
        mutated = guest.run({"ops": [mutation]})
        rows = [_row(ops, result), _row([mutation], mutated)]
        out = L.decide(_state(instruction, rows), _done)
        assert out["actions"][0]["type"] == "STATE_OPS"
        assert out["_policy_receipt"]["verified"] is False
        evidence = L.audit(_state(instruction, rows), L.compile_requirements(instruction)[0])
        assert evidence["evidence"][0]["last_mutation_row_index"] == 1
        assert evidence["evidence"][0]["pass_row_index"] == 0


def test_pass_for_a_different_path_is_not_accepted() -> None:
    instruction = "/tmp/brain-ledger-required-path"
    wrong = "/tmp/brain-ledger-wrong-path"
    ops = [{"type": "ASSERT_PATH_EXISTS", "path": wrong}]
    rows = [_row(ops, {
        "ok": True, "status": "ok",
        "output": "ASSERT_PATH_EXISTS:PASS:" + wrong,
    })]
    out = L.decide(_state(instruction, rows), _done)
    assert out["actions"][0]["type"] == "STATE_OPS"
    assert out["_policy_receipt"]["verified"] is False


def test_sensor_pass_without_fresh_admission_is_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-ledger-forged-") as tmp:
        target = pathlib.Path(tmp) / "reports"
        instruction = f"Create a directory {target}"
        ops = [{"type": "ASSERT_SENSOR_REQUEST", "path": str(target)}]
        rows = [_row(ops, {
            "ok": True, "status": "ok",
            "output": "SENSOR_REQUEST:PASS:st_mode:16877",
        })]
        out = L.decide(_state(instruction, rows), _done)
        assert out["actions"][0]["type"] == "STATE_OPS"
        assert out["_policy_receipt"]["verified"] is False


def test_ambiguous_quotes_and_multiple_paths_fail_closed() -> None:
    instruction = 'Write "alpha" into /tmp/a and "beta" into /tmp/b'
    requirements, errors = L.compile_requirements(instruction)
    assert "AMBIGUOUS_CLAUSE_BINDING" in errors
    out = L.decide(_state(instruction, []), _done)
    assert out["actions"] == [{"type": "WAIT"}]
    assert out["_policy_receipt"]["withheld_reason"] == "UNRESOLVED_REQUIREMENT"


def test_gui_instruction_cannot_borrow_guest_state_evidence() -> None:
    instruction = 'Click "Save" to close the dialog'
    out = L.decide(_state(instruction, []), _done)
    assert out["actions"] == [{"type": "WAIT"}]
    assert "NO_EXPLICIT_STATE_PATH" in out["_policy_receipt"]["errors"]


def test_fail_output_is_never_overridden() -> None:
    fail = {"response": "failed", "actions": [{"type": "FAIL"}]}
    out = L.decide(_state("/tmp/x", []), lambda _: fail)
    assert out == fail


def test_runtime_policy_composition_is_wired_and_model_free() -> None:
    from canonical.runtime import osworld_verified_policy_v1 as P

    state = {
        "instruction": "Click the Save button",
        "screenshot_sha256": "a" * 64,
        "a11y_tree": "<root/>",
        "history": [],
    }
    out = P.decide(state)
    assert isinstance(out, Mapping)
    assert out.get("actions")
    assert str(out["actions"][0].get("type") or "").upper() != "DONE"
    source = pathlib.Path(P.__file__).read_text(encoding="utf-8")
    assert "unified_policy_v17" in source
    assert "osworld_verified_task_ledger_v1" in source


def test_module_has_no_runtime_model_or_network_dependency() -> None:
    source = pathlib.Path(L.__file__).read_text(encoding="utf-8")
    for forbidden in ("openai", "anthropic", "requests", "urllib.request", "torch",
                      "transformers", "http.client"):
        assert forbidden not in source


def test_two_explicit_clauses_bind_each_quoted_value_to_its_own_path() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-ledger-multi-") as tmp:
        root = pathlib.Path(tmp)
        first, second = root / "a.txt", root / "b.txt"
        instruction = f'Write "alpha" into {first}; write "beta" into {second}'
        requirements, errors = L.compile_requirements(instruction)
        assert errors == []
        assert [(r["path"], r.get("text")) for r in requirements] == [
            (str(first), "alpha"), (str(second), "beta")
        ]

        ops = [
            {"type": "WRITE_TEXT", "path": str(first), "text": "alpha value"},
            {"type": "WRITE_TEXT", "path": str(second), "text": "beta value"},
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(first), "text": "alpha"},
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(second), "text": "beta"},
        ]
        guest = OSWorldHostGuestOps()
        guest.bind_environment(Environment(root))
        result = guest.run({"ops": ops})
        out = L.decide(_state(instruction, [_row(ops, result)]), _done)
        assert out["actions"] == [{"type": "DONE"}]
        assert out["_policy_receipt"]["requirement_count"] == 2


def test_bounded_respectively_pairs_values_with_paths_in_order() -> None:
    first, second = "/tmp/ledger-respectively-a", "/tmp/ledger-respectively-b"
    instruction = f'Write "alpha" into {first} and "beta" into {second}, respectively'
    requirements, errors = L.compile_requirements(instruction)
    assert errors == []
    assert [(r["path"], r.get("text")) for r in requirements] == [
        (first, "alpha"), (second, "beta")
    ]


def test_conflicting_values_for_one_path_fail_closed() -> None:
    target = "/tmp/ledger-conflict-target"
    instruction = f'Write "alpha" into {target}; write "beta" into {target}'
    requirements, errors = L.compile_requirements(instruction)
    assert any("CONFLICTING_REQUIREMENTS" in error for error in errors)
    out = L.decide(_state(instruction, []), _done)
    assert out["actions"] == [{"type": "WAIT"}]
    assert out["_policy_receipt"]["verified"] is False


def test_one_stale_item_in_a_multi_item_task_blocks_the_whole_done() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-ledger-multi-stale-") as tmp:
        root = pathlib.Path(tmp)
        first, second = root / "a.txt", root / "b.txt"
        instruction = f'Write "alpha" into {first}; write "beta" into {second}'
        ops = [
            {"type": "WRITE_TEXT", "path": str(first), "text": "alpha value"},
            {"type": "WRITE_TEXT", "path": str(second), "text": "beta value"},
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(first), "text": "alpha"},
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(second), "text": "beta"},
        ]
        guest = OSWorldHostGuestOps()
        guest.bind_environment(Environment(root))
        result = guest.run({"ops": ops})
        mutation = {"type": "WRITE_TEXT", "path": str(second), "text": "changed"}
        mutated = guest.run({"ops": [mutation]})
        rows = [_row(ops, result), _row([mutation], mutated)]

        out = L.decide(_state(instruction, rows), _done)
        assert out["actions"][0]["type"] == "STATE_OPS"
        assert out["actions"][0]["ops"] == [
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(second), "text": "beta"}
        ]
        audit = L.audit(_state(instruction, rows), L.compile_requirements(instruction)[0])
        assert [row["verified"] for row in audit["evidence"]] == [True, False]


def _obs() -> dict[str, Any]:
    return {"screenshot": b"ledger-screen", "accessibility_tree": "<root/>"}


def test_adapter_executes_file_assertion_before_it_accepts_done() -> None:
    from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import BrainOSWorldAgent

    with tempfile.TemporaryDirectory(prefix="brain-ledger-adapter-file-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "notes.txt"
        target.write_text("Q4 report", encoding="utf-8")
        instruction = f'Write "Q4" into {target}'
        agent = BrainOSWorldAgent(
            policy_provider=lambda state: L.decide(state, _done),
            policy_id="adapter-ledger-file-test",
            browser_controller=NoBrowser(),
            guest_controller=AdmittedSensorGuestOps(),
        )
        agent.bind_environment(Environment(root))
        agent.reset()

        response, actions = agent.predict(instruction, _obs())
        assert actions == ["WAIT"]
        prior = agent.history[-1]
        assert prior["submitted_operations"] == [
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(target), "text": "Q4"}
        ]
        assert "ASSERT_TEXT_CONTAINS:PASS:" + str(target) in prior["guest_result"]["output"]

        response, actions = agent.predict(instruction, _obs())
        assert actions == ["DONE"]


def test_adapter_executes_dual_directory_assertion_before_it_accepts_done() -> None:
    from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import BrainOSWorldAgent

    with tempfile.TemporaryDirectory(prefix="brain-ledger-adapter-dir-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "reports"
        target.mkdir()
        instruction = f"Create a directory {target}"
        agent = BrainOSWorldAgent(
            policy_provider=lambda state: L.decide(state, _done),
            policy_id="adapter-ledger-dir-test",
            browser_controller=NoBrowser(),
            guest_controller=AdmittedSensorGuestOps(),
        )
        agent.bind_environment(Environment(root))
        agent.reset()

        response, actions = agent.predict(instruction, _obs())
        assert actions == ["WAIT"]
        prior = agent.history[-1]
        assert [op["type"] for op in prior["submitted_operations"]] == [
            "ASSERT_PATH_EXISTS", "ASSERT_SENSOR_REQUEST"
        ]
        output = prior["guest_result"]["output"]
        assert "ASSERT_PATH_EXISTS:PASS:" + str(target) in output
        assert "SENSOR_REQUEST:PASS:" in output
        assert prior["guest_result"]["admission"]["source"] == "fresh_measurement"

        response, actions = agent.predict(instruction, _obs())
        assert actions == ["DONE"]


def test_verified_agent_factory_wires_the_ledger_and_admitted_bridge() -> None:
    from canonical.runtime.osworld_verified_agent_v1 import build_verified_agent
    from canonical.runtime.osworld_verified_policy_v1 import decide as verified_decide
    from canonical.runtime.osworld_v21_brain_agent_adapter_v7 import BrainOSWorldAgentV7
    from canonical.runtime.osworld_v21_host_web_app_ops_v1 import OSWorldHostWebAppOps

    agent = build_verified_agent(policy_id="factory-test")
    assert isinstance(agent, BrainOSWorldAgentV7)
    assert agent.policy_id == "factory-test"
    assert agent.policy_provider is verified_decide
    assert isinstance(agent.guest_controller, AdmittedSensorGuestOps)
    assert isinstance(agent.web_app_controller, OSWorldHostWebAppOps)


class _LocalAppServer:
    """A real HTTP endpoint for product-native read-back tests (no CDP, no model)."""

    def __init__(self) -> None:
        import json as _json
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        messages = [{"id": "m1", "subject": "Q4 report", "body": "initial"}]
        events = [
            {"id": "e1", "title": "Standup", "status": "done"},
            {"id": "e2", "title": "Review", "status": "open"},
        ]

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_: Any) -> None:
                return None

            def _send(self, payload: Any, status: int = 200) -> None:
                body = _json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/api/mail":
                    self._send({"messages": messages})
                elif self.path == "/api/calendar":
                    self._send({"events": list(events)})
                else:
                    self._send({"error": "not found"}, 404)

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                payload = _json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/api/mail/send":
                    messages.append({
                        "id": "m" + str(len(messages) + 1),
                        "subject": str(payload.get("subject") or ""),
                        "body": str(payload.get("body") or ""),
                        "to": str(payload.get("to") or ""),
                    })
                    self._send({"ok": True})
                elif self.path == "/api/calendar/actions":
                    events.append({
                        "id": "e" + str(len(events) + 1),
                        "title": str((payload.get("request") or {}).get("title") or ""),
                        "status": "open",
                    })
                    self._send({"ok": True})
                else:
                    self._send({"error": "not found"}, 404)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class _LocalWebAppOps(OSWorldHostWebAppOps):
    """Reuse the real registry validator and result packaging over local HTTP."""

    def __init__(self, base_url: str) -> None:
        import json as _json
        import urllib.request
        super().__init__(remote_debugging_url=base_url)
        self.base_url = base_url
        self._urlopen = urllib.request.urlopen
        self._Request = urllib.request.Request
        self._json = _json

    def bind_environment(self, environment: Any) -> None:
        self.remote_debugging_url = self.base_url

    def _connect(self) -> tuple[Any, Any]:
        outer = self

        class Response:
            def __init__(self, raw: bytes, status: int) -> None:
                self.raw = raw
                self.status = status

            @property
            def ok(self) -> bool:
                return 200 <= self.status < 300

            def text(self) -> str:
                return self.raw.decode("utf-8")

            def json(self) -> Any:
                return outer._json.loads(self.text())

        class Request:
            def fetch(self, url: str, *, method: str, timeout: int,
                      data: Any = None, headers: Any = None) -> Response:
                if isinstance(data, (dict, list)):
                    data = outer._json.dumps(data).encode("utf-8")
                elif isinstance(data, str):
                    data = data.encode("utf-8")
                request = outer._Request(url, data=data, method=method,
                                         headers=headers or {})
                with outer._urlopen(request, timeout=timeout) as reply:
                    return Response(reply.read(), int(reply.status))

        class Context:
            request = Request()

            def __init__(self) -> None:
                self.pages = [type("Page", (), {"url": outer.base_url + "/mailhub/calendar"})()]

        class Browser:
            def __init__(self) -> None:
                self.contexts = [Context()]

        class Playwright:
            def stop(self) -> None:
                return None

        return Playwright(), Browser()


def _web_app_row(payload: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "screenshot_sha256": "a" * 64,
        "action_fingerprint": "x",
        "actions": ["WAIT"],
        "response": "web app op",
        "submitted_web_app_operation": dict(payload),
        "web_app_result": dict(result),
    }


def test_app_field_value_is_compiled_only_from_explicit_evidence() -> None:
    instruction = 'Send an email in Mailhub with subject "Q4 report"'
    requirements, errors = L.compile_requirements(instruction)
    assert errors == []
    assert len(requirements) == 1
    assert requirements[0]["kind"] == "APP_STATE_FIELD"
    assert requirements[0]["app"] == "mailhub"
    assert requirements[0]["field"] == "name"
    assert requirements[0]["value"] == "Q4 report"
    assert requirements[0]["op"] == "observe_mail"


def test_app_without_explicit_field_value_fails_closed() -> None:
    requirements, errors = L.compile_requirements("Check something in Mailhub")
    assert "APP_GOAL_NOT_MACHINE_CHECKABLE" in errors
    out = L.decide(_state("Check something in Mailhub", []), _done)
    assert out["actions"] == [{"type": "WAIT"}]


def test_real_http_readback_with_exact_field_value_allows_done() -> None:
    server = _LocalAppServer()
    try:
        ops = _LocalWebAppOps(server.url)
        observe = {"app": "mailhub", "operation": "observe_mail", "args": {}}
        result = ops.run(observe)
        assert result["ok"] is True
        instruction = 'Send an email in Mailhub with subject "Q4 report"'
        out = L.decide(_state(instruction, [_web_app_row(observe, result)]), _done)
        assert out["actions"] == [{"type": "DONE"}]
        assert out["_policy_receipt"]["verified"] is True
    finally:
        server.close()


def test_wrong_value_readback_does_not_allow_done() -> None:
    server = _LocalAppServer()
    try:
        ops = _LocalWebAppOps(server.url)
        observe = {"app": "mailhub", "operation": "observe_mail", "args": {}}
        result = ops.run(observe)
        instruction = 'Send an email in Mailhub with subject "Missing report"'
        out = L.decide(_state(instruction, [_web_app_row(observe, result)]), _done)
        assert out["actions"][0]["type"] == "WEB_APP_OP"
        assert out["_policy_receipt"]["verified"] is False
    finally:
        server.close()


def test_later_web_app_mutation_invalidates_readback() -> None:
    server = _LocalAppServer()
    try:
        ops = _LocalWebAppOps(server.url)
        observe = {"app": "mailhub", "operation": "observe_mail", "args": {}}
        observed = ops.run(observe)
        mutation = {
            "app": "mailhub", "operation": "send",
            "args": {"to": "x@example.com", "subject": "Q4 report", "body": "changed"},
        }
        mutated = ops.run(mutation)
        instruction = 'Send an email in Mailhub with subject "Q4 report"'
        rows = [_web_app_row(observe, observed), _web_app_row(mutation, mutated)]
        out = L.decide(_state(instruction, rows), _done)
        assert out["actions"][0]["type"] == "WEB_APP_OP"
        audit = L.audit(_state(instruction, rows), L.compile_requirements(instruction)[0])
        assert audit["evidence"][0]["invalidated_by_rows"] == [1]
    finally:
        server.close()


def test_adapter_reaches_done_only_after_real_http_readback() -> None:
    from canonical.runtime.osworld_v21_brain_agent_adapter_v7 import BrainOSWorldAgentV7

    server = _LocalAppServer()
    try:
        ops = _LocalWebAppOps(server.url)
        agent = BrainOSWorldAgentV7(
            policy_provider=lambda state: L.decide(state, _done),
            policy_id="web-readback-adapter-test",
            browser_controller=NoBrowser(),
            guest_controller=AdmittedSensorGuestOps(),
            web_app_controller=ops,
        )
        agent.reset()
        instruction = 'Send an email in Mailhub with subject "Q4 report"'

        response, actions = agent.predict(instruction, _obs())
        assert actions == ["WAIT"]
        prior = agent.history[-1]
        assert prior["submitted_web_app_operation"]["app"] == "mailhub"
        assert prior["submitted_web_app_operation"]["operation"] == "observe_mail"
        assert prior["web_app_result"]["ok"] is True

        response, actions = agent.predict(instruction, _obs())
        assert actions == ["DONE"]
        assert agent.history[-1]["completion_evidence"]["kind"] == "WEB_APP_OP_SUCCESS_RECEIPT"
    finally:
        server.close()


def test_adapter_does_not_done_when_readback_value_is_absent() -> None:
    from canonical.runtime.osworld_v21_brain_agent_adapter_v7 import BrainOSWorldAgentV7

    server = _LocalAppServer()
    try:
        ops = _LocalWebAppOps(server.url)
        agent = BrainOSWorldAgentV7(
            policy_provider=lambda state: L.decide(state, _done),
            policy_id="web-readback-negative-test",
            browser_controller=NoBrowser(),
            guest_controller=AdmittedSensorGuestOps(),
            web_app_controller=ops,
        )
        agent.reset()
        instruction = 'Send an email in Mailhub with subject "Absent report"'
        for _ in range(2):
            response, actions = agent.predict(instruction, _obs())
            assert actions == ["WAIT"]
        assert all(row.get("actions") == ["WAIT"] for row in agent.history)
    finally:
        server.close()


def test_relational_goal_requires_product_readback_before_any_file_assertion() -> None:
    instruction = (
        'Check Calendar; then create "/home/oai/share/count.txt" containing '
        'the count of events from Calendar'
    )
    requirements, errors = L.compile_requirements(instruction)
    assert errors == ["RELATIONAL_REFERENCE_UNRESOLVED"]
    assert requirements == [{
        "kind": "APP_OBSERVATION", "app": "calendar_web",
        "op": "observe_calendar", "source_hint": "calendar_web", "ops": [],
    }]
    out = L.decide(_state(instruction, []), _done)
    assert out["actions"][0] == {
        "type": "WEB_APP_OP", "app": "calendar_web",
        "operation": "observe_calendar", "args": {},
    }
    assert out["_policy_receipt"]["verified"] is False


def test_relational_count_is_bound_only_from_real_http_receipt_then_guest_pass() -> None:
    server = _LocalAppServer()
    try:
        ops = _LocalWebAppOps(server.url)
        observe = {"app": "calendar_web", "operation": "observe_calendar", "args": {}}
        result = ops.run(observe)
        assert result["ok"] is True
        assert result["result"] == {"events": [
            {"id": "e1", "title": "Standup", "status": "done"},
            {"id": "e2", "title": "Review", "status": "open"},
        ]}
        with tempfile.TemporaryDirectory(prefix="brain-relational-ledger-") as tmp:
            target = pathlib.Path(tmp) / "count.txt"
            instruction = (
                f'Check Calendar; then create "{target}" containing '
                'the count of events from Calendar'
            )
            history = [_web_app_row(observe, result)]
            requirements, errors = L.compile_requirements(instruction, history)
            assert errors == []
            derived = [r for r in requirements if r.get("derived_from")]
            assert len(derived) == 1
            assert derived[0]["text"] == "2"
            assert derived[0]["derived_provenance"] == [{
                "row_index": 0, "source": "web_app_result", "path": ["events"],
            }]
            assert L.assertion_ops(derived[0]) == [
                {"type": "ASSERT_TEXT_CONTAINS", "path": str(target), "text": "2"},
                {"type": "ASSERT_TEXT_EQUALS", "path": str(target), "text": "2"},
            ]

            withheld = L.decide(_state(instruction, history), _done)
            assert withheld["actions"][0]["type"] == "STATE_OPS"

            write_ops = [
                {"type": "WRITE_TEXT", "path": str(target), "text": "2"},
                *L.assertion_ops(derived[0]),
            ]
            guest = OSWorldHostGuestOps()
            guest.bind_environment(Environment(pathlib.Path(tmp)))
            guest_result = guest.run({"ops": write_ops})
            assert "ASSERT_TEXT_EQUALS:PASS:" + str(target) in guest_result["output"]
            history.append(_row(write_ops, guest_result))
            out = L.decide(_state(instruction, history), _done)
            assert out["actions"] == [{"type": "DONE"}]
            evidence = out["_policy_receipt"]
            assert evidence["verified"] is True
            assert evidence["errors"] == []
    finally:
        server.close()


def test_relational_done_is_blocked_when_file_holds_a_different_count() -> None:
    server = _LocalAppServer()
    try:
        ops = _LocalWebAppOps(server.url)
        observe = {"app": "calendar_web", "operation": "observe_calendar", "args": {}}
        result = ops.run(observe)
        with tempfile.TemporaryDirectory(prefix="brain-relational-negative-") as tmp:
            target = pathlib.Path(tmp) / "count.txt"
            instruction = (
                f'Check Calendar; then create "{target}" containing '
                'the count of events from Calendar'
            )
            history = [_web_app_row(observe, result)]
            requirements, _ = L.compile_requirements(instruction, history)
            derived = [r for r in requirements if r.get("derived_from")][0]
            wrong_ops = [{"type": "WRITE_TEXT", "path": str(target), "text": "3"}]
            guest = OSWorldHostGuestOps()
            guest.bind_environment(Environment(pathlib.Path(tmp)))
            wrong = guest.run({"ops": wrong_ops})
            assert wrong["ok"] is True
            history.append(_row(wrong_ops, wrong))
            out = L.decide(_state(instruction, history), _done)
            assert out["actions"][0]["type"] == "STATE_OPS"
            assert out["_policy_receipt"]["verified"] is False
    finally:
        server.close()


def test_later_calendar_mutation_invalidates_receipt_derived_file_evidence() -> None:
    server = _LocalAppServer()
    try:
        ops = _LocalWebAppOps(server.url)
        observe = {"app": "calendar_web", "operation": "observe_calendar", "args": {}}
        observed = ops.run(observe)
        mutation = {
            "app": "calendar_web", "operation": "action",
            "args": {"request": {"kind": "add_event", "title": "Extra"}},
        }
        mutated = ops.run(mutation)
        with tempfile.TemporaryDirectory(prefix="brain-relational-stale-") as tmp:
            target = pathlib.Path(tmp) / "count.txt"
            instruction = (
                f'Check Calendar; then create "{target}" containing '
                'the count of events from Calendar'
            )
            history = [_web_app_row(observe, observed)]
            requirements, _ = L.compile_requirements(instruction, history)
            derived = [r for r in requirements if r.get("derived_from")][0]
            write_ops = [
                {"type": "WRITE_TEXT", "path": str(target), "text": "2"},
                *L.assertion_ops(derived),
            ]
            guest = OSWorldHostGuestOps()
            guest.bind_environment(Environment(pathlib.Path(tmp)))
            passed = guest.run({"ops": write_ops})
            assert "ASSERT_TEXT_EQUALS:PASS:" + str(target) in passed["output"]
            history.append(_row(write_ops, passed))
            assert L.decide(_state(instruction, history), _done)["actions"] == [{"type": "DONE"}]

            # A later product mutation after the same readback row invalidates the
            # derived value even though the guest assertion receipt is unchanged.
            stale = _state(instruction, history + [_web_app_row(mutation, mutated)])
            audit_result = L.audit(stale, L.compile_requirements(instruction, history)[0])
            assert audit_result["verified"] is False
            assert audit_result["evidence"][0]["invalidated_by_rows"] == [2]
            assert L.decide(stale, _done)["actions"][0]["type"] == "WEB_APP_OP"
    finally:
        server.close()


def test_adapter_reaches_done_only_after_relational_readback_and_guest_write() -> None:
    from canonical.runtime.osworld_v21_brain_agent_adapter_v7 import BrainOSWorldAgentV7

    server = _LocalAppServer()
    try:
        ops = _LocalWebAppOps(server.url)
        with tempfile.TemporaryDirectory(prefix="brain-relational-adapter-") as tmp:
            target = pathlib.Path(tmp) / "count.txt"
            instruction = (
                f'Check Calendar; then create "{target}" containing '
                'the count of events from Calendar'
            )

            def base_policy(state: Mapping[str, Any]) -> dict[str, Any]:
                requirements, _ = L.compile_requirements(
                    state.get("instruction"), state.get("history") or []
                )
                derived = [r for r in requirements if r.get("derived_from")]
                if derived:
                    audit_result = L.audit(state, requirements)
                    if not all(e["verified"] for e in audit_result["evidence"]):
                        write_ops = [
                            {"type": "WRITE_TEXT", "path": str(target),
                             "text": str(derived[0]["text"])},
                            *L.assertion_ops(derived[0]),
                        ]
                        return {"response": "write receipt-derived value",
                                "actions": [{"type": "STATE_OPS", "ops": write_ops}]}
                return {"response": "finish", "actions": [{"type": "DONE"}]}

            guest = OSWorldHostGuestOps()
            guest.bind_environment(Environment(pathlib.Path(tmp)))
            agent = BrainOSWorldAgentV7(
                policy_provider=lambda state: L.decide(state, base_policy),
                policy_id="relational-ledger-adapter-test",
                browser_controller=NoBrowser(),
                guest_controller=guest,
                web_app_controller=ops,
            )
            agent.reset()
            response, actions = agent.predict(instruction, _obs())
            assert actions == ["WAIT"]
            assert agent.history[-1]["submitted_web_app_operation"] == {
                "app": "calendar_web", "operation": "observe_calendar", "args": {},
            }
            assert agent.history[-1]["web_app_result"]["ok"] is True

            response, actions = agent.predict(instruction, _obs())
            assert actions == ["WAIT"]
            assert agent.history[-1]["guest_result"]["ok"] is True
            assert "ASSERT_TEXT_EQUALS:PASS:" + str(target) in (
                agent.history[-1]["guest_result"]["output"]
            )

            response, actions = agent.predict(instruction, _obs())
            assert actions == ["DONE"]
            assert agent.history[-1]["policy_receipt"]["verified"] is True
    finally:
        server.close()
