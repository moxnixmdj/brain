from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime import content_addressed_artifact_measurement_v1 as base

SCHEMA="PROJECT_BRAIN_ARTIFACT_MEASUREMENT_XLSX_FILE_EXTENSION_V1"
KINDS={
 "FILE_BASENAME_EQUALS","FILE_STEM_EQUALS","FILE_SUFFIX_IN",
 "XLSX_FIRST_SHEET_NAME_EQUALS","XLSX_SHEET_NAME_CONTAINS",
 "XLSX_EXTERNAL_LINK_COUNT","XLSX_MACRO_PRESENT",
}

def _eq(a:str,b:str,case_sensitive:bool)->bool:
 return a==b if case_sensitive else a.casefold()==b.casefold()

def measure_one(path, req:Mapping[str,Any]):
 kind=str(req.get("kind") or "")
 if kind not in KINDS: raise base.ArtifactMeasurementError("EXTENSION_KIND_UNSUPPORTED:"+kind)
 cs=bool(req.get("case_sensitive",True))
 if kind=="FILE_BASENAME_EQUALS":
  x=req.get("expected")
  if not isinstance(x,str) or not x: raise base.ArtifactMeasurementError("EXPECTED_BASENAME_REQUIRED")
  return base._typed(_eq(path.name,x,cs))[0],_eq(path.name,x,cs),{"expected":x,"case_sensitive":cs}
 if kind=="FILE_STEM_EQUALS":
  x=req.get("expected")
  if not isinstance(x,str) or not x: raise base.ArtifactMeasurementError("EXPECTED_STEM_REQUIRED")
  return base._typed(_eq(path.stem,x,cs))[0],_eq(path.stem,x,cs),{"expected":x,"case_sensitive":cs}
 if kind=="FILE_SUFFIX_IN":
  xs=req.get("allowed_suffixes")
  if not isinstance(xs,list) or not xs: raise base.ArtifactMeasurementError("ALLOWED_SUFFIXES_REQUIRED")
  ys=[]
  for x in xs:
   if not isinstance(x,str) or not x: raise base.ArtifactMeasurementError("ALLOWED_SUFFIX_INVALID")
   ys.append((x if x.startswith(".") else "."+x).lower())
  if len(ys)!=len(set(ys)): raise base.ArtifactMeasurementError("ALLOWED_SUFFIX_DUPLICATE")
  value=path.suffix.lower() in set(ys)
  return "boolean",value,{"allowed_suffixes":sorted(ys)}
 names=base._xlsx_sheet_names(path) if kind.startswith("XLSX_") and kind not in {"XLSX_EXTERNAL_LINK_COUNT","XLSX_MACRO_PRESENT"} else None
 if kind=="XLSX_FIRST_SHEET_NAME_EQUALS":
  x=req.get("expected")
  if not isinstance(x,str) or not x: raise base.ArtifactMeasurementError("EXPECTED_SHEET_NAME_REQUIRED")
  value=bool(names) and _eq(names[0].strip(),x.strip(),cs)
  return "boolean",value,{"expected":x,"case_sensitive":cs,"observed_first_sheet":names[0] if names else None}
 if kind=="XLSX_SHEET_NAME_CONTAINS":
  x=req.get("text")
  if not isinstance(x,str) or not x: raise base.ArtifactMeasurementError("SHEET_NAME_TEXT_REQUIRED")
  target=x if cs else x.casefold()
  hits=[n for n in names if target in (n if cs else n.casefold())]
  return "boolean",bool(hits),{"text":x,"case_sensitive":cs,"matching_sheet_names":hits}
 with base._zip(path) as zf: members=set(zf.namelist())
 if kind=="XLSX_EXTERNAL_LINK_COUNT":
  n=sum(1 for x in members if x.startswith("xl/externalLinks/") and x.endswith(".xml"))
  return "integer",n,{}
 return "boolean","xl/vbaProject.bin" in members,{}
