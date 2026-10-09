from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
from typing import Any,Mapping,Sequence

SCHEMA="PROJECT_BRAIN_SEMANTIC_HYPOTHESIS_COMPLETENESS_V1"
UNIVERSE_SCHEMA="PROJECT_BRAIN_CLOSED_SEMANTIC_HYPOTHESIS_UNIVERSE_V1"
CLOSURE="EXACTLY_THESE_INTERPRETATIONS_ARE_ADMISSIBLE_WITHIN_SCOPE"

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _sha(x:Any)->str:
    return sha256(_canon(x).encode()).hexdigest()

def _fail(reason:str)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":reason,
            "hypothesis_set_complete":False,"terminal_authority":False,"terminal_credit_delta":0}

def _strings(v:Any,name:str)->list[str]:
    if not isinstance(v,Sequence) or isinstance(v,(str,bytes)) or not v:
        raise ValueError(name+"_INVALID")
    out=[]
    for x in v:
        if not isinstance(x,str) or not x.strip():
            raise ValueError(name+"_INVALID")
        x=x.strip()
        if x in out:
            raise ValueError(name+"_DUPLICATE")
        out.append(x)
    return out

def compile_universe(universe:Mapping[str,Any],*,expected_manifest_sha256:str)->dict[str,Any]:
    try:
        if not isinstance(universe,Mapping) or universe.get("schema")!=UNIVERSE_SCHEMA:
            raise ValueError("UNIVERSE_SCHEMA_INVALID")
        if not isinstance(expected_manifest_sha256,str) or len(expected_manifest_sha256)!=64:
            raise ValueError("EXPECTED_MANIFEST_SHA256_REQUIRED")
        actual=_sha(dict(universe))
        if actual!=expected_manifest_sha256:
            raise ValueError("MANIFEST_SHA256_MISMATCH")
        allowed={"schema","universe_id","scope_id","closure_statement",
                 "terminal_signature_keys","interpretations","observations"}
        if set(universe)!=allowed:
            raise ValueError("UNIVERSE_FIELD_SET_NOT_EXACT")
        uid=universe.get("universe_id"); sid=universe.get("scope_id")
        if not isinstance(uid,str) or not uid.strip() or not isinstance(sid,str) or not sid.strip():
            raise ValueError("UNIVERSE_OR_SCOPE_ID_INVALID")
        if universe.get("closure_statement")!=CLOSURE:
            raise ValueError("CLOSED_WORLD_STATEMENT_MISSING")
        keys=_strings(universe.get("terminal_signature_keys"),"TERMINAL_SIGNATURE_KEYS")
        keyset=set(keys)
        rows=universe.get("interpretations")
        if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
            raise ValueError("INTERPRETATIONS_INVALID")
        worlds=[]; ids=[]
        for i,row in enumerate(rows):
            if not isinstance(row,Mapping) or set(row)!={"world_id","terminal_signature"}:
                raise ValueError(f"INTERPRETATION_INVALID:{i}")
            wid=row.get("world_id"); sig=row.get("terminal_signature")
            if not isinstance(wid,str) or not wid.strip() or wid in ids:
                raise ValueError(f"WORLD_ID_INVALID:{i}")
            if not isinstance(sig,Mapping) or set(sig)!=keyset:
                raise ValueError(f"TERMINAL_SIGNATURE_INCOMPLETE:{wid}")
            ids.append(wid)
            worlds.append({"world_id":wid,"terminal_signature_complete":True,
                           "terminal_signature":deepcopy(dict(sig))})
        obsraw=universe.get("observations")
        if not isinstance(obsraw,Sequence) or isinstance(obsraw,(str,bytes)):
            raise ValueError("OBSERVATIONS_INVALID")
        observations=[]; oids=set()
        for i,row in enumerate(obsraw):
            if not isinstance(row,Mapping) or set(row)!={"observation_id","cost_units","outcomes"}:
                raise ValueError(f"OBSERVATION_INVALID:{i}")
            oid=row.get("observation_id"); cost=row.get("cost_units"); outcomes=row.get("outcomes")
            if not isinstance(oid,str) or not oid.strip() or oid in oids:
                raise ValueError(f"OBSERVATION_ID_INVALID:{i}")
            if not isinstance(cost,(int,float)) or isinstance(cost,bool) or cost<0:
                raise ValueError(f"OBSERVATION_COST_INVALID:{oid}")
            if not isinstance(outcomes,Mapping) or set(outcomes)!=set(ids):
                raise ValueError(f"OBSERVATION_DOMAIN_INCOMPLETE:{oid}")
            oids.add(oid)
            observations.append({"observation_id":oid,"cost_units":float(cost),
                                 "outcome_map_complete":True,"outcomes":deepcopy(dict(outcomes))})
        cert={"universe_id":uid.strip(),"scope_id":sid.strip(),"manifest_sha256":actual,
              "world_ids":ids,"terminal_signature_keys":keys,"observation_ids":sorted(oids)}
        return {"schema":SCHEMA,"status":"PASS__SOURCE_BOUND_CLOSED_HYPOTHESIS_UNIVERSE_COMPILED",
                "pass":True,"hypothesis_set_complete":True,
                "completeness_scope":"EXACT_CONTENT_ADDRESSED_CLOSED_UNIVERSE_ONLY",
                "completeness_authority":"SOURCE_BOUND_CLOSED_ENUMERATION",
                "frontier_problem":{"hypothesis_set_complete":True,"worlds":worlds,"observations":observations},
                "completeness_certificate":{**cert,"certificate_sha256":_sha(cert)},
                "global_semantic_completeness_claimed":False,
                "terminal_authority":False,"terminal_credit_delta":0}
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc))
