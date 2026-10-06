from copy import deepcopy

from canonical.runtime import load_bearing_result_propagation_gate_v1 as gate


MISSION = "MISSION-X"
MISSION_SHA = "a" * 64
STEP_ID = "STEP-A"


def result():
    return {
        "adapter": "goal",
        "returncode": 0,
        "stdout": "complete",
        "final_summary": "complete",
        "controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN",
    }


def cert(value=None, *, mission_id=MISSION, mission_sha=MISSION_SHA, step_index=0, step_id=STEP_ID, ok=True):
    return gate.certify_result(
        result() if value is None else value,
        mission_id=mission_id,
        mission_sha256=mission_sha,
        step_index=step_index,
        step_id=step_id,
        verification_ok=ok,
    )


def verify(value=None, certificate=None, *, mission_id=MISSION, mission_sha=MISSION_SHA, step_index=0, step_id=STEP_ID, ok=True):
    return gate.verify_certificate(
        result() if value is None else value,
        cert() if certificate is None else certificate,
        mission_id=mission_id,
        mission_sha256=mission_sha,
        step_index=step_index,
        step_id=step_id,
        verification_ok=ok,
    )


def test_valid_result_certificate_passes():
    c = cert()
    out = verify(certificate=c)
    assert out["status"] == "PASS"
    assert c["ledger_semantic_completeness_claimed"] is False
    assert c["honesty_record"]["ledger_semantic_completeness_claimed"] is False


def test_result_mutation_fails_closed():
    c = cert()
    changed = result()
    changed["final_summary"] = "different"
    assert verify(value=changed, certificate=c)["status"] == "FAIL_CLOSED"


def test_mission_substitution_fails_closed():
    c = cert()
    assert verify(certificate=c, mission_id="MISSION-Y")["status"] == "FAIL_CLOSED"


def test_mission_hash_substitution_fails_closed():
    c = cert()
    assert verify(certificate=c, mission_sha="b" * 64)["status"] == "FAIL_CLOSED"


def test_step_identity_substitution_fails_closed():
    c = cert()
    assert verify(certificate=c, step_index=1)["status"] == "FAIL_CLOSED"
    assert verify(certificate=c, step_id="STEP-B")["status"] == "FAIL_CLOSED"


def test_verification_state_substitution_fails_closed():
    c = cert()
    assert verify(certificate=c, ok=False)["status"] == "FAIL_CLOSED"


def test_honesty_record_mutation_fails_closed():
    c = cert()
    bad = deepcopy(c)
    bad["honesty_record"]["completion_claim"] = "PARTIAL"
    assert verify(certificate=bad)["status"] == "FAIL_CLOSED"


def test_certificate_cannot_claim_ledger_semantic_completeness():
    c = cert()
    bad = deepcopy(c)
    bad["honesty_record"]["ledger_semantic_completeness_claimed"] = True
    bad["honesty_record_sha256"] = gate._sha(bad["honesty_record"])
    bad["honesty_result"] = gate.honesty.adjudicate(bad["honesty_record"])
    bad["honesty_result_sha256"] = gate._sha(bad["honesty_result"])
    assert verify(certificate=bad)["status"] == "FAIL_CLOSED"


def test_failed_step_is_truthfully_certified_failed_not_complete():
    r = {"adapter": "shell", "returncode": 7, "stdout": "", "stderr": "boom"}
    c = cert(r, ok=False)
    assert c["honesty_record"]["completion_claim"] == "FAILED"
    out = gate.verify_certificate(
        r,
        c,
        mission_id=MISSION,
        mission_sha256=MISSION_SHA,
        step_index=0,
        step_id=STEP_ID,
        verification_ok=False,
    )
    assert out["status"] == "PASS"
