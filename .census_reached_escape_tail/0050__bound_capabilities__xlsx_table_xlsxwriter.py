#!/usr/bin/env python3
"""Create an XLSX table from an unambiguous JSON record collection."""
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
    if column=="capability_id" or (column.endswith("_id") and column not in record):
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
    # Prefer the shallowest matching collection. Equal-depth alternatives are
    # genuinely ambiguous and fail closed.
    min_depth=min(len(path) for path,_ in valid)
    best=[x for x in valid if len(x[0])==min_depth]
    if len(best)!=1:
        raise RuntimeError("XLSX_RECORD_COLLECTION_AMBIGUOUS:"+json.dumps([list(p) for p,_ in best]))
    return best[0]

def run(args,root):
    source=_safe(root,args.get("json_path"),require_file=True)
    output=_safe(root,args.get("output_path"))
    data=json.loads(source.read_text(encoding="utf-8"))
    goal=str(args.get("goal") or "")
    cols=_columns(goal)
    collection_path,records=_select_collection(data,cols)
    rows=[]
    for key,record in _record_items(records) or []:
        rows.append([_cell(record,str(key),c) for c in cols])
    if not rows:
        raise RuntimeError("XLSX_ROWS_EMPTY")
    wanted=_status_value_from_records(records)

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
