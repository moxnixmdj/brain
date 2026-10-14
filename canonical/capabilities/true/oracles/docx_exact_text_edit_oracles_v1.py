"""Oracles for DOCX_EXACT_TEXT_EDIT_V1.  Must not import the solver.

All oracles are derived from the OOXML package structure, using a different
code path from the solver (namespace-aware xml.dom.minidom, never the solver's parser),
and from the claim itself.  Text nodes are the namespace-qualified elements
{wordprocessingml/2006/main}t, whatever prefix the serializer chose:

  EXPECTED_OUTCOME        ANALYTIC_CLOSED_FORM  unique target -> PASS with exactly that text node replaced; otherwise FAIL_CLOSED, no output
  PACKAGE_INTEGRITY       PROPERTY              output is a valid zip, same member names in the same order, every member except
                                                word/document.xml byte-identical, document.xml well-formed, text-node count unchanged
  INVERSE_EDIT_RESTORES   METAMORPHIC           when `new` is unique in the output, replacing new->old restores the original text sequence
"""
from __future__ import annotations

import base64
import io
import zipfile
from xml.dom import minidom

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _members(blob: bytes) -> list[tuple[str, bytes]]:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return [(i.filename, z.read(i.filename)) for i in z.infolist()]


def _texts(doc_xml: bytes) -> list[str]:
    dom = minidom.parseString(doc_xml)
    out = []
    for node in dom.getElementsByTagNameNS(W_NS, "t"):
        out.append("".join(c.data for c in node.childNodes if c.nodeType in (c.TEXT_NODE, c.CDATA_SECTION_NODE)))
    return out


def _doc(blob: bytes) -> bytes:
    return dict(_members(blob))["word/document.xml"]


def oracles():
    def expected_outcome(inst, out, solve):
        src = base64.b64decode(inst["docx_b64"])
        texts = _texts(_doc(src))
        count = texts.count(inst["old"])
        if count != 1:
            ok = out.get("status") == "FAIL_CLOSED" and out.get("output_docx_b64") is None and not out.get("output_file_left_behind_on_failure")
            return ok, f"occurrences={count} status={out.get('status')} reason={out.get('reason')}"
        if out.get("status") != "PASS" or not out.get("output_docx_b64"):
            return False, f"unique target but status={out.get('status')} reason={out.get('reason')}"
        got = _texts(_doc(base64.b64decode(out["output_docx_b64"])))
        idx = texts.index(inst["old"])
        expected = texts[:idx] + [inst["new"]] + texts[idx + 1:]
        return got == expected, f"text sequence {'matches' if got == expected else 'differs'} (n={len(texts)})"

    def package_integrity(inst, out, solve):
        if out.get("status") != "PASS":
            return True, "not applicable (fail-closed outcome checked by EXPECTED_OUTCOME)"
        src = base64.b64decode(inst["docx_b64"]); dst = base64.b64decode(out["output_docx_b64"])
        with zipfile.ZipFile(io.BytesIO(dst)) as z:
            if z.testzip() is not None:
                return False, "corrupt member"
        a, b = _members(src), _members(dst)
        if [n for n, _ in a] != [n for n, _ in b]:
            return False, "member names/order changed"
        for (n1, d1), (n2, d2) in zip(a, b):
            if n1 != "word/document.xml" and d1 != d2:
                return False, f"member {n1} mutated"
        try:
            minidom.parseString(dict(b)["word/document.xml"])
        except Exception as exc:  # noqa: BLE001
            return False, f"document.xml not well-formed: {type(exc).__name__}"
        if len(_texts(dict(a)["word/document.xml"])) != len(_texts(dict(b)["word/document.xml"])):
            return False, "text node count changed"
        return True, "package intact"

    def inverse_edit_restores(inst, out, solve):
        if out.get("status") != "PASS":
            return True, "not applicable"
        if inst["new"] == "":
            return True, "not applicable (the inverse edit would need an empty target, which is outside the input class)"
        dst = base64.b64decode(out["output_docx_b64"])
        if _texts(_doc(dst)).count(inst["new"]) != 1:
            return True, "not applicable (new text not unique in output)"
        back = solve({"docx_b64": out["output_docx_b64"], "old": inst["new"], "new": inst["old"]})
        if back.get("status") != "PASS":
            return False, f"inverse edit failed: {back.get('reason')}"
        orig = _texts(_doc(base64.b64decode(inst["docx_b64"])))
        restored = _texts(_doc(base64.b64decode(back["output_docx_b64"])))
        return orig == restored, "restored" if orig == restored else "text sequence not restored"

    return [
        {"id": "EXPECTED_OUTCOME", "check": expected_outcome},
        {"id": "PACKAGE_INTEGRITY", "check": package_integrity},
        {"id": "INVERSE_EDIT_RESTORES", "check": inverse_edit_restores},
    ]
