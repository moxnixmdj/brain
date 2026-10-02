"""Information-safe bounded candidate for native structured artifact preservation.

The candidate receives a native artifact plus an explicit low-level structural edit
specification. It owns only deterministic execution. Semantic target selection,
oracle expectations, unrelated-structure snapshots and render acceptance are not
candidate-visible.
"""
from __future__ import annotations

import base64
from pathlib import Path
import tempfile
from typing import Any, Mapping

from canonical.runtime.ooxml_package_transaction import XmlSetText, apply_ooxml_transaction
from canonical.runtime.pdf_native_edit_transaction import replace_unique_pdf_text_operand

OOXML_FORMATS={"docx","xlsx","pptx"}

def _decode(value: Any) -> bytes:
    if not isinstance(value,str) or not value:
        raise ValueError("DOCUMENT_B64_REQUIRED")
    return base64.b64decode(value.encode("ascii"),validate=True)

def solve(public_case: Mapping[str,Any]) -> dict[str,Any]:
    task=public_case.get("task")
    if not isinstance(task,Mapping):
        return {"status":"FAIL_CLOSED","reason":"TASK_INVALID"}
    fmt=str(task.get("format") or "").lower()
    edit=task.get("edit")
    if not isinstance(edit,Mapping):
        return {"status":"FAIL_CLOSED","reason":"EDIT_INVALID"}
    try:
        payload=_decode(task.get("document_b64"))
    except Exception as exc:
        return {"status":"FAIL_CLOSED","reason":"DOCUMENT_DECODE_FAILED","error":type(exc).__name__}

    if fmt not in OOXML_FORMATS|{"pdf"}:
        return {"status":"FAIL_CLOSED","reason":"FORMAT_UNSUPPORTED"}

    with tempfile.TemporaryDirectory() as td:
        src=Path(td)/f"in.{fmt}"
        dst=Path(td)/f"out.{fmt}"
        src.write_bytes(payload)
        if fmt in OOXML_FORMATS:
            if edit.get("kind")!="XML_SET_TEXT":
                return {"status":"FAIL_CLOSED","reason":"OOXML_EDIT_KIND_UNSUPPORTED"}
            member=edit.get("member")
            path=edit.get("path")
            text=edit.get("new_text")
            expected_tag=edit.get("expected_tag")
            if not isinstance(member,str) or not isinstance(path,list) or not all(
                isinstance(x,int) and not isinstance(x,bool) and x>=0 for x in path
            ) or not isinstance(text,str):
                return {"status":"FAIL_CLOSED","reason":"OOXML_EDIT_SCHEMA_INVALID"}
            out=apply_ooxml_transaction(
                src,dst,
                operations=[XmlSetText(member,tuple(path),text,expected_tag if isinstance(expected_tag,str) else None)],
            )
        else:
            if edit.get("kind")!="PDF_REPLACE_UNIQUE_TEXT":
                return {"status":"FAIL_CLOSED","reason":"PDF_EDIT_KIND_UNSUPPORTED"}
            out=replace_unique_pdf_text_operand(
                src,dst,
                page_index=edit.get("page_index"),
                old=edit.get("old"),
                new=edit.get("new"),
            )
        if out.get("status")!="PASS" or not dst.is_file():
            return {"status":"FAIL_CLOSED","reason":"TRANSACTION_FAILED","transaction":out}
        return {
            "status":"OK",
            "format":fmt,
            "output_b64":base64.b64encode(dst.read_bytes()).decode("ascii"),
            "transaction_scope":out.get("scope"),
            "terminal_authority":False,
        }
