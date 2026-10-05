"""Zero-learned event-sourced task memory for H100.

Capability logic is deterministic program code. Event logs and snapshots are
nonlearned task state / knowledge, not learned parameters.
"""
from __future__ import annotations

import copy
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_H100_ZERO_LEARNED_EVENT_MEMORY_V1"
GENESIS="0"*64


class EventMemoryError(ValueError):
    pass


def _canon(obj:Any)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


def _sha(obj:Any)->str:
    return hashlib.sha256(_canon(obj)).hexdigest()


def make_event(*,seq:int,op:str,key:str,value:Any,prev_hash:str)->dict[str,Any]:
    if not isinstance(seq,int) or isinstance(seq,bool) or seq<1:
        raise EventMemoryError("SEQ_INVALID")
    if op not in {"SET","DELETE"}:
        raise EventMemoryError("OP_INVALID")
    if not isinstance(key,str) or not key:
        raise EventMemoryError("KEY_INVALID")
    if not isinstance(prev_hash,str) or len(prev_hash)!=64:
        raise EventMemoryError("PREV_HASH_INVALID")
    body={"seq":seq,"op":op,"key":key,"value":value if op=="SET" else None,"prev_hash":prev_hash}
    return {**body,"event_hash":_sha(body)}


def verify_event(event:Mapping[str,Any],*,expected_seq:int,expected_prev_hash:str)->None:
    required={"seq","op","key","value","prev_hash","event_hash"}
    if not isinstance(event,Mapping) or set(event)!=required:
        raise EventMemoryError("EVENT_SCHEMA_INVALID")
    if event["seq"]!=expected_seq:
        raise EventMemoryError("EVENT_SEQUENCE_GAP_OR_REPLAY")
    if event["prev_hash"]!=expected_prev_hash:
        raise EventMemoryError("EVENT_PREV_HASH_MISMATCH")
    if event["op"] not in {"SET","DELETE"}:
        raise EventMemoryError("EVENT_OP_INVALID")
    if not isinstance(event["key"],str) or not event["key"]:
        raise EventMemoryError("EVENT_KEY_INVALID")
    if event["op"]=="DELETE" and event["value"] is not None:
        raise EventMemoryError("DELETE_VALUE_MUST_BE_NULL")
    body={k:event[k] for k in ("seq","op","key","value","prev_hash")}
    if event["event_hash"]!=_sha(body):
        raise EventMemoryError("EVENT_HASH_MISMATCH")


def apply_event(state:dict[str,Any],event:Mapping[str,Any],*,last_seq:int,last_hash:str)->tuple[int,str]:
    verify_event(event,expected_seq=last_seq+1,expected_prev_hash=last_hash)
    if event["op"]=="SET":
        state[str(event["key"])]=copy.deepcopy(event["value"])
    else:
        state.pop(str(event["key"]),None)
    return int(event["seq"]),str(event["event_hash"])


def make_snapshot(state:Mapping[str,Any],*,last_seq:int,last_event_hash:str)->dict[str,Any]:
    if not isinstance(last_seq,int) or last_seq<0:
        raise EventMemoryError("SNAPSHOT_SEQ_INVALID")
    if not isinstance(last_event_hash,str) or len(last_event_hash)!=64:
        raise EventMemoryError("SNAPSHOT_LAST_HASH_INVALID")
    body={
        "last_seq":last_seq,
        "last_event_hash":last_event_hash,
        "state":copy.deepcopy(dict(state)),
    }
    return {**body,"snapshot_hash":_sha(body)}


def verify_snapshot(snapshot:Mapping[str,Any])->None:
    required={"last_seq","last_event_hash","state","snapshot_hash"}
    if not isinstance(snapshot,Mapping) or set(snapshot)!=required:
        raise EventMemoryError("SNAPSHOT_SCHEMA_INVALID")
    if not isinstance(snapshot["last_seq"],int) or snapshot["last_seq"]<0:
        raise EventMemoryError("SNAPSHOT_SEQ_INVALID")
    if not isinstance(snapshot["last_event_hash"],str) or len(snapshot["last_event_hash"])!=64:
        raise EventMemoryError("SNAPSHOT_LAST_HASH_INVALID")
    if not isinstance(snapshot["state"],Mapping):
        raise EventMemoryError("SNAPSHOT_STATE_INVALID")
    body={k:snapshot[k] for k in ("last_seq","last_event_hash","state")}
    if snapshot["snapshot_hash"]!=_sha(body):
        raise EventMemoryError("SNAPSHOT_HASH_MISMATCH")


def replay(events:Iterable[Mapping[str,Any]],snapshot:Mapping[str,Any]|None=None)->dict[str,Any]:
    if snapshot is None:
        state={}
        last_seq=0
        last_hash=GENESIS
    else:
        verify_snapshot(snapshot)
        state=copy.deepcopy(dict(snapshot["state"]))
        last_seq=int(snapshot["last_seq"])
        last_hash=str(snapshot["last_event_hash"])
    for event in events:
        last_seq,last_hash=apply_event(state,event,last_seq=last_seq,last_hash=last_hash)
    return {
        "state":state,
        "last_seq":last_seq,
        "last_event_hash":last_hash,
        "snapshot":make_snapshot(state,last_seq=last_seq,last_event_hash=last_hash),
    }


