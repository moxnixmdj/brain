"""GDPval objective artifact criteria V2.

Extends V1 only with additional whole-criterion forms whose truth is directly
decidable from the submitted native artifact set. No partial-regex credit.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import gdpval_objective_artifact_criteria_v1 as v1

SCHEMA="PROJECT_BRAIN_GDPVAL_OBJECTIVE_ARTIFACT_CRITERIA_V2"


def _base_payload(text:str, criterion_id:str|None)->dict[str,Any]:
    import hashlib
    return {
        "schema":SCHEMA,
        "criterion_id":criterion_id,
        "criterion":text,
        "criterion_sha256":hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "terminal_authority":False,
    }


def compile_criterion(criterion:str,*,criterion_id:str|None=None)->dict[str,Any]:
    base=v1.compile_criterion(criterion,criterion_id=criterion_id)
    if base.get("status")=="COMPILED_OBJECTIVE_CHECK":
        return {
            **base,
            "schema":SCHEMA,
            "compiler_version":"V1_DELEGATED",
        }

    text=" ".join(str(criterion or "").split())
    out=_base_payload(text,criterion_id)
    if not text:
        return {**out,"status":"FAIL_CLOSED","reason":"CRITERION_MISSING"}

    # Sheet/tab identity variants with explicit comparison semantics.
    patterns=(
        (
            re.compile(
                r'^The\s+workbook\s+contains\s+a\s+worksheet\s+named\s+exactly\s+[\'"“](.+?)[\'"”]\s*\(case-insensitive\)[.]?$',
                re.I,
            ),
            "XLSX_SHEET_NAME_CASEFOLD",
        ),
        (
            re.compile(r'^Workbook\s+includes\s+a\s+sheet\s+titled\s+exactly\s+[\'"“](.+?)[\'"”][.]?$',re.I),
            "XLSX_SHEET_NAME_EXACT",
        ),
        (
            re.compile(r'^Excel\s+workbook\s+includes\s+tab\s+titled\s+[\'"“](.+?)[\'"”][.]?$',re.I),
            "XLSX_SHEET_NAME_EXACT",
        ),
    )
    for pat,kind in patterns:
        m=pat.fullmatch(text)
        if m:
            return {
                **out,
                "status":"COMPILED_OBJECTIVE_CHECK",
                "checks":[{"kind":kind,"args":{"sheet_name":m.group(1)}}],
                "soundness_boundary":"WHOLE_CRITERION_EXACT_MATCH_ONLY__SHEET_TITLE_IDENTITY_ONLY__NO_TABLE_OR_CONTENT_SEMANTICS",
            }

    # Exact one-file PDF forms.
    single_pdf=(
        r'^The\s+deliverable\s+is\s+provided\s+as\s+a\s+single\s+PDF\s+file[.]?$',
        r'^The\s+deliverable\s+is\s+a\s+single\s+PDF\s+file(?:\s*\(\.pdf\))?[.]?$',
        r'^The\s+final\s+deliverable\s+is\s+a\s+single\s+PDF\s+file[.]?$',
        r'^Exactly\s+one\s+deliverable\s+is\s+provided\s+and\s+it\s+is\s+a\s+single\s+PDF\s+file[.]?$',
        r'^The\s+deliverable\s+is\s+exactly\s+one\s+PDF\s+file\s*\(not\s+multiple\s+files\s+or\s+a\s+ZIP\)[.]?$',
    )
    if any(re.fullmatch(p,text,re.I) for p in single_pdf):
        return {
            **out,
            "status":"COMPILED_OBJECTIVE_CHECK",
            "checks":[{
                "kind":"EXACT_TOP_LEVEL_FILE_COUNT_BY_EXTENSION",
                "args":{"count":1,"extension":".pdf","total_files_must_equal_count":True},
            }],
            "soundness_boundary":"WHOLE_CRITERION_EXACT_MATCH_ONLY__TOP_LEVEL_FILE_COUNT_AND_NATIVE_PDF_VALIDITY",
        }

    # Plain PDF format, no uniqueness claim.
    if re.fullmatch(r'^The\s+deliverable\s+is\s+provided\s+as\s+a\s+PDF\s+file[.]?$',text,re.I):
        return {
            **out,
            "status":"COMPILED_OBJECTIVE_CHECK",
            "checks":[{"kind":"AT_LEAST_ONE_VALID_FILE_BY_EXTENSION","args":{"extension":".pdf"}}],
            "soundness_boundary":"WHOLE_CRITERION_EXACT_MATCH_ONLY__PDF_NATIVE_VALIDITY_ONLY",
        }

    # Exact one-file XLSX forms.
    single_xlsx=(
        r'^Deliverable\s+is\s+provided\s+as\s+a\s+single\s+Excel\s+workbook\s+file\s*\(\.xlsx\)[.]?$',
        r'^The\s+deliverable\s+is\s+a\s+single\s+Excel\s+workbook\s+in\s+\.xlsx\s+format[.]?$',
        r'^The\s+deliverable\s+is\s+a\s+single\s+Excel\s+workbook\s+file\s+with\s+\.xlsx\s+extension[.]?$',
        r'^The\s+deliverable\s+is\s+a\s+single\s+Microsoft\s+Excel\s+workbook\s+file\s*\(\.xlsx\)[.]?$',
    )
    if any(re.fullmatch(p,text,re.I) for p in single_xlsx):
        return {
            **out,
            "status":"COMPILED_OBJECTIVE_CHECK",
            "checks":[{
                "kind":"EXACT_TOP_LEVEL_FILE_COUNT_BY_EXTENSION",
                "args":{"count":1,"extension":".xlsx","total_files_must_equal_count":True},
            }],
            "soundness_boundary":"WHOLE_CRITERION_EXACT_MATCH_ONLY__TOP_LEVEL_FILE_COUNT_AND_NATIVE_XLSX_VALIDITY",
        }

    # Plain XLSX format requirements, no uniqueness claim.
    xlsx_plain=(
        r'^The\s+spreadsheet\s+deliverable\s+is\s+an\s+Excel\s+workbook\s+in\s+\.xlsx\s+format[.]?$',
        r'^Deliverable\s+is\s+an\s+Excel\s+workbook\s+file\s+with\s+a\s+\.xlsx\s+extension[.]?$',
    )
    if any(re.fullmatch(p,text,re.I) for p in xlsx_plain):
        return {
            **out,
            "status":"COMPILED_OBJECTIVE_CHECK",
            "checks":[{"kind":"AT_LEAST_ONE_VALID_FILE_BY_EXTENSION","args":{"extension":".xlsx"}}],
            "soundness_boundary":"WHOLE_CRITERION_EXACT_MATCH_ONLY__XLSX_NATIVE_VALIDITY_ONLY",
        }

    # Exact total slide count. The artifact must be a valid PPTX.
    m=re.fullmatch(
        r'^The\s+presentation\s+contains\s+exactly\s+(\d+)\s+slides(?:\s+in\s+total\s*\(counting\s+title\s+and\s+any\s+closing/references\s+slides\))?[.]?$',
        text,re.I,
    )
    if m:
        return {
            **out,
            "status":"COMPILED_OBJECTIVE_CHECK",
            "checks":[{"kind":"PPTX_TOTAL_SLIDE_COUNT","args":{"count":int(m.group(1))}}],
            "soundness_boundary":"WHOLE_CRITERION_EXACT_MATCH_ONLY__PPTX_NATIVE_VALIDITY_AND_TOTAL_SLIDE_COUNT",
        }

    return {
        **out,
        "status":"UNRESOLVED",
        "reason":"OUTSIDE_EXACT_OBJECTIVE_ARTIFACT_GRAMMAR_V2",
    }


def verify_compiled(compiled:Mapping[str,Any],artifact_dir:str|Path)->dict[str,Any]:
    if compiled.get("compiler_version")=="V1_DELEGATED":
        return v1.verify_compiled(compiled,artifact_dir)

    if compiled.get("status")!="COMPILED_OBJECTIVE_CHECK":
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "errors":["CRITERION_NOT_COMPILED"],"terminal_authority":False,
        }

    root=Path(artifact_dir)
    if not root.is_dir():
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "errors":["ARTIFACT_DIR_INVALID"],"terminal_authority":False,
        }
    files=v1._files(root)
    errors=[]; evidence=[]

    for row in compiled.get("checks",[]):
        kind=row.get("kind"); args=row.get("args") or {}
        ok=False
        if kind in {"XLSX_SHEET_NAME_CASEFOLD","XLSX_SHEET_NAME_EXACT"}:
            target=str(args.get("sheet_name") or "")
            for p in files:
                if p.suffix.lower() not in {".xlsx",".xlsm"}:
                    continue
                names=v1._xlsx_sheet_names(p)
                if names is None:
                    continue
                if kind=="XLSX_SHEET_NAME_CASEFOLD":
                    ok=any(n.casefold()==target.casefold() for n in names)
                else:
                    ok=target in names
                if ok: break
        elif kind=="PPTX_TOTAL_SLIDE_COUNT":
            target=int(args.get("count",-1))
            cand=[p for p in files if p.suffix.lower()==".pptx"]
            if len(cand)==1 and v1._valid_package(cand[0]):
                try:
                    from pptx import Presentation
                    ok=len(Presentation(str(cand[0])).slides)==target
                except Exception:
                    ok=False
        else:
            # Reuse V1 verifier for its exact check kinds.
            delegated={
                "schema":v1.SCHEMA,
                "status":"COMPILED_OBJECTIVE_CHECK",
                "criterion_id":compiled.get("criterion_id"),
                "criterion_sha256":compiled.get("criterion_sha256"),
                "checks":[row],
                "terminal_authority":False,
            }
            sub=v1.verify_compiled(delegated,root)
            ok=sub.get("pass") is True

        evidence.append({"kind":kind,"pass":bool(ok)})
        if not ok: errors.append("CHECK_FAILED:"+str(kind))

    return {
        "schema":SCHEMA,
        "status":"PASS__OBJECTIVE_CRITERION_VERIFIED" if not errors else "FALSIFIED_OR_FAIL_CLOSED",
        "pass":not errors,
        "criterion_id":compiled.get("criterion_id"),
        "criterion_sha256":compiled.get("criterion_sha256"),
        "evidence":evidence,
        "errors":errors,
        "terminal_authority":False,
        "u_deletion_authority":False,
    }
