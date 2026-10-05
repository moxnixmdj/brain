from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from canonical.runtime.material_effect_reference_monitor_v1 import (
    EffectDenied,
    ReferenceMonitor,
    classify_audit_event,
    git_blob_sha,
    sha256_json,
)

PREDICATES = [
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
]


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path):
    runtime = tmp_path / "canonical/runtime/astra_runtime.py"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("# exact runtime\n", encoding="utf-8")
    runtime_blob = git_blob_sha(runtime.read_bytes())

    payload = {"step": {"adapter": "shell", "command": "printf ok"}}
    action_sha = sha256_json(payload)

    action_receipt = tmp_path / "canonical/verification/action.json"
    _write_json(action_receipt, {
        "proved": True,
        "scope_complete": True,
        "independent_or_objective": True,
        "runtime_git_blob_sha": runtime_blob,
        "predicate_ids": PREDICATES,
        "zero_critical_violations": True,
        "action_sha256": action_sha,
    })

    admin_receipt = tmp_path / "canonical/verification/admin.json"
    _write_json(admin_receipt, {
        "proved": True,
        "scope_complete": True,
        "independent_or_objective": True,
        "runtime_git_blob_sha": runtime_blob,
        "predicate_ids": PREDICATES,
        "administrative_state_writes_zero_critical_violation": True,
    })

    policy = tmp_path / "canonical/governance/policy.json"
    _write_json(policy, {
        "schema": "PROJECT_BRAIN_MATERIAL_EFFECT_POLICY_V1",
        "runtime": {
            "path": "canonical/runtime/astra_runtime.py",
            "git_blob_sha": runtime_blob,
        },
        "required_predicate_ids": PREDICATES,
        "administrative_state": {
            "allowed_repo_prefixes": ["canonical/runtime_state"],
            "receipt": {
                "path": "canonical/verification/admin.json",
                "git_blob_sha": git_blob_sha(admin_receipt.read_bytes()),
            },
        },
        "rules": [{
            "id": "shell-ok",
            "channel": "shell",
            "action_sha256": action_sha,
            "predicate_ids": PREDICATES,
            "allowed_sinks": ["process.spawn", "file.open_write"],
            "allowed_repo_prefixes": ["canonical/runtime_state"],
            "allowed_network_hosts": [],
            "receipt": {
                "path": "canonical/verification/action.json",
                "git_blob_sha": git_blob_sha(action_receipt.read_bytes()),
            },
        }],
    })

    monitor = ReferenceMonitor(
        repo_root=tmp_path,
        runtime_path="canonical/runtime/astra_runtime.py",
        policy_path="canonical/governance/policy.json",
    )
    return monitor, payload, policy, action_receipt


def test_exact_action_authorization_and_sink_scope(tmp_path):
    monitor, payload, _, _ = _fixture(tmp_path)
    with monitor.activate("shell", payload):
        assert monitor.require_sink("process.spawn").rule_id == "shell-ok"
        p = tmp_path / "canonical/runtime_state/x.json"
        assert monitor.require_sink("file.open_write", path=p).rule_id == "shell-ok"


def test_unknown_action_fails_closed(tmp_path):
    monitor, _, _, _ = _fixture(tmp_path)
    with pytest.raises(EffectDenied, match="NO_EXACT_AUTHORIZATION"):
        monitor.authorize("shell", {
            "step": {"adapter": "shell", "command": "whoami"}
        })


def test_sink_and_path_escape_fail_closed(tmp_path):
    monitor, payload, _, _ = _fixture(tmp_path)
    with monitor.activate("shell", payload):
        with pytest.raises(EffectDenied, match="SINK_NOT_AUTHORIZED"):
            monitor.require_sink("network.connect", network_host="example.com")
        with pytest.raises(EffectDenied, match="PATH_NOT_AUTHORIZED"):
            monitor.require_sink(
                "file.open_write", path=tmp_path / "canonical/governance/no.json"
            )


def test_receipt_mutation_fails_content_address(tmp_path):
    _, _, policy, action_receipt = _fixture(tmp_path)
    action_receipt.write_text("{}\n", encoding="utf-8")
    with pytest.raises(EffectDenied, match="RECEIPT_BLOB_MISMATCH"):
        ReferenceMonitor(
            repo_root=tmp_path,
            runtime_path="canonical/runtime/astra_runtime.py",
            policy_path=str(policy.relative_to(tmp_path)),
        )


def test_runtime_drift_fails_closed(tmp_path):
    _, _, policy, _ = _fixture(tmp_path)
    runtime = tmp_path / "canonical/runtime/astra_runtime.py"
    runtime.write_text("# drift\n", encoding="utf-8")
    with pytest.raises(EffectDenied, match="POLICY_RUNTIME_BLOB_MISMATCH"):
        ReferenceMonitor(
            repo_root=tmp_path,
            runtime_path="canonical/runtime/astra_runtime.py",
            policy_path=str(policy.relative_to(tmp_path)),
        )


def test_admin_write_is_tightly_scoped(tmp_path):
    monitor, _, _, _ = _fixture(tmp_path)
    inside = tmp_path / "canonical/runtime_state/admin.json"
    assert monitor.require_sink("file.open_write", path=inside).rule_id == (
        "ADMINISTRATIVE_STATE_RECEIPT"
    )
    with pytest.raises(EffectDenied, match="MATERIAL_EFFECT_WITHOUT_AUTHORIZATION"):
        monitor.require_sink(
            "file.open_write", path=tmp_path / "canonical/governance/no.json"
        )


def test_audit_event_classifier_catches_material_channels():
    assert classify_audit_event("subprocess.Popen", ())[0] == "process.spawn"
    sink, detail = classify_audit_event(
        "open", ("x", "wb", os.O_WRONLY | os.O_CREAT)
    )
    assert sink == "file.open_write"
    assert detail["path"] == "x"
    sink, detail = classify_audit_event(
        "socket.connect", (object(), ("example.com", 443))
    )
    assert sink == "network.connect"
    assert detail["network_host"] == "example.com"
    assert classify_audit_event("ctypes.dlopen", ("x",))[0] == "native.escape"


def test_read_open_is_not_material():
    assert classify_audit_event("open", ("x", "r", os.O_RDONLY)) == (None, {})
