"""Bounded Brain candidate for native exact-text edit preservation.

The candidate receives a native source path and an explicit exact-text replacement
request. It must discover the unique target location from source bytes. It never
receives target bytes, a member/page location, or an expected structural diff.

OOXML formats reuse the Brain-owned atomic package transaction. PDF reuses the
Brain-owned bounded native PDF text transaction. This is a bounded exact-text
route only and grants no whole-contract authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import xml.etree.ElementTree as ET
import zipfile

from canonical.runtime.ooxml_package_transaction import XmlSetText, apply_ooxml_transaction
from canonical.runtime.pdf_native_edit_transaction import replace_unique_pdf_text_operand


_OOXML_PREFIX={"docx":"word/","xlsx":"xl/","pptx":"ppt/"}


def _walk(node:ET.Element,path:tuple[int,...]=()):
    yield path,node
    for i,child in enumerate(list(node)):
        yield from _walk(child,path+(i,))


def _find_ooxml_target(src:Path,fmt:str,old:str):
    prefix=_OOXML_PREFIX[fmt]
    matches=[]
    try:
        with zipfile.ZipFile(src,"r") as z:
            for name in sorted(z.namelist()):
                if not name.startswith(prefix) or not name.endswith(".xml"):
                    continue
                try:
                    root=ET.fromstring(z.read(name))
                except ET.ParseError:
                    continue
                for path,node in _walk(root):
                    if (node.text or "")==old:
                        matches.append((name,path,node.tag))
    except Exception:
        return []
    return matches


def _find_pdf_page(src:Path,old:str)->list[int]:
    try:
        from pypdf import PdfReader
        reader=PdfReader(src,strict=True)
        if reader.is_encrypted:
            return []
        pages=[]
        for i,page in enumerate(reader.pages):
            text=page.extract_text() or ""
            if text.count(old):
                pages.extend([i]*text.count(old))
        return pages
    except Exception:
        return []


def apply_request(
    input_path:str|Path,
    output_path:str|Path,
    request:Mapping[str,Any],
)->dict[str,Any]:
    src=Path(input_path)
    if not src.is_file() or not isinstance(request,Mapping):
        return {"status":"FAIL_CLOSED","reason":"INPUT_OR_REQUEST_INVALID"}
    fmt=str(request.get("format") or "").lower()
    op=request.get("operation")
    old=request.get("old")
    new=request.get("new")
    if op!="replace_exact_text" or not isinstance(old,str) or not old or not isinstance(new,str) or old==new:
        return {"status":"FAIL_CLOSED","reason":"REQUEST_UNSUPPORTED_OR_INVALID"}

    if fmt in _OOXML_PREFIX:
        matches=_find_ooxml_target(src,fmt,old)
        if len(matches)!=1:
            return {
                "status":"FAIL_CLOSED",
                "reason":"OOXML_TEXT_TARGET_NOT_UNIQUE",
                "match_count":len(matches),
            }
        member,path,tag=matches[0]
        out=apply_ooxml_transaction(
            src,output_path,
            operations=[XmlSetText(member,path,new,expected_tag=tag)],
        )
        if out.get("status")!="PASS":
            return out
        return {
            **out,
            "format":fmt,
            "discovered_target_member":member,
            "discovered_target_path":list(path),
            "scope":"UNIQUE_EXACT_XML_TEXT_TARGET_DISCOVERY_PLUS_ATOMIC_OOXML_TRANSACTION",
        }

    if fmt=="pdf":
        pages=_find_pdf_page(src,old)
        if len(pages)!=1:
            return {
                "status":"FAIL_CLOSED",
                "reason":"PDF_TEXT_TARGET_NOT_UNIQUE",
                "match_count":len(pages),
            }
        out=replace_unique_pdf_text_operand(
            src,output_path,page_index=pages[0],old=old,new=new,
        )
        if out.get("status")!="PASS":
            return out
        return {
            **out,
            "format":"pdf",
            "discovered_page_index":pages[0],
            "scope":"UNIQUE_EXTRACTED_TEXT_PAGE_DISCOVERY_PLUS_NATIVE_PDF_TEXT_TRANSACTION",
        }

    return {"status":"FAIL_CLOSED","reason":"FORMAT_UNSUPPORTED"}
