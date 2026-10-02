import tempfile
from pathlib import Path
import unittest
import zipfile
import xml.etree.ElementTree as ET

from canonical.runtime.docx_story_part_replace import replace_unique_story_part_span

W="http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _story_xml(root_tag: str, paragraphs: list[list[str]]) -> bytes:
    ps=[]
    for runs in paragraphs:
        rs="".join(
            f'<w:r><w:rPr><w:i/></w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>'
            for text in runs
        )
        ps.append(f"<w:p>{rs}</w:p>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:{root_tag} xmlns:w="{W}" xmlns:xml="http://www.w3.org/XML/1998/namespace">'
        f'{"".join(ps)}</w:{root_tag}>'
    ).encode()


def make_docx(path: Path, part_name: str, root_tag: str, paragraphs: list[list[str]]):
    document=(
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>BODY</w:t></w:r></w:p></w:body></w:document>'
    ).encode()
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("[Content_Types].xml",b"types")
        z.writestr("word/document.xml",document)
        z.writestr(part_name,_story_xml(root_tag,paragraphs))
        z.writestr("word/_rels/document.xml.rels",b"RELATIONSHIP-CANARY")
        z.writestr("custom.bin",b"OPAQUE-CANARY")


def visible_text(path: Path, part_name: str) -> list[str]:
    with zipfile.ZipFile(path,"r") as z:
        root=ET.fromstring(z.read(part_name))
    ptag=f"{{{W}}}p"; ttag=f"{{{W}}}t"
    return ["".join(n.text or "" for n in p.iter(ttag)) for p in root.iter(ptag)]


class StoryPartTests(unittest.TestCase):
    def _pass_case(self, part_name: str, root_tag: str):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,part_name,root_tag,[["Alpha ","Beta"],["Untouched"]])
            with zipfile.ZipFile(src,"r") as z:
                before={n:z.read(n) for n in z.namelist()}
            out=replace_unique_story_part_span(
                src,dst,part_name=part_name,old="Alpha Beta",new="Gamma"
            )
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(out["changed_members"],[part_name])
            self.assertEqual(visible_text(dst,part_name),["Gamma","Untouched"])
            with zipfile.ZipFile(dst,"r") as z:
                after={n:z.read(n) for n in z.namelist()}
            self.assertEqual(set(before),set(after))
            for name in before:
                if name!=part_name:
                    self.assertEqual(before[name],after[name],name)

    def test_header(self):
        self._pass_case("word/header1.xml","hdr")

    def test_footer(self):
        self._pass_case("word/footer2.xml","ftr")

    def test_footnotes(self):
        self._pass_case("word/footnotes.xml","footnotes")

    def test_endnotes(self):
        self._pass_case("word/endnotes.xml","endnotes")

    def test_comments(self):
        self._pass_case("word/comments.xml","comments")

    def test_ambiguous_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,"word/header1.xml","hdr",[["same"],["same"]])
            out=replace_unique_story_part_span(
                src,dst,part_name="word/header1.xml",old="same",new="x"
            )
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertFalse(dst.exists())

    def test_forbidden_document_part_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,"word/header1.xml","hdr",[["A"]])
            out=replace_unique_story_part_span(
                src,dst,part_name="word/document.xml",old="BODY",new="x"
            )
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertEqual(out["reason"],"STORY_PART_NOT_ALLOWED")
            self.assertFalse(dst.exists())

    def test_arbitrary_part_path_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,"word/header1.xml","hdr",[["A"]])
            out=replace_unique_story_part_span(
                src,dst,part_name="../word/header1.xml",old="A",new="x"
            )
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertEqual(out["reason"],"STORY_PART_NOT_ALLOWED")

    def test_missing_allowed_part_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,"word/header1.xml","hdr",[["A"]])
            out=replace_unique_story_part_span(
                src,dst,part_name="word/footer1.xml",old="A",new="x"
            )
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertEqual(out["reason"],"STORY_PART_MISSING")


if __name__=="__main__":
    unittest.main(verbosity=2)
