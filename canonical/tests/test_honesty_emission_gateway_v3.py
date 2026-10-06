import hashlib
from canonical.runtime import honesty_emission_gateway_v3 as g

R="a"*64
def rec(state="VERIFIED",claim="COMPLETE"):
    return {"schema":"PROJECT_BRAIN_HONESTY_ENVELOPE_INPUT_V1",
      "task_contract":{"task_id":"T","required_obligations":["O"]},
      "obligations":[{"id":"O","state":state,"receipts":[R] if state=="VERIFIED" else []}],
      "completion_claim":claim,"provenance_events":[],"material_claims":[],"belief_assertions":[]}

def raw(record=None,payload=None):
    return g.encode_capsule(g.make_capsule(sequence=0,emission_id="E",
      payload={"status":"COMPLETE"} if payload is None else payload,
      honesty_record=rec() if record is None else record))

def runner(b,status="CHILD_EXITED",rc=0,effects=0,sha=None,n=None):
    return lambda _:{
      "status":status,"returncode":rc,"material_effects_committed":effects,
      "policy_sha256":"p","broker_payload":b,"broker_bytes":len(b) if n is None else n,
      "broker_sha256":hashlib.sha256(b).hexdigest() if sha is None else sha}

def test_valid_capsule_passes():
    out=g.run({},confined_runner=runner(raw()))
    assert out["status"]=="PASS__CONTENT_BOUND_HONESTY_EMISSIONS_ONLY"
    assert out["emission_count"]==1 and out["raw_broker_exposed"] is False

def test_false_completion_fails():
    out=g.run({},confined_runner=runner(raw(rec("OPEN","COMPLETE"))))
    assert out["status"]=="FAIL_CLOSED" and out["emissions"]==[]

def test_payload_record_substitution_fails_even_with_payload_hash_refreshed():
    c=g.make_capsule(sequence=0,emission_id="E",payload={"x":1},honesty_record=rec())
    c["payload"]={"x":2}; c["payload_sha256"]=g._sha(c["payload"])
    out=g.run({},confined_runner=runner(g.encode_capsule(c)))
    assert out["status"]=="FAIL_CLOSED"

def test_replayed_record_under_new_emission_identity_fails():
    c=g.make_capsule(sequence=0,emission_id="E1",payload={"x":1},honesty_record=rec())
    c["emission_id"]="E2"
    out=g.run({},confined_runner=runner(g.encode_capsule(c)))
    assert out["status"]=="FAIL_CLOSED"

def test_timeout_nonzero_exit_and_effect_state_suppress_capsules():
    b=raw()
    for kw in ({"status":"WALLCLOCK_LIMIT_EXCEEDED","rc":9},{"rc":7},{"effects":1}):
        out=g.run({},confined_runner=runner(b,**kw))
        assert out["status"]=="FAIL_CLOSED" and out["emissions"]==[]

def test_broker_length_and_hash_drift_fail():
    b=raw()
    assert g.run({},confined_runner=runner(b,n=len(b)+1))["status"]=="FAIL_CLOSED"
    assert g.run({},confined_runner=runner(b,sha="0"*64))["status"]=="FAIL_CLOSED"
