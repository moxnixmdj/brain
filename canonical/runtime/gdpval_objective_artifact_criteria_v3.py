"""Conservative V3 compiler for objective GDPval artifact criteria.

V3 preserves every V2 admission and adds only whole-criterion structural forms
whose truth is independently checkable from artifact bytes. Where a criterion
allows several legacy/equivalent formats, V3 may require one Brain-owned native
format as a sound sufficient subset. Mixed format+content/role criteria remain
unresolved.
"""
from __future__ import annotations
from pathlib import Path
import re
from typing import Any,Mapping
from canonical.runtime import gdpval_objective_artifact_criteria_v2 as v2

SCHEMA="PROJECT_BRAIN_GDPVAL_OBJECTIVE_ARTIFACT_CRITERIA_V3"

def _norm(v:Any)->str:return " ".join(str(v or "").split())
def _preserved(out:Mapping[str,Any])->dict[str,Any]:
    d=dict(out);d["schema"]=SCHEMA;d["compiler_origin"]="V2_PRESERVED";d["v2_schema"]=v2.SCHEMA;return d

def _one(ext:str,base:Mapping[str,Any],subset:bool=False)->dict[str,Any]:
    return v2._compiled(base,kind="EXACT_TOP_LEVEL_FILE_COUNT_BY_EXTENSION",
        args={"count":1,"extension":ext,"total_files_must_equal_count":True},
        relation="SOUND_SUFFICIENT_SUBSET__FALSE_NEGATIVES_ALLOWED" if subset else "EXACT_MECHANICAL_EQUIVALENCE")

def _exists(ext:str,base:Mapping[str,Any],subset:bool=False)->dict[str,Any]:
    return v2._compiled(base,kind="AT_LEAST_ONE_VALID_FILE_BY_EXTENSION",args={"extension":ext},
        relation="SOUND_SUFFICIENT_SUBSET__FALSE_NEGATIVES_ALLOWED" if subset else "EXACT_MECHANICAL_EQUIVALENCE")

