"""Brain deterministic native artifact edit-preservation engine.

Supports bounded explicit text edits inside DOCX/XLSX/PPTX OOXML packages and PDF
content streams. It receives source bytes plus an explicit target specification; it
never receives target bytes or hidden structural hashes.
"""
from __future__ import annotations
import io,re,zipfile
from html import escape
from typing import Any,Mapping


def _edit_zip(source:bytes,target_part:str,old_text:str,new_text:str)->bytes:
    src=io.BytesIO(source)
    out=io.BytesIO()
    old_xml=escape(old_text)
    new_xml=escape(new_text)
    with zipfile.ZipFile(src,"r") as zin, zipfile.ZipFile(out,"w") as zout:
        names=zin.namelist()
        if target_part not in names:
            raise ValueError("TARGET_PART_MISSING")
        for info in zin.infolist():
            data=zin.read(info.filename)
            if info.filename==target_part:
                text=data.decode("utf-8")
                if text.count(old_xml)!=1:
                    raise ValueError("OLD_TEXT_NOT_UNIQUE")
                data=text.replace(old_xml,new_xml,1).encode("utf-8")
            # Preserve per-entry metadata where the ZIP format permits it.
            clone=zipfile.ZipInfo(info.filename,date_time=info.date_time)
            clone.compress_type=info.compress_type
            clone.comment=info.comment
            clone.extra=info.extra
            clone.internal_attr=info.internal_attr
            clone.external_attr=info.external_attr
            clone.create_system=info.create_system
            clone.flag_bits=info.flag_bits
            zout.writestr(clone,data)
    return out.getvalue()


def _parse_pdf_objects(data:bytes)->dict[int,bytes]:
    text=data.decode("latin1")
    rows={}
    for m in re.finditer(r"(?ms)^(\d+) 0 obj\n(.*?)\nendobj\n",text):
        rows[int(m.group(1))]=m.group(2).encode("latin1")
    if not rows:
        raise ValueError("PDF_OBJECTS_MISSING")
    return rows


def _rebuild_pdf(objects:Mapping[int,bytes])->bytes:
    buf=io.BytesIO(); buf.write(b"%PDF-1.4\n")
    offsets={0:0}
    for oid in sorted(objects):
        offsets[oid]=buf.tell()
        buf.write(f"{oid} 0 obj\n".encode("ascii"))
        buf.write(objects[oid]); buf.write(b"\nendobj\n")
    xref=buf.tell()
    size=max(objects)+1
    buf.write(f"xref\n0 {size}\n".encode("ascii"))
    buf.write(b"0000000000 65535 f \n")
    for oid in range(1,size):
        off=offsets.get(oid,0)
        flag=b"n" if oid in offsets else b"f"
        buf.write(f"{off:010d} 00000 ".encode("ascii")+flag+b" \n")
    buf.write(f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return buf.getvalue()


def _edit_pdf(source:bytes,target_object:int,old_text:str,new_text:str)->bytes:
    objects=_parse_pdf_objects(source)
    if target_object not in objects:
        raise ValueError("TARGET_OBJECT_MISSING")
    body=objects[target_object]
    old=("("+old_text+")").encode("latin1")
    new=("("+new_text+")").encode("latin1")
    if body.count(old)!=1:
        raise ValueError("OLD_TEXT_NOT_UNIQUE")
    body=body.replace(old,new,1)
    m=re.search(rb"(?s)stream\n(.*?)\nendstream",body)
    if not m:
        raise ValueError("TARGET_STREAM_MISSING")
    stream=m.group(1)
    body=re.sub(rb"/Length\s+\d+",f"/Length {len(stream)}".encode("ascii"),body,count=1)
    objects=dict(objects); objects[target_object]=body
    return _rebuild_pdf(objects)


def apply_edit(public:Mapping[str,Any])->dict[str,Any]:
    fmt=str(public.get("format") or "").lower()
    source=public.get("source_bytes")
    edit=public.get("edit")
    if not isinstance(source,bytes) or not isinstance(edit,Mapping):
        return {"status":"FAIL_CLOSED","reason":"INPUT_INVALID","terminal_authority":False}
    old=str(edit.get("old_text") or ""); new=str(edit.get("new_text") or "")
    if not old or not new or old==new:
        return {"status":"FAIL_CLOSED","reason":"EDIT_INVALID","terminal_authority":False}
    try:
        if fmt in {"docx","xlsx","pptx"}:
            out=_edit_zip(source,str(edit.get("target_part") or ""),old,new)
        elif fmt=="pdf":
            out=_edit_pdf(source,int(edit.get("target_object")),old,new)
        else:
            return {"status":"FAIL_CLOSED","reason":"FORMAT_UNSUPPORTED","terminal_authority":False}
    except Exception as exc:
        return {"status":"FAIL_CLOSED","reason":type(exc).__name__+":"+str(exc),"terminal_authority":False}
    return {"status":"PASS","output_bytes":out,"format":fmt,"terminal_authority":False}
