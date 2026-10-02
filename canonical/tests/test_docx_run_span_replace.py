import tempfile
from pathlib import Path
import unittest
import zipfile

from canonical.runtime.docx_run_span_replace import replace_unique_paragraph_span

W="http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_docx(path: Path, paragraphs: list[list[str]], marker: bytes=b"KEEP-ME"):
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


def paragraph_texts(path: Path):
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(path,"r") as z:
        root=ET.fromstring(z.read("word/document.xml"))
    ptag=f"{{{W}}}p"; ttag=f"{{{W}}}t"
    return ["".join(n.text or "" for n in p.iter(ttag)) for p in root.iter(ptag)]


class Tests(unittest.TestCase):
    def test_replaces_across_multiple_runs(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["Hello ","World"],["Untouched"]])
            out=replace_unique_paragraph_span(src,dst,old="Hello World",new="Hi")
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(out["spanned_text_node_count"],2)
            self.assertEqual(paragraph_texts(dst),["Hi","Untouched"])

    def test_preserves_prefix_and_suffix_across_runs(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["abc12","345xyz"]])
            out=replace_unique_paragraph_span(src,dst,old="12345",new="Q")
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(paragraph_texts(dst),["abcQxyz"])

    def test_single_node_occurrence(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["prefix target suffix"]])
            out=replace_unique_paragraph_span(src,dst,old="target",new="X")
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(paragraph_texts(dst),["prefix X suffix"])

    def test_ambiguous_occurrence_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["same"],["same"]])
            out=replace_unique_paragraph_span(src,dst,old="same",new="x")
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertFalse(dst.exists())

    def test_cross_paragraph_target_is_not_matched(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["AB"],["CD"]])
            out=replace_unique_paragraph_span(src,dst,old="ABCD",new="x")
            self.assertEqual(out["status"],"FAIL_CLOSED",out)

    def test_missing_target_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,[["abc"]])
            out=replace_unique_paragraph_span(src,dst,old="missing",new="x")
            self.assertEqual(out["status"],"FAIL_CLOSED",out)

    def test_non_document_members_are_byte_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            marker=b"\x00\x01opaque\xff"
            make_docx(src,[["A","B"]],marker)
            out=replace_unique_paragraph_span(src,dst,old="AB",new="Z")
            self.assertEqual(out["status"],"PASS",out)
            with zipfile.ZipFile(src,"r") as a, zipfile.ZipFile(dst,"r") as b:
                self.assertEqual(a.read("custom.bin"),b.read("custom.bin"))
                self.assertEqual(a.read("[Content_Types].xml"),b.read("[Content_Types].xml"))


if __name__=="__main__":
    unittest.main(verbosity=2)