def generate_trace(count:int=10000)->list[dict[str,Any]]:
    if count<1:
        raise EventMemoryError("COUNT_INVALID")
    out=[]
    prev=GENESIS
    for i in range(1,count+1):
        key=f"key_{i%257:03d}"
        op="DELETE" if i%19==0 else "SET"
        value=None if op=="DELETE" else (i*7919+17)%1000003
        event=make_event(seq=i,op=op,key=key,value=value,prev_hash=prev)
        out.append(event)
        prev=event["event_hash"]
    return out


def _roundtrip_json(obj:Any)->Any:
    return json.loads(json.dumps(obj,sort_keys=True,separators=(",",":")))


def run_experiment()->dict[str,Any]:
    events=generate_trace(10000)

    t0=time.perf_counter()
    full=replay(events)
    full_seconds=time.perf_counter()-t0

    # Three explicit restart boundaries.
    seg1=replay(events[:2500])
    snap1=_roundtrip_json(seg1["snapshot"])
    seg2=replay(events[2500:5000],snap1)
    snap2=_roundtrip_json(seg2["snapshot"])
    seg3=replay(events[5000:7500],snap2)
    snap3=_roundtrip_json(seg3["snapshot"])
    restarted=replay(events[7500:],snap3)

    t1=time.perf_counter()
    tail=replay(events[7500:],snap3)
    tail_seconds=time.perf_counter()-t1

    full_state=full["state"]
    restarted_state=restarted["state"]
    tail_state=tail["state"]
    keys=[f"key_{i:03d}" for i in range(257)]

    controls={}
    # 1. Mutate content but preserve old hash.
    tampered=copy.deepcopy(events[5000])
    tampered["value"]=999999999
    try:
        replay([*events[:5000],tampered])
        controls["mutated_event_rejected"]=False
    except EventMemoryError:
        controls["mutated_event_rejected"]=True

    # 2. Remove one event, creating seq/hash discontinuity.
    try:
        replay([*events[:6999],*events[7000:7002]])
        controls["sequence_gap_rejected"]=False
    except EventMemoryError:
        controls["sequence_gap_rejected"]=True

    # 3. Replay a divergent event at an already-applied sequence.
    base6000=replay(events[:6000])
    divergent=make_event(
        seq=6000,op="SET",key="divergent",value=1,
        prev_hash=events[5998]["event_hash"],
    )
    try:
        replay([divergent],base6000["snapshot"])
        controls["divergent_replay_rejected"]=False
    except EventMemoryError:
        controls["divergent_replay_rejected"]=True

    # 4. Mutate snapshot state without updating its hash.
    bad_snap=copy.deepcopy(snap3)
    bad_snap["state"]["tampered"]=True
    try:
        replay(events[7500:7501],bad_snap)
        controls["snapshot_tamper_rejected"]=False
    except EventMemoryError:
        controls["snapshot_tamper_rejected"]=True

    event_bytes=sum(len(_canon(e)) for e in events)
    snapshot_bytes=len(_canon(snap3))
    equivalences={
        "full_equals_three_restart":full_state==restarted_state,
        "full_equals_snapshot_tail":full_state==tail_state,
        "snapshot_roundtrip_preserved":_roundtrip_json(snap3)==snap3,
        "all_257_key_queries_match":all(
            full_state.get(k)==restarted_state.get(k)==tail_state.get(k) for k in keys
        ),
    }
    passed=all(equivalences.values()) and all(controls.values()) and full["last_seq"]==10000
    return {
        "schema":SCHEMA,
        "status":"PASS__10000_EVENT_THREE_RESTART_CONTINUITY_AND_FAIL_CLOSED_INTEGRITY__ZERO_LEARNED" if passed else "FAIL__EVENT_MEMORY_RESIDUAL",
        "event_count":len(events),
        "restart_boundaries":[2500,5000,7500],
        "final_state_key_count":len(full_state),
        "full_replay_wall_clock_seconds":full_seconds,
        "snapshot_tail_replay_wall_clock_seconds":tail_seconds,
        "event_log_canonical_bytes":event_bytes,
        "snapshot_canonical_bytes_at_7500":snapshot_bytes,
        "equivalences":equivalences,
        "fail_closed_controls":controls,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "task_state_bytes_count_as_learned_state":False,
        "hard_nonclaims":[
            "TASK_STATE_BYTES_ARE_NOT_ZERO",
            "THIS_IS_DETERMINISTIC_CONTINUITY_NOT_OPEN_WORLD_SEMANTIC_MEMORY",
            "DOES_NOT_PROVE_UNBOUNDED_RETENTION",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta":0,
    }


if __name__=="__main__":
    print(json.dumps(run_experiment(),indent=2,sort_keys=True))
