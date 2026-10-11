"""Deterministic scientific artifact contract compiler and materializer.

Transforms only an already-verified scientific result into explicitly declared
JSON, CSV, or Markdown artifacts. It never invents output fields, never chooses
paths outside the supplied root, and delegates byte writes to the exact artifact
materializer with SHA-256 round-trip verification.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_SCIENTIFIC_ARTIFACT_CONTRACT_V1"
_PATH_PART=re.compile(r"^[A-Za-z0-9_.-]+$")
_LABEL=re.compile(r"^[A-Za-z0-9 _./:+()%-]{1,120}$")
MAX_ARTIFACTS=32
MAX_BYTES=16_000_000


class ScientificArtifactError(ValueError):
    pass


def _materialize_exact(output_path:Path,target_bytes:bytes,target_sha256:str)->dict[str,Any]:
    if not isinstance(target_bytes,bytes) or hashlib.sha256(target_bytes).hexdigest()!=target_sha256:
        return {"status":"FAIL_CLOSED","reason":"TARGET_BYTES_OR_SHA_INVALID"}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    tmp=output_path.with_name(output_path.name+".brain-tmp")
    try:
        tmp.write_bytes(target_bytes)
        observed=tmp.read_bytes()
        if observed!=target_bytes or hashlib.sha256(observed).hexdigest()!=target_sha256:
            tmp.unlink(missing_ok=True)
            return {"status":"FAIL_CLOSED","reason":"ROUNDTRIP_MISMATCH"}
        tmp.replace(output_path)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        return {"status":"FAIL_CLOSED","reason":"WRITE_FAILED","error":type(exc).__name__}
    return {"status":"PASS","output_path":str(output_path),"target_sha256":target_sha256,"byte_count":len(target_bytes)}


def _lookup(root:Any,path:str)->Any:
    if not isinstance(path,str) or not path:
        raise ScientificArtifactError("VALUE_PATH_INVALID")
    value=root
    for part in path.split("."):
        if not part or not _PATH_PART.fullmatch(part):
            raise ScientificArtifactError("VALUE_PATH_INVALID")
        if isinstance(value,Mapping):
            if part not in value:
                raise ScientificArtifactError("VALUE_PATH_MISSING:"+path)
            value=value[part]
        elif isinstance(value,list) and part.isdigit():
            idx=int(part)
            if idx<0 or idx>=len(value):
                raise ScientificArtifactError("VALUE_PATH_INDEX_INVALID:"+path)
            value=value[idx]
        else:
            raise ScientificArtifactError("VALUE_PATH_NOT_TRAVERSABLE:"+path)
    return value


def _safe_relative(path:Any)->str:
    if not isinstance(path,str) or not path or "\\" in path:
        raise ScientificArtifactError("ARTIFACT_PATH_INVALID")
    p=Path(path)
    if p.is_absolute() or any(x in {"",".."} for x in p.parts):
        raise ScientificArtifactError("ARTIFACT_PATH_INVALID")
    if len(p.parts)>8 or any(not _PATH_PART.fullmatch(x) for x in p.parts):
        raise ScientificArtifactError("ARTIFACT_PATH_INVALID")
    return p.as_posix()


def _scalar(value:Any)->str:
    if value is None:
        return ""
    if isinstance(value,(str,int,float,bool)):
        if isinstance(value,str):
            return value.replace("\r"," ").replace("\n"," ")
        return str(value)
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)


def _json_bytes(result:Mapping[str,Any],spec:Mapping[str,Any])->bytes:
    value=_lookup(result,str(spec.get("value_path") or ""))
    return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode("utf-8")


def _csv_bytes(result:Mapping[str,Any],spec:Mapping[str,Any])->bytes:
    rows=_lookup(result,str(spec.get("rows_path") or ""))
    raw_columns=spec.get("columns")
    if not isinstance(rows,list):
        raise ScientificArtifactError("CSV_ROWS_NOT_LIST")
    if not isinstance(raw_columns,list) or not raw_columns or len(raw_columns)>64:
        raise ScientificArtifactError("CSV_COLUMNS_INVALID")
    columns=[]
    seen=set()
    for row in raw_columns:
        if not isinstance(row,Mapping):
            raise ScientificArtifactError("CSV_COLUMN_INVALID")
        name=row.get("name"); path=row.get("path")
        if not isinstance(name,str) or not _LABEL.fullmatch(name) or name in seen:
            raise ScientificArtifactError("CSV_COLUMN_NAME_INVALID")
        if not isinstance(path,str) or not path:
            raise ScientificArtifactError("CSV_COLUMN_PATH_INVALID")
        seen.add(name); columns.append((name,path))
    stream=io.StringIO(newline="")
    writer=csv.DictWriter(stream,fieldnames=[x[0] for x in columns],lineterminator="\n")
    writer.writeheader()
    for item in rows:
        if not isinstance(item,Mapping):
            raise ScientificArtifactError("CSV_ROW_NOT_OBJECT")
        writer.writerow({name:_scalar(_lookup(item,path)) for name,path in columns})
    return stream.getvalue().encode("utf-8")


def _markdown_bytes(result:Mapping[str,Any],spec:Mapping[str,Any])->bytes:
    title=spec.get("title")
    fields=spec.get("fields")
    if not isinstance(title,str) or not _LABEL.fullmatch(title):
        raise ScientificArtifactError("MARKDOWN_TITLE_INVALID")
    if not isinstance(fields,list) or not fields or len(fields)>128:
        raise ScientificArtifactError("MARKDOWN_FIELDS_INVALID")
    lines=["# "+title,""]
    seen=set()
    for row in fields:
        if not isinstance(row,Mapping):
            raise ScientificArtifactError("MARKDOWN_FIELD_INVALID")
        label=row.get("label"); path=row.get("path")
        if not isinstance(label,str) or not _LABEL.fullmatch(label) or label in seen:
            raise ScientificArtifactError("MARKDOWN_LABEL_INVALID")
        if not isinstance(path,str) or not path:
            raise ScientificArtifactError("MARKDOWN_FIELD_PATH_INVALID")
        seen.add(label)
        lines.append(f"- {label}: {_scalar(_lookup(result,path))}")
    return ("\n".join(lines)+"\n").encode("utf-8")


def compile_artifacts(verified_result:Mapping[str,Any],specs:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if not isinstance(verified_result,Mapping) or verified_result.get("verified") is not True:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"VERIFIED_RESULT_REQUIRED","artifacts":[]}
    if not isinstance(specs,Sequence) or isinstance(specs,(str,bytes)) or not 1<=len(specs)<=MAX_ARTIFACTS:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"ARTIFACT_SPECS_INVALID","artifacts":[]}
    try:
        out=[]; paths=set()
        for raw in specs:
            if not isinstance(raw,Mapping):
                raise ScientificArtifactError("ARTIFACT_SPEC_INVALID")
            rel=_safe_relative(raw.get("relative_path"))
            if rel in paths:
                raise ScientificArtifactError("ARTIFACT_PATH_DUPLICATE")
            paths.add(rel)
            fmt=raw.get("format")
            if fmt=="json":
                data=_json_bytes(verified_result,raw)
            elif fmt=="csv":
                data=_csv_bytes(verified_result,raw)
            elif fmt=="markdown":
                data=_markdown_bytes(verified_result,raw)
            else:
                raise ScientificArtifactError("ARTIFACT_FORMAT_UNSUPPORTED")
            if not data or len(data)>MAX_BYTES:
                raise ScientificArtifactError("ARTIFACT_BYTES_INVALID")
            out.append({
                "relative_path":rel,"format":fmt,"bytes":data,
                "sha256":hashlib.sha256(data).hexdigest(),"byte_count":len(data),
            })
        return {
            "schema":SCHEMA,"status":"COMPILED","artifacts":out,
            "artifact_count":len(out),"semantic_authority":False,"terminal_authority":False,
        }
    except ScientificArtifactError as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":str(exc),"artifacts":[]}


def materialize_artifacts(verified_result:Mapping[str,Any],specs:Sequence[Mapping[str,Any]],output_root:str|Path)->dict[str,Any]:
    compiled=compile_artifacts(verified_result,specs)
    if compiled.get("status")!="COMPILED":
        return compiled
    root=Path(output_root).resolve()
    receipts=[]
    for row in compiled["artifacts"]:
        target=(root/row["relative_path"]).resolve()
        if target==root or root not in target.parents:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"OUTPUT_ESCAPE","receipts":receipts}
        receipt=_materialize_exact(target,row["bytes"],row["sha256"])
        if receipt.get("status")!="PASS":
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"MATERIALIZATION_FAILED","receipts":receipts+[receipt]}
        observed=target.read_bytes()
        if hashlib.sha256(observed).hexdigest()!=row["sha256"] or observed!=row["bytes"]:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"POST_WRITE_READBACK_MISMATCH","receipts":receipts}
        receipts.append({
            "relative_path":row["relative_path"],"format":row["format"],
            "sha256":row["sha256"],"byte_count":row["byte_count"],
            "materializer_receipt":receipt,
        })
    return {
        "schema":SCHEMA,"status":"PASS__DECLARED_SCIENTIFIC_ARTIFACTS_MATERIALIZED_AND_VERIFIED",
        "receipts":receipts,"artifact_count":len(receipts),
        "semantic_authority":False,"terminal_authority":False,
    }
