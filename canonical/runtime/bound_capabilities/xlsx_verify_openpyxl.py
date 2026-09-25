#!/usr/bin/env python3
"""Independently reopen an XLSX workbook and compare it to canonical JSON records."""
from __future__ import annotations
import hashlib,json,pathlib,re,sys

def _safe(root,raw,require_file=True):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if require_file and not p.is_file():
        raise RuntimeError("INPUT_FILE_MISSING")
    return p

def _import_openpyxl():
    try:
        import openpyxl
        return openpyxl
    except ModuleNotFoundError:
        dist=pathlib.Path("/usr/lib/python3/dist-packages")
        if dist.is_dir() and str(dist) not in sys.path:
            sys.path.insert(0,str(dist))
        import openpyxl
        return openpyxl

def _find_collection(data,wanted,path=()):
    if isinstance(data,dict):
        if data and all(isinstance(v,dict) for v in data.values()):
            if any(wanted in rec.values() for rec in data.values()):
                return path,data
        for k,v in data.items():
            found=_find_collection(v,wanted,path+(str(k),))
            if found is not None:
                return found
    return None

def _status_value(goal,data):
    for token in re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b",str(goal or "")):
        if _find_collection(data,token) is not None:
            return token
    raise RuntimeError("XLSX_STATUS_VALUE_UNRESOLVED")

def _columns(goal):
    m=re.search(r"\bcolumns?\s+(.+?)(?=\.\s|\bfinally\b|$)",str(goal or ""),flags=re.I)
    if not m:
        raise RuntimeError("XLSX_COLUMNS_UNRESOLVED")
    raw=re.sub(r"\s+and\s+",", ",m.group(1),flags=re.I)
    return [x.strip(" .,;:") for x in raw.split(",") if x.strip(" .,;:")]

def _flatten_paths(record,path=()):
    out={}
    if isinstance(record,dict):
        for k,v in record.items():
            out.update(_flatten_paths(v,path+(str(k),)))
    else:
        out["_".join(path)]=record
    return out

def _cell(record,key,column):
    if column=="capability_id" or (column.endswith("_id") and column not in record):
        return key
    value=record[column] if column in record else _flatten_paths(record).get(column,"__MISSING__")
    if value=="__MISSING__":
        raise RuntimeError("XLSX_COLUMN_UNRESOLVED:"+column)
    if isinstance(value,(list,dict)):
        return json.dumps(value,sort_keys=True,separators=(",",":"))
    if value is None:
        return ""
    return value

def _norm(v):
    return "" if v is None else v

def run(args,root):
    source=_safe(root,args.get("json_path"))
    workbook_path=_safe(root,args.get("xlsx_path"))
    data=json.loads(source.read_text(encoding="utf-8"))
    goal=str(args.get("goal") or "")
    wanted=_status_value(goal,data)
    found=_find_collection(data,wanted)
    if found is None:
        raise RuntimeError("XLSX_STATUS_COLLECTION_NOT_FOUND")
    _,records=found

    # Verification clauses need not repeat the producer's column declaration.
    # Reopen the artifact, treat its header row as the claimed schema, then
    # resolve every claimed column against canonical source data. An invented
    # or unresolvable column fails closed.
    openpyxl=_import_openpyxl()
    wb=openpyxl.load_workbook(str(workbook_path),read_only=True,data_only=True)
    try:
        ws=wb[wb.sheetnames[0]]
        rows=list(ws.iter_rows(values_only=True))
    finally:
        wb.close()
    if not rows:
        raise RuntimeError("XLSX_WORKBOOK_EMPTY")
    cols=[str(x or "").strip() for x in rows[0]]
    if not cols or any(not x for x in cols) or len(set(cols))!=len(cols):
        raise RuntimeError("XLSX_HEADER_INVALID:"+json.dumps(cols))
    if "capability_id" not in cols:
        raise RuntimeError("XLSX_ID_COLUMN_REQUIRED")

    expected={}
    for key,record in sorted(records.items()):
        if wanted not in record.values():
            continue
        expected[str(key)]=[_cell(record,str(key),c) for c in cols]
    observed={}
    for row in rows[1:]:
        values=[_norm(x) for x in row[:len(cols)]]
        if not values or values[0]=="":
            continue
        key=str(values[0])
        if key in observed:
            raise RuntimeError("XLSX_DUPLICATE_ID:"+key)
        observed[key]=values
    if set(observed)!=set(expected):
        raise RuntimeError("XLSX_ID_SET_MISMATCH:"+json.dumps({
          "missing":sorted(set(expected)-set(observed)),
          "extra":sorted(set(observed)-set(expected))
        },sort_keys=True))
    mismatches=[]
    for key in sorted(expected):
        exp=expected[key]; obs=observed[key]
        for i,(a,b) in enumerate(zip(exp,obs)):
            if a==b:
                continue
            if isinstance(a,(int,float)) and isinstance(b,(int,float)) and float(a)==float(b):
                continue
            mismatches.append({"id":key,"column":cols[i],"expected":a,"observed":b})
    if mismatches:
        raise RuntimeError("XLSX_VALUE_MISMATCH:"+json.dumps(mismatches[:20],sort_keys=True))
    raw=workbook_path.read_bytes()
    return {
      "adapter":"xlsx_verify_openpyxl",
      "xlsx_path":str(workbook_path.relative_to(pathlib.Path(root).resolve())).replace("\\","/"),
      "xlsx_sha256":hashlib.sha256(raw).hexdigest(),
      "verified_rows":len(expected),
      "columns":cols,
      "status_value":wanted,
      "producer_independent_verifier":True,
      "verified":True,
    }
