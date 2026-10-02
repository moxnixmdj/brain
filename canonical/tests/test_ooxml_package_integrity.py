import tempfile
import unittest
from pathlib import Path
import zipfile

from canonical.runtime.ooxml_package_integrity import validate_ooxml_package

CT = b'''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
</Types>'''
DOC = b'''<w:document xmlns:w="urn:w"><w:body/></w:document>'''
RELS = b'''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="x" Target="media/image1.png"/>
</Relationships>'''


def make_pkg(path: Path, *, rels=RELS, ct=CT, doc=DOC, include_image=True):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("word/document.xml", doc)
        z.writestr("word/_rels/document.xml.rels", rels)
        if include_image:
            z.writestr("word/media/image1.png", b"PNG")


class Tests(unittest.TestCase):
    def test_valid_package_passes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.docx"; make_pkg(p)
            out=validate_ooxml_package(p)
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(out["internal_relationships_checked"],1)

    def test_missing_internal_relationship_target_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.docx"; make_pkg(p,include_image=False)
            out=validate_ooxml_package(p)
            self.assertEqual(out["reason"],"RELATIONSHIP_TARGET_MISSING")

    def test_duplicate_relationship_id_fails(self):
        rels=RELS.replace(b"</Relationships>",b'<Relationship Id="rId1" Type="y" Target="media/image1.png"/></Relationships>')
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.docx"; make_pkg(p,rels=rels)
            out=validate_ooxml_package(p)
            self.assertEqual(out["reason"],"RELATIONSHIP_ID_MISSING_OR_DUPLICATE")

    def test_missing_content_type_coverage_fails(self):
        ct=b'''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
        <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
        <Default Extension="xml" ContentType="application/xml"/>
        </Types>'''
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.docx"; make_pkg(p,ct=ct)
            out=validate_ooxml_package(p)
            self.assertEqual(out["reason"],"CONTENT_TYPE_COVERAGE_MISSING")

    def test_malformed_xml_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.docx"; make_pkg(p,doc=b"<broken")
            out=validate_ooxml_package(p)
            self.assertEqual(out["reason"],"XML_PART_INVALID")

    def test_external_relationship_is_allowed(self):
        rels=b'''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
        <Relationship Id="rId1" Type="x" Target="https://example.com" TargetMode="External"/>
        </Relationships>'''
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.docx"; make_pkg(p,rels=rels,include_image=False)
            out=validate_ooxml_package(p)
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(out["external_relationships_seen"],1)

    def test_relationship_path_traversal_fails(self):
        rels=b'''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
        <Relationship Id="rId1" Type="x" Target="../../../evil.xml"/>
        </Relationships>'''
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.docx"; make_pkg(p,rels=rels)
            out=validate_ooxml_package(p)
            self.assertEqual(out["reason"],"RELATIONSHIP_TARGET_INVALID")


if __name__=="__main__":
    unittest.main(verbosity=2)
