"""Fail-closed exact text replacement in a DOCX OOXML package.

Scope: one exact text-node replacement in word/document.xml while preserving every
other ZIP member byte-for-byte. This is a narrow native-structure edit mechanism,
not a claim of visual-layout preservation or general DOCX editing.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile

W_NS="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
TEXT_TAG=f"{{{W_NS}}}t"

def _sha(data: bytes)->str:
    return hashlib.sha256(data).hexdigest()

def replace_unique_docx_text(
    input_path: str|Path,
    output_path: str|Path,
    *,
    old: str,
    new: str,
)->dict:
    src=Path(input_path); dst=Path(output_path)
    if not old or not isinstance(old,str) or not isinstance(new,str):
        return {"status":"FAIL_CLOSED","reason":"INVALID_TEXT_ARGUMENT"}
    if not src.is_file():
        return {"status":"FAIL_CLOSED","reason":"INPUT_MISSING"}
    try:
        with zipfile.ZipFile(src,"r") as zin:
            infos=zin.infolist()
            names=[i.filename for i in infos]
            if "word/document.xml" not in names:
                return {"status":"FAIL_CLOSED","reason":"DOCX_DOCUMENT_PART_MISSING"}
            original={i.filename:zin.read(i.filename) for i in infos}
    except Exception as exc:
        return {"status":"FAIL_CLOSED","reason":"INVALID_ZIP_PACKAGE","error":type(exc).__name__}

    try:
        root=ET.fromstring(original["word/document.xml"])
    except Exception as exc:
        return {"status":"FAIL_CLOSED","reason":"DOCUMENT_XML_INVALID","error":type(exc).__name__}

    matches=[node for node in root.iter(TEXT_TAG) if node.text==old]
    if len(matches)!=1:
        return {
            "status":"FAIL_CLOSED",
            "reason":"TARGET_TEXT_NOT_UNIQUE",
            "match_count":len(matches),
        }
    matches[0].text=new
    edited_xml=ET.tostring(root,encoding="utf-8",xml_declaration=True)

    dst.parent.mkdir(parents=True,exist_ok=True)
    try:
        with zipfile.ZipFile(src,"r") as zin, zipfile.ZipFile(dst,"w") as zout:
            for info in zin.infolist():
                data=edited_xml if info.filename=="word/document.xml" else zin.read(info.filename)
                zout.writestr(info,data)
    except Exception as exc:
        if dst.exists():
            dst.unlink()
        return {"status":"FAIL_CLOSED","reason":"WRITE_FAILED","error":type(exc).__name__}

    with zipfile.ZipFile(dst,"r") as z:
        after={i.filename:z.read(i.filename) for i in z.infolist()}
    if set(after)!=set(original):
        dst.unlink(missing_ok=True)
        return {"status":"FAIL_CLOSED","reason":"PACKAGE_MEMBER_SET_CHANGED"}

    changed=[]
    for name in sorted(original):
        if _sha(original[name])!=_sha(after[name]):
            changed.append(name)
    if changed!=["word/document.xml"]:
        dst.unlink(missing_ok=True)
        return {"status":"FAIL_CLOSED","reason":"UNRELATED_PACKAGE_MEMBER_MUTATED","changed":changed}

    try:
        check=ET.fromstring(after["word/document.xml"])
        # An emptied text node serialises as <w:t/> and re-parses with text None:
        # compare against "" so that replacement by the empty string is recognised
        # (defect found by fresh-instance measurement, 2026-10-14).
        old_count=sum(1 for n in check.iter(TEXT_TAG) if (n.text or "")==old)
        new_count=sum(1 for n in check.iter(TEXT_TAG) if (n.text or "")==new)
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status":"FAIL_CLOSED","reason":"ROUNDTRIP_XML_INVALID","error":type(exc).__name__}
    if old_count!=0 or new_count<1:
        dst.unlink(missing_ok=True)
        return {"status":"FAIL_CLOSED","reason":"ROUNDTRIP_CONTENT_MISMATCH"}

    return {
        "status":"PASS",
        "output_path":str(dst),
        "changed_members":changed,
        "preserved_member_count":len(original)-1,
        "scope":"UNIQUE_EXACT_WORD_TEXT_NODE_REPLACEMENT_ONLY",
        "visual_layout_authority":False,
        "terminal_authority":False,
    }


# ---------------------------------------------------------------------------
# True-capability entry point (canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md).
# Pure adapter: dict instance -> dict output.  No logic beyond the function above.
# ---------------------------------------------------------------------------

def solve_instance(instance: dict) -> dict:
    """instance = {"docx_b64": <base64 of a .docx package>, "old": str, "new": str}

    Returns {"status", "reason"?, "changed_members"?, "output_docx_b64"?}.
    """
    import base64
    with tempfile.TemporaryDirectory() as td:
        src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
        src.write_bytes(base64.b64decode(instance["docx_b64"]))
        res=replace_unique_docx_text(src,dst,old=instance["old"],new=instance["new"])
        out={k:v for k,v in res.items() if k!="output_path"}
        out["output_docx_b64"]=base64.b64encode(dst.read_bytes()).decode("ascii") if (res.get("status")=="PASS" and dst.exists()) else None
        out["output_file_left_behind_on_failure"]=bool(res.get("status")!="PASS" and dst.exists())
        return out
