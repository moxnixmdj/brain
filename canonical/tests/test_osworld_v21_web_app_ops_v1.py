from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime.osworld_v21_brain_agent_adapter_v3 import BrainOSWorldAgentV3
from canonical.runtime.osworld_v21_host_web_app_ops_v1 import (
    OSWorldHostWebAppOps,
    WebAppOpsError,
)


class FakeResponse:
    def __init__(self, payload, *, ok=True, status=200):
        self.payload = payload
        self.ok = ok
        self.status = status
    def text(self):
        return json.dumps(self.payload)
    def json(self):
        return self.payload


class FakeRequest:
    def __init__(self):
        self.calls = []
    def fetch(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse({"ok": True, "echo": kwargs.get("data")})


class FakePage:
    def __init__(self, url):
        self.url = url


class FakeContext:
    def __init__(self, pages):
        self.pages = pages
        self.request = FakeRequest()


class FakeBrowser:
    def __init__(self, pages):
        self.contexts = [FakeContext(pages)]


class FakePW:
    def __init__(self):
        self.stopped = False
    def stop(self):
        self.stopped = True


def controller_with_pages(*urls):
    ctl = OSWorldHostWebAppOps()
    ctl.remote_debugging_url = "http://vm:9222"
    pw = FakePW()
    browser = FakeBrowser([FakePage(x) for x in urls])
    ctl._connect = lambda: (pw, browser)
    return ctl, pw, browser


def test_observe_mail_uses_product_projection_and_same_context():
    ctl, pw, browser = controller_with_pages("http://mailhub.local/inbox")
    out = ctl.run({"app": "mailhub", "operation": "observe_mail", "args": {}})
    assert out["ok"] is True
    assert out["path"] == "/api/mail"
    assert out["method"] == "GET"
    assert browser.contexts[0].request.calls == [
        ("http://mailhub.local/api/mail", {"method": "GET", "timeout": 30000})
    ]
    assert pw.stopped is True


def test_mail_send_serializes_only_allowed_product_fields():
    ctl, _, browser = controller_with_pages(
        "http://other.local/", "http://mailhub.local/inbox"
    )
    out = ctl.run({
        "app": "mailhub",
        "operation": "send",
        "args": {"to": "a@example.com", "subject": "Hi", "body": "Body"},
    })
    assert out["path"] == "/api/mail/send"
    call = browser.contexts[0].request.calls[0]
    assert call[0] == "http://mailhub.local/api/mail/send"
    assert call[1]["method"] == "POST"
    assert call[1]["data"] == {"to": "a@example.com", "subject": "Hi", "body": "Body"}


def test_unknown_or_control_plane_fields_fail_closed():
    ctl, _, _ = controller_with_pages("http://mailhub.local/inbox")
    with pytest.raises(WebAppOpsError, match="WEB_APP_ARGUMENT_NOT_ALLOWED"):
        ctl.run({
            "app": "mailhub",
            "operation": "send",
            "args": {
                "to": "a@example.com",
                "subject": "Hi",
                "body": "Body",
                "state": {"evaluator_marker": False},
            },
        })
    with pytest.raises(WebAppOpsError, match="WEB_APP_OPERATION_NOT_ALLOWED"):
        ctl.run({"app": "mailhub", "operation": "patch_state", "args": {}})


def test_protected_benchmark_paths_fail_closed_even_as_data():
    ctl, _, _ = controller_with_pages("http://mailhub.local/inbox")
    with pytest.raises(WebAppOpsError, match="WEB_APP_PROTECTED_PATH"):
        ctl.run({
            "app": "mailhub",
            "operation": "send",
            "args": {
                "to": "a@example.com",
                "subject": "x",
                "body": "x",
                "attachments": [{"path": "/evaluation_examples/secret"}],
            },
        })


def test_wrong_tab_identity_fails_closed():
    ctl, _, _ = controller_with_pages("http://teamchat.local/general")
    with pytest.raises(WebAppOpsError, match="WEB_APP_PAGE_NOT_FOUND"):
        ctl.run({"app": "mailhub", "operation": "observe_mail", "args": {}})


def test_registry_contains_no_control_plane_state_operation():
    path = Path(__file__).resolve().parents[1] / "runtime" / "osworld_v21_web_app_ops_registry_v1.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    paths = [
        op["path"]
        for app in raw["apps"].values()
        for op in app["operations"].values()
    ]
    assert "/api/state" not in paths
    assert not any(path.startswith("/api/state/") for path in paths)
    assert "/api/state" in raw["forbidden_surfaces"]
    assert "arbitrary_url" in raw["forbidden_surfaces"]


def test_v3_adapter_records_web_app_receipt_and_returns_wait():
    class FakeWeb:
        def run(self, payload):
            return {
                "type": "WEB_APP_OP",
                "ok": True,
                "app": payload["app"],
                "operation": payload["operation"],
                "result": {"mail": {"emails": []}},
            }

    agent = BrainOSWorldAgentV3(
        lambda _state: {
            "response": "inspect mail",
            "actions": [
                {"type": "WEB_APP_OP", "app": "mailhub", "operation": "observe_mail", "args": {}}
            ],
        },
        policy_id="web-app-test",
        web_app_controller=FakeWeb(),
    )
    response, actions = agent.predict("check mail", {"screenshot": b"img"})
    assert response == "inspect mail"
    assert actions == ["WAIT"]
    assert agent.history[-1]["web_app_result"]["ok"] is True
    assert agent.history[-1]["submitted_web_app_operation"]["app"] == "mailhub"
