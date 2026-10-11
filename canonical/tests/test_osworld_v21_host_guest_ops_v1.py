from canonical.runtime.osworld_v21_host_guest_ops_v1 import GuestOpsError, OSWorldHostGuestOps


class Controller:
    def __init__(self, result=None, raises=None):
        self.result = result
        self.raises = raises
        self.programs = []

    def execute_python_command(self, program):
        self.programs.append(program)
        if self.raises is not None:
            raise self.raises
        return self.result


class Env:
    def __init__(self, controller):
        self.controller = controller


def test_successful_state_operation_returns_receipt():
    ctl = Controller({"status": "success", "output": "ASSERT_TEXT_EQUALS:PASS:/home/oai/share/a.txt", "error": None})
    bridge = OSWorldHostGuestOps()
    bridge.bind_environment(Env(ctl))
    out = bridge.run({
        "ops": [{"type": "ASSERT_TEXT_EQUALS", "path": "/home/oai/share/a.txt", "text": "alpha"}]
    })
    assert out["ok"] is True
    assert "ASSERT_TEXT_EQUALS:PASS" in out["output"]
    assert "TEXT_MISMATCH" in ctl.programs[0]


def test_missing_python_controller_rejected():
    class Bad:
        controller = object()
    bridge = OSWorldHostGuestOps()
    try:
        bridge.bind_environment(Bad())
    except GuestOpsError as exc:
        assert str(exc) == "DESKTOP_ENV_PYTHON_CONTROLLER_MISSING"
    else:
        raise AssertionError("expected rejection")


def test_none_receipt_rejected():
    bridge = OSWorldHostGuestOps()
    bridge.bind_environment(Env(Controller(None)))
    try:
        bridge.run({"ops": [{"type": "ASSERT_PATH_EXISTS", "path": "/home/oai/share/a.txt"}]})
    except GuestOpsError as exc:
        assert str(exc) == "GUEST_STATE_EXECUTION_NO_RECEIPT"
    else:
        raise AssertionError("expected rejection")


def test_guest_error_receipt_rejected():
    bridge = OSWorldHostGuestOps()
    bridge.bind_environment(Env(Controller({"status": "error", "error": "boom", "output": ""})))
    try:
        bridge.run({"ops": [{"type": "ASSERT_PATH_EXISTS", "path": "/home/oai/share/a.txt"}]})
    except GuestOpsError as exc:
        assert str(exc) == "GUEST_STATE_EXECUTION_FAILED:boom"
    else:
        raise AssertionError("expected rejection")
