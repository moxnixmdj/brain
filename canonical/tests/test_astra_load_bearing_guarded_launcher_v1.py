from copy import deepcopy

import pytest

from canonical.runtime import astra_load_bearing_guarded_launcher_v1 as guarded
from canonical.runtime import load_bearing_result_propagation_gate_v1 as gate


MISSION_SHA = "a" * 64


def state_with(result=None, *, ok=True):
    value = {"adapter": "goal", "returncode": 0, "stdout": "x"} if result is None else result
    return {
        "schema": "PROJECT_BRAIN_ASTRA_RUNTIME_STATE_V1",
        "mission_id": "M",
        "mission_sha256": MISSION_SHA,
        "history": [
            {
                "step_index": 0,
                "step_id": "S0",
                "ok": ok,
                "result": value,
            }
        ],
        "rehydrations": [],
    }


def test_guard_state_adds_content_bound_certificate():
    state = state_with()
    guarded.guard_state_for_write(state)
    rec = state["history"][0]
    cert = rec["load_bearing_result_certificate"]
    assert cert["status"] == gate.PASS_STATUS
    assert cert["binding"]["result_sha256"] == gate._sha(rec["result"])


def test_guarded_context_accepts_only_valid_certificate():
    state = state_with()
    guarded.guard_state_for_write(state)
    out = guarded._guarded_context_result_map(state)
    assert out[0] == state["history"][0]["result"]


def test_missing_certificate_is_not_load_bearing():
    state = state_with()
    with pytest.raises(guarded.GuardedAstraError, match="CERTIFICATE_MISSING"):
        guarded._guarded_context_result_map(state)


def test_result_tamper_after_persistence_fails_closed():
    state = state_with()
    guarded.guard_state_for_write(state)
    state["history"][0]["result"]["stdout"] = "tampered"
    with pytest.raises(guarded.GuardedAstraError, match="CERTIFICATE_INVALID"):
        guarded._guarded_context_result_map(state)


def test_cross_mission_record_substitution_fails_closed():
    state = state_with()
    guarded.guard_state_for_write(state)
    stolen = deepcopy(state["history"][0])
    other = {
        "schema": "PROJECT_BRAIN_ASTRA_RUNTIME_STATE_V1",
        "mission_id": "OTHER",
        "mission_sha256": "b" * 64,
        "history": [stolen],
        "rehydrations": [],
    }
    with pytest.raises(guarded.GuardedAstraError, match="CERTIFICATE_INVALID"):
        guarded._guarded_context_result_map(other)


def test_rehydration_records_are_certified_too():
    state = state_with()
    state["rehydrations"] = [
        {
            "steps": [
                {
                    "step_index": 1,
                    "step_id": "S1",
                    "ok": True,
                    "result": {"adapter": "shell", "returncode": 0, "stdout": "rehydrated"},
                }
            ]
        }
    ]
    guarded.guard_state_for_write(state)
    assert "load_bearing_result_certificate" in state["rehydrations"][0]["steps"][0]
    out = guarded._guarded_context_result_map(state)
    assert set(out) == {0, 1}


def test_failed_blocker_result_is_certified_as_failed():
    state = state_with()
    state["blocker"] = {
        "step_index": 2,
        "step_id": "S2",
        "adapter": "shell",
        "error": "VERIFICATION_FAILED",
        "result": {"returncode": 9, "stdout": "", "stderr": "boom"},
    }
    guarded.guard_state_for_write(state)
    cert = state["blocker"]["load_bearing_result_certificate"]
    assert cert["honesty_record"]["completion_claim"] == "FAILED"


def test_install_replaces_only_persistence_and_context_boundaries():
    original_execute = guarded.astra.execute_step
    guarded.install()
    assert guarded.astra.write_statej is guarded._guarded_write_statej
    assert guarded.astra._context_result_map is guarded._guarded_context_result_map
    assert guarded.astra.execute_step is original_execute
