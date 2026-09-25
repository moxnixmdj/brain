#!/usr/bin/env python3
"""Create an XLSX table from a status-bearing JSON record collection."""
from __future__ import annotations
import hashlib,json,pathlib,re,sys

def _safe(root,raw,require_file=False):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if require_file and not p.is_file():
        raise RuntimeError("INPUT_JSON_MISSING")
    return p

def _import_xlsxwriter():
    try:
        import xlsxwriter
        return xlsxwriter
    except ModuleNotFoundError:
        dist=pathlib.Path("/usr/lib/python3/dist-packages")
        if dist.is_dir() and str(dist) not in sys.path:
            sys.path.insert(0,str(dist))
        import xlsxwriter
        return xlsxwriter

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
    cols=[x.strip(" .,;:") for x in raw.split(",") if x.strip(" .,;:")]
    if not cols or len(cols)>64:
        raise RuntimeError("XLSX_COLUMNS_INVALID")
    if len(set(cols))!=len(cols):
        raise RuntimeError("XLSX_COLUMNS_DUPLICATE")
    return cols

def _flatten_paths(record,path=()):
    out={}
    if isinstance(record,dict):
        for k,v in record.items():
            out.update(_flatten_paths(v,path+(str(k),)))
    else:
        out["_".join(path)]=record
    return out

def _cell(record,key,column):
    if column=="capability_id":
        return key
    if column in record:
        value=record[column]
    else:
        flat=_flatten_paths(record)
        if column not in flat:
            raise RuntimeError("XLSX_COLUMN_UNRESOLVED:"+column)
        value=flat[column]
    if isinstance(value,(list,dict)):
        return json.dumps(value,sort_keys=True,separators=(",",":"))
    if value is None:
        return ""
    return value

def run(args,root):
    source=_safe(root,args.get("json_path"),require_file=True)
    output=_safe(root,args.get("output_path"))
    data=json.loads(source.read_text(encoding="utf-8"))
    goal=str(args.get("goal") or "")
    wanted=_status_value(goal,data)
    found=_find_collection(data,wanted)
    if found is None:
        raise RuntimeError("XLSX_STATUS_COLLECTION_NOT_FOUND")
    collection_path,records=found
    cols=_columns(goal)
    rows=[]
    for key,record in sorted(records.items()):
        if wanted not in record.values():
            continue
        rows.append([_cell(record,str(key),c) for c in cols])
    if not rows:
        raise RuntimeError("XLSX_ROWS_EMPTY")

    xlsxwriter=_import_xlsxwriter()
    output.parent.mkdir(parents=True,exist_ok=True)
    workbook=xlsxwriter.Workbook(str(output))
    try:
        sheet=workbook.add_worksheet("data")
        for col,name in enumerate(cols):
            sheet.write(0,col,name)
        for r,row in enumerate(rows,1):
            for col,value in enumerate(row):
                sheet.write(r,col,value)
    finally:
        workbook.close()
    raw=output.read_bytes()
    if not raw.startswith(b"PK\x03\x04"):
        raise RuntimeError("XLSX_ZIP_MAGIC_MISSING")
    return {
      "adapter":"xlsx_table_xlsxwriter",
      "output_path":str(output.relative_to(pathlib.Path(root).resolve())).replace("\\","/"),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "output_bytes":len(raw),
      "row_count":len(rows),
      "column_count":len(cols),
      "columns":cols,
      "status_value":wanted,
      "collection_path":list(collection_path),
      "output_verified":True,
    }
