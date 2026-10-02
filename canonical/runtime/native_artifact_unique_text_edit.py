"""Bounded cross-format native artifact exact-text edit route.

The route accepts a native source artifact plus an explicit old/new text edit request.
For DOCX/XLSX/PPTX it resolves the unique visible XML text node itself, applies one
atomic OOXML transaction, and validates package integrity. For PDF it resolves the
unique page by extracted text and delegates to the exact whole text-show operand
transaction, which independently fails closed on split/ambiguous encodings.

This is a bounded deterministic mechanism. It does not claim arbitrary semantic edit
planning, visual-layout equivalence, or whole-contract terminal authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET
import zipfile

from canonical.runtime.ooxml_package_integrity import validate_ooxml_package
from canonical.runtime.ooxml_package_transaction import XmlSetText, apply_ooxml_transaction
from canonical.runtime.pdf_native_edit_transaction import replace_unique_pdf_text_operand


_OOXML = {".docx", ".xlsx", ".pptx"}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _walk(node: ET.Element, path: tuple[int, ...] = ()):
    yield path, node
    for i, child in enumerate(list(node)):
        yield from _walk(child, path + (i,))


def _allowed_text_part(ext: str, member: str) -> bool:
    if ext == ".docx":
        return (
            member == "word/document.xml"
            or member.startswith("word/header") and member.endswith(".xml")
            or member.startswith("word/footer") and member.endswith(".xml")
            or member in {"word/footnotes.xml", "word/endnotes.xml"}
        )
    if ext == ".xlsx":
        # Inline worksheet strings only. Shared-string indirection is intentionally
        # excluded because one shared string may drive multiple cells.
        return member.startswith("xl/worksheets/") and member.endswith(".xml")
    if ext == ".pptx":
        return member.startswith("ppt/slides/slide") and member.endswith(".xml")
    return False


def _resolve_unique_ooxml_text(src: Path, ext: str, old: str):
    matches: list[tuple[str, tuple[int, ...], str]] = []
    try:
        with zipfile.ZipFile(src, "r") as zf:
            for info in zf.infolist():
                member = info.filename
                if not _allowed_text_part(ext, member):
                    continue
                try:
                    root = ET.fromstring(zf.read(member))
                except Exception:
                    return None, "VISIBLE_XML_PART_INVALID"
                for path, node in _walk(root):
                    if _local(node.tag) == "t" and (node.text or "") == old:
                        matches.append((member, path, node.tag))
    except Exception:
        return None, "INVALID_OOXML_PACKAGE"
    if len(matches) != 1:
        return None, "VISIBLE_TEXT_TARGET_NOT_UNIQUE"
    return matches[0], None


def _resolve_unique_pdf_page(src: Path, old: str):
    try:
        from pypdf import PdfReader
        reader = PdfReader(src, strict=True)
        if reader.is_encrypted:
            return None, "ENCRYPTED_PDF_UNSUPPORTED"
        hits = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            count = text.count(old)
            if count:
                hits.extend([i] * count)
    except Exception:
        return None, "PDF_READ_FAILED"
    if len(hits) != 1:
        return None, "PDF_VISIBLE_TEXT_TARGET_NOT_UNIQUE"
    return hits[0], None


def apply_unique_text_edit(
    input_path: str | Path,
    output_path: str | Path,
    *,
    old: str,
    new: str,
) -> dict[str, Any]:
    src = Path(input_path)
    dst = Path(output_path)
    ext = src.suffix.lower()

    if not src.is_file():
        return {"status":"FAIL_CLOSED","reason":"INPUT_MISSING"}
    if ext not in _OOXML | {".pdf"}:
        return {"status":"FAIL_CLOSED","reason":"FORMAT_UNSUPPORTED","format":ext}
    if not isinstance(old, str) or not old or not isinstance(new, str) or not new:
        return {"status":"FAIL_CLOSED","reason":"TEXT_ARGUMENT_INVALID"}
    if old == new:
        return {"status":"FAIL_CLOSED","reason":"NO_OP_REPLACEMENT"}
    if dst.resolve() == src.resolve():
        return {"status":"FAIL_CLOSED","reason":"IN_PLACE_MUTATION_FORBIDDEN"}

    if ext in _OOXML:
        target, err = _resolve_unique_ooxml_text(src, ext, old)
        if err:
            return {"status":"FAIL_CLOSED","reason":err}
        member, path, expected_tag = target
        out = apply_ooxml_transaction(
            src,
            dst,
            operations=[XmlSetText(member=member, path=path, text=new, expected_tag=expected_tag)],
        )
        if out.get("status") != "PASS":
            return out
        integrity = validate_ooxml_package(dst)
        if integrity.get("status") != "PASS":
            dst.unlink(missing_ok=True)
            return {
                "status":"FAIL_CLOSED",
                "reason":"POST_EDIT_PACKAGE_INTEGRITY_FAILED",
                "integrity":integrity,
            }
        return {
            "status":"PASS",
            "format":ext[1:].upper(),
            "output_path":str(dst),
            "resolved_member":member,
            "resolved_child_index_path":list(path),
            "changed_members":out.get("changed_members", []),
            "unrelated_members_preserved":True,
            "package_integrity_valid":True,
            "scope":"UNIQUE_EXACT_VISIBLE_XML_TEXT_NODE_EDIT_WITHIN_BOUNDED_NATIVE_OOXML_PARTS",
            "semantic_authority":False,
            "visual_layout_authority":False,
            "terminal_authority":False,
        }

    page_index, err = _resolve_unique_pdf_page(src, old)
    if err:
        return {"status":"FAIL_CLOSED","reason":err}
    out = replace_unique_pdf_text_operand(
        src,
        dst,
        page_index=page_index,
        old=old,
        new=new,
    )
    if out.get("status") != "PASS":
        return out
    return {
        **out,
        "format":"PDF",
        "resolved_page_index":page_index,
        "scope":"UNIQUE_EXACT_WHOLE_PDF_TEXT_SHOW_OPERAND_RESOLVED_FROM_VISIBLE_TEXT",
        "semantic_authority":False,
        "visual_layout_authority":False,
        "terminal_authority":False,
    }
