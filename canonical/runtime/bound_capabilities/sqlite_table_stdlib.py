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

def _status_value_from_goal(goal,records):
    """The status the SENTENCE names, chosen from the records' own vocabulary.

    The old code derived the filter only from the data, and only when every record
    agreed on one status.  A goal that says "from the ACTIVE records" over a mixed
    collection therefore produced wanted=None, the filter was skipped, and the table
    was built from every record -- a confident superset of what was asked for.  Measured
    on the live harness: 4 of 10 instances correct, the other 6 silently over-inclusive.

    This does not enumerate phrasings.  It takes the distinct status values the records
    actually carry and asks which of them the sentence mentions as a whole word, so any
    vocabulary works and no list of words is maintained.  Exactly one named value is a
    fact about the sentence; two is a contradiction and fails closed; none falls back to
    the data-derived value, which is still right when the records are unanimous.
    """
    values=set()
    for _,record in _record_items(records) or []:
        value=record.get("status")
        if value is not None and not isinstance(value,(dict,list)):
            text=str(value).strip()
            if text:
                values.add(text)
    sentence=str(goal or "")
    named=sorted(
        v for v in values
        if re.search(r"(?<![A-Za-z0-9_])"+re.escape(v)+r"(?![A-Za-z0-9_])",sentence,flags=re.I)
    )
    if len(named)>1:
        raise RuntimeError("SQLITE_STATUS_AMBIGUOUS:"+json.dumps(named,sort_keys=True))
    return named[0] if named else None


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
    cols=_columns(goal)
    # Chosen by the columns this table will have, not by a token the sentence must contain.
    collection_path,records=_select_collection(data,cols)
    wanted=_status_value_from_goal(goal,records) or _status_value_from_records(records)
    table=_table_name(goal)
    rows=[]
    for key,record in _record_items(records) or []:
        if wanted is not None and wanted not in record.values():
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
