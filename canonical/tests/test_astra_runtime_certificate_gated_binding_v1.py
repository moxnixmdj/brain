import hashlib
import json

import pytest

from canonical.runtime import astra_runtime
from canonical.runtime.certificate_gated_route_execution_binding_v1 import (
    operative_step_git_blob_sha,
)

def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def _bound_step(tmp_path):
    admission = tmp_path / "admission.json"
    adequacy = tmp_path / "adequacy.json"
    admission.write_text('{"admission":true}\n')
    adequacy.write_text('{"adequacy":true}\n')
    mission = {
        "certificate_gated_routing_required": True,
        "certificate_gated_context": {"scope": "integration", "case": "one"},
    }
    step = {
        "id": "route-bound-shell",
        "adapter": "shell",
        "command": "printf ok",
        "verify": {"type": "returncode_zero"},
    }
    ctx = "sha256:" + hashlib.sha256(
        json.dumps(
            mission["certificate_gated_context"],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    step["certificate_gated_route"] = {
        "route_id": "route-one",
        "admission_certificate_path": "admission.json",
        "adequacy_certificate_path": "adequacy.json",
        "receipts": [{
            "context_digest": ctx,
            "cell_id": "cell-one",
            "route_id": "route-one",
            "route_blob_sha": operative_step_git_blob_sha(step),
            "adequacy_certificate_blob_sha": _git_blob(adequacy.read_bytes()),
            "admission_certificate_blob_sha": _git_blob(admission.read_bytes()),
            "admitted": True,
        }],
    }
    return mission, step

def test_execute_step_is_actually_gated_before_shell_execution(tmp_path, monkeypatch):
    mission, step = _bound_step(tmp_path)
    monkeypatch.setattr(astra_runtime, "ROOT", tmp_path)
    called = []
    monkeypatch.setattr(
        astra_runtime,
        "run_shell",
        lambda step, prior: called.append(step["id"]) or {"returncode": 0, "stdout": "ok"},
    )
    out = astra_runtime.execute_step(step, mission=mission)
    assert called == ["route-bound-shell"]
    assert out["certificate_gated_route_binding"]["route_id"] == "route-one"
    assert out["certificate_gated_route_binding"]["admitted"] is True

def test_execute_step_blocks_drift_before_shell_execution(tmp_path, monkeypatch):
    mission, step = _bound_step(tmp_path)
    step["command"] = "printf drifted"
    monkeypatch.setattr(astra_runtime, "ROOT", tmp_path)
    called = []
    monkeypatch.setattr(
        astra_runtime,
        "run_shell",
        lambda step, prior: called.append(step["id"]) or {"returncode": 0},
    )
    with pytest.raises(astra_runtime.Blocker, match="OPERATIVE_STEP_BLOB_MISMATCH"):
        astra_runtime.execute_step(step, mission=mission)
    assert called == []
