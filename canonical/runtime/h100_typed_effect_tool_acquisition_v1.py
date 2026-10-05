"""Content-addressed typed effect-tool acquisition for H100.

This broker executes declarative tool packs, not arbitrary code. Effects are
confined to a caller-supplied sandbox root and limited to canonical JSON writes,
JSONL append, and SHA-256 readback.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from canonical.runtime import h100_verified_capability_registry_v7 as registry

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_TYPED_EFFECT_TOOL_ACQUISITION_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_TYPED_EFFECT_TOOL_ACQUISITION_RESULT_V1"
PACK_SCHEMA="PROJECT_BRAIN_H100_TYPED_EFFECT_TOOL_PACK_V1"
_ALLOWED_TYPES={"string","int","float","bool"}
_ALLOWED_EFFECTS={"WRITE_JSON","APPEND_JSONL","RETURN_SHA256"}
_FIELD_RE=re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_PATH_RE=re.compile(r"^[A-Za-z0-9._/-]+$")

class TypedEffectToolError(ValueError):
    pass

def _git_blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _scalar(v:Any)->bool:
    return v is None or isinstance(v,(str,int,float,bool))

def _validate_path(rel:Any)->str:
    if not isinstance(rel,str) or not rel or "\\" in rel or not _PATH_RE.fullmatch(rel):
        raise TypedEffectToolError("PATH_INVALID")
    p=PurePosixPath(rel)
    if p.is_absolute() or any(part in {"","..","."} for part in p.parts):
        raise TypedEffectToolError("PATH_TRAVERSAL_OR_ABSOLUTE")
    return rel

def _validate_object_spec(spec:Any,input_schema:Mapping[str,Any])->None:
    if not isinstance(spec,Mapping) or not spec:
        raise TypedEffectToolError("OBJECT_SPEC_INVALID")
    for key,val in spec.items():
        if not isinstance(key,str) or not _FIELD_RE.fullmatch(key):
            raise TypedEffectToolError("OBJECT_FIELD_INVALID")
        if not isinstance(val,Mapping) or len(val)!=1:
            raise TypedEffectToolError("OBJECT_VALUE_SPEC_INVALID")
        if "input" in val:
            name=val["input"]
            if not isinstance(name,str) or name not in input_schema:
                raise TypedEffectToolError("OBJECT_INPUT_REF_INVALID")
        elif "const" in val:
            c=val["const"]
            if not _scalar(c) or (isinstance(c,float) and not math.isfinite(c)):
                raise TypedEffectToolError("OBJECT_CONST_INVALID")
        else:
            raise TypedEffectToolError("OBJECT_VALUE_SPEC_INVALID")

def load_tool_pack(path:Path,expected_git_blob_sha:str,contract:Mapping[str,Any])->dict[str,Any]:
    raw=Path(path).read_bytes()
    actual=_git_blob_sha(raw)
    if actual!=expected_git_blob_sha:
        raise TypedEffectToolError("PACK_GIT_BLOB_SHA_MISMATCH")
    try:
        pack=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise TypedEffectToolError("PACK_JSON_INVALID") from exc
    if pack.get("schema")!=PACK_SCHEMA or pack.get("source_class")!="CONTENT_ADDRESSED_TYPED_EFFECT_TOOL_PACK":
        raise TypedEffectToolError("PACK_SCHEMA_OR_SOURCE_INVALID")
    tool_id=pack.get("tool_id")
    if not isinstance(tool_id,str) or not _FIELD_RE.fullmatch(tool_id):
        raise TypedEffectToolError("TOOL_ID_INVALID")
    schema=pack.get("input_schema")
    if not isinstance(schema,Mapping) or not schema:
        raise TypedEffectToolError("INPUT_SCHEMA_INVALID")
    for name,typ in schema.items():
        if not isinstance(name,str) or not _FIELD_RE.fullmatch(name) or typ not in _ALLOWED_TYPES:
            raise TypedEffectToolError("INPUT_SCHEMA_INVALID")
    effects=pack.get("effects")
    if not isinstance(effects,list) or not effects or len(effects)>int(contract["max_effects"]):
        raise TypedEffectToolError("EFFECTS_INVALID")
    for eff in effects:
        if not isinstance(eff,Mapping):
            raise TypedEffectToolError("EFFECT_INVALID")
        op=eff.get("op")
        if op not in _ALLOWED_EFFECTS:
            raise TypedEffectToolError("EFFECT_OPCODE_NOT_ALLOWED")
        _validate_path(eff.get("path"))
        if op in {"WRITE_JSON","APPEND_JSONL"}:
            _validate_object_spec(eff.get("object"),schema)
            if set(eff)!={"op","path","object"}:
                raise TypedEffectToolError("EFFECT_FIELDS_INVALID")
        else:
            if set(eff)!={"op","path"}:
                raise TypedEffectToolError("EFFECT_FIELDS_INVALID")
    return {"pack":pack,"git_blob_sha":actual}

def _validate_input(payload:Any,schema:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping) or set(payload)!=set(schema):
        raise TypedEffectToolError("INPUT_KEYS_INVALID")
    out={}
    for name,typ in schema.items():
        v=payload[name]
        if typ=="string":
            if not isinstance(v,str) or len(v)>1024: raise TypedEffectToolError("INPUT_TYPE_INVALID:"+name)
            out[name]=v
        elif typ=="int":
            if not isinstance(v,int) or isinstance(v,bool): raise TypedEffectToolError("INPUT_TYPE_INVALID:"+name)
            out[name]=v
        elif typ=="float":
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(float(v)):
                raise TypedEffectToolError("INPUT_TYPE_INVALID:"+name)
            out[name]=float(v)
        elif typ=="bool":
            if not isinstance(v,bool): raise TypedEffectToolError("INPUT_TYPE_INVALID:"+name)
            out[name]=v
        else:
            raise TypedEffectToolError("INPUT_TYPE_UNKNOWN")
    return out

def _materialize_object(spec:Mapping[str,Any],payload:Mapping[str,Any])->dict[str,Any]:
    out={}
    for k,v in spec.items():
        out[k]=payload[v["input"]] if "input" in v else v["const"]
    return out

def _canonical_json_bytes(obj:Any)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _safe_target(root:Path,rel:str)->Path:
    root=root.resolve()
    p=PurePosixPath(_validate_path(rel))
    cur=root
    for part in p.parts:
        cur=cur/part
        if cur.exists() and cur.is_symlink():
            raise TypedEffectToolError("SYMLINK_COMPONENT_REJECTED")
    target=(root/Path(*p.parts)).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise TypedEffectToolError("TARGET_ESCAPES_SANDBOX") from exc
    return target

def _hash_file(path:Path)->dict[str,Any]:
    raw=path.read_bytes()
    return {"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}

def execute_tool(loaded:Mapping[str,Any],payload:Mapping[str,Any],sandbox_root:Path,max_output_bytes:int)->dict[str,Any]:
    root=Path(sandbox_root)
    root.mkdir(parents=True,exist_ok=True)
    if root.is_symlink():
        raise TypedEffectToolError("SANDBOX_ROOT_SYMLINK_REJECTED")
    pack=loaded["pack"]
    data=_validate_input(payload,pack["input_schema"])
    receipts=[]
    for eff in pack["effects"]:
        op=eff["op"]; target=_safe_target(root,eff["path"])
        if op=="WRITE_JSON":
            target.parent.mkdir(parents=True,exist_ok=True)
            raw=_canonical_json_bytes(_materialize_object(eff["object"],data))
            if len(raw)>max_output_bytes: raise TypedEffectToolError("OUTPUT_LIMIT_EXCEEDED")
            tmp=target.with_name(target.name+".tmp-h100")
            tmp.write_bytes(raw)
            os.replace(tmp,target)
            receipts.append({"op":op,"path":eff["path"],**_hash_file(target)})
        elif op=="APPEND_JSONL":
            target.parent.mkdir(parents=True,exist_ok=True)
            raw=_canonical_json_bytes(_materialize_object(eff["object"],data))+b"\n"
            current=target.stat().st_size if target.exists() else 0
            if current+len(raw)>max_output_bytes: raise TypedEffectToolError("OUTPUT_LIMIT_EXCEEDED")
            with target.open("ab") as f:
                f.write(raw)
            receipts.append({"op":op,"path":eff["path"],**_hash_file(target)})
        elif op=="RETURN_SHA256":
            if not target.is_file(): raise TypedEffectToolError("RETURN_TARGET_MISSING")
            receipts.append({"op":op,"path":eff["path"],**_hash_file(target)})
        else:
            raise TypedEffectToolError("EFFECT_OPCODE_NOT_ALLOWED")
    return {
        "tool_id":pack["tool_id"],
        "pack_git_blob_sha":loaded["git_blob_sha"],
        "receipts":receipts,
        "sandbox_root":str(root.resolve()),
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "arbitrary_code_execution":0,
        "shell_calls":0,
        "subprocess_calls":0,
        "network_calls":0,
    }

def _registry_absent(tool_id:str)->bool:
    snap=registry.registry_snapshot()
    return all(row.get("capability_id")!=tool_id for row in snap["entries"])

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    contract=pre["tool_contract"]
    results=[]
    all_pass=True
    for spec in pre["packs"]:
        loaded=load_tool_pack(ROOT/spec["path"],spec["git_blob_sha"],contract)
        absent=_registry_absent(spec["tool_id"])
        if spec["tool_id"]=="JSON_RECEIPT_WRITER_V1":
            with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b, tempfile.TemporaryDirectory() as c:
                seed1=execute_tool(loaded,spec["seed_input"],Path(a),int(contract["max_output_bytes_per_file"]))
                seed2=execute_tool(loaded,spec["seed_input"],Path(b),int(contract["max_output_bytes_per_file"]))
                transfer=execute_tool(loaded,spec["transfer_input"],Path(c),int(contract["max_output_bytes_per_file"]))
                rb1=Path(a,"receipts/result.json").read_bytes()
                rb2=Path(b,"receipts/result.json").read_bytes()
                tb=Path(c,"receipts/result.json").read_bytes()
                seed_obj=json.loads(rb1); transfer_obj=json.loads(tb)
                deterministic=rb1==rb2
                passed=absent and deterministic and seed_obj==spec["expected_seed_object"] and transfer_obj==spec["expected_transfer_object"]
                result={"tool_id":spec["tool_id"],"registry_v7_absent":absent,"deterministic_replay":deterministic,"seed_object":seed_obj,"transfer_object":transfer_obj,"seed_receipts":seed1["receipts"],"transfer_receipts":transfer["receipts"],"pass":passed}
        elif spec["tool_id"]=="JSONL_LEDGER_APPEND_V1":
            def sequence(root):
                a=execute_tool(loaded,spec["seed_input"],Path(root),int(contract["max_output_bytes_per_file"]))
                b=execute_tool(loaded,spec["transfer_input"],Path(root),int(contract["max_output_bytes_per_file"]))
                raw=Path(root,"ledger/events.jsonl").read_bytes()
                rows=[json.loads(x) for x in raw.decode().splitlines()]
                return a,b,raw,rows
            with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
                a1,b1,raw1,rows1=sequence(a)
                a2,b2,raw2,rows2=sequence(b)
                deterministic=raw1==raw2
                passed=absent and deterministic and rows1==spec["expected_rows"] and rows2==spec["expected_rows"]
                result={"tool_id":spec["tool_id"],"registry_v7_absent":absent,"deterministic_replay":deterministic,"rows":rows1,"seed_receipts":a1["receipts"],"transfer_receipts":b1["receipts"],"pass":passed}
        else:
            raise TypedEffectToolError("TOOL_ID_UNKNOWN")
        all_pass=all_pass and result["pass"]
        results.append(result)
    return {
        "schema":SCHEMA,
        "status":"PASS__CONTENT_ADDRESSED_TYPED_EFFECT_TOOL_ACQUISITION_TWO_OF_TWO__ZERO_CREDIT" if all_pass else "FAIL__TYPED_EFFECT_TOOL_RESIDUAL",
        "tools":results,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "arbitrary_code_execution":0,
        "shell_calls":0,
        "subprocess_calls":0,
        "network_calls":0,
        "h100_terminal_credit_delta":0,
        "hard_nonclaims":["NO_ARBITRARY_EXTERNAL_BINARY_SHELL_OR_NETWORK_SERVICE_ACQUISITION","NO_H100_TERMINAL_CREDIT"],
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
