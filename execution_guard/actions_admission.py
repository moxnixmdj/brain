"""Fail-closed at-most-one admission for a GitHub Actions run."""
from __future__ import annotations
import dataclasses, hashlib, json, re, unicodedata, uuid
from datetime import datetime, timezone

class AdmissionDenied(RuntimeError): pass
class DispatchUncertain(RuntimeError): pass

def _canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)
def _nonempty(v,label):
    if not isinstance(v,str) or not v.strip() or len(v)>4096: raise ValueError("INVALID_"+label.upper())
def _digest(v,label,n):
    if not isinstance(v,str) or not re.fullmatch(r"[0-9a-f]{%d}"%n,v): raise ValueError("INVALID_"+label.upper())
def problem_sha256(goal_text:str)->str:
    _nonempty(goal_text,"goal_text")
    norm=" ".join(unicodedata.normalize("NFKC",goal_text).strip().lower().split())
    return hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest()

def gate_key(gate_id):
    _nonempty(gate_id,"gate_id"); return "gates/"+hashlib.sha256(gate_id.encode()).hexdigest()+".json"
def attempt_key(kind,attempt_id):
    if not isinstance(attempt_id,str) or not re.fullmatch(r"[0-9a-f]{32}",attempt_id): raise AdmissionDenied("INVALID_ATTEMPT_ID")
    return kind+"/"+attempt_id+".json"

@dataclasses.dataclass(frozen=True)
class FrozenExecution:
    gate_id:str; problem_sha256:str; task_sha256:str; runtime_sha256:str; canonical_base:str; authorization_sha256:str
    def validate(self):
        _nonempty(self.gate_id,"gate_id")
        for f in ("problem_sha256","task_sha256","runtime_sha256","authorization_sha256"): _digest(getattr(self,f),f,64)
        _digest(self.canonical_base,"canonical_base",40)

def _create(store,key,record,uncertain="RESERVATION_UNCONFIRMED_NO_EXECUTION"):
    try: created=store.create(key,record)
    except Exception as exc: raise AdmissionDenied(uncertain) from exc
    if created is not True: raise AdmissionDenied("ALREADY_RESERVED_OR_CREATE_NOT_CONFIRMED")

def admit_current_run_once(store,spec:FrozenExecution,owner_id:str,run_ref:str)->dict:
    """Return only after gate, stable problem, and current run ack are immutable."""
    spec.validate(); _nonempty(owner_id,"owner_id"); _nonempty(run_ref,"run_ref")
    attempt_id=uuid.uuid4().hex
    reservation={"schema":"BRAIN_DISPATCH_RESERVATION_V1","attempt_id":attempt_id,"owner_id":owner_id,
                 "frozen":dataclasses.asdict(spec),"reserved_at":datetime.now(timezone.utc).isoformat()}
    _create(store,gate_key(spec.gate_id),reservation)
    _create(store,"problems/"+spec.problem_sha256+".json",reservation)
    ack={"schema":"BRAIN_DISPATCH_ACK_V1","attempt_id":attempt_id,"gate_id":spec.gate_id,"run_ref":run_ref}
    try: created=store.create(attempt_key("dispatches",attempt_id),ack)
    except Exception as exc: raise DispatchUncertain("CURRENT_RUN_ACK_UNCERTAIN:"+attempt_id) from exc
    if created is not True: raise DispatchUncertain("CURRENT_RUN_ACK_NOT_PERSISTED:"+attempt_id)
    return {"status":"CURRENT_RUN_ADMITTED","attempt_id":attempt_id,"run_ref":run_ref,"execution_count":None}