def compile_criterion(criterion:str,*,criterion_id:str|None=None)->dict[str,Any]:
    text=_norm(criterion);base=v2._base(text,criterion_id)
    if not text:return {**base,"status":"FAIL_CLOSED","reason":"CRITERION_MISSING"}
    prior=v2.compile_criterion(text,criterion_id=criterion_id)
    if prior.get("status")=="COMPILED_OBJECTIVE_CHECK":return _preserved(prior)

    # Pure length/count forms. Requiring one native PDF/PPTX is a sound
    # sufficient subset when the criterion itself does not constrain format.
    if re.fullmatch(r"Document length is 2–3 pages[.]?",text,re.I) or text.casefold().rstrip(".")=="the document length is between 2 and 3 pages (inclusive)":
        return v2._compiled(base,kind="SINGLE_PDF_PAGE_COUNT_RANGE",
          args={"min_pages":2,"max_pages":3,"total_files_must_equal_count":True},
          relation="SOUND_SUFFICIENT_SUBSET__FALSE_NEGATIVES_ALLOWED")
    if re.fullmatch(r"Submission length is no more than 10 slides total[.]?",text,re.I):
        return v2._compiled(base,kind="SINGLE_PPTX_SLIDE_COUNT_MAX",
          args={"max_slides":10,"total_files_must_equal_count":True},
          relation="SOUND_SUFFICIENT_SUBSET__FALSE_NEGATIVES_ALLOWED")
    if re.fullmatch(r"Response provides two deliverables[.]?",text,re.I):
        return v2._compiled(base,kind="EXACT_TOP_LEVEL_TOTAL_FILE_COUNT",args={"count":2})

    # Pure single-PDF forms. Fullmatch is intentional: content-bearing suffixes
    # such as "containing the screenplay" do not enter this route.
    pdf_single=(
      r"The submission is provided as a single PDF file \(\.pdf\)[.]?",
      r"The deliverable is a single PDF file \(\.pdf\)[.]?",
      r"Exactly one deliverable is provided and it is a single PDF file[.]?",
      r"Submission is a single PDF file \(\.pdf\)[.]?",
      r"The deliverable is a single file in PDF format[.]?",
    )
    if any(re.fullmatch(p,text,re.I) for p in pdf_single):return _one(".pdf",base)
    if re.fullmatch(r"(?:The )?(?:output )?deliverable(?: file)? is a (?:pdf|PDF) file[.]?",text,re.I):
        return _one(".pdf",base,subset=True)

    # Pure DOCX / Word-format forms.
    docx_single=(
      r"Exactly one deliverable file is submitted and it is a Microsoft Word \.docx document[.]?",
      r"Submission is provided as a single Microsoft Word document with a \.docx extension[.]?",
      r"The deliverable is provided as a single Microsoft Word file \(\.docx\)[.]?",
      r"The deliverable is a single Microsoft Word \(\.docx\) file[.]?",
    )
    if any(re.fullmatch(p,text,re.I) for p in docx_single):return _one(".docx",base)
    docx_exists=(
      r"The submission is delivered as a Microsoft Word document with a \.docx extension[.]?",
    )
    if any(re.fullmatch(p,text,re.I) for p in docx_exists):
        return _one(".docx",base,subset=True)
    docx_subset=(
      r"A Word file is submitted as a separate file in \.docx or \.doc format \(not PDF/ODT/Google Doc and not embedded\)[.]?",
      r"The deliverable is a file type compatible with Microsoft Word \(\.docx, \.doc, \.docm, \.dotx, \.dotm\)[.]?",
      r"The deliverable is a Microsoft Word \.docx file \(not \.pdf, \.txt, \.rtf, \.md, or \.pages\)[.]?",
      r"The uploaded deliverable is a Microsoft Word document \(\.docx or \.doc\)[.]?",
    )
    if any(re.fullmatch(p,text,re.I) for p in docx_subset):return _one(".docx",base,subset=True)
    m=re.fullmatch(r'The file ["“]Telehealth Workflow["”] is delivered in Word format \(\.doc or \.docx\)[.]?',text,re.I)
    if m:
        return v2._compiled(base,kind="EXACT_STEM_ALLOWED_EXTENSIONS",
          args={"stem":"Telehealth Workflow","extensions":[".docx"]},
          relation="SOUND_SUFFICIENT_SUBSET__FALSE_NEGATIVES_ALLOWED")

    # Pure spreadsheet-format forms. A native XLSX is a safe subset when legacy
    # XLS/XLSM/CSV/equivalent alternatives are also allowed.
    xlsx_single=(
      r"Provides a single Excel workbook \(\.xlsx\) as the primary deliverable[.]?",
      r"The deliverable is a single Excel \.xlsx workbook file \(no PDFs, CSVs, Google links, or multiple files\)[.]?",
      r"The deliverable is a single Microsoft Excel workbook file \(\.xlsx\)[.]?",
      r"A single Excel workbook \(\.xlsx\) is submitted as the deliverable[.]?",
      r"Returns the completed deliverable as a single Excel workbook in \.xlsx format \(not \.csv, \.xlsm, or other\)[.]?",
      r"The deliverable is a single Excel workbook saved with the \.xlsx extension[.]?",
    )
    if any(re.fullmatch(p,text,re.I) for p in xlsx_single):return _one(".xlsx",base)
    xlsx_exists=(
      r"Provides an Excel deliverable file[.]?",
      r"Provides an Excel workbook \(\.xlsx\) as part of the deliverable[.]?",
    )
    if any(re.fullmatch(p,text,re.I) for p in xlsx_exists):return _exists(".xlsx",base,subset=True)
    xlsx_subset=(
      r"Provides an Excel workbook file \(\.xlsx or \.xls\)[.]?",
      r"Deliverable includes an Excel workbook file in Excel format \(\.xlsx or \.xlsm\)[.]?",
      r"The deliverable is provided in a spreadsheet format \(e\.g\., Excel, CSV, or equivalent\)[.]?",
    )
    if any(re.fullmatch(p,text,re.I) for p in xlsx_subset):return _one(".xlsx",base,subset=True)

    # Pure PowerPoint-format forms.
    pptx_single=(
      r"Delivers a single presentation file in \.pptx \(PowerPoint\) format[.]?",
    )
    if any(re.fullmatch(p,text,re.I) for p in pptx_single):return _one(".pptx",base)
    pptx_exists=(
      r"Delivers the work as a PowerPoint file in \.pptx format[.]?",
      r"A PowerPoint presentation file is included among the deliverables[.]?",
      r"Provides the deliverable as a PowerPoint file[.]?",
      r"Submission is a PowerPoint file with a \.pptx extension that opens without error in PowerPoint‑compatible software[.]?",
    )
    if any(re.fullmatch(p,text,re.I) for p in pptx_exists):
        # These forms describe the submission/deliverable itself, so requiring
        # exactly one PPTX is a sound sufficient subset and prevents an
        # unrelated PPTX companion file from satisfying the criterion.
        return _one(".pptx",base,subset=True)

    if re.fullmatch(r"Exactly three separate PDF files are delivered[.]?",text,re.I):
        return v2._compiled(base,kind="EXACT_TOP_LEVEL_FILE_COUNT_BY_EXTENSION",
          args={"count":3,"extension":".pdf","total_files_must_equal_count":True})

    # "Audio file" is format-generic; requiring one valid WAV is a conservative
    # sufficient subset and makes no claim that WAV is the only accepted audio.
    if re.fullmatch(r"The deliverable is an audio file[.]?",text,re.I):
        return _exists(".wav",base,subset=True)

    return {**base,"status":"UNRESOLVED","reason":"OUTSIDE_V3_CONTROLLED_OBJECTIVE_ARTIFACT_GRAMMAR",
      "v2_status":prior.get("status"),"v2_reason":prior.get("reason")}

