"""Benchmark-independent numeric scientific resource pipeline V1.

Discovers bounded local tabular resources, compiles each against the explicit
instruction, requires exactly one compilable table, then delegates solving,
verification, and optional artifact production to the verified numeric pipeline.

No benchmark identifiers, model calls, network calls, or dynamic code.
"""
from __future__ import annotations

import csv
from hashlib import sha256
import json
import pathlib
from typing import Any, Mapping, Sequence

from canonical.runtime import scientific_numeric_task_compiler_v1 as compiler
from canonical.runtime import scientific_numeric_task_pipeline_v1 as pipeline

SCHEMA="PROJECT_BRAIN_SCIENTIFIC_NUMERIC_RESOURCE_PIPELINE_V1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0
NETWORK_DEPENDENCY_COUNT=0
MAX_ROOTS=16
MAX_FILES=64
MAX_FILE_BYTES=20_000_000
MAX_ROWS_PER_TABLE=100_000
EXTENSIONS=frozenset({".csv",".tsv",".txt",".dat",".json"})


def _canon(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False,default=str)


def _sha(value:Any)->str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _fail(reason:str,*,attempts=None,details=None)->dict[str,Any]:
    out={
        "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"verified":False,
        "reason":reason,"attempts":list(attempts or []),
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "network_dependency_count":0,"benchmark_identifier_used_for_routing":False,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    if details: out["details"]=dict(details)
    return out


def _safe_roots(raw:Any)->list[pathlib.Path]:
    if not isinstance(raw,Sequence) or isinstance(raw,(str,bytes)) or not raw or len(raw)>MAX_ROOTS:
        raise ValueError("RESOURCE_ROOTS_INVALID")
    out=[]
    for item in raw:
        if not isinstance(item,(str,pathlib.Path)):
            raise ValueError("RESOURCE_ROOT_INVALID")
        p=pathlib.Path(item).expanduser().resolve()
        if p not in out: out.append(p)
    return out


def _discover(roots:list[pathlib.Path],exclude:list[pathlib.Path])->list[pathlib.Path]:
    found=[]; seen=set()
    for root in roots:
        if not root.exists(): continue
        candidates=[root] if root.is_file() else root.rglob("*")
        for p in candidates:
            try:
                rp=p.resolve()
                if not rp.is_file() or rp.suffix.lower() not in EXTENSIONS: continue
                if any(rp==x or x in rp.parents for x in exclude): continue
                size=rp.stat().st_size
                if size<=0 or size>MAX_FILE_BYTES: continue
            except Exception:
                continue
            key=str(rp)
            if key in seen: continue
            seen.add(key); found.append(rp)
            if len(found)>=MAX_FILES: return sorted(found)
    return sorted(found)


def _read_delimited(path:pathlib.Path)->list[dict[str,Any]]:
    raw=path.read_text(encoding="utf-8",errors="replace")
    sample=raw[:4096]
    try:
        dialect=csv.Sniffer().sniff(sample,delimiters=",\t;|")
        delim=dialect.delimiter
    except Exception:
        delim="\t" if "\t" in sample and "," not in sample else ","
    out=[]
    for i,row in enumerate(csv.DictReader(raw.splitlines(),delimiter=delim)):
        if i>=MAX_ROWS_PER_TABLE: break
        if isinstance(row,dict): out.append(dict(row))
    return out


def _json_records(value:Any)->list[dict[str,Any]]:
    if isinstance(value,list) and all(isinstance(x,dict) for x in value):
        return [dict(x) for x in value[:MAX_ROWS_PER_TABLE]]
    if isinstance(value,dict):
        for key in ("rows","records","data","observations","measurements"):
            child=value.get(key)
            if isinstance(child,list) and all(isinstance(x,dict) for x in child):
                return [dict(x) for x in child[:MAX_ROWS_PER_TABLE]]
        lists={str(k):v for k,v in value.items() if isinstance(v,list)}
        if lists:
            n=min((len(v) for v in lists.values()),default=0)
            if n>0:
                return [{k:v[i] for k,v in lists.items()} for i in range(min(n,MAX_ROWS_PER_TABLE))]
    return []


def _read_table(path:pathlib.Path)->list[dict[str,Any]]:
    if path.suffix.lower()==".json":
        try: return _json_records(json.loads(path.read_text(encoding="utf-8")))
        except Exception: return []
    return _read_delimited(path)


def bind_resource(instruction:str,roots:Any,*,exclude_roots:Any=None)->dict[str,Any]:
    if not isinstance(instruction,str) or not instruction.strip():
        return _fail("INSTRUCTION_INVALID")
    try:
        root_paths=_safe_roots(roots)
        excludes=[] if exclude_roots is None else _safe_roots(exclude_roots)
    except ValueError as exc:
        return _fail(str(exc))
    files=_discover(root_paths,excludes)
    attempts=[]; candidates=[]
    for path in files:
        try: rows=_read_table(path)
        except Exception as exc:
            attempts.append({"path":str(path),"status":"READ_FAILED","error_type":type(exc).__name__})
            continue
        if len(rows)<4:
            attempts.append({"path":str(path),"status":"TABLE_INSUFFICIENT_ROWS","row_count":len(rows)})
            continue
        compiled=compiler.compile_numeric_task(instruction,rows)
        attempt={
            "path":str(path),"row_count":len(rows),"compile_status":compiled.get("status"),
            "family":compiled.get("family"),"reason":compiled.get("reason"),
        }
        attempts.append(attempt)
        if compiled.get("status")=="COMPILED":
            candidates.append((path,rows,compiled))
    if not candidates:
        return _fail("NO_COMPILABLE_NUMERIC_RESOURCE",attempts=attempts,
                     details={"discovered_file_count":len(files)})
    if len(candidates)>1:
        return _fail("AMBIGUOUS_MULTIPLE_COMPILABLE_NUMERIC_RESOURCES",attempts=attempts,
                     details={"candidate_paths":[str(x[0]) for x in candidates]})
    path,rows,compiled=candidates[0]
    return {
        "schema":SCHEMA,"status":"PASS__UNIQUE_NUMERIC_RESOURCE_BOUND","pass":True,
        "selected_path":str(path),"row_count":len(rows),"rows_sha256":_sha(rows),
        "rows":rows,"compiler_receipt":compiled,"attempts":attempts,
        "discovered_file_count":len(files),
        "model_dependency_count":0,"external_model_runtime_calls":0,"network_dependency_count":0,
        "benchmark_identifier_used_for_routing":False,"terminal_authority":False,
    }


def execute(
    instruction:str,
    roots:Any,
    *,
    artifact_specs:Sequence[Mapping[str,Any]]|None=None,
    output_root:str|pathlib.Path|None=None,
)->dict[str,Any]:
    excludes=[output_root] if output_root is not None else None
    bound=bind_resource(instruction,roots,exclude_roots=excludes)
    if bound.get("pass") is not True:
        return bound
    inner=pipeline.execute(
        instruction,bound["rows"],artifact_specs=artifact_specs,output_root=output_root
    )
    if inner.get("verified") is not True:
        return _fail("INNER_SCIENTIFIC_PIPELINE_NOT_VERIFIED",attempts=bound.get("attempts"),
                     details={"binding_receipt":{k:v for k,v in bound.items() if k!="rows"},
                              "pipeline_receipt":inner})
    receipt={
        "schema":SCHEMA,"status":"PASS__RESOURCE_BOUND_SCIENTIFIC_PIPELINE_VERIFIED",
        "pass":True,"verified":True,
        "resource_binding":{k:v for k,v in bound.items() if k!="rows"},
        "scientific_pipeline":inner,
        "model_dependency_count":0,"external_model_runtime_calls":0,"network_dependency_count":0,
        "dynamic_code_execution":False,"benchmark_identifier_used_for_routing":False,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    receipt["receipt_sha256"]=_sha({
        "resource_binding":receipt["resource_binding"],
        "scientific_pipeline":inner,
    })
    return receipt
