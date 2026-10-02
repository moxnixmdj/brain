import tempfile
from pathlib import Path
import unittest
import zipfile

from canonical.runtime.docx_text_edit_transaction import TextEdit, apply_text_edit_transaction

W="http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_docx(path: Path, paragraphs: list[list[str]], marker: bytes=b"KEEP"):
    ps=[]
    for runs in paragraphs:
        rs="".join(f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>' for text in runs)
        ps.append(f"<w:p>{rs}</w:p>")
    xml=(
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{W}" xmlns:xml="http://www.w3.org/XML/1998/namespace">'
        f'<w:body>{"".join(ps)}</w:body></w:document>'
    ).encode()
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("[Content_Types].xml",b"types")
        z.writestr("word/document.xml",xml)
        z.writestr("custom.bin",marker)


def texts(path: Path):
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(path,"r") as z:
        root=ET.fromstring(z.read("word/document.xml"))
    ptag=f"{{{W}}}p"; ttag=f"{{{W}}}t"
    return ["".join(n.text or "" for n in p.iter(ttag)) for p in root.iter(ptag)]


class Tests(unittest.TestCase):
    def test_atomic_multi_paragraph_transaction(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["Hello ","World"],["Value ","100"],["Untouched"]])
            out=apply_text_edit_transaction(
                src,dst,
                edits=[TextEdit("Hello World","Hi"),TextEdit("100","250")],
            )
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(out["edit_count"],2)
            self.assertEqual(out["edited_paragraph_count"],2)
            self.assertEqual(texts(dst),["Hi","Value 250","Untouched"])

    def test_multiple_nonoverlapping_edits_same_paragraph(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["alpha ","beta ","gamma"]])
            out=apply_text_edit_transaction(
                src,dst,
                edits=[TextEdit("alpha","A"),TextEdit("gamma","G")],
            )
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(texts(dst),["A beta G"])

    def test_target_can_span_runs(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["abc12","345xyz"],["tail"]])
            out=apply_text_edit_transaction(src,dst,edits=[TextEdit("12345","Q"),TextEdit("tail","end")])
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(texts(dst),["abcQxyz","end"])

    def test_ambiguity_aborts_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["same"],["same"],["unique"]])
            out=apply_text_edit_transaction(
                src,dst,
                edits=[TextEdit("unique","U"),TextEdit("same","X")],
            )
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertFalse(dst.exists())

    def test_overlapping_targets_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["abcdef"]])
            out=apply_text_edit_transaction(
                src,dst,
                edits=[TextEdit("abcd","X"),TextEdit("cdef","Y")],
            )
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertEqual(out["reason"],"EDIT_TARGETS_OVERLAP")
            self.assertFalse(dst.exists())

    def test_missing_target_aborts_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["abc"]])
            out=apply_text_edit_transaction(src,dst,edits=[TextEdit("abc","A"),TextEdit("missing","M")])
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertFalse(dst.exists())

    def test_cross_paragraph_target_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["AB"],["CD"]])
            out=apply_text_edit_transaction(src,dst,edits=[TextEdit("ABCD","X")])
            self.assertEqual(out["status"],"FAIL_CLOSED",out)

    def test_non_document_members_byte_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            marker=b"\x00\x01opaque\xff"
            make_docx(src,[["A"],["B"]],marker)
            out=apply_text_edit_transaction(src,dst,edits=[TextEdit("A","AA"),TextEdit("B","BB")])
            self.assertEqual(out["status"],"PASS",out)
            with zipfile.ZipFile(src,"r") as a, zipfile.ZipFile(dst,"r") as b:
                self.assertEqual(a.read("custom.bin"),b.read("custom.bin"))
                self.assertEqual(a.read("[Content_Types].xml"),b.read("[Content_Types].xml"))

    def test_empty_edit_set_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["A"]])
            out=apply_text_edit_transaction(src,dst,edits=[])
            self.assertEqual(out["status"],"FAIL_CLOSED",out)


if __name__=="__main__":
    unittest.main(verbosity=2)
