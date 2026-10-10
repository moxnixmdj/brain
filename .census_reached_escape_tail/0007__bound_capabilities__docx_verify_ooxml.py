#!/usr/bin/env python3
"""Independent DOCX semantic verifier using Python stdlib OOXML parsing only."""
from __future__ import annotations
import hashlib,json,pathlib,zipfile
import xml.etree.ElementTree as ET

W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def _safe(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_file():
        raise RuntimeError("DOCX_INPUT_MISSING")
    return p

def _text(node):
    return "".join((t.text or "") for t in node.iter(W+"t"))

def run(args,root):
    path=_safe(root,args.get("path"))
    expected=args.get("expected")
    if not isinstance(expected,dict):
        raise RuntimeError("DOCX_EXPECTED_STRUCTURE_REQUIRED")
    title=str(expected.get("title") or "")
    paragraphs=[str(x) for x in expected.get("paragraphs") or []]
    headers=[str(x) for x in expected.get("headers") or []]
    rows=[[str(v) for v in row] for row in expected.get("rows") or []]
    if not title or not paragraphs or not headers or not rows:
        raise RuntimeError("DOCX_EXPECTED_STRUCTURE_INVALID")

    with zipfile.ZipFile(path) as zf:
        names=set(zf.namelist())
        if "word/document.xml" not in names:
            raise RuntimeError("DOCX_DOCUMENT_XML_MISSING")
        raw_xml=zf.read("word/document.xml")
    root_xml=ET.fromstring(raw_xml)
    body=root_xml.find(W+"body")
    if body is None:
        raise RuntimeError("DOCX_BODY_MISSING")

    observed_paragraphs=[]
    observed_tables=[]
    for child in list(body):
        if child.tag==W+"p":
            text=_text(child).strip()
            if text:
                observed_paragraphs.append(text)
        elif child.tag==W+"tbl":
            table=[]
            for tr in child.findall(W+"tr"):
                row=[]
                for tc in tr.findall(W+"tc"):
                    row.append(_text(tc).strip())
                table.append(row)
            if table:
                observed_tables.append(table)

    expected_table=[headers]+rows
    title_ok=title in observed_paragraphs
    paragraphs_ok=all(x in observed_paragraphs for x in paragraphs)
    table_ok=expected_table in observed_tables
    verified=bool(title_ok and paragraphs_ok and table_ok)
    raw=path.read_bytes()
    return {
      "adapter":"docx_verify_ooxml",
      "path":str(path.relative_to(pathlib.Path(root).resolve())).replace("\\","/"),
      "sha256":hashlib.sha256(raw).hexdigest(),
      "bytes":len(raw),
      "observed_paragraphs":observed_paragraphs,
      "observed_tables":observed_tables,
      "expected":expected,
      "title_ok":title_ok,
      "paragraphs_ok":paragraphs_ok,
      "table_ok":table_ok,
      "verified":verified,
      "producer_independent_verifier":True,
    }