def verify_compiled(compiled:Mapping[str,Any],artifact_dir:str|Path)->dict[str,Any]:
    if compiled.get("status")!="COMPILED_OBJECTIVE_CHECK":
      return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":["CRITERION_NOT_COMPILED"],"terminal_authority":False}
    checks=list(compiled.get("checks") or [])
    if len(checks)==1 and checks[0].get("kind") in {"SINGLE_PDF_PAGE_COUNT_RANGE","SINGLE_PPTX_SLIDE_COUNT_MAX"}:
      root=Path(artifact_dir)
      if not root.is_dir():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":["ARTIFACT_DIR_INVALID"],"terminal_authority":False}
      files=sorted([p for p in root.iterdir() if p.is_file()],key=lambda p:p.name.casefold())
      row=checks[0];args=row.get("args") or {};kind=row["kind"];ok=False;observed=None
      try:
        if kind=="SINGLE_PDF_PAGE_COUNT_RANGE":
          cand=[p for p in files if p.suffix.lower()==".pdf"]
          if len(cand)==1 and (not args.get("total_files_must_equal_count") or len(files)==1):
            from pypdf import PdfReader
            observed=len(PdfReader(str(cand[0]),strict=True).pages)
            ok=int(args["min_pages"])<=observed<=int(args["max_pages"])
        else:
          cand=[p for p in files if p.suffix.lower()==".pptx"]
          if len(cand)==1 and (not args.get("total_files_must_equal_count") or len(files)==1):
            from pptx import Presentation
            observed=len(Presentation(str(cand[0])).slides)
            ok=observed<=int(args["max_slides"])
      except Exception:
        ok=False
      return {"schema":SCHEMA,"status":"PASS__OBJECTIVE_CRITERION_VERIFIED" if ok else "FALSIFIED_OR_FAIL_CLOSED",
        "pass":ok,"criterion_id":compiled.get("criterion_id"),"criterion_sha256":compiled.get("criterion_sha256"),
        "evidence":[{"kind":kind,"observed":observed,"pass":bool(ok)}],
        "errors":[] if ok else ["CHECK_FAILED:"+kind],"terminal_authority":False,"u_deletion_authority":False}
    delegated=dict(compiled); delegated["schema"]=v2.SCHEMA
    out=dict(v2.verify_compiled(delegated,artifact_dir));out["schema"]=SCHEMA;out["verification_origin"]="V2_OR_V1_INDEPENDENT_ARTIFACT_VERIFIER";return out
