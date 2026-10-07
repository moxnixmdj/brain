from __future__ import annotations
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SYMBOLIC_ADMISSION_PREDICATE_ROUTER_V1"
OPS = {"TRUE","FALSE","AND","OR","NOT","EQ","IN","EXISTS"}

def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",",":"), ensure_ascii=False)

def predicate_sha256(predicate: Mapping[str, Any]) -> str:
    return sha256(_canon(predicate).encode("utf-8")).hexdigest()

def _path_get(context: Any, path: str):
    cur=context
    if not isinstance(path,str) or not path:
        return False, None
    for part in path.split("."):
        if isinstance(cur, Mapping) and part in cur:
            cur=cur[part]
        elif isinstance(cur, Sequence) and not isinstance(cur,(str,bytes)) and part.isdigit():
            i=int(part)
            if i<0 or i>=len(cur):
                return False,None
            cur=cur[i]
        else:
            return False,None
    return True,cur

def _valid(node: Any) -> bool:
    if not isinstance(node, Mapping):
        return False
    op=node.get("op")
    if op not in OPS:
        return False
    if op in {"TRUE","FALSE"}:
        return set(node.keys())=={"op"}
    if op in {"AND","OR"}:
        args=node.get("args")
        return (
            set(node.keys())=={"op","args"}
            and isinstance(args,Sequence)
            and not isinstance(args,(str,bytes))
            and bool(args)
            and all(_valid(x) for x in args)
        )
    if op=="NOT":
        return set(node.keys())=={"op","arg"} and _valid(node.get("arg"))
    if op=="EXISTS":
        return set(node.keys())=={"op","path"} and isinstance(node.get("path"),str) and bool(node["path"])
    if op=="EQ":
        return set(node.keys())=={"op","path","value"} and isinstance(node.get("path"),str) and bool(node["path"])
    if op=="IN":
        vals=node.get("values")
        return (
            set(node.keys())=={"op","path","values"}
            and isinstance(node.get("path"),str)
            and bool(node["path"])
            and isinstance(vals,list)
            and bool(vals)
        )
    return False

def evaluate_predicate(node: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    if not _valid(node) or not isinstance(context, Mapping):
        return False
    op=node["op"]
    if op=="TRUE":
        return True
    if op=="FALSE":
        return False
    if op=="AND":
        return all(evaluate_predicate(x,context) for x in node["args"])
    if op=="OR":
        return any(evaluate_predicate(x,context) for x in node["args"])
    if op=="NOT":
        return not evaluate_predicate(node["arg"],context)
    ok,value=_path_get(context,node["path"])
    if op=="EXISTS":
        return ok
    if not ok:
        return False
    if op=="EQ":
        return value==node["value"]
    if op=="IN":
        return value in node["values"]
    return False

def _hex40(v: Any) -> bool:
    return isinstance(v,str) and len(v)==40 and all(c in "0123456789abcdef" for c in v)

def validate_route(route: Mapping[str, Any]) -> tuple[bool,str]:
    if not isinstance(route,Mapping):
        return False,"ROUTE_MAPPING_REQUIRED"
    for field in ("route_id","admission_predicate_id","scope_id"):
        if not isinstance(route.get(field),str) or not route[field].strip():
            return False,field.upper()+"_REQUIRED"
    pred=route.get("predicate")
    if not _valid(pred):
        return False,"PREDICATE_INVALID"
    if route.get("predicate_sha256")!=predicate_sha256(pred):
        return False,"PREDICATE_DIGEST_MISMATCH"
    for field in ("adequacy_certificate_blob_sha","admission_soundness_receipt_blob_sha"):
        if not _hex40(route.get(field)):
            return False,field.upper()+"_INVALID"
    receipt=route.get("admission_soundness_receipt")
    if not isinstance(receipt,Mapping):
        return False,"ADMISSION_SOUNDNESS_RECEIPT_REQUIRED"
    required={
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
        "admission_implies_route_adequacy":True,
    }
    if any(receipt.get(k)!=v for k,v in required.items()):
        return False,"ADMISSION_SOUNDNESS_UNPROVED"
    if receipt.get("route_id")!=route["route_id"]:
        return False,"RECEIPT_ROUTE_MISMATCH"
    if receipt.get("scope_id")!=route["scope_id"]:
        return False,"RECEIPT_SCOPE_MISMATCH"
    if receipt.get("admission_predicate_id")!=route["admission_predicate_id"]:
        return False,"RECEIPT_PREDICATE_ID_MISMATCH"
    if receipt.get("predicate_sha256")!=route["predicate_sha256"]:
        return False,"RECEIPT_PREDICATE_DIGEST_MISMATCH"
    if receipt.get("adequacy_certificate_blob_sha")!=route["adequacy_certificate_blob_sha"]:
        return False,"RECEIPT_ADEQUACY_BLOB_MISMATCH"
    return True,"PASS"

def route_context(registry: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(registry,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"REGISTRY_MAPPING_REQUIRED"}
    scope_id=registry.get("scope_id")
    routes=registry.get("routes")
    if not isinstance(scope_id,str) or not scope_id or not isinstance(routes,list):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"REGISTRY_INVALID"}
    matches=[]
    seen=set()
    for i,route in enumerate(routes):
        ok,reason=validate_route(route)
        if not ok:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,"index":i}
        if route["scope_id"]!=scope_id:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"ROUTE_SCOPE_MISMATCH","index":i}
        pid=route["admission_predicate_id"]
        if pid in seen:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"DUPLICATE_PREDICATE_ID","index":i}
        seen.add(pid)
        if evaluate_predicate(route["predicate"],context):
            matches.append(route["route_id"])
    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__SYMBOLIC_ADMISSION_EVALUATED",
        "scope_id":scope_id,
        "matched_route_ids":sorted(matches),
        "matched":bool(matches),
        "selected_cover_complete":False,
        "u_empty_authorized":False,
        "terminal_authority":False,
        "boundary":"SYMBOLIC_MATCHING_ONLY__EVERY_TRUE_PREDICATE_IS_SOUND_BY_BOUND_RECEIPT__GLOBAL_COVER_STILL_REQUIRES_INDEPENDENT_RESIDUAL_COMPLEMENT_UNSAT_OR_EQUIVALENT_TOTAL_COVER_PROOF",
    }
