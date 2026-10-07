"""Sound sufficient certificates for narrow GDPval XLSX table criteria.

The verifier does not guess headers from arbitrary cell text. It requires a native
Excel Table object with a real header row. This is stronger than necessary, but
safe for positive-cover use.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
from typing import Any, Mapping

from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries

SCHEMA="PROJECT_BRAIN_GDPVAL_XLSX_TABLE_CRITERIA_V1"


def _payload(text:str,criterion_id:str|None)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "criterion_id":criterion_id,
        "criterion":text,
        "criterion_sha256":sha256(text.encode("utf-8")).hexdigest(),
        "terminal_authority":False,
    }


def compile_criterion(criterion:str,*,criterion_id:str|None=None)->dict[str,Any]:
    text=" ".join(str(criterion or "").split())
    base=_payload(text,criterion_id)
    if not text:
        return {**base,"status":"FAIL_CLOSED","reason":"CRITERION_MISSING"}

    m=re.fullmatch(
        r"First\s+worksheet\s+includes\s+a\s+column\s+titled\s+['\"“](.+?)['\"”]\s*"
        r"\(case-insensitive\s+match\)[.]?",
        text,re.I,
    )
    if m:
        return {
            **base,
            "status":"COMPILED_SUFFICIENT_XLSX_TABLE_CHECK",
            "check":{"kind":"SHEET_ORDINAL_NATIVE_TABLE_COLUMN_CASEFOLD","sheet_index":0,"column_name":m.group(1)},
            "sufficiency_rule":"NATIVE_EXCEL_TABLE_HEADER_IS_A_SOUND_WITNESS_OF_A_TITLED_COLUMN",
        }

    m=re.fullmatch(
        r"Second\s+worksheet\s+includes\s+a\s+column\s+titled\s+['\"“](.+?)['\"”]\s*"
        r"\(case-insensitive\s+match\)[.]?",
        text,re.I,
    )
    if m:
        return {
            **base,
            "status":"COMPILED_SUFFICIENT_XLSX_TABLE_CHECK",
            "check":{"kind":"SHEET_ORDINAL_NATIVE_TABLE_COLUMN_CASEFOLD","sheet_index":1,"column_name":m.group(1)},
            "sufficiency_rule":"NATIVE_EXCEL_TABLE_HEADER_IS_A_SOUND_WITNESS_OF_A_TITLED_COLUMN",
        }

    m=re.fullmatch(
        r"No\s+row\s+on\s+the\s+second\s+worksheet\s+has\s+Well\s+Description\s+containing\s+"
        r"['\"“](.+?)['\"”]\s*\(case-insensitive\)[.]?",
        text,re.I,
    )
    if m:
        return {
            **base,
            "status":"COMPILED_SUFFICIENT_XLSX_TABLE_CHECK",
            "check":{
                "kind":"SHEET_ORDINAL_NATIVE_TABLE_COLUMN_GLOBAL_NOT_CONTAINS_CASEFOLD",
                "sheet_index":1,
                "column_name":"Well Description",
                "needle":m.group(1),
            },
            "sufficiency_rule":"A_NATIVE_TABLE_BINDS_THE_COLUMN_IDENTITY_AND_THE_VERIFIER_SCANS_EVERY_LOWER_CELL_IN_THAT_WORKSHEET_COLUMN_THROUGH_MAX_ROW",
        }

    return {
        **base,
        "status":"UNRESOLVED",
        "reason":"OUTSIDE_CERTIFIED_NATIVE_XLSX_TABLE_GRAMMAR",
    }


def _native_table_column(ws, target:str):
    wanted=target.casefold()
    matches=[]
    for table in ws.tables.values():
        if not getattr(table,"ref",None):
            continue
        min_col,min_row,max_col,_=range_boundaries(table.ref)
        # A native Excel table header row is the first row of its ref.
        if getattr(table,"headerRowCount",1)==0:
            continue
        for col in range(min_col,max_col+1):
            value=ws.cell(min_row,col).value
            if isinstance(value,str) and value.strip().casefold()==wanted:
                matches.append((table,min_row,col))
    return matches


def verify_compiled(compiled:Mapping[str,Any],artifact_dir:str|Path)->dict[str,Any]:
    if compiled.get("status")!="COMPILED_SUFFICIENT_XLSX_TABLE_CHECK":
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
    books=sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in {".xlsx",".xlsm"}
    )
    if len(books)!=1:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "errors":["EXACTLY_ONE_NATIVE_XLSX_REQUIRED"],"terminal_authority":False,
        }

    try:
        wb=load_workbook(
            books[0],read_only=False,data_only=False,
            keep_vba=(books[0].suffix.lower()==".xlsm"),
        )
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "errors":[type(exc).__name__+":"+str(exc)],"terminal_authority":False,
        }

    try:
        check=compiled.get("check") or {}
        idx=check.get("sheet_index")
        if not isinstance(idx,int) or idx<0 or idx>=len(wb.worksheets):
            return {
                "schema":SCHEMA,"status":"FALSIFIED","pass":False,
                "errors":["WORKSHEET_ORDINAL_MISSING"],"terminal_authority":False,
            }
        ws=wb.worksheets[idx]
        kind=check.get("kind")
        matches=_native_table_column(ws,str(check.get("column_name") or ""))
        if not matches:
            return {
                "schema":SCHEMA,"status":"FALSIFIED","pass":False,
                "errors":["NATIVE_TABLE_COLUMN_WITNESS_MISSING"],"terminal_authority":False,
            }

        if kind=="SHEET_ORDINAL_NATIVE_TABLE_COLUMN_CASEFOLD":
            passed=True
            detail={"sheet_title":ws.title,"matching_native_table_column_count":len(matches)}

        elif kind=="SHEET_ORDINAL_NATIVE_TABLE_COLUMN_GLOBAL_NOT_CONTAINS_CASEFOLD":
            needle=str(check.get("needle") or "").casefold()
            if not needle:
                return {
                    "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                    "errors":["NEEDLE_MISSING"],"terminal_authority":False,
                }
            # Stronger-than-necessary certificate: every matching native-table
            # header column must be free of the forbidden substring in every
            # cell below that header through the worksheet's max_row.
            violations=[]
            for _,header_row,col in matches:
                for row in range(header_row+1,ws.max_row+1):
                    value=ws.cell(row,col).value
                    if value is not None and needle in str(value).casefold():
                        violations.append({"row":row,"column":col})
            passed=not violations
            detail={
                "sheet_title":ws.title,
                "matching_native_table_column_count":len(matches),
                "violations":violations,
            }
        else:
            return {
                "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "errors":["UNKNOWN_CHECK_KIND:"+str(kind)],"terminal_authority":False,
            }

        return {
            "schema":SCHEMA,
            "status":"PASS__SUFFICIENT_NATIVE_XLSX_TABLE_CERTIFICATE" if passed else "FALSIFIED",
            "pass":passed,
            "artifact":books[0].name,
            "criterion_id":compiled.get("criterion_id"),
            "criterion_sha256":compiled.get("criterion_sha256"),
            "detail":detail,
            "terminal_authority":False,
            "u_deletion_authority":False,
            "soundness_boundary":"STRONGER_NATIVE_TABLE_WITNESS_ONLY__FAILURE_DOES_NOT_PROVE_CRITERION_FAILURE",
        }
    finally:
        wb.close()
