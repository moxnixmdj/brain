#!/usr/bin/env python3
"""Create a SQLite table from a status-bearing canonical JSON record collection."""
from __future__ import annotations
import hashlib,json,pathlib,re,sqlite3

IDENT=re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")

def _safe(root,raw,require_file=False):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if require_file and not p.is_file():
        raise RuntimeError("INPUT_JSON_MISSING")
    return p

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
    raise RuntimeError("SQLITE_STATUS_VALUE_UNRESOLVED")

def _columns(goal):
    m=re.search(r"\bcolumns?\s+(.+?)(?=\.\s|\bfinally\b|$)",str(goal or ""),flags=re.I)
    if not m:
        raise RuntimeError("SQLITE_COLUMNS_UNRESOLVED")
    raw=re.sub(r"\s+and\s+",", ",m.group(1),flags=re.I)
    cols=[x.strip(" .,;:") for x in raw.split(",") if x.strip(" .,;:")]
    if not cols or len(cols)>64 or len(set(cols))!=len(cols):
        raise RuntimeError("SQLITE_COLUMNS_INVALID")
    for col in cols:
        if not IDENT.fullmatch(col):
            raise RuntimeError("SQLITE_COLUMN_IDENTIFIER_INVALID:"+col)
    return cols

def _table_name(goal):
    m=re.search(r"\btable\s+named\s+([A-Za-z_][A-Za-z0-9_]*)\b",str(goal or ""),flags=re.I)
    if not m:
        raise RuntimeError("SQLITE_TABLE_NAME_UNRESOLVED")
    name=m.group(1)
    if not IDENT.fullmatch(name):
        raise RuntimeError("SQLITE_TABLE_NAME_INVALID")
    return name

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
        value=key
    elif column in record:
        value=record[column]
    else:
        flat=_flatten_paths(record)
        if column not in flat:
            raise RuntimeError("SQLITE_COLUMN_UNRESOLVED:"+column)
        value=flat[column]
    if isinstance(value,(list,dict)):
        return json.dumps(value,sort_keys=True,separators=(",",":"))
    if value is None:
        return ""
    if isinstance(value,bool):
        return "true" if value else "false"
    return str(value)

def run(args,root):
    source=_safe(root,args.get("json_path"),require_file=True)
    output=_safe(root,args.get("output_path"))
    goal=str(args.get("goal") or "")
    data=json.loads(source.read_text(encoding="utf-8"))
    wanted=_status_value(goal,data)
    found=_find_collection(data,wanted)
    if found is None:
        raise RuntimeError("SQLITE_STATUS_COLLECTION_NOT_FOUND")
    collection_path,records=found
    cols=_columns(goal)
    table=_table_name(goal)
    rows=[]
    for key,record in sorted(records.items()):
        if wanted not in record.values():
            continue
        rows.append([_cell(record,str(key),c) for c in cols])
    if not rows:
        raise RuntimeError("SQLITE_ROWS_EMPTY")

    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        output.unlink()
    conn=sqlite3.connect(str(output))
    try:
        quoted_cols=", ".join('"'+c+'"'+" TEXT NOT NULL" for c in cols)
        conn.execute(f'CREATE TABLE "{table}" ({quoted_cols})')
        placeholders=",".join("?" for _ in cols)
        conn.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})',rows)
        conn.commit()
        count=conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        integrity=conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        conn.close()
    if count!=len(rows) or integrity!="ok":
        raise RuntimeError("SQLITE_CREATION_VERIFICATION_FAILED")
    raw=output.read_bytes()
    if not raw.startswith(b"SQLite format 3\x00"):
        raise RuntimeError("SQLITE_MAGIC_MISSING")
    return {
      "adapter":"sqlite_table_stdlib",
      "output_path":str(output.relative_to(pathlib.Path(root).resolve())).replace("\\","/"),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "output_bytes":len(raw),
      "row_count":len(rows),
      "column_count":len(cols),
      "columns":cols,
      "table_name":table,
      "status_value":wanted,
      "collection_path":list(collection_path),
      "sqlite_version":sqlite3.sqlite_version,
      "output_verified":True
    }
