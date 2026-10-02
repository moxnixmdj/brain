"""Information-safe bounded proof for cross-format native artifact preservation.

The candidate receives only the source artifact and explicit old/new edit request.
The verifier owns the expected target mutation and unrelated-structure snapshot.

Preflight only. It does not establish arbitrary edit planning, application-native
render fidelity, or terminal contract scope equivalence.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from typing import Any

from canonical.runtime.native_artifact_unique_text_edit import apply_unique_text_edit
from canonical.runtime.ooxml_package_integrity import validate_ooxml_package


FORMATS = ("docx", "xlsx", "pptx", "pdf")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _content_types(main: str) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Override PartName="/{main}" ContentType="application/xml"/>
</Types>""".encode()


def _root_rels(main: str) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="urn:project-brain:main" Target="{main}"/>
</Relationships>""".encode()


def _ooxml_main(fmt: str, old: str) -> tuple[str, bytes]:
    if fmt == "docx":
        main = "word/document.xml"
        xml = f"""<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>{old}</w:t></w:r></w:p><w:p><w:r><w:t>KEEP</w:t></w:r></w:p></w:body></w:document>"""
    elif fmt == "xlsx":
        main = "xl/worksheets/sheet1.xml"
        xml = f"""<worksheet xmlns="urn:x"><sheetData><row><c t="inlineStr"><is><t>{old}</t></is></c><c t="inlineStr"><is><t>KEEP</t></is></c></row></sheetData></worksheet>"""
    elif fmt == "pptx":
        main = "ppt/slides/slide1.xml"
        xml = f"""<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{old}</a:t></a:r></a:p><a:p><a:r><a:t>KEEP</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>"""
    else:
        raise ValueError(fmt)
    return main, xml.encode()


def _make_ooxml(path: Path, fmt: str, old: str) -> str:
    main, payload = _ooxml_main(fmt, old)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", _content_types(main))
        z.writestr("_rels/.rels", _root_rels(main))
        z.writestr(main, payload)
        z.writestr("custom/keep.xml", b"<keep><value>UNCHANGED</value></keep>")
    return main


def _make_pdf(path: Path, old: str) -> None:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    w = PdfWriter()
    page = w.add_blank_page(width=200, height=200)
    font = DictionaryObject({
        NameObject("/Type"):NameObject("/Font"),
        NameObject("/Subtype"):NameObject("/Type1"),
        NameObject("/BaseFont"):NameObject("/Helvetica"),
    })
    font_ref = w._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"):DictionaryObject({NameObject("/F1"):font_ref})
    })
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 20 100 Td ({old}) Tj 0 -20 Td (KEEP) Tj ET".encode())
    page[NameObject("/Contents")] = w._add_object(stream)
    with path.open("wb") as f:
        w.write(f)


def _zip_snapshot(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path, "r") as z:
        return {i.filename:_sha(z.read(i.filename)) for i in z.infolist()}


def _visible_texts_from_xml(payload: bytes) -> list[str]:
    root = ET.fromstring(payload)
    return [
        node.text or ""
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "t"
    ]


def run_case(fmt: str, ordinal: int) -> dict[str, Any]:
    if fmt not in FORMATS:
        raise ValueError("FORMAT")
    old = f"TARGET_{ordinal}"
    new = f"UPDATED_{ordinal}"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = root / f"in.{fmt}"
        dst = root / f"out.{fmt}"

        if fmt == "pdf":
            _make_pdf(src, old)
            from pypdf import PdfReader
            before = PdfReader(src, strict=True)
            before_pages = len(before.pages)
            before_box = tuple(float(x) for x in before.pages[0].mediabox)
            out = apply_unique_text_edit(src, dst, old=old, new=new)
            if out.get("status") != "PASS":
                return {"pass":False,"format":fmt,"reason":"CANDIDATE:"+str(out)}
            after = PdfReader(dst, strict=True)
            text = after.pages[0].extract_text() or ""
            ok = (
                len(after.pages) == before_pages
                and tuple(float(x) for x in after.pages[0].mediabox) == before_box
                and old not in text
                and new in text
                and "KEEP" in text
            )
            return {
                "pass":ok,
                "format":fmt,
                "reason":"PASS" if ok else "PDF_ORACLE_MISMATCH",
            }

        main = _make_ooxml(src, fmt, old)
        before = _zip_snapshot(src)
        if validate_ooxml_package(src).get("status") != "PASS":
            return {"pass":False,"format":fmt,"reason":"SOURCE_PACKAGE_INVALID"}

        out = apply_unique_text_edit(src, dst, old=old, new=new)
        if out.get("status") != "PASS":
            return {"pass":False,"format":fmt,"reason":"CANDIDATE:"+str(out)}

        after = _zip_snapshot(dst)
        if set(before) != set(after):
            return {"pass":False,"format":fmt,"reason":"MEMBER_SET_CHANGED"}
        changed = sorted(k for k in before if before[k] != after[k])
        if changed != [main]:
            return {"pass":False,"format":fmt,"reason":"UNRELATED_MEMBER_MUTATION:"+str(changed)}
        if validate_ooxml_package(dst).get("status") != "PASS":
            return {"pass":False,"format":fmt,"reason":"OUTPUT_PACKAGE_INVALID"}

        with zipfile.ZipFile(dst, "r") as z:
            texts = _visible_texts_from_xml(z.read(main))
            keep = z.read("custom/keep.xml")
        ok = old not in texts and new in texts and "KEEP" in texts and keep == b"<keep><value>UNCHANGED</value></keep>"
        return {
            "pass":ok,
            "format":fmt,
            "reason":"PASS" if ok else "OOXML_ORACLE_MISMATCH",
        }


def run_grid(cases_per_format: int = 12) -> dict[str, Any]:
    rows = []
    for fmt in FORMATS:
        for i in range(cases_per_format):
            rows.append(run_case(fmt, i))
    passed = sum(int(x["pass"]) for x in rows)
    return {
        "schema":"PROJECT_BRAIN_NATIVE_ARTIFACT_CROSS_FORMAT_PREFLIGHT_RESULT_V1",
        "case_count":len(rows),
        "passed":passed,
        "failed":len(rows)-passed,
        "all_pass":passed == len(rows),
        "by_format":{
            fmt:{
                "pass":sum(int(x["pass"]) for x in rows if x["format"] == fmt),
                "total":sum(1 for x in rows if x["format"] == fmt),
            }
            for fmt in FORMATS
        },
        "failures":[x for x in rows if not x["pass"]],
        "terminal_authority":False,
        "capability_credit_delta":0,
    }
