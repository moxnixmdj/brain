#!/usr/bin/env python3
"""Generic Python document-builder adapter for an introspected DOCX contract."""
from __future__ import annotations
import hashlib,importlib,json,pathlib,re,sys,zipfile

def _safe(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def _parse_spec(goal):
    text=" ".join(str(goal or "").strip().split())
    title_m=re.search(
        r"\btitle\s+(.+?)(?=,\s*(?:a\s+)?paragraph\b|,\s*(?:and\s+)?(?:a\s+)?table\b|$)",
        text,re.I
    )
    para_m=re.search(
        r"\bparagraph(?:\s+containing|\s+exactly)?\s+(.+?)(?=,\s*(?:and\s+)?(?:a\s+)?(?:two-column\s+)?table\b|$)",
        text,re.I
    )
    table_m=re.search(
        r"\btable\s+with\s+(?:headers|columns)\s+(.+?)\s+containing\s+(.+)$",
        text,re.I
    )
    if not title_m or not para_m or not table_m:
        raise RuntimeError("DOCUMENT_SPEC_UNRESOLVED")
    title=title_m.group(1).strip(" .,:;")
    paragraph=para_m.group(1).strip(" .,:;")
    raw_headers=re.sub(r"\s+and\s+",", ",table_m.group(1),flags=re.I)
    headers=[x.strip(" .,:;") for x in raw_headers.split(",") if x.strip(" .,:;")]
    raw_rows=table_m.group(2).strip(" .")
    row_chunks=[x.strip() for x in re.split(r"\s+and\s+",raw_rows,flags=re.I) if x.strip()]
    rows=[]
    for chunk in row_chunks:
        cells=[x.strip(" .,:;") for x in chunk.split("|")]
        if len(cells)!=len(headers):
            raise RuntimeError("DOCUMENT_TABLE_ROW_WIDTH_MISMATCH")
        rows.append(cells)
    if not title or not paragraph or len(headers)<2 or not rows:
        raise RuntimeError("DOCUMENT_SPEC_INVALID")
    return {"title":title,"paragraphs":[paragraph],"headers":headers,"rows":rows}

def _import_module(name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        dist="/usr/lib/python3/dist-packages"
        if dist not in sys.path:
            sys.path.insert(0,dist)
        return importlib.import_module(name)

def run(args,root):
    goal=str(args.get("goal") or "")
    output=_safe(root,args.get("output_path"))
    module_name=str(args.get("module") or "").strip()
    factory_name=str(args.get("factory") or "").strip()
    if not module_name or not factory_name:
        raise RuntimeError("PYTHON_LIBRARY_CONTRACT_INCOMPLETE")
    spec=_parse_spec(goal)
    module=_import_module(module_name)
    factory=getattr(module,factory_name,None)
    if not callable(factory):
        raise RuntimeError("PYTHON_LIBRARY_FACTORY_MISSING")
    doc=factory()
    add_heading=getattr(doc,"add_heading",None)
    add_paragraph=getattr(doc,"add_paragraph",None)
    add_table=getattr(doc,"add_table",None)
    save=getattr(doc,"save",None)
    if not all(callable(x) for x in (add_heading,add_paragraph,add_table,save)):
        raise RuntimeError("PYTHON_DOCUMENT_BUILDER_METHODS_MISSING")
    add_heading(spec["title"],level=0)
    for paragraph in spec["paragraphs"]:
        add_paragraph(paragraph)
    table=add_table(rows=1,cols=len(spec["headers"]))
    for i,value in enumerate(spec["headers"]):
        table.rows[0].cells[i].text=value
    for row in spec["rows"]:
        cells=table.add_row().cells
        for i,value in enumerate(row):
            cells[i].text=value
    output.parent.mkdir(parents=True,exist_ok=True)
    save(str(output))
    intent_path=pathlib.Path(str(output)+".intent.json")
    intent_payload={
      "schema":"PROJECT_BRAIN_DOCUMENT_INTENT_V1",
      "source_goal":goal,
      "output_path":str(output.relative_to(pathlib.Path(root).resolve())).replace("\\","/"),
    }
    intent_path.write_text(json.dumps(intent_payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    if not raw.startswith(b"PK\x03\x04"):
        raise RuntimeError("DOCX_ZIP_MAGIC_MISSING")
    with zipfile.ZipFile(output) as zf:
        if "word/document.xml" not in zf.namelist():
            raise RuntimeError("DOCX_DOCUMENT_XML_MISSING")
    return {
      "adapter":"python_document_builder",
      "output_path":str(output.relative_to(pathlib.Path(root).resolve())).replace("\\","/"),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "output_bytes":len(raw),
      "document_spec":spec,
      "intent_path":str(intent_path.relative_to(pathlib.Path(root).resolve())).replace("\\","/"),
      "intent_sha256":hashlib.sha256(intent_path.read_bytes()).hexdigest(),
      "output_verified":True,
    }
