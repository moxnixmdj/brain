import hashlib
import pathlib
import tempfile
import unittest
from unittest import mock

from canonical.runtime.bound_capabilities import image_ocr_tesseract


PINNED_DEP={
    "status":"PINNED_DEPENDENCY_SURFACE_VERIFIED",
    "tesseract_version":"5.3.4",
    "packages":dict(image_ocr_tesseract.EXPECTED_PACKAGES),
    "eng_model_path":str(image_ocr_tesseract.EXPECTED_ENG_MODEL_PATH),
    "eng_model_sha256":image_ocr_tesseract.EXPECTED_ENG_MODEL_SHA256,
}


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
            with mock.patch.object(image_ocr_tesseract,"verify_dependency_surface",return_value=PINNED_DEP):
                with mock.patch("canonical.runtime.bound_capabilities.image_ocr_tesseract.subprocess.run",side_effect=results) as run:
                    out=image_ocr_tesseract.run({"path":"drawing.png"},root)
            self.assertEqual(out["selected_psm"],"7")
            self.assertEqual(out["text"],"A B")
            self.assertEqual(run.call_args_list[0].args[0][0],"tesseract")
            self.assertEqual(run.call_args_list[0].args[0][2],"stdout")
            self.assertEqual(run.call_args_list[0].args[0][3:5],["-l","eng"])
            self.assertEqual(run.call_args_list[0].args[0][5:7],["--psm","6"])
            self.assertEqual(out["dependency"]["eng_model_sha256"],image_ocr_tesseract.EXPECTED_ENG_MODEL_SHA256)
            self.assertFalse(out["terminal_semantic_authority"])

    def test_path_escape_fails(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RuntimeError):
                image_ocr_tesseract.run({"path":"../outside.png"},td)

    def test_language_outside_pinned_scope_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); (root/"drawing.png").write_bytes(b"x")
            with self.assertRaisesRegex(RuntimeError,"OCR_LANGUAGE_OUTSIDE_PINNED_SCOPE"):
                image_ocr_tesseract.run({"path":"drawing.png","language":"deu"},root)

    def test_all_psm_failure_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); (root/"drawing.png").write_bytes(b"x")
            bad=mock.Mock(returncode=1,stdout="",stderr="failure")
            with mock.patch.object(image_ocr_tesseract,"verify_dependency_surface",return_value=PINNED_DEP):
                with mock.patch("canonical.runtime.bound_capabilities.image_ocr_tesseract.subprocess.run",return_value=bad):
                    with self.assertRaisesRegex(RuntimeError,"TESSERACT_FAILED_ALL_PSM"):
                        image_ocr_tesseract.run({"path":"drawing.png"},root)

    def test_model_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            model=pathlib.Path(td)/"eng.traineddata"
            model.write_bytes(b"wrong")
            version=mock.Mock(returncode=0,stdout="tesseract 5.3.4\n",stderr="")
            pkg=mock.Mock(returncode=0,stdout="5.3.4-1build5",stderr="")
            eng=mock.Mock(returncode=0,stdout="1:4.1.0-2",stderr="")
            with mock.patch("canonical.runtime.bound_capabilities.image_ocr_tesseract.subprocess.run",side_effect=[version,pkg,pkg,eng]):
                with self.assertRaisesRegex(RuntimeError,"OCR_ENG_MODEL_HASH_MISMATCH"):
                    image_ocr_tesseract.verify_dependency_surface(model_path=model)


if __name__=="__main__":
    unittest.main()
