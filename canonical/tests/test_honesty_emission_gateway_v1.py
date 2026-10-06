from canonical.runtime.honesty_emission_gateway_v1 import adjudicate_broker_payload, encode_capsule, make_capsule, run

R="a"*64

def rec(state="VERIFIED",claim="COMPLETE"):
    return {
      "schema":"PROJECT_BRAIN_HONESTY_ENVELOPE_INPUT_V1",
      "task_contract":{"task_id":"T","required_obligations":["O"]},
      "obligations":[{"id":"O","state":state,"receipts":[R] if state=="VERIFIED" else []}],
      "completion_claim":claim,
      "provenance_events":[],
      "material_claims":[],
      "belief_assertions":[]
    }

def cap(record=None):
    return make_capsule(sequence=0,emission_id="E",payload={"status":"COMPLETE"},honesty_record=record or rec())

def test_valid_capsule_passes():
    out=adjudicate_broker_payload(encode_capsule(cap()))
    assert out[0]["honesty_status"]=="PASS"

def test_raw_json_is_not_capsule():
    try: adjudicate_broker_payload(b'{"status":"COMPLETE"}\n')
    except Exception as e: assert "NOT_EMISSION_CAPSULE" in str(e)
    else: raise AssertionError("raw output escaped")

def test_false_completion_is_denied():
    try: adjudicate_broker_payload(encode_capsule(cap(rec("OPEN","COMPLETE"))))
    except Exception as e: assert "HONESTY_ENVELOPE_DENIED" in str(e)
    else: raise AssertionError("false completion escaped")

def test_gateway_does_not_return_raw_broker():
    raw=encode_capsule(cap())
    def runner(_):
        return {"status":"CHILD_EXITED","returncode":0,"policy_sha256":"p","broker_payload":raw,"broker_bytes":len(raw),"broker_sha256":"b"*64,"material_effects_committed":0}
    out=run({},confined_runner=runner)
    assert out["emission_count"]==1
    assert out["raw_broker_exposed"] is False
    assert "broker_payload" not in out


def test_timeout_drops_even_valid_complete_capsule():
    raw=encode_capsule(cap())
    def runner(_):
        return {"status":"WALLCLOCK_LIMIT_EXCEEDED","returncode":9,"broker_payload":raw,"material_effects_committed":0}
    out=run({},confined_runner=runner)
    assert out["status"]=="FAIL_CLOSED"
    assert out["emissions"]==[]
    assert out["raw_broker_exposed"] is False

def test_nonzero_exit_drops_even_valid_complete_capsule():
    raw=encode_capsule(cap())
    def runner(_):
        return {"status":"CHILD_EXITED","returncode":7,"broker_payload":raw,"material_effects_committed":0}
    out=run({},confined_runner=runner)
    assert out["status"]=="FAIL_CLOSED"
    assert out["emissions"]==[]

def test_nonzero_material_effect_state_drops_capsules():
    raw=encode_capsule(cap())
    def runner(_):
        return {"status":"CHILD_EXITED","returncode":0,"broker_payload":raw,"material_effects_committed":1}
    out=run({},confined_runner=runner)
    assert out["status"]=="FAIL_CLOSED"
    assert out["emissions"]==[]
