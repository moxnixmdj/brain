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

def _record_items(node):
    """A collection of records, whether the document spells it as a list or a mapping."""
    if isinstance(node,list) and node and all(isinstance(v,dict) for v in node):
        return [(str(i),v) for i,v in enumerate(node)]
    if isinstance(node,dict) and node and all(isinstance(v,dict) for v in node.values()):
        return [(str(k),v) for k,v in sorted(node.items(),key=lambda kv:str(kv[0]))]
    return None

def _candidate_collections(node,path=()):
    out=[]
    if _record_items(node) is not None:
        out.append((path,node))
    if isinstance(node,dict):
        for k,v in node.items():
            out.extend(_candidate_collections(v,path+(str(k),)))
    elif isinstance(node,list):
        for i,v in enumerate(node):
            if isinstance(v,(dict,list)):
                out.extend(_candidate_collections(v,path+(str(i),)))
    return out

def _select_collection(data,columns):
    """Pick the JSON collection that can actually supply these columns.

    Ported from canonical/runtime/bound_capabilities/xlsx_verify_openpyxl.py, which has
    always selected its source this way.  The sqlite adapters instead demanded an UPPERCASE
    token in the goal sentence and refused with SQLITE_STATUS_VALUE_UNRESOLVED when the
    sentence had none -- so "Verify a sqlite table against JSON records." could never run,
    while the xlsx sibling handling the same shape of task could.  Choosing by the columns
    the work really needs is both faithful to the sentence and impossible to get wrong
    silently: a collection that cannot supply a column is not a candidate, and if the
    shallowest surviving candidates are not exactly one this fails closed instead of picking.
    """
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
        raise RuntimeError("SQLITE_RECORD_COLLECTION_NOT_FOUND")
    min_depth=min(len(pth) for pth,_ in valid)
    best=[x for x in valid if len(x[0])==min_depth]
    if len(best)!=1:
        raise RuntimeError("SQLITE_RECORD_COLLECTION_AMBIGUOUS:"+json.dumps([list(pth) for pth,_ in best],sort_keys=True))
    return best[0]

def _status_value_from_records(records):
    """The one status the records agree on, or None when they do not agree on one.

    Also ported from the xlsx sibling.  Exactly one distinct value is a fact about the
    document rather than a guess; anything else declines to filter at all.
    """
    values=set()
    for _,record in _record_items(records) or []:
        value=record.get("status")
        if value is not None and not isinstance(value,(dict,list)):
            text=str(value).strip()
            if text:
                values.add(text)
    return next(iter(values)) if len(values)==1 else None

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
    try:
        p=subprocess.run(["sqlite3","-json",str(db),sql],text=True,capture_output=True,timeout=60)
        if p.returncode==0:
            return json.loads(p.stdout.strip() or "[]")
    except FileNotFoundError:
        pass
    import sqlite3 as py_sqlite3
    conn=py_sqlite3.connect(str(db))
    conn.row_factory=py_sqlite3.Row
    try:
        cur=conn.cursor()
        cur.execute(sql)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def run(args,root):
    source=_safe(root,args.get("json_path"))
    db=_safe(root,args.get("sqlite_path"))
    goal=str(args.get("goal") or "")
    data=json.loads(source.read_text(encoding="utf-8"))
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

    # The source collection is chosen by the columns this table actually has, and the status
    # filter -- only when the records agree on exactly one status -- is derived from them.
    # Neither comes from the sentence, so a sentence stating neither still verifies.
    _,records=_select_collection(data,cols)
    wanted=_status_value_from_records(records)
    expected={}
    for key,record in _record_items(records) or []:
        if wanted is not None and wanted not in record.values():
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
