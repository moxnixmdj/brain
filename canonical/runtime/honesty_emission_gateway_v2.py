from __future__ import annotations

import hashlib, json
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import honesty_emission_gateway_v1 as v1
from canonical.runtime import zero_ambient_namespace_launcher_v1 as namespace

CAPSULE_SCHEMA="PROJECT_BRAIN_EXTERNAL_EMISSION_CAPSULE_V2"
RESULT_SCHEMA="PROJECT_BRAIN_HONESTY_EMISSION_GATEWAY_RESULT_V2"

class EmissionGatewayV2Error(ValueError): pass

def make_capsule(*,sequence:int,emission_id:str,payload:Any,honesty_record:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(sequence,int) or isinstance(sequence,bool) or sequence<0:
        raise EmissionGatewayV2Error("SEQUENCE_INVALID")
    if not isinstance(emission_id,str) or not emission_id.strip():
        raise EmissionGatewayV2Error("EMISSION_ID_INVALID")
    if not isinstance(honesty_record,Mapping):
        raise EmissionGatewayV2Error("HONESTY_RECORD_INVALID")
    eid=emission_id.strip(); psha=v1._sha(payload); record=dict(honesty_record)
    record["emission_binding"]={"emission_id":eid,"sequence":sequence,"payload_sha256":psha}
    return {
      "schema":CAPSULE_SCHEMA,"sequence":sequence,"emission_id":eid,
      "payload":payload,"payload_sha256":psha,
      "honesty_record":record,"honesty_record_sha256":v1._sha(record)
    }

def encode_capsule(capsule:Mapping[str,Any])->bytes:
    if not isinstance(capsule,Mapping): raise EmissionGatewayV2Error("CAPSULE_MAPPING_REQUIRED")
    return v1._canon(dict(capsule))+b"\n"

def _validate_binding(value:Mapping[str,Any],expected_sequence:int)->None:
    if value.get("schema")!=CAPSULE_SCHEMA: raise EmissionGatewayV2Error("CAPSULE_SCHEMA_INVALID")
    if value.get("sequence")!=expected_sequence: raise EmissionGatewayV2Error("SEQUENCE_NOT_CONTIGUOUS")
    eid=value.get("emission_id")
    if not isinstance(eid,str) or not eid.strip(): raise EmissionGatewayV2Error("EMISSION_ID_INVALID")
    if value.get("payload_sha256")!=v1._sha(value.get("payload")):
        raise EmissionGatewayV2Error("PAYLOAD_HASH_MISMATCH")
    record=value.get("honesty_record")
    if not isinstance(record,Mapping): raise EmissionGatewayV2Error("HONESTY_RECORD_INVALID")
    if value.get("honesty_record_sha256")!=v1._sha(record):
        raise EmissionGatewayV2Error("HONESTY_RECORD_HASH_MISMATCH")
    binding=record.get("emission_binding")
    if not isinstance(binding,Mapping): raise EmissionGatewayV2Error("EMISSION_BINDING_MISSING")
    if binding.get("emission_id")!=eid.strip(): raise EmissionGatewayV2Error("EMISSION_ID_BINDING_MISMATCH")
    if binding.get("sequence")!=expected_sequence: raise EmissionGatewayV2Error("SEQUENCE_BINDING_MISMATCH")
    if binding.get("payload_sha256")!=value.get("payload_sha256"):
        raise EmissionGatewayV2Error("PAYLOAD_BINDING_MISMATCH")

def adjudicate_broker_payload(raw:bytes)->list[dict[str,Any]]:
    if not isinstance(raw,bytes): raise EmissionGatewayV2Error("BROKER_BYTES_REQUIRED")
    if not raw: return []
    try: lines=raw.decode("utf-8","strict").splitlines()
    except UnicodeDecodeError as exc: raise EmissionGatewayV2Error("BROKER_UTF8_INVALID") from exc
    if not lines or any(not x.strip() for x in lines): raise EmissionGatewayV2Error("BROKER_EMPTY_LINE")
    seen=set(); out=[]
    for index,line in enumerate(lines):
        try: value=json.loads(line)
        except Exception as exc: raise EmissionGatewayV2Error("BROKER_JSON_INVALID") from exc
        if not isinstance(value,Mapping): raise EmissionGatewayV2Error("CAPSULE_OBJECT_REQUIRED")
        _validate_binding(value,index)
        eid=str(value["emission_id"]).strip()
        if eid in seen: raise EmissionGatewayV2Error("EMISSION_ID_DUPLICATE")
        seen.add(eid)
        shadow=dict(value); shadow["schema"]=v1.CAPSULE_SCHEMA
        out.append(v1._parse_line(json.dumps(shadow,separators=(",",":")),index,set()))
    return out

def run(policy:Mapping[str,Any],*,confined_runner:Callable[[Mapping[str,Any]],Mapping[str,Any]]=namespace.run_confined)->dict[str,Any]:
    common={
      "schema":RESULT_SCHEMA,"emissions":[],"emission_count":0,
      "raw_broker_exposed":False,"stdout_exposed":False,"stderr_exposed":False,
      "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
      "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
      "fresh_reality_authority":False
    }
    try:
        rr=confined_runner(policy)
        if not isinstance(rr,Mapping): raise EmissionGatewayV2Error("CONFINED_RESULT_INVALID")
        if str(rr.get("status") or "")!="CHILD_EXITED": raise EmissionGatewayV2Error("CHILD_NOT_NORMAL")
        if rr.get("returncode")!=0: raise EmissionGatewayV2Error("CHILD_EXIT_NONZERO")
        if rr.get("material_effects_committed")!=0: raise EmissionGatewayV2Error("MATERIAL_EFFECT_STATE_NOT_ZERO")
        broker=rr.get("broker_payload",b"")
        if not isinstance(broker,bytes): raise EmissionGatewayV2Error("BROKER_BYTES_INVALID")
        if rr.get("broker_bytes")!=len(broker): raise EmissionGatewayV2Error("BROKER_LENGTH_MISMATCH")
        bsha=hashlib.sha256(broker).hexdigest()
        if rr.get("broker_sha256")!=bsha: raise EmissionGatewayV2Error("BROKER_HASH_MISMATCH")
        emissions=adjudicate_broker_payload(broker)
        return {**common,"status":"PASS__CONTENT_BOUND_HONESTY_EMISSIONS_ONLY",
          "emissions":emissions,"emission_count":len(emissions),
          "child_status":"CHILD_EXITED","child_returncode":0,
          "policy_sha256":rr.get("policy_sha256"),"broker_bytes":len(broker),"broker_sha256":bsha}
    except Exception as exc:
        return {**common,"status":"FAIL_CLOSED","errors":[type(exc).__name__+":"+str(exc)]}
