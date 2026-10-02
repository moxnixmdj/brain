import tempfile
import unittest
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

from canonical.runtime.ooxml_package_transaction import (
    AddMember,
    XmlSetAttribute,
    XmlSetText,
    apply_ooxml_transaction,
)

W="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL="http://schemas.openxmlformats.org/package/2006/relationships"
A="http://schemas.openxmlformats.org/drawingml/2006/main"

DOC=f'''<w:document xmlns:w="{W}" xmlns:r="{R}" xmlns:a="{A}">
<w:body>
 <w:p><w:fldSimple w:instr="DATE"><w:r><w:t>OLD</w:t></w:r></w:fldSimple></w:p>
 <w:p><w:ins w:id="1"><w:r><w:t>Tracked</w:t></w:r></w:ins></w:p>
 <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
 <w:p><w:r><w:drawing><a:blip r:embed="rId5"/></w:drawing></w:r></w:p>
</w:body></w:document>'''.encode()

STYLES=f'''<w:styles xmlns:w="{W}"><w:style w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>'''.encode()

RELS=f'''<Relationships xmlns="{REL}"><Relationship Id="rId5" Type="{R}/image" Target="media/image1.png"/></Relationships>'''.encode()


def make_docx(path):
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("[Content_Types].xml",b"<Types/>")
        z.writestr("word/document.xml",DOC)
        z.writestr("word/styles.xml",STYLES)
        z.writestr("word/_rels/document.xml.rels",RELS)
        z.writestr("word/media/image1.png",b"old-image")
        z.writestr("custom.bin",b"UNCHANGED")


def read(path,name):
    with zipfile.ZipFile(path) as z:
        return z.read(name)


class DocxStructuralCoverageTests(unittest.TestCase):
    def test_field_tracked_table_style_relationship_transaction(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_docx(src)
            out=apply_ooxml_transaction(src,dst,operations=[
                XmlSetAttribute("word/document.xml",(0,0,0),f"{{{W}}}instr","TIME",expected_tag=f"{{{W}}}fldSimple"),
                XmlSetText("word/document.xml",(0,1,0,0,0),"Tracked2",expected_tag=f"{{{W}}}t"),
                XmlSetText("word/document.xml",(0,2,0,0,0,0,0),"Cell2",expected_tag=f"{{{W}}}t"),
                XmlSetAttribute("word/styles.xml",(0,0),f"{{{W}}}val","Body",expected_tag=f"{{{W}}}name"),
                XmlSetAttribute("word/_rels/document.xml.rels",(0,),"Target","media/image2.png",expected_tag=f"{{{REL}}}Relationship"),
                AddMember("word/media/image2.png",b"new-image"),
            ])
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(read(dst,"custom.bin"),b"UNCHANGED")
            doc=ET.fromstring(read(dst,"word/document.xml"))
            body=doc[0]
            self.assertEqual(body[0][0].get(f"{{{W}}}instr"),"TIME")
            self.assertEqual(body[1][0][0][0].text,"Tracked2")
            self.assertEqual(body[2][0][0][0][0][0].text,"Cell2")
            styles=ET.fromstring(read(dst,"word/styles.xml"))
            self.assertEqual(styles[0][0].get(f"{{{W}}}val"),"Body")
            rels=ET.fromstring(read(dst,"word/_rels/document.xml.rels"))
            self.assertEqual(rels[0].get("Target"),"media/image2.png")
            self.assertEqual(read(dst,"word/media/image1.png"),b"old-image")
            self.assertEqual(read(dst,"word/media/image2.png"),b"new-image")

    def test_wrong_tag_precondition_aborts_whole_transaction(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_docx(src)
            out=apply_ooxml_transaction(src,dst,operations=[
                XmlSetText("word/document.xml",(0,2,0,0,0,0,0),"Cell2",expected_tag=f"{{{W}}}wrong"),
                AddMember("word/media/image2.png",b"new-image"),
            ])
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertFalse(dst.exists())


if __name__=="__main__":
    unittest.main(verbosity=2)
