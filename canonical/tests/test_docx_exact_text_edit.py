import tempfile, zipfile
from pathlib import Path
import unittest

from canonical.runtime.docx_exact_text_edit import replace_unique_docx_text

DOC="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p></w:body></w:document>"""

class DocxExactTextEditTests(unittest.TestCase):
    def _make(self, root:Path, text=DOC):
        p=root/"in.docx"
        with zipfile.ZipFile(p,"w") as z:
            z.writestr("[Content_Types].xml","types")
            z.writestr("_rels/.rels","rels")
            z.writestr("word/document.xml",text)
            z.writestr("word/styles.xml","styles")
            z.writestr("word/media/image1.bin",b"\x00\x01binary")
        return p

    def test_unique_edit_preserves_other_members(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=self._make(root); dst=root/"out.docx"
            out=replace_unique_docx_text(src,dst,old="Hello",new="World")
            self.assertEqual(out["status"],"PASS")
            self.assertEqual(out["changed_members"],["word/document.xml"])
            with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst) as b:
                for name in a.namelist():
                    if name!="word/document.xml":
                        self.assertEqual(a.read(name),b.read(name))

    def test_missing_target_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=self._make(root)
            out=replace_unique_docx_text(src,root/"out.docx",old="Missing",new="X")
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertEqual(out["reason"],"TARGET_TEXT_NOT_UNIQUE")

    def test_duplicate_target_fails_closed(self):
        duplicate=DOC.replace("</w:body>","<w:p><w:r><w:t>Hello</w:t></w:r></w:p></w:body>")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=self._make(root,duplicate)
            out=replace_unique_docx_text(src,root/"out.docx",old="Hello",new="X")
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertEqual(out["match_count"],2)

    def test_non_docx_zip_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"in.docx"
            with zipfile.ZipFile(src,"w") as z: z.writestr("x","y")
            out=replace_unique_docx_text(src,root/"out.docx",old="a",new="b")
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertEqual(out["reason"],"DOCX_DOCUMENT_PART_MISSING")

if __name__=="__main__":
    unittest.main()
