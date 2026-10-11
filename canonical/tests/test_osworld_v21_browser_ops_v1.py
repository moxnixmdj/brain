from canonical.runtime.osworld_v21_browser_ops_v1 import BrowserOpsError, compile_browser_op
from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import compile_actions


def test_open_url_compiles_to_fixed_cdp_bridge():
    src = compile_browser_op({"type": "BROWSER_OPEN_URL", "url": "https://example.com/a"})
    assert "127.0.0.1:1337/json/list" in src
    assert "Runtime.evaluate" in src
    assert "https://example.com/a" in src
    assert "websockets.connect" in src


def test_click_text_is_data_not_raw_javascript():
    malicious = "x'); window.__pwned=1; ('"
    src = compile_browser_op({"type": "BROWSER_CLICK_TEXT", "text": malicious})
    assert "window.__pwned=1" in src
    # It must occur only inside the JSON-quoted target payload, never as standalone code.
    assert "const q=\"x'); window.__pwned=1; ('\".toLowerCase()" in src


def test_disallowed_url_scheme_fails_closed():
    try:
        compile_browser_op({"type": "BROWSER_OPEN_URL", "url": "file:///etc/passwd"})
    except BrowserOpsError as exc:
        assert str(exc) == "URL_SCHEME_NOT_ALLOWED"
    else:
        raise AssertionError("expected URL scheme rejection")


def test_raw_javascript_action_is_not_supported():
    try:
        compile_browser_op({"type": "BROWSER_JAVASCRIPT", "javascript": "document.body.remove()"})
    except BrowserOpsError as exc:
        assert str(exc).startswith("BROWSER_OP_UNSUPPORTED")
    else:
        raise AssertionError("expected raw javascript rejection")


def test_adapter_does_not_compile_host_browser_op_as_guest_pyautogui():
    try:
        compile_actions({
            "actions": [{"type": "BROWSER_FILL", "label": "Email", "value": "a@example.com"}]
        })
    except Exception as exc:
        assert "HOST_OPERATION_MUST_BE_SINGLETON_RUNTIME_ACTION" in str(exc)
    else:
        raise AssertionError("expected host browser operation to stay outside guest action compiler")
