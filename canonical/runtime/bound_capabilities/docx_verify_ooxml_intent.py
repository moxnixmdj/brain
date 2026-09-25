#!/usr/bin/env python3
"""Verify DOCX content against independently parsed raw creation intent."""
from __future__ import annotations
import importlib.util,json,pathlib,re,sys

def _safe(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_file():
        raise RuntimeError("DOCX_INPUT_MISSING")
    return p

def _expected(goal):
    text=" ".join(str(goal or "").strip().split())
    title_m=re.search(r"\btitle\s+(.+?)(?=,\s*(?:a\s+)?paragraph\b|,\s*(?:and\s+)?(?:a\s+)?table\b|$)",text,re.I)
    para_m=re.search(r"\bparagraph(?:\s+containing|\s+exactly)?\s+(.+?)(?=,\s*(?:and\s+)?(?:a\s+)?(?:two-column\s+)?table\b|$)",text,re.I)
    table_m=re.search(r"\btable\s+with\s+(?:headers|columns)\s+(.+?)\s+containing\s+(.+)$",text,re.I)
    if not title_m or not para_m or not table_m:
        raise RuntimeError("DOCX_INTENT_GOAL_UNRESOLVED")
    headers=[x.strip(" .,:;") for x in re.sub(r"\s+and\s+",", ",table_m.group(1),flags=re.I).split(",") if x.strip(" .,:;")]
    rows=[]
    for chunk in [x.strip() for x in re.split(r"\s+and\s+",table_m.group(2).strip(" ."),flags=re.I) if x.strip()]:
        cells=[x.strip(" .,:;") for x in chunk.split("|")]
        if len(cells)!=len(headers):
            raise RuntimeError("DOCX_INTENT_ROW_WIDTH_MISMATCH")
        rows.append(cells)
    if not headers or not rows:
        raise RuntimeError("DOCX_INTENT_STRUCTURE_INVALID")
    return {
      "title":title_m.group(1).strip(" .,:;"),
      "paragraphs":[para_m.group(1).strip(" .,:;")],
      "headers":headers,
      "rows":rows,
    }

def _expected_json(goal,data):
    text=" ".join(str(goal or "").strip().split())
    title_m=re.search(r"\btitle\s+(.+?)(?=,\s*(?:a\s+)?paragraph\b)",text,re.I)
    para_m=re.search(r"\bparagraph\s+(.+?)(?=,\s*(?:and\s+)?(?:a\s+)?(?:two-column\s+)?table\b)",text,re.I)
    table_m=re.search(r"\btable\s+with\s+(?:headers|columns)\s+(.+?)\s+containing\s+one\s+row\s+for\s+each\s+of\s+(.+?)\s+using\s+their\s+values\s+from\s+the\s+(?:normalized\s+)?json\b",text,re.I)
    if not title_m or not para_m or not table_m:
        raise RuntimeError("DOCX_JSON_INTENT_UNRESOLVED")
    headers=[x.strip(" .,:;") for x in re.sub(r"\s+and\s+",", ",table_m.group(1),flags=re.I).split(",") if x.strip(" .,:;")]
    fields=[x.strip(" .,:;") for x in re.sub(r"\s+and\s+",", ",table_m.group(2),flags=re.I).split(",") if x.strip(" .,:;")]
    hits=[]
    def walk(v):
        if isinstance(v,dict):
            if all(f in v and not isinstance(v[f],(dict,list)) for f in fields): hits.append(v)
            for x in v.values(): walk(x)
        elif isinstance(v,list):
            for x in v: walk(x)
    walk(data)
    if len(headers)!=2 or not fields or len(hits)!=1:
        raise RuntimeError("DOCX_JSON_INTENT_STRUCTURE_INVALID")
    record=hits[0]
    return {
      "title":title_m.group(1).strip(" .,:;"),
      "paragraphs":[para_m.group(1).strip(" .,:;")],
      "headers":headers,
      "rows":[[f,"" if record[f] is None else str(record[f])] for f in fields],
    }

def _load_base():
    path=pathlib.Path(__file__).resolve().with_name("docx_verify_ooxml.py")
    spec=importlib.util.spec_from_file_location("project_brain_docx_verify_ooxml_base",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("DOCX_BASE_VERIFIER_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def run(args,root):
    docx=_safe(root,args.get("path"))
    intent=pathlib.Path(str(docx)+".intent.json")
    if not intent.is_file():
        raise RuntimeError("DOCX_INTENT_SIDECAR_MISSING")
    obj=json.loads(intent.read_text(encoding="utf-8"))
    schema=obj.get("schema")
    source_json_path=None
    if schema=="PROJECT_BRAIN_DOCUMENT_INTENT_V1":
        expected=_expected(obj.get("source_goal"))
    elif schema=="PROJECT_BRAIN_DOCUMENT_JSON_INTENT_V1":
        source=_safe(root,obj.get("source_json_path"))
        source_json_path=str(source.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
        expected=_expected_json(obj.get("source_goal"),json.loads(source.read_text(encoding="utf-8")))
    else:
        raise RuntimeError("DOCX_INTENT_SCHEMA_INVALID")
    result=_load_base().run({"path":str(docx.relative_to(pathlib.Path(root).resolve())),"expected":expected},root)
    result["adapter"]="docx_verify_ooxml_intent"
    result["intent_path"]=str(intent.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    result["intent_source_goal"]=obj.get("source_goal")
    result["intent_derived_expected"]=expected
    result["source_json_path"]=source_json_path
    result["source_record_verified"]=schema=="PROJECT_BRAIN_DOCUMENT_JSON_INTENT_V1"
    return result
