"""Bounded native PDF edit transactions using pinned permissive PDF mechanics.

Pinned mechanism:
- pypdf 6.19.0 (BSD-3-Clause)
- Pillow 12.3.0 for image payload replacement

Owned bounded operations:
1. Replace exactly one whole PDF text-show operand (Tj, TJ, ', or ") on one
   declared page. Ambiguous/split/encoded text not represented as TextStringObject
   fails closed.
2. Replace exactly one declared page image XObject with an image of identical
   pixel dimensions and mode. The page content stream must remain unchanged.

These operations preserve native PDF object semantics; they do not rasterize or
rebuild pages. They make no claim that arbitrary text has equal glyph width or
that a semantic user request can be mapped to the correct operand/image key.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any


def _deps():
    try:
        from PIL import Image
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import ArrayObject, ContentStream, TextStringObject
        return Image, PdfReader, PdfWriter, ArrayObject, ContentStream, TextStringObject
    except Exception as exc:
        return exc


def _page_signature(page: Any) -> dict[str, Any]:
    mb=page.mediabox
    content=page.get_contents()
    return {
        "mediabox": tuple(float(x) for x in (mb.left,mb.bottom,mb.right,mb.top)),
        "rotation": int(page.get("/Rotate",0) or 0),
        "content_operator_sequence": [] if content is None else None,
    }


def _text_matches(operations, old, TextStringObject, ArrayObject):
    matches=[]
    for oi,(operands,operator) in enumerate(operations):
        if operator in (b"Tj",b"'",b'"'):
            if operands and isinstance(operands[-1],TextStringObject) and str(operands[-1])==old:
                matches.append(("scalar",oi,len(operands)-1))
        elif operator==b"TJ" and operands and isinstance(operands[0],ArrayObject):
            for ai,item in enumerate(operands[0]):
                if isinstance(item,TextStringObject) and str(item)==old:
                    matches.append(("array",oi,ai))
    return matches


def replace_unique_pdf_text_operand(
    input_path: str|Path,
    output_path: str|Path,
    *,
    page_index: int,
    old: str,
    new: str,
) -> dict:
    deps=_deps()
    if isinstance(deps,Exception):
        return {"status":"FAIL_CLOSED","reason":"DEPENDENCY_UNAVAILABLE","error":type(deps).__name__}
    _,PdfReader,PdfWriter,ArrayObject,ContentStream,TextStringObject=deps
    src=Path(input_path); dst=Path(output_path)
    if not src.is_file():
        return {"status":"FAIL_CLOSED","reason":"INPUT_MISSING"}
    if not isinstance(page_index,int) or isinstance(page_index,bool) or page_index<0:
        return {"status":"FAIL_CLOSED","reason":"PAGE_INDEX_INVALID"}
    if not isinstance(old,str) or not old or not isinstance(new,str):
        return {"status":"FAIL_CLOSED","reason":"TEXT_ARGUMENT_INVALID"}
    if old==new:
        return {"status":"FAIL_CLOSED","reason":"NO_OP_REPLACEMENT"}

    try:
        reader=PdfReader(src,strict=True)
        if reader.is_encrypted:
            return {"status":"FAIL_CLOSED","reason":"ENCRYPTED_PDF_UNSUPPORTED"}
        if page_index>=len(reader.pages):
            return {"status":"FAIL_CLOSED","reason":"PAGE_INDEX_OUT_OF_RANGE"}
        before_page=reader.pages[page_index]
        before_sig=_page_signature(before_page)
        before_text=before_page.extract_text()
        writer=PdfWriter(clone_from=src)
        page=writer.pages[page_index]
        original_content=page.get_contents()
        if original_content is None:
            return {"status":"FAIL_CLOSED","reason":"PAGE_CONTENT_MISSING"}
        content=ContentStream(original_content,writer)
        operations=content.operations
        operator_sequence=[op for _,op in operations]
        matches=_text_matches(operations,old,TextStringObject,ArrayObject)
        if len(matches)!=1:
            return {"status":"FAIL_CLOSED","reason":"TEXT_OPERAND_NOT_UNIQUE","match_count":len(matches)}
        kind,oi,idx=matches[0]
        operands,operator=operations[oi]
        if kind=="scalar":
            operands[idx]=TextStringObject(new)
        else:
            operands[0][idx]=TextStringObject(new)
        content.operations=operations
        page.replace_contents(content)
        dst.parent.mkdir(parents=True,exist_ok=True)
        writer.write(dst)
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status":"FAIL_CLOSED","reason":"PDF_TEXT_TRANSACTION_FAILED","error":type(exc).__name__,"detail":str(exc)}

    try:
        check=PdfReader(dst,strict=True)
        if len(check.pages)!=len(reader.pages):
            raise ValueError("page count changed")
        after_page=check.pages[page_index]
        after_sig=_page_signature(after_page)
        after_content=ContentStream(after_page.get_contents(),check)
        after_ops=after_content.operations
        if [op for _,op in after_ops] != operator_sequence:
            raise ValueError("operator sequence changed")
        after_matches_new=_text_matches(after_ops,new,TextStringObject,ArrayObject)
        after_matches_old=_text_matches(after_ops,old,TextStringObject,ArrayObject)
        if len(after_matches_new)!=1 or after_matches_old:
            raise ValueError("roundtrip target mismatch")
        if before_sig["mediabox"]!=after_sig["mediabox"] or before_sig["rotation"]!=after_sig["rotation"]:
            raise ValueError("page geometry changed")
        after_text=after_page.extract_text()
        if old in (before_text or "") and new not in (after_text or ""):
            raise ValueError("roundtrip extraction missing replacement")
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status":"FAIL_CLOSED","reason":"PDF_TEXT_ROUNDTRIP_FAILED","error":type(exc).__name__,"detail":str(exc)}

    return {
        "status":"PASS",
        "output_path":str(dst),
        "page_index":page_index,
        "operator":operator.decode("latin1"),
        "page_count":len(reader.pages),
        "page_geometry_preserved":True,
        "operator_sequence_preserved":True,
        "scope":"EXACT_UNIQUE_WHOLE_TEXT_SHOW_OPERAND_REPLACEMENT_ON_DECLARED_PAGE",
        "visual_layout_authority":False,
        "semantic_authority":False,
        "terminal_authority":False,
    }


def replace_pdf_page_image(
    input_path: str|Path,
    output_path: str|Path,
    *,
    page_index: int,
    image_key: str,
    replacement_image: bytes,
) -> dict:
    deps=_deps()
    if isinstance(deps,Exception):
        return {"status":"FAIL_CLOSED","reason":"DEPENDENCY_UNAVAILABLE","error":type(deps).__name__}
    Image,PdfReader,PdfWriter,_,_,_=deps
    src=Path(input_path); dst=Path(output_path)
    if not src.is_file():
        return {"status":"FAIL_CLOSED","reason":"INPUT_MISSING"}
    if not isinstance(page_index,int) or isinstance(page_index,bool) or page_index<0:
        return {"status":"FAIL_CLOSED","reason":"PAGE_INDEX_INVALID"}
    if not isinstance(image_key,str) or not image_key:
        return {"status":"FAIL_CLOSED","reason":"IMAGE_KEY_INVALID"}
    if not isinstance(replacement_image,(bytes,bytearray)) or not replacement_image:
        return {"status":"FAIL_CLOSED","reason":"REPLACEMENT_IMAGE_INVALID"}

    try:
        reader=PdfReader(src,strict=True)
        if reader.is_encrypted:
            return {"status":"FAIL_CLOSED","reason":"ENCRYPTED_PDF_UNSUPPORTED"}
        if page_index>=len(reader.pages):
            return {"status":"FAIL_CLOSED","reason":"PAGE_INDEX_OUT_OF_RANGE"}
        writer=PdfWriter(clone_from=src)
        page=writer.pages[page_index]
        keys=list(page.images.keys())
        if image_key not in keys:
            return {"status":"FAIL_CLOSED","reason":"IMAGE_KEY_NOT_FOUND","available_keys":[str(x) for x in keys]}
        image_file=page.images[image_key]
        if image_file.is_inline:
            return {"status":"FAIL_CLOSED","reason":"INLINE_IMAGE_UNSUPPORTED"}
        if image_file.image is None:
            return {"status":"FAIL_CLOSED","reason":"SOURCE_IMAGE_DECODE_UNAVAILABLE"}
        old_size=image_file.image.size
        old_mode=image_file.image.mode
        content=page.get_contents()
        content_before=b"" if content is None else content.get_data()
        new_image=Image.open(BytesIO(bytes(replacement_image)))
        new_image.load()
        if new_image.size!=old_size:
            return {"status":"FAIL_CLOSED","reason":"IMAGE_DIMENSIONS_DIFFER","old_size":list(old_size),"new_size":list(new_image.size)}
        if new_image.mode!=old_mode:
            return {"status":"FAIL_CLOSED","reason":"IMAGE_MODE_DIFFERS","old_mode":old_mode,"new_mode":new_image.mode}
        image_file.replace(new_image)
        content_after=b"" if page.get_contents() is None else page.get_contents().get_data()
        if content_after!=content_before:
            return {"status":"FAIL_CLOSED","reason":"PAGE_CONTENT_STREAM_MUTATED_BY_IMAGE_REPLACEMENT"}
        dst.parent.mkdir(parents=True,exist_ok=True)
        writer.write(dst)
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status":"FAIL_CLOSED","reason":"PDF_IMAGE_TRANSACTION_FAILED","error":type(exc).__name__,"detail":str(exc)}

    try:
        check=PdfReader(dst,strict=True)
        if len(check.pages)!=len(reader.pages):
            raise ValueError("page count changed")
        p=check.pages[page_index]
        check_content=p.get_contents()
        if (b"" if check_content is None else check_content.get_data())!=content_before:
            raise ValueError("page content stream changed")
        if image_key not in list(p.images.keys()):
            raise ValueError("image key disappeared")
        out_image=p.images[image_key]
        if out_image.image is None or out_image.image.size!=old_size:
            raise ValueError("roundtrip image dimensions changed")
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status":"FAIL_CLOSED","reason":"PDF_IMAGE_ROUNDTRIP_FAILED","error":type(exc).__name__,"detail":str(exc)}

    return {
        "status":"PASS",
        "output_path":str(dst),
        "page_index":page_index,
        "image_key":image_key,
        "pixel_dimensions":list(old_size),
        "image_mode":old_mode,
        "page_content_stream_preserved":True,
        "scope":"EXACT_DECLARED_PDF_PAGE_IMAGE_XOBJECT_REPLACEMENT_WITH_IDENTICAL_PIXEL_GEOMETRY_AND_MODE",
        "visual_layout_authority":False,
        "semantic_authority":False,
        "terminal_authority":False,
    }
