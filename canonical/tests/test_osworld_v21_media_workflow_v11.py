from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import canonical.runtime.osworld_v21_host_media_ops_v1 as media_mod
from canonical.runtime.osworld_v21_brain_agent_adapter_v5 import BrainOSWorldAgentV5
from canonical.runtime.osworld_v21_brain_subject_v11 import SUBJECT_ID, build_subject
from canonical.runtime.osworld_v21_host_media_ops_v1 import MediaOpsError, OSWorldHostMediaOps
from canonical.runtime.osworld_v21_media_policy_overlay_v1 import route_media
from canonical.runtime.osworld_v21_workflow_policy_v7 import decide


def state(instruction, history=None):
    return {
        "instruction": instruction,
        "history": list(history or []),
        "a11y_tree": None,
        "ocr": None,
        "screenshot_sha256": "s0",
    }


def action(out):
    assert len(out["actions"]) == 1
    return out["actions"][0]


def media_receipt(out, result):
    a = action(out)
    return {
        "screenshot_sha256": "s0",
        "actions": ["WAIT"],
        "policy_receipt": out["_policy_receipt"],
        "submitted_media_operation": {
            "operation": a["operation"],
            "args": a.get("args", {}),
        },
        "media_result": {
            "type": "MEDIA_OP",
            "ok": result.get("ok") is True,
            "operation": a["operation"],
            "result": dict(result),
        },
    }


def test_media_policy_parses_trim_independent_of_digits_in_filenames():
    out = route_media(state(
        "Trim /home/oai/share/video2026.mp4 from 12.5 seconds to 20 seconds "
        "and save to /home/oai/share/out9.mp4"
    ))
    assert action(out) == {
        "type": "MEDIA_OP",
        "operation": "TRIM",
        "args": {
            "input": "/home/oai/share/video2026.mp4",
            "output": "/home/oai/share/out9.mp4",
            "start_s": 12.5,
            "end_s": 20.0,
        },
    }


def test_media_policy_routes_crop_and_volume():
    out = route_media(state(
        "Crop /home/oai/share/in.png to 640x480 at 10,20 and save to /home/oai/share/out.png"
    ))
    assert action(out)["operation"] == "CROP"
    assert action(out)["args"]["x"] == 10
    assert action(out)["args"]["y"] == 20

    out = route_media(state(
        "Set volume of /home/oai/share/in.mp4 to 150% and save to /home/oai/share/out.mp4"
    ))
    assert action(out)["operation"] == "SET_VOLUME"
    assert action(out)["args"]["factor"] == 1.5


class FakePythonController:
    def __init__(self):
        self.files = {"/home/oai/share/in.mp4": b"INPUT"}

    def get_file(self, path):
        return self.files.get(path)


class FakeSetupController:
    def __init__(self, controller):
        self.controller = controller
        self.uploads = []

    def download(self, files):
        for row in files:
            self.uploads.append(dict(row))
            self.controller.files[row["path"]] = Path(row["url"]).read_bytes()


class FakeEnv:
    def __init__(self):
        self.controller = FakePythonController()
        self.setup_controller = FakeSetupController(self.controller)


def test_host_media_roundtrip_requires_upload_readback(monkeypatch):
    env = FakeEnv()
    ops = OSWorldHostMediaOps()
    ops.bind_environment(env)

    monkeypatch.setattr(media_mod.shutil, "which", lambda name: "/fake/" + name)

    def fake_run(cmd, capture_output, text, timeout, check):
        if "ffprobe" in cmd[0]:
            return SimpleNamespace(
                returncode=0, stderr="",
                stdout=json.dumps({"streams": [], "format": {"duration": "1.0"}}),
            )
        Path(cmd[-1]).write_bytes(b"OUTPUT")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(media_mod.subprocess, "run", fake_run)
    out = ops.run({
        "operation": "RESIZE",
        "args": {
            "input": "/home/oai/share/in.mp4",
            "output": "/home/oai/share/out.mp4",
            "width": 640,
            "height": 360,
        },
    })
    assert out["ok"] is True
    assert env.controller.files["/home/oai/share/out.mp4"] == b"OUTPUT"
    assert len(env.setup_controller.uploads) == 1
    assert out["result"]["bytes"] == len(b"OUTPUT")


