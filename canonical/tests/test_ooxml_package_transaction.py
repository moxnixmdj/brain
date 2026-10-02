import hashlib
import tempfile
from pathlib import Path
import unittest
import zipfile
import xml.etree.ElementTree as ET
from canonical.runtime.ooxml_package_transaction import AddMember, DeleteMember, ReplaceMember, XmlReplaceSubtree, XmlSetAttribute, XmlSetText, apply_ooxml_transaction

def make_package(path):
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("[Content_Types].xml",b"<types/>")
        z.writestr("word/document.xml",b"<doc><p id='a'><t>Hello</t></p><p id='b'><t>Keep</t></p></doc>")
        z.writestr("word/_rels/document.xml.rels",b"<rels><rel id='r1'/></rels>")
        z.writestr("word/media/image1.bin",b"IMAGE")
        z.writestr("custom.bin",b"UNCHANGED")

def read_member(path,name):
    with zipfile.ZipFile(path,"r") as z:
        return z.read(name)

class Tests(unittest.TestCase):
    def test_multi_part_transaction(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_package(src)
            sha=hashlib.sha256(b"IMAGE").hexdigest()
            out=apply_ooxml_transaction(src,dst,operations=[
                XmlSetText("word/document.xml",(0,0),"Hi",expected_tag="t"),
                XmlSetAttribute("word/document.xml",(0,),"class","lead",expected_tag="p"),
                XmlSetAttribute("word/_rels/document.xml.rels",(0,),"target","media/image2.bin",expected_tag="rel"),
                ReplaceMember("word/media/image1.bin",b"NEWIMAGE",sha),
                AddMember("word/media/image2.bin",b"SECOND"),
            ])
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(read_member(dst,"custom.bin"),b"UNCHANGED")
            self.assertEqual(read_member(dst,"word/media/image1.bin"),b"NEWIMAGE")
            root=ET.fromstring(read_member(dst,"word/document.xml"))
            self.assertEqual(root[0][0].text,"Hi")
            self.assertEqual(root[0].attrib["class"],"lead")

    def test_subtree_replace_preserves_sibling(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_package(src)
            out=apply_ooxml_transaction(src,dst,operations=[XmlReplaceSubtree("word/document.xml",(0,),"<p id='new'><t>Replaced</t></p>",expected_tag="p")])
            self.assertEqual(out["status"],"PASS",out)
            root=ET.fromstring(read_member(dst,"word/document.xml"))
            self.assertEqual(root[0].attrib["id"],"new")
            self.assertEqual(root[1][0].text,"Keep")

    def test_delete_with_sha(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_package(src)
            sha=hashlib.sha256(b"IMAGE").hexdigest()
            out=apply_ooxml_transaction(src,dst,operations=[DeleteMember("word/media/image1.bin",sha)])
            self.assertEqual(out["status"],"PASS",out)
            with zipfile.ZipFile(dst,"r") as z:
                self.assertNotIn("word/media/image1.bin",z.namelist())

    def test_wrong_sha_aborts(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_package(src)
            out=apply_ooxml_transaction(src,dst,operations=[ReplaceMember("word/media/image1.bin",b"X","0"*64)])
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertFalse(dst.exists())

    def test_invalid_path_aborts(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_package(src)
            out=apply_ooxml_transaction(src,dst,operations=[XmlSetText("word/document.xml",(99,),"X")])
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertFalse(dst.exists())

    def test_tag_precondition(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_package(src)
            out=apply_ooxml_transaction(src,dst,operations=[XmlSetText("word/document.xml",(0,0),"X",expected_tag="wrong")])
            self.assertEqual(out["status"],"FAIL_CLOSED",out)

    def test_malformed_subtree(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_package(src)
            out=apply_ooxml_transaction(src,dst,operations=[XmlReplaceSubtree("word/document.xml",(0,),"<p>",expected_tag="p")])
            self.assertEqual(out["status"],"FAIL_CLOSED",out)

    def test_untouched_bytes_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_package(src)
            before=read_member(src,"custom.bin")
            out=apply_ooxml_transaction(src,dst,operations=[XmlSetText("word/document.xml",(0,0),"Changed")])
            self.assertEqual(out["status"],"PASS",out)
            self.assertEqual(read_member(dst,"custom.bin"),before)
            self.assertEqual(read_member(dst,"word/media/image1.bin"),b"IMAGE")

    def test_empty_ops_fail(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.docx"; dst=Path(td)/"out.docx"; make_package(src)
            self.assertEqual(apply_ooxml_transaction(src,dst,operations=[])["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main(verbosity=2)
