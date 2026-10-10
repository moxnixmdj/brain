import copy

from canonical.runtime.execution_authority_reducer import (
    canonical_event_hash,
    derive_authority,
)


def chain(carrier):
    raw = [
        ("STAGE_A_PASS", "stage-a"),
        ("STAGE_B_PASS", "stage-b"),
        ("SOURCE_BOUNDARY_PASS", "source"),
        ("EXECUTION_SURFACE_PASS", "surface"),
        ("LEASE_ISSUED", "lease"),
        ("CARRIER_OPEN", carrier),
    ]
    out=[]
    prev=None
    for seq,(typ,evidence) in enumerate(raw):
        e={
            "schema":"BRAIN_AUTHORITY_EVENT_V1",
            "task":"t",
            "seq":seq,
            "event_id":f"E{seq}",
            "type":typ,
            "evidence":evidence,
            "prev_event_sha256":prev,
        }
        e["event_sha256"]=canonical_event_hash(e)
        prev=e["event_sha256"]
        out.append(e)
    return out


def append(events, typ, evidence):
    out=copy.deepcopy(events)
    e={
        "schema":"BRAIN_AUTHORITY_EVENT_V1",
        "task":"t",
        "seq":len(out),
        "event_id":f"E{len(out)}",
        "type":typ,
        "evidence":evidence,
        "prev_event_sha256":out[-1]["event_sha256"] if out else None,
    }
    e["event_sha256"]=canonical_event_hash(e)
    out.append(e)
    return out


def test_exact_carrier_identity_changes_authority_hash():
    a=derive_authority(chain({"pr":425,"head":"aaa"}),task="t",execution_budget=1,verifier_budget=1)
    b=derive_authority(chain({"pr":427,"head":"bbb"}),task="t",execution_budget=1,verifier_budget=1)
    assert a["valid"] and b["valid"]
    assert a["can_execute"] and b["can_execute"]
    assert a["active_carrier_binding_sha256"] != b["active_carrier_binding_sha256"]
    assert a["state_sha256"] != b["state_sha256"]


def test_second_open_carrier_without_close_fails_closed():
    events=append(chain({"pr":425}),"CARRIER_OPEN",{"pr":427})
    out=derive_authority(events,task="t",execution_budget=1,verifier_budget=1)
    assert out["valid"] is False
    assert out["can_execute"] is False
    assert any(x.startswith("SECOND_CARRIER_OPEN_WITHOUT_CLOSE") for x in out["errors"])


def test_execution_consumed_flips_builder_to_verifier_only():
    events=append(chain({"pr":425}),"EXECUTION_CONSUMED",{"run":1})
    out=derive_authority(events,task="t",execution_budget=1,verifier_budget=1)
    assert out["valid"] is True
    assert out["can_execute"] is False
    assert out["can_verify"] is True


def test_consumption_without_open_carrier_is_invalid():
    events=chain({"pr":425})
    events=append(events,"CARRIER_CLOSED",{"pr":425})
    events=append(events,"EXECUTION_CONSUMED",{"run":1})
    out=derive_authority(events,task="t",execution_budget=1,verifier_budget=1)
    assert out["valid"] is False
    assert any(x.startswith("EXECUTION_CONSUMED_WITHOUT_OPEN_CARRIER") for x in out["errors"])


def test_revocation_and_close_remove_all_authority():
    events=append(chain({"pr":425}),"EXECUTION_CONSUMED",{"run":1})
    events=append(events,"LEASE_REVOKED","failure")
    events=append(events,"CARRIER_CLOSED",{"pr":425})
    out=derive_authority(events,task="t",execution_budget=1,verifier_budget=1)
    assert out["valid"] is True
    assert out["can_execute"] is False
    assert out["can_verify"] is False
    assert out["state"]["execution_used"] == 1
    assert out["state"]["active_carrier_binding_sha256"] is None
