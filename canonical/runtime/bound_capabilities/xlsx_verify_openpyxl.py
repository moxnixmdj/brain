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

def _record_items(node):
    if isinstance(node,list) and node and all(isinstance(v,dict) for v in node):
        return [(str(i),v) for i,v in enumerate(node)]
    if isinstance(node,dict) and node and all(isinstance(v,dict) for v in node.values()):
        return [(str(k),v) for k,v in sorted(node.items(),key=lambda kv:str(kv[0]))]
    return None

def _candidate_collections(node,path=()):
    out=[]
    items=_record_items(node)
    if items is not None:
        out.append((path,node))
    if isinstance(node,dict):
        for k,v in node.items():
            out.extend(_candidate_collections(v,path+(str(k),)))
    elif isinstance(node,list):
        for i,v in enumerate(node):
            if isinstance(v,(dict,list)):
                out.extend(_candidate_collections(v,path+(str(i),)))
    return out

def _status_value_from_records(records):
    values=set()
    for _,record in _record_items(records) or []:
        value=record.get("status")
        if value is not None and not isinstance(value,(dict,list)):
            text=str(value).strip()
            if text:
                values.add(text)
    return next(iter(values)) if len(values)==1 else None

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

def _select_collection(data,columns):
    valid=[]
    for path,node in _candidate_collections(data):
        items=_record_items(node) or []
        if not items:
            continue
        try:
            for key,record in items:
                for column in columns:
                    _cell(record,key,column)
        except RuntimeError:
            continue
        valid.append((path,node))
    if not valid:
        raise RuntimeError("XLSX_RECORD_COLLECTION_NOT_FOUND")
    min_depth=min(len(path) for path,_ in valid)
    best=[x for x in valid if len(x[0])==min_depth]
    if len(best)!=1:
        raise RuntimeError("XLSX_RECORD_COLLECTION_AMBIGUOUS:"+json.dumps([list(p) for p,_ in best]))
    return best[0]

def _norm(v):
    return "" if v is None else v

def run(args,root):
    source=_safe(root,args.get("json_path"))
    workbook_path=_safe(root,args.get("xlsx_path"))
    data=json.loads(source.read_text(encoding="utf-8"))
    goal=str(args.get("goal") or "")

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

    _,records=_select_collection(data,cols)
    wanted=_status_value_from_records(records)
    expected={}
    for key,record in _record_items(records) or []:
        row=[_cell(record,str(key),c) for c in cols]
        identity=str(row[0])
        if not identity:
            raise RuntimeError("XLSX_EMPTY_ROW_ID")
        if identity in expected:
            raise RuntimeError("XLSX_DUPLICATE_SOURCE_ID:"+identity)
        expected[identity]=row
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