def test_media_paths_fail_closed():
    ops = OSWorldHostMediaOps()
    try:
        ops.run({"operation": "PROBE", "args": {"input": "/tmp/x.mp4"}})
    except MediaOpsError as exc:
        assert str(exc) == "MEDIA_PATH_OUTSIDE_SAFE_ROOT"
    else:
        raise AssertionError("expected path rejection")


def test_trim_then_probe_workflow_is_receipt_gated():
    instruction = (
        "Trim /home/oai/share/in.mp4 from 2 to 5 seconds to /home/oai/share/out.mp4; "
        "then inspect metadata of /home/oai/share/out.mp4"
    )
    first = decide(state(instruction))
    assert action(first)["operation"] == "TRIM"
    h1 = media_receipt(first, {
        "ok": True,
        "input": "/home/oai/share/in.mp4",
        "output": "/home/oai/share/out.mp4",
        "bytes": 10,
        "sha256": "a",
        "probe": {},
    })

    second = decide(state(instruction, [h1]))
    assert action(second) == {
        "type": "MEDIA_OP",
        "operation": "PROBE",
        "args": {"input": "/home/oai/share/out.mp4"},
    }
    h2 = media_receipt(second, {
        "ok": True,
        "input": "/home/oai/share/out.mp4",
        "bytes": 10,
        "sha256": "a",
        "probe": {"format": {"duration": "3.0"}},
    })
    third = decide(state(instruction, [h1, h2]))
    assert third["actions"] == [{"type": "DONE"}]


def test_failed_media_transform_never_completes():
    instruction = (
        "Resize /home/oai/share/in.mp4 to 640x360 and save to /home/oai/share/out.mp4"
    )
    first = decide(state(instruction))
    failed = media_receipt(first, {"ok": False})
    second = decide(state(instruction, [failed]))
    assert action(second)["type"] == "MEDIA_OP"
    assert action(second)["operation"] == "RESIZE"


class FakeMedia:
    def run(self, payload):
        return {
            "type": "MEDIA_OP",
            "ok": True,
            "operation": payload["operation"],
            "result": {"ok": True},
        }


def test_adapter_records_media_receipt_and_receipted_done():
    calls = {"n": 0}

    def policy(_state):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "response": "probe",
                "actions": [{
                    "type": "MEDIA_OP",
                    "operation": "PROBE",
                    "args": {"input": "/home/oai/share/in.mp4"},
                }],
            }
        return {"response": "done", "actions": [{"type": "DONE"}]}

    agent = BrainOSWorldAgentV5(
        policy, policy_id="test-v11", media_controller=FakeMedia()
    )
    _, actions = agent.predict(
        "Inspect /home/oai/share/in.mp4",
        {"screenshot": b"one", "accessibility_tree": None},
    )
    assert actions == ["WAIT"]
    assert agent.history[-1]["media_result"]["ok"] is True

    _, actions = agent.predict(
        "Inspect /home/oai/share/in.mp4",
        {"screenshot": b"two", "accessibility_tree": None},
    )
    assert actions == ["DONE"]
    assert agent.history[-1]["completion_evidence"]["kind"] == "MEDIA_OP_VERIFIED_RECEIPT"


def test_v11_subject_remains_model_independent():
    subject = build_subject()
    assert subject.policy_id == SUBJECT_ID
    import canonical.runtime.osworld_v21_host_media_ops_v1 as h
    import canonical.runtime.osworld_v21_media_policy_overlay_v1 as p
    import canonical.runtime.osworld_v21_workflow_policy_v7 as w
    import canonical.runtime.osworld_v21_brain_subject_v11 as s
    source = "\n".join(inspect.getsource(x).casefold() for x in (h, p, w, s))
    for forbidden in ("openai", "anthropic", "gemini", "qwen", "reference_trajectory", "task_001"):
        assert forbidden not in source
