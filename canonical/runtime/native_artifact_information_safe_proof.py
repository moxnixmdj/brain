"""Independent bounded cross-format proof for NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001."""
from __future__ import annotations
import hashlib,io,random,re,zipfile
import xml.etree.ElementTree as ET
from html import escape
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_NATIVE_ARTIFACT_INFORMATION_SAFE_PROOF_V1"
FORMATS=("docx","xlsx","pptx","pdf")


def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def _zip_bytes(entries:Mapping[str,bytes])->bytes:
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as z:
        for name in sorted(entries):
            info=zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,entries[name])
    return out.getvalue()


def _ooxml_case(fmt:str,old:str,tag:str)->tuple[bytes,str]:
    if fmt=="docx":
        part="word/document.xml"
        entries={
          "[Content_Types].xml":b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
          "_rels/.rels":b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
          part:(f'<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>{escape(old)}</w:t></w:r></w:p></w:body></w:document>').encode(),
          "word/styles.xml":(f'<w:styles xmlns:w="urn:w"><w:style w:styleId="{tag}"/></w:styles>').encode(),
          "word/_rels/document.xml.rels":b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="media/image.bin"/></Relationships>',
          "word/media/image.bin":("MEDIA-"+tag).encode(),
        }
    elif fmt=="xlsx":
        part="xl/sharedStrings.xml"
        entries={
          "[Content_Types].xml":b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
          "_rels/.rels":b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
          "xl/workbook.xml":(f'<workbook xmlns="urn:x"><sheets><sheet name="{tag}" sheetId="1"/></sheets></workbook>').encode(),
          part:(f'<sst xmlns="urn:x"><si><t>{escape(old)}</t></si></sst>').encode(),
          "xl/styles.xml":b'<styleSheet xmlns="urn:x"><fonts count="1"/></styleSheet>',
          "xl/media/image.bin":("MEDIA-"+tag).encode(),
        }
    else:
        part="ppt/slides/slide1.xml"
        entries={
          "[Content_Types].xml":b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
          "_rels/.rels":b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
          "ppt/presentation.xml":(f'<p:presentation xmlns:p="urn:p"><p:sldIdLst data-tag="{tag}"/></p:presentation>').encode(),
          part:(f'<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><a:t>{escape(old)}</a:t></p:sld>').encode(),
          "ppt/theme/theme1.xml":b'<a:theme xmlns:a="urn:a" name="Theme"/>',
          "ppt/media/image.bin":("MEDIA-"+tag).encode(),
        }
    return _zip_bytes(entries),part


def _build_pdf(old:str,tag:str)->bytes:
    stream=f"BT /F1 12 Tf 72 720 Td ({old}) Tj ET".encode("latin1")
    objects={
      1:b"<< /Type /Catalog /Pages 2 0 R >>",
      2:b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
      3:b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
      4:b"<< /Length "+str(len(stream)).encode()+b" >>\nstream\n"+stream+b"\nendstream",
      5:b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
      6:(f"<< /Producer (BrainFixture) /Tag ({tag}) >>").encode("latin1"),
    }
    buf=io.BytesIO();buf.write(b"%PDF-1.4\n");offs={}
    for oid in sorted(objects):
        offs[oid]=buf.tell();buf.write(f"{oid} 0 obj\n".encode());buf.write(objects[oid]);buf.write(b"\nendobj\n")
    xref=buf.tell();size=7
    buf.write(f"xref\n0 {size}\n".encode());buf.write(b"0000000000 65535 f \n")
    for oid in range(1,size):buf.write(f"{offs[oid]:010d} 00000 n \n".encode())
    buf.write(f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return buf.getvalue()


def _pdf_objects(data:bytes)->dict[int,bytes]:
    text=data.decode("latin1")
    return {int(m.group(1)):m.group(2).encode("latin1") for m in re.finditer(r"(?ms)^(\d+) 0 obj\n(.*?)\nendobj\n",text)}


def _pdf_xref_valid(data:bytes)->bool:
    try:
        text=data.decode("latin1")
        sx=int(re.search(r"startxref\n(\d+)\n%%EOF",text).group(1))
        if data[sx:sx+4]!=b"xref":return False
        lines=data[sx:].splitlines()
        header=lines[1].split(); size=int(header[1])
        for oid in range(1,size):
            off=int(lines[2+oid].split()[0])
            if not data[off:].startswith(f"{oid} 0 obj\n".encode()):return False
        return True
    except Exception:return False


def generate_case(seed:int,ordinal:int)->dict[str,Any]:
    r=random.Random((seed<<11)^ordinal^0xA471)
    fmt=FORMATS[ordinal%4]
    old="OLD"+str(r.randrange(10000,99999))
    new="NEWVALUE"+str(r.randrange(100000,999999))
    tag=str(r.randrange(100000,999999))
    if fmt=="pdf":
        source=_build_pdf(old,tag); target_part=None; target_object=4
        oracle={"objects":{k:_sha(v) for k,v in _pdf_objects(source).items()}}
    else:
        source,target_part=_ooxml_case(fmt,old,tag);target_object=None
        with zipfile.ZipFile(io.BytesIO(source),"r") as z:
            oracle={"entries":{n:_sha(z.read(n)) for n in z.namelist()}}
    return {
      "schema":SCHEMA,"case_id":f"ART-{seed}-{ordinal}","format":fmt,"source_bytes":source,
      "edit":{"target_part":target_part,"target_object":target_object,"old_text":old,"new_text":new},
      "_oracle":oracle,
    }


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in case.items() if k!="_oracle"}


