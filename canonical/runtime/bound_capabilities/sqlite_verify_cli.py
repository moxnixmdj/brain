#!/usr/bin/env python3
"""Independently verify a SQLite table against canonical JSON using sqlite3 CLI."""
from __future__ import annotations
import hashlib,json,pathlib,re,subprocess

IDENT=re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")

def _safe(root,raw,require_file=True):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if require_file and not p.is_file():
        raise RuntimeError("INPUT_FILE_MISSING")
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

def _table_name(goal):
    m=re.search(r"\btable\s+named\s+([A-Za-z_][A-Za-z0-9_]*)\b",str(goal or ""),flags=re.I)
    return m.group(1) if m else None

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

def _run_json(db,sql):
    p=subprocess.run(["sqlite3","-json",str(db),sql],text=True,capture_output=True,timeout=60)
    if p.returncode!=0:
        raise RuntimeError("SQLITE_CLI_FAILED:"+p.stderr[-1200:])
    text=p.stdout.strip()
    return json.loads(text or "[]")

def run(args,root):
    source=_safe(root,args.get("json_path"))
    db=_safe(root,args.get("sqlite_path"))
    goal=str(args.get("goal") or "")
    data=json.loads(source.read_text(encoding="utf-8"))
    wanted=_status_value(goal,data)
    found=_find_collection(data,wanted)
    if found is None:
        raise RuntimeError("SQLITE_STATUS_COLLECTION_NOT_FOUND")
    _,records=found
    table=_table_name(goal)
    if table is None:
        tables=_run_json(
            db,
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        names=[str(x.get("name") or "") for x in tables if str(x.get("name") or "")]
        if len(names)!=1:
            raise RuntimeError("SQLITE_TABLE_NAME_AMBIGUOUS:"+json.dumps(names,sort_keys=True))
        table=names[0]
    if not IDENT.fullmatch(table):
        raise RuntimeError("SQLITE_TABLE_NAME_INVALID")

    schema=_run_json(db,f'PRAGMA table_info("{table}")')
    cols=[str(x.get("name") or "") for x in schema]
    if not cols or any(not IDENT.fullmatch(c) for c in cols):
        raise RuntimeError("SQLITE_SCHEMA_INVALID")
    if "capability_id" not in cols:
        raise RuntimeError("SQLITE_ID_COLUMN_REQUIRED")

    expected={}
    for key,record in sorted(records.items()):
        if wanted not in record.values():
            continue
        expected[str(key)]={c:_cell(record,str(key),c) for c in cols}

    col_sql=", ".join('"'+c+'"' for c in cols)
    observed_rows=_run_json(db,f'SELECT {col_sql} FROM "{table}" ORDER BY "capability_id"')
    observed={}
    for row in observed_rows:
        key=str(row.get("capability_id") or "")
        if not key:
            raise RuntimeError("SQLITE_EMPTY_ID")
        if key in observed:
            raise RuntimeError("SQLITE_DUPLICATE_ID:"+key)
        observed[key]={c:("" if row.get(c) is None else str(row.get(c))) for c in cols}

    if set(observed)!=set(expected):
        raise RuntimeError("SQLITE_ID_SET_MISMATCH:"+json.dumps({
          "missing":sorted(set(expected)-set(observed)),
          "extra":sorted(set(observed)-set(expected))
        },sort_keys=True))
    mismatches=[]
    for key in sorted(expected):
        for c in cols:
            if observed[key][c]!=expected[key][c]:
                mismatches.append({"id":key,"column":c,"expected":expected[key][c],"observed":observed[key][c]})
    if mismatches:
        raise RuntimeError("SQLITE_VALUE_MISMATCH:"+json.dumps(mismatches[:20],sort_keys=True))
    integrity=_run_json(db,"PRAGMA integrity_check")
    if not integrity or list(integrity[0].values())[0]!="ok":
        raise RuntimeError("SQLITE_INTEGRITY_CHECK_FAILED")
    raw=db.read_bytes()
    return {
      "adapter":"sqlite_verify_cli",
      "sqlite_path":str(db.relative_to(pathlib.Path(root).resolve())).replace("\\","/"),
      "sqlite_sha256":hashlib.sha256(raw).hexdigest(),
      "verified_rows":len(expected),
      "columns":cols,
      "table_name":table,
      "status_value":wanted,
      "producer_independent_verifier":True,
      "verified":True
    }
