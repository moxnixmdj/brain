from __future__ import annotations

import copy
import hashlib
import importlib.util
import pathlib

from canonical.runtime.honesty_load_bearing_result_gate_v1 import (
    LoadBearingHonestyError,
    certify_result,
    certify_terminal_completion,
    validate_result_certificate,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def honesty_record(task_id: str, completion: str = "COMPLETE"):
    state = "VERIFIED" if completion == "COMPLETE" else "OPEN"
    return {
        "schema": "PROJECT_BRAIN_HONESTY_ENVELOPE_INPUT_V1",
        "task_contract": {
            "task_id": task_id,
            "required_obligations": ["o1"],
        },
        "obligations": [
            {
                "id": "o1",
                "state": state,
                "receipts": [h("receipt-o1")] if state == "VERIFIED" else [],
            }
        ],
        "completion_claim": completion,
        "provenance_events": [],
        "material_claims": [],
        "belief_assertions": [],
    }


def test_exact_step_record_certifies_and_revalidates():
    result = {"stdout": "done", "returncode": 0}
    rec = honesty_record("M1::step::S1")
    cert = certify_result(
        mission_id="M1",
        mission_sha256=h("mission"),
        step_index=0,
        step_id="S1",
        result=result,
        honesty_record=rec,
    )
    out = validate_result_certificate(
        certificate=cert,
        mission_id="M1",
        mission_sha256=h("mission"),
        step_index=0,
        step_id="S1",
        result=result,
    )
    assert out["load_bearing_authorized"] is True


def test_unrelated_valid_honesty_record_cannot_be_laundered():
    try:
        certify_result(
            mission_id="M1",
            mission_sha256=h("mission"),
            step_index=0,
            step_id="S1",
            result={"stdout": "done"},
            honesty_record=honesty_record("OTHER"),
        )
    except LoadBearingHonestyError as exc:
        assert "STEP_CONTRACT_MISMATCH" in str(exc)
    else:
        raise AssertionError("unrelated record accepted")


def test_result_byte_change_invalidates_certificate():
    result = {"stdout": "done"}
    cert = certify_result(
        mission_id="M1",
        mission_sha256=h("mission"),
        step_index=0,
        step_id="S1",
        result=result,
        honesty_record=honesty_record("M1::step::S1"),
    )
    try:
        validate_result_certificate(
            certificate=cert,
            mission_id="M1",
            mission_sha256=h("mission"),
            step_index=0,
            step_id="S1",
            result={"stdout": "changed"},
        )
    except LoadBearingHonestyError as exc:
        assert "RESULT_SHA256_MISMATCH" in str(exc)
    else:
        raise AssertionError("changed result accepted")


def test_embedded_honesty_record_tamper_invalidates_certificate():
    result = {"stdout": "done"}
    cert = certify_result(
        mission_id="M1",
        mission_sha256=h("mission"),
        step_index=0,
        step_id="S1",
        result=result,
        honesty_record=honesty_record("M1::step::S1"),
    )
    cert = copy.deepcopy(cert)
    cert["honesty_record"]["completion_claim"] = "PARTIAL"
    try:
        validate_result_certificate(
            certificate=cert,
            mission_id="M1",
            mission_sha256=h("mission"),
            step_index=0,
            step_id="S1",
            result=result,
        )
    except LoadBearingHonestyError as exc:
        assert "HONESTY_RECORD_HASH_MISMATCH" in str(exc)
    else:
        raise AssertionError("tampered record accepted")


def test_terminal_completion_requires_exact_mission_record():
    rec = honesty_record("M1")
    cert = certify_terminal_completion(
        mission_id="M1",
        mission_sha256=h("mission"),
        state_sha256=h("state"),
        honesty_record=rec,
    )
    assert cert["terminal_completion_authorized"] is True

    try:
        certify_terminal_completion(
            mission_id="M1",
            mission_sha256=h("mission"),
            state_sha256=h("state"),
            honesty_record=honesty_record("OTHER"),
        )
    except LoadBearingHonestyError as exc:
        assert "MISSION_MISMATCH" in str(exc)
    else:
        raise AssertionError("unrelated terminal record accepted")


def test_partial_terminal_record_cannot_authorize_complete():
    try:
        certify_terminal_completion(
            mission_id="M1",
            mission_sha256=h("mission"),
            state_sha256=h("state"),
            honesty_record=honesty_record("M1", completion="PARTIAL"),
        )
    except LoadBearingHonestyError as exc:
        assert "TERMINAL_COMPLETION_NOT_COMPLETE" in str(exc)
    else:
        raise AssertionError("partial completion authorized")


def test_astra_cross_step_context_rejects_uncertified_prior_result():
    path = ROOT / "canonical/runtime/astra_runtime.py"
    spec = importlib.util.spec_from_file_location("astra_gate_test", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    state = {
        "mission_id": "M1",
        "mission_sha256": h("mission"),
        "history": [
            {
                "step_index": 0,
                "step_id": "S1",
                "ok": True,
                "result": {"stdout": "untrusted"},
                "quarantined_untrusted_audit_data": True,
            }
        ],
    }
    try:
        mod.context_results(state)
    except mod.Blocker as exc:
        assert "HONESTY_CERTIFICATE_REQUIRED" in str(exc)
    else:
        raise AssertionError("uncertified result became load-bearing")


def test_astra_source_contains_terminal_honesty_gate():
    src = (ROOT / "canonical/runtime/astra_runtime.py").read_text()
    assert 'state["status"]="COMPLETE_PENDING_HONESTY"' in src
    assert "certify_terminal_completion" in src
    assert "TERMINAL_HONESTY_CERTIFICATION_FAILED" in src