def score_case(case:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    if result.get("status")!="PASS" or not isinstance(result.get("output_bytes"),bytes):
        return {"pass":False,"reason":"CANDIDATE_DID_NOT_RETURN_BYTES"}
    out=result["output_bytes"];fmt=case["format"];edit=case["edit"]
    old=edit["old_text"];new=edit["new_text"]
    if fmt in {"docx","xlsx","pptx"}:
        try:
            with zipfile.ZipFile(io.BytesIO(case["source_bytes"]),"r") as za, zipfile.ZipFile(io.BytesIO(out),"r") as zb:
                if set(za.namelist())!=set(zb.namelist()):return {"pass":False,"reason":"ENTRY_SET_CHANGED"}
                target=edit["target_part"]
                for name in za.namelist():
                    before=za.read(name);after=zb.read(name)
                    if name==target:
                        expected=before.replace(escape(old).encode(),escape(new).encode(),1)
                        if after!=expected:return {"pass":False,"reason":"TARGET_PART_UNINTENDED_MUTATION"}
                    elif after!=before:return {"pass":False,"reason":"UNRELATED_PART_MUTATED:"+name}
                    if name.endswith(".xml"):
                        ET.fromstring(after)
                if new.encode() not in zb.read(target) or old.encode() in zb.read(target):
                    return {"pass":False,"reason":"REQUESTED_EDIT_MISSING"}
        except Exception as exc:return {"pass":False,"reason":"PACKAGE_INVALID:"+type(exc).__name__}
        return {"pass":True,"reason":"PASS"}
    if fmt=="pdf":
        if not _pdf_xref_valid(out):return {"pass":False,"reason":"PDF_XREF_INVALID"}
        before=_pdf_objects(case["source_bytes"]);after=_pdf_objects(out)
        if set(before)!=set(after):return {"pass":False,"reason":"PDF_OBJECT_SET_CHANGED"}
        for oid in before:
            if oid!=4 and before[oid]!=after[oid]:return {"pass":False,"reason":"PDF_UNRELATED_OBJECT_MUTATED"}
        expected=before[4].replace(("("+old+")").encode(),("("+new+")").encode(),1)
        m=re.search(rb"(?s)stream\n(.*?)\nendstream",expected)
        expected=re.sub(rb"/Length\s+\d+",f"/Length {len(m.group(1))}".encode(),expected,count=1)
        if after[4]!=expected:return {"pass":False,"reason":"PDF_TARGET_UNINTENDED_MUTATION"}
        return {"pass":True,"reason":"PASS"}
    return {"pass":False,"reason":"FORMAT_UNKNOWN"}


def run_batch(seed:int,count:int,candidate_fn)->dict[str,Any]:
    rows=[]
    for ordinal in range(count):
        case=generate_case(seed,ordinal)
        try: verdict=score_case(case,candidate_fn(public_task(case)))
        except Exception as exc:verdict={"pass":False,"reason":"EXCEPTION:"+type(exc).__name__+":"+str(exc)}
        rows.append({"case_id":case["case_id"],"format":case["format"],**verdict})
    passed=sum(int(x["pass"]) for x in rows)
    return {"schema":"PROJECT_BRAIN_NATIVE_ARTIFACT_INFORMATION_SAFE_PREFLIGHT_RESULT_V1","case_count":count,"passed":passed,"failed":count-passed,"all_pass":passed==count,"failures":[x for x in rows if not x["pass"]],"terminal_authority":False}
