import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from canonical.runtime.pdf_native_edit_transaction import (
    replace_pdf_page_image,
    replace_unique_pdf_text_operand,
)


def make_text_pdf(path: Path, *, duplicate=False):
    w=PdfWriter()
    page=w.add_blank_page(width=200,height=200)
    font=DictionaryObject({
        NameObject("/Type"):NameObject("/Font"),
        NameObject("/Subtype"):NameObject("/Type1"),
        NameObject("/BaseFont"):NameObject("/Helvetica"),
    })
    font_ref=w._add_object(font)
    page[NameObject("/Resources")]=DictionaryObject({
        NameObject("/Font"):DictionaryObject({NameObject("/F1"):font_ref})
    })
    stream=DecodedStreamObject()
    data=b"BT /F1 12 Tf 20 100 Td (HELLO) Tj"
    if duplicate:
        data+=b" 0 -20 Td (HELLO) Tj"
    data+=b" ET"
    stream.set_data(data)
    page[NameObject("/Contents")]=w._add_object(stream)
    with path.open("wb") as f:
        w.write(f)


def make_image_pdf(path: Path):
    Image.new("RGB",(24,16),(255,0,0)).save(path,"PDF")


def png_bytes(color):
    b=BytesIO()
    Image.new("RGB",(24,16),color).save(b,"PNG")
    return b.getvalue()


class PdfNativeEditTransactionTests(unittest.TestCase):
    def test_unique_text_operand_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.pdf"; dst=Path(td)/"out.pdf"
            make_text_pdf(src)
            before=PdfReader(src).pages[0]
            out=replace_unique_pdf_text_operand(src,dst,page_index=0,old="HELLO",new="WORLD")
            self.assertEqual(out["status"],"PASS",out)
            after=PdfReader(dst).pages[0]
            self.assertIn("WORLD",after.extract_text())
            self.assertNotIn("HELLO",after.extract_text())
            self.assertEqual(tuple(float(x) for x in before.mediabox),tuple(float(x) for x in after.mediabox))
            self.assertTrue(out["operator_sequence_preserved"])

    def test_noop_text_replacement_fails_closed_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.pdf"; dst=Path(td)/"out.pdf"
            make_text_pdf(src)
            out=replace_unique_pdf_text_operand(src,dst,page_index=0,old="HELLO",new="HELLO")
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertEqual(out["reason"],"NO_OP_REPLACEMENT")
            self.assertFalse(dst.exists())

    def test_duplicate_text_operand_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.pdf"; dst=Path(td)/"out.pdf"
            make_text_pdf(src,duplicate=True)
            out=replace_unique_pdf_text_operand(src,dst,page_index=0,old="HELLO",new="WORLD")
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertEqual(out["reason"],"TEXT_OPERAND_NOT_UNIQUE")
            self.assertEqual(out["match_count"],2)
            self.assertFalse(dst.exists())

    def test_same_geometry_image_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.pdf"; dst=Path(td)/"out.pdf"
            make_image_pdf(src)
            r=PdfReader(src)
            keys=list(r.pages[0].images.keys())
            self.assertEqual(len(keys),1)
            key=keys[0]
            self.assertIsInstance(key,str)
            before_content=r.pages[0].get_contents().get_data()
            out=replace_pdf_page_image(src,dst,page_index=0,image_key=key,replacement_image=png_bytes((0,0,255)))
            self.assertEqual(out["status"],"PASS",out)
            rr=PdfReader(dst)
            self.assertEqual(rr.pages[0].get_contents().get_data(),before_content)
            img=rr.pages[0].images[key].image
            self.assertEqual(img.size,(24,16))
            self.assertTrue(out["page_content_stream_preserved"])

    def test_different_geometry_image_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"in.pdf"; dst=Path(td)/"out.pdf"
            make_image_pdf(src)
            key=list(PdfReader(src).pages[0].images.keys())[0]
            b=BytesIO(); Image.new("RGB",(25,16),(0,0,255)).save(b,"PNG")
            out=replace_pdf_page_image(src,dst,page_index=0,image_key=key,replacement_image=b.getvalue())
            self.assertEqual(out["status"],"FAIL_CLOSED",out)
            self.assertEqual(out["reason"],"IMAGE_DIMENSIONS_DIFFER")
            self.assertFalse(dst.exists())


if __name__=="__main__":
    unittest.main(verbosity=2)
