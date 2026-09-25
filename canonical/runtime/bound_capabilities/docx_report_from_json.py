#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,re,sys

def _safe(root,raw):
    root=pathlib.Path(root).resolve(); p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents: raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def _load():
    p=pathlib.Path(__file__).resolve().with_name("python_document_builder.py")
    s=importlib.util.spec_from_file_location("pb_docx_builder",p)
    if s is None or s.loader is None: raise RuntimeError("DOCX_BUILDER_LOAD_FAILED")
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); return m

def _spec(goal):
    text=" ".join(str(goal or "").split())
    tm=re.search(r"\btitle\s+(.+?)(?=,\s*(?:a\s+)?paragraph\b)",text,re.I)
    pm=re.search(r"\bparagraph\s+(.+?)(?=,\s*(?:and\s+)?(?:a\s+)?(?:two-column\s+)?table\b)",text,re.I)
    hm=re.search(r"\btable\s+with\s+(?:headers|columns)\s+(.+?)\s+containing\s+one\s+row\s+for\s+each\s+of\s+(.+?)\s+using\s+their\s+values\s+from\s+the\s+(?:normalized\s+)?json\b",text,re.I)
    if not tm or not pm or not hm: raise RuntimeError("JSON_DOCX_SPEC_UNRESOLVED")
    headers=[x.strip(" .,:;") for x in re.sub(r"\s+and\s+",", ",hm.group(1),flags=re.I).split(",") if x.strip(" .,:;")]
    fields=[x.strip(" .,:;") for x in re.sub(r"\s+and\s+",", ",hm.group(2),flags=re.I).split(",") if x.strip(" .,:;")]
    if len(headers)!=2 or not fields: raise RuntimeError("JSON_DOCX_SPEC_INVALID")
    return tm.group(1).strip(" .,:;"),pm.group(1).strip(" .,:;"),headers,fields

def _record(data,fields):
    hits=[]
    def walk(v):
        if isinstance(v,dict):
            if all(f in v and not isinstance(v[f],(dict,list)) for f in fields): hits.append(v)
            for x in v.values(): walk(x)
        elif isinstance(v,list):
            for x in v: walk(x)
    walk(data)
    if len(hits)!=1: raise RuntimeError("JSON_DOCX_RECORD_AMBIGUOUS:"+str(len(hits)))
    return hits[0]

def run(args,root):
    goal=str(args.get("goal") or ""); source=_safe(root,args.get("json_path")); output=_safe(root,args.get("output_path"))
    if not source.is_file(): raise RuntimeError("INPUT_JSON_MISSING")
    title,paragraph,headers,fields=_spec(goal); record=_record(json.loads(source.read_text(encoding="utf-8")),fields)
    rows=[[f,"" if record[f] is None else str(record[f])] for f in fields]
    literal=(
      f"Create {output.relative_to(pathlib.Path(root).resolve())} with title {title}, paragraph {paragraph}, "
      f"and a table with columns {headers[0]} and {headers[1]} containing "+
      " and ".join(" | ".join(row) for row in rows)+"."
    )
    result=_load().run({"goal":literal,"output_path":str(output.relative_to(pathlib.Path(root).resolve())),"module":"docx","factory":"Document"},root)
    intent=pathlib.Path(str(output)+".intent.json")
    intent.write_text(json.dumps({
      "schema":"PROJECT_BRAIN_DOCUMENT_JSON_INTENT_V1",
      "source_goal":goal,
      "source_json_path":str(source.relative_to(pathlib.Path(root).resolve())).replace("\\","/"),
      "output_path":str(output.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result.update({"adapter":"docx_report_from_json","source_json_path":str(source.relative_to(pathlib.Path(root).resolve())).replace("\\","/"),"fields":fields,"rows":rows})
    return result
