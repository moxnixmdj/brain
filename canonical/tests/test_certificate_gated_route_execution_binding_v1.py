import hashlib
import json

import pytest

from canonical.runtime.certificate_gated_route_execution_binding_v1 import (
    RouteExecutionBindingError,
    authorize_step,
    operative_step_git_blob_sha,
)

def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def _fixture(tmp_path):
    (tmp_path / "admission.json").write_text('{"ok":"admission"}\n')
    (tmp_path / "adequacy.json").write_text('{"ok":"adequacy"}\n')
    mission = {
        "certificate_gated_routing_required": True,
        "certificate_gated_context": {"family": "finance", "case": "x"},
    }
    step = {
        "id": "s1",
        "adapter": "shell",
        "command": "printf ok",
        "verify": {"type": "returncode_zero"},
    }
    context_digest = "sha256:" + hashlib.sha256(
        json.dumps(
            mission["certificate_gated_context"],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    step["certificate_gated_route"] = {
        "route_id": "r1",
        "admission_certificate_path": "admission.json",
        "adequacy_certificate_path": "adequacy.json",
        "receipts": [{
            "context_digest": context_digest,
            "cell_id": "c1",
            "route_id": "r1",
            "route_blob_sha": operative_step_git_blob_sha(step),
            "admission_certificate_blob_sha": _git_blob((tmp_path / "admission.json").read_bytes()),
            "adequacy_certificate_blob_sha": _git_blob((tmp_path / "adequacy.json").read_bytes()),
            "admitted": True,
        }],
    }
    return mission, step

def test_exact_bound_step_passes(tmp_path):
    mission, step = _fixture(tmp_path)
    out = authorize_step(root=tmp_path, mission=mission, step=step)
    assert out["admitted"] is True
    assert out["route_id"] == "r1"

def test_command_drift_fails(tmp_path):
    mission, step = _fixture(tmp_path)
    step["command"] = "printf changed"
    with pytest.raises(RouteExecutionBindingError, match="OPERATIVE_STEP_BLOB_MISMATCH"):
        authorize_step(root=tmp_path, mission=mission, step=step)

def test_context_drift_fails(tmp_path):
    mission, step = _fixture(tmp_path)
    mission["certificate_gated_context"]["case"] = "changed"
    with pytest.raises(RouteExecutionBindingError, match="ROUTER_FAIL_CLOSED:NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT"):
        authorize_step(root=tmp_path, mission=mission, step=step)

def test_certificate_drift_fails(tmp_path):
    mission, step = _fixture(tmp_path)
    (tmp_path / "adequacy.json").write_text("changed")
    with pytest.raises(RouteExecutionBindingError, match="ADEQUACY_CERTIFICATE_BLOB_MISMATCH"):
        authorize_step(root=tmp_path, mission=mission, step=step)

def test_required_missing_binding_fails(tmp_path):
    with pytest.raises(RouteExecutionBindingError, match="CERTIFICATE_GATED_ROUTE_REQUIRED"):
        authorize_step(
            root=tmp_path,
            mission={"certificate_gated_routing_required": True},
            step={"id": "x"},
        )

def test_nonliteral_required_fails(tmp_path):
    with pytest.raises(RouteExecutionBindingError, match="ROUTING_REQUIRED_MUST_BE_LITERAL_BOOL"):
        authorize_step(
            root=tmp_path,
            mission={"certificate_gated_routing_required": 1},
            step={"id": "x"},
        )
