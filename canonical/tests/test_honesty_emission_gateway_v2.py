import hashlib
from canonical.runtime import honesty_emission_gateway_v2 as g

R="a"*64
def rec(state="VERIFIED",claim="COMPLETE"):
    return {"schema":"PROJECT_BRAIN_HONESTY_ENVELOPE_INPUT_V1",
      "task_contract":{"task_id":"T","required_obligations":["O"]},
      "obligations":[{"id":"O","state":state,"receipts":[R] if state=="VERIFIED" else []}],
      "completion_claim":claim,"provenance_events":[],"material_claims":[],"belief_assertions":[]}

def raw(record=None,payload=None):
    c=g.make_capsule(sequence=0,emission_id="E",payload=payload or {"status":"COMPLETE"},honesty_record=record or rec())
    return g.encode_capsule(c)

def runner_for(b,status="CHILD_EXITED",rc=0,effects=0):
    return lambda _:{
      "status":status,"returncode":rc,"material_effects_committed":effects,
      "policy_sha256":"p","broker_payload":b,"broker_bytes":len(b),
      "broker_sha256":hashlib.sha256(b).hexdigest()}

def test_valid_content_bound_capsule_passes():
    out=g.run({},confined_runner=runner_for(raw()))
    assert out["status"]=="PASS__CONTENT_BOUND_HONESTY_EMISSIONS_ONLY"
    assert out["emission_count"]==1 and out["raw_broker_exposed"] is False

def test_false_completion_fails():
    out=g.run({},confined_runner=runner_for(raw(rec("OPEN","COMPLETE"))))
    assert out["status"]=="FAIL_CLOSED" and out["emissions"]==[]

def test_payload_record_substitution_fails():
    c=g.make_capsule(sequence=0,emission_id="E",payload={"x":1},honesty_record=rec())
    c["payload"]={"x":2}; c["payload_sha256"]=g.v1._sha(c["payload"])
    b=g.encode_capsule(c)
    out=g.run({},confined_runner=runner_for(b))
    assert out["status"]=="FAIL_CLOSED" and out["emissions"]==[]

def test_timeout_suppresses_valid_complete_capsule():
    out=g.run({},confined_runner=runner_for(raw(),status="WALLCLOCK_LIMIT_EXCEEDED",rc=9))
    assert out["status"]=="FAIL_CLOSED" and out["emissions"]==[]

def test_nonzero_exit_suppresses_valid_complete_capsule():
    out=g.run({},confined_runner=runner_for(raw(),rc=7))
    assert out["status"]=="FAIL_CLOSED" and out["emissions"]==[]

def test_material_effect_state_suppresses_capsule():
    out=g.run({},confined_runner=runner_for(raw(),effects=1))
    assert out["status"]=="FAIL_CLOSED" and out["emissions"]==[]

def test_broker_hash_mismatch_fails():
    b=raw()
    def bad(_):
        return {"status":"CHILD_EXITED","returncode":0,"material_effects_committed":0,
          "broker_payload":b,"broker_bytes":len(b),"broker_sha256":"0"*64}
    out=g.run({},confined_runner=bad)
    assert out["status"]=="FAIL_CLOSED" and out["emissions"]==[]
