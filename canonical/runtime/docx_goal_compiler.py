#!/usr/bin/env python3
"""DOCX-specific deterministic compiler helpers for verified capability composition."""
from __future__ import annotations
import pathlib,re

def expected_from_creation(subgoal):
    text=" ".join(str(subgoal or "").strip().split())
    title_m=re.search(r"\btitle\s+(.+?)(?=,\s*(?:a\s+)?paragraph\b|,\s*(?:and\s+)?(?:a\s+)?table\b|$)",text,re.I)
    para_m=re.search(r"\bparagraph(?:\s+containing|\s+exactly)?\s+(.+?)(?=,\s*(?:and\s+)?(?:a\s+)?(?:two-column\s+)?table\b|$)",text,re.I)
    table_m=re.search(r"\btable\s+with\s+(?:headers|columns)\s+(.+?)\s+containing\s+(.+)$",text,re.I)
    if not title_m or not para_m or not table_m:
        return None
    headers=[x.strip(" .,:;") for x in re.sub(r"\s+and\s+",", ",table_m.group(1),flags=re.I).split(",") if x.strip(" .,:;")]
    rows=[]
    for chunk in [x.strip() for x in re.split(r"\s+and\s+",table_m.group(2).strip(" ."),flags=re.I) if x.strip()]:
        cells=[x.strip(" .,:;") for x in chunk.split("|")]
        if len(cells)!=len(headers):
            return None
        rows.append(cells)
    if not headers or not rows:
        return None
    return {
      "title":title_m.group(1).strip(" .,:;"),
      "paragraphs":[para_m.group(1).strip(" .,:;")],
      "headers":headers,
      "rows":rows,
    }

def compile_independent_verification(subgoal,context_paths,compiled_parts,registry):
    lower=str(subgoal or "").lower()
    if not re.match(r"^(?:finally\s+)?independently\s+(?:reopen|open|read|inspect)\b",lower):
        return None
    if "docx" not in lower or not re.search(r"\bverify\b",lower):
        return None
    entry=(registry or {}).get("docx.document.verify.ooxml")
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".docx"]
    if not paths:
        return None
    creation=None
    for part in reversed(list(compiled_parts or [])):
        if isinstance(part,dict) and part.get("selected_capability")=="docx.document.create.python_docx":
            creation=str(part.get("subgoal") or "")
            break
    if not creation:
        return None
    expected=expected_from_creation(creation)
    if expected is None:
        return None
    path=paths[-1]
    return {
      "action":{
        "type":"invoke_capability",
        "args":{
          "capability_id":"docx.document.verify.ooxml",
          "path":path,
          "expected":expected
        },
        "expect":{"type":"field_equals","field":"verified","value":True}
      },
      "evidence":{
        "path":path,
        "expected":expected,
        "capability_id":"docx.document.verify.ooxml",
        "producer_independent_verifier":True
      }
    }
