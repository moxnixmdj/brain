import tempfile
import unittest
from pathlib import Path
import zipfile

from canonical.runtime.docx_relationship_image_replace import replace_image_by_relationship

PNG1 = b"\x89PNG\r\n\x1a\nOLD"
PNG2 = b"\x89PNG\r\n\x1a\nNEW"

DOC = b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
 <w:body><w:p><w:r><w:drawing><a:blip r:embed="rId5"/></w:drawing></w:r></w:p></w:body>
</w:document>'''

RELS = b'''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>'''

CT = b'''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="png" ContentType="image/png"/>
</Types>'''

def make_docx(path: Path, *, document=DOC, rels=RELS):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("word/document.xml", document)
        z.writestr("word/_rels/document.xml.rels", rels)
        z.writestr("word/media/image1.png", PNG1)
        z.writestr("word/styles.xml", b"<styles/>")

def members(path: Path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}

class Tests(unittest.TestCase):
    def test_exact_relationship_replacement_changes_only_media(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src)
            before=members(src)
            out=replace_image_by_relationship(
                src,dst,source_part="word/document.xml",
                relationship_id="rId5",replacement_image=PNG2,
            )
            self.assertEqual(out["status"],"PASS",out)
            after=members(dst)
            self.assertEqual(after["word/media/image1.png"],PNG2)
            changed=[n for n in sorted(before) if before[n] != after[n]]
            self.assertEqual(changed,["word/media/image1.png"])
            self.assertTrue(out["layout_xml_preserved_byte_identical"])
            self.assertTrue(out["relationship_xml_preserved_byte_identical"])

    def test_unreferenced_relationship_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,document=DOC.replace(b'r:embed="rId5"',b'r:embed="rId9"'))
            out=replace_image_by_relationship(
                src,dst,source_part="word/document.xml",
                relationship_id="rId5",replacement_image=PNG2,
            )
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertEqual(out["reason"],"RELATIONSHIP_ID_NOT_REFERENCED_BY_SOURCE_PART")
            self.assertFalse(dst.exists())

    def test_media_signature_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src)
            out=replace_image_by_relationship(
                src,dst,source_part="word/document.xml",
                relationship_id="rId5",replacement_image=b"not a png",
            )
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertEqual(out["reason"],"REPLACEMENT_IMAGE_SIGNATURE_MISMATCH")
            self.assertFalse(dst.exists())

    def test_non_image_relationship_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            rels=RELS.replace(
                b"/relationships/image",
                b"/relationships/hyperlink",
            )
            make_docx(src,rels=rels)
            out=replace_image_by_relationship(
                src,dst,source_part="word/document.xml",
                relationship_id="rId5",replacement_image=PNG2,
            )
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertEqual(out["reason"],"RELATIONSHIP_NOT_IMAGE")
            self.assertFalse(dst.exists())

if __name__=="__main__":
    unittest.main(verbosity=2)
