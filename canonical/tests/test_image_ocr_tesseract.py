import pathlib
import tempfile
import unittest
from unittest import mock

from canonical.runtime.bound_capabilities import image_ocr_tesseract


class ImageOCRTesseractTests(unittest.TestCase):
    def test_exact_command_shape_and_best_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            p=root/"drawing.png"
            p.write_bytes(b"fake-png")
            results=[
                mock.Mock(returncode=0,stdout="A",stderr=""),
                mock.Mock(returncode=0,stdout="A B",stderr=""),
                mock.Mock(returncode=0,stdout="",stderr=""),
                mock.Mock(returncode=0,stdout="A",stderr=""),
            ]
            with mock.patch("canonical.runtime.bound_capabilities.image_ocr_tesseract.subprocess.run",side_effect=results) as run:
                out=image_ocr_tesseract.run({"path":"drawing.png"},root)
            self.assertEqual(out["selected_psm"],"7")
            self.assertEqual(out["text"],"A B")
            self.assertEqual(run.call_args_list[0].args[0][0],"tesseract")
            self.assertEqual(run.call_args_list[0].args[0][2],"stdout")
            self.assertEqual(run.call_args_list[0].args[0][3:5],["-l","eng"])
            self.assertEqual(run.call_args_list[0].args[0][5:7],["--psm","6"])
            self.assertFalse(out["terminal_semantic_authority"])

    def test_path_escape_fails(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RuntimeError):
                image_ocr_tesseract.run({"path":"../outside.png"},td)

    def test_all_psm_failure_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); (root/"drawing.png").write_bytes(b"x")
            bad=mock.Mock(returncode=1,stdout="",stderr="failure")
            with mock.patch("canonical.runtime.bound_capabilities.image_ocr_tesseract.subprocess.run",return_value=bad):
                with self.assertRaisesRegex(RuntimeError,"TESSERACT_FAILED_ALL_PSM"):
                    image_ocr_tesseract.run({"path":"drawing.png"},root)


if __name__=="__main__":
    unittest.main()
