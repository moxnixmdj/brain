import tempfile
import unittest
from pathlib import Path
import zipfile

from canonical.runtime.docx_relationship_image_replace import replace_image_by_relationship

DOC = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
 <w:body><w:p><w:r><w:drawing><a:blip r:embed="rId5"/></w:drawing></w:r></w:p></w:body>
</w:document>"""

RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>"""

CT = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="png" ContentType="image/png"/>
</Types>"""

OLD_PNG = b"\x89PNG\r\n\x1a\nOLDPAYLOAD"
NEW_PNG = b"\x89PNG\r\n\x1a\nNEWPAYLOAD"


def make_docx(path: Path, *, referenced=True, rel_type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"):
    doc = DOC if referenced else DOC.replace('r:embed="rId5"', 'r:embed="rId999"')
    rels = RELS.replace("http://schemas.openxmlformats.org/officeDocument/2006/relationships/image", rel_type)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("word/document.xml", doc)
        z.writestr("word/_rels/document.xml.rels", rels)
        z.writestr("word/media/image1.png", OLD_PNG)
        z.writestr("word/styles.xml", "<styles/>")


class DocxRelationshipImageReplaceTests(unittest.TestCase):
    def test_replaces_only_media_part(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src)
            out=replace_image_by_relationship(src,dst,source_part="word/document.xml",relationship_id="rId5",replacement_image=NEW_PNG)
            self.assertEqual(out["status"],"PASS")
            self.assertEqual(out["changed_members"],["word/media/image1.png"])
            self.assertEqual(out["relationship_reference_count"],1)
            with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst) as b:
                for name in a.namelist():
                    if name=="word/media/image1.png":
                        self.assertEqual(b.read(name),NEW_PNG)
                    else:
                        self.assertEqual(a.read(name),b.read(name))

    def test_wrong_signature_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_docx(src)
            out=replace_image_by_relationship(src,dst,source_part="word/document.xml",relationship_id="rId5",replacement_image=b"not png")
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertEqual(out["reason"],"REPLACEMENT_IMAGE_SIGNATURE_MISMATCH")
            self.assertFalse(dst.exists())

    def test_unreferenced_relationship_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_docx(src,referenced=False)
            out=replace_image_by_relationship(src,dst,source_part="word/document.xml",relationship_id="rId5",replacement_image=NEW_PNG)
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertEqual(out["reason"],"RELATIONSHIP_ID_NOT_REFERENCED_BY_SOURCE_PART")

    def test_non_image_relationship_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"
            make_docx(src,rel_type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink")
            out=replace_image_by_relationship(src,dst,source_part="word/document.xml",relationship_id="rId5",replacement_image=NEW_PNG)
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertEqual(out["reason"],"RELATIONSHIP_NOT_IMAGE")


if __name__=="__main__":
    unittest.main()
