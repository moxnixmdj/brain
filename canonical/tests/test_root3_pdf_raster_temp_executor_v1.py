from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import root3_pdf_raster_temp_executor_v1 as ex
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED


def _minimal_pdf_bytes() -> bytes:
    parts = []
    def add(s: bytes):
        parts.append(s)
    add(b"%PDF-1.4\n")
    offsets = [0]
    body = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Contents 4 0 R /Resources << >> >>\nendobj\n",
        b"4 0 obj\n<< /Length 0 >>\nstream\n\nendstream\nendobj\n",
    ]
    raw = b"".join(parts)
    objs = []
    for i, obj in enumerate(body, start=1):
        offsets.append(len(raw) + sum(len(x) for x in objs))
        objs.append(obj)
    raw += b"".join(objs)
    xref = len(raw)
    raw += b"xref\n0 5\n0000000000 65535 f \n"
    for off in offsets[1:]:
        raw += f"{off:010d} 00000 n \n".encode()
    raw += b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
    return raw


def _context(root: pathlib.Path):
    td = tempfile.TemporaryDirectory(prefix="project-brain-ocr-")
    out_dir = pathlib.Path(td.name)
    src = root / "in.pdf"
    src.write_bytes(_minimal_pdf_bytes())
    ctx = {
        "effect_class": "TEMPORARY_FILESYSTEM_TRANSFORM",
        "api": "subprocess.run",
        "args": ([
            "pdftoppm", "-f", "1", "-l", "3", "-r", "300", "-png",
            str(src), str(out_dir / "page"),
        ],),
        "kwargs": {"text": True, "capture_output": True, "timeout": 180},
        "callsite": {
            "module_path": "canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",
            "lineno": 29,
            "process_api": "subprocess.run",
        },
    }
    return td, out_dir, ctx


class PdfRasterTempExecutorTests(unittest.TestCase):
    def test_temp_class_is_exactly_one_current_site(self):
        current = {k for k, v in EXPECTED.items() if v == "TEMPORARY_FILESYSTEM_TRANSFORM"}
        self.assertEqual(current, {ex.SUPPORTED_SITE})

    def test_prepare_maps_exact_input_and_ephemeral_output(self):
        with tempfile.TemporaryDirectory() as root_s:
            root = pathlib.Path(root_s)
            td, out_dir, ctx = _context(root)
            try:
                with patch.object(ex.shutil, "which", side_effect=lambda n: "/usr/bin/pdftoppm" if n == "pdftoppm" else "/usr/bin/" + n):
                    prepared = ex._prepare(ctx)
                self.assertEqual(prepared["input_dir"], root)
                self.assertEqual(prepared["output_dir"], out_dir.resolve())
                self.assertEqual(prepared["inner_argv"][-2], "/input/in.pdf")
                self.assertEqual(prepared["inner_argv"][-1], "/output/page")
            finally:
                td.cleanup()

    def test_wrong_callsite_denies(self):
        with tempfile.TemporaryDirectory() as root_s:
            root = pathlib.Path(root_s)
            td, _, ctx = _context(root)
            try:
                ctx["callsite"]["lineno"] = 30
                with self.assertRaisesRegex(ex.PdfRasterTempDenied, "CALLSITE_NOT_SUPPORTED"):
                    ex._prepare(ctx)
            finally:
                td.cleanup()

    def test_nonempty_output_dir_denies_before_spawn(self):
        with tempfile.TemporaryDirectory() as root_s:
            root = pathlib.Path(root_s)
            td, out_dir, ctx = _context(root)
            try:
                (out_dir / "preexisting.txt").write_text("x")
                with patch.object(ex.shutil, "which", return_value="/usr/bin/pdftoppm"):
                    with self.assertRaisesRegex(ex.PdfRasterTempDenied, "MUST_BE_EMPTY"):
                        ex._prepare(ctx)
            finally:
                td.cleanup()

    def test_output_outside_project_temp_prefix_denies(self):
        with tempfile.TemporaryDirectory() as root_s, tempfile.TemporaryDirectory(prefix="other-") as other:
            root = pathlib.Path(root_s)
            td, _, ctx = _context(root)
            try:
                ctx["args"] = ([
                    "pdftoppm", "-f", "1", "-l", "3", "-r", "300", "-png",
                    str(root / "in.pdf"), str(pathlib.Path(other) / "page"),
                ],)
                with patch.object(ex.shutil, "which", return_value="/usr/bin/pdftoppm"):
                    with self.assertRaisesRegex(ex.PdfRasterTempDenied, "OUTPUT_DIR_PREFIX_INVALID"):
                        ex._prepare(ctx)
            finally:
                td.cleanup()

    def test_shell_and_custom_env_deny(self):
        with tempfile.TemporaryDirectory() as root_s:
            root = pathlib.Path(root_s)
            td, _, ctx = _context(root)
            try:
                with patch.object(ex.shutil, "which", return_value="/usr/bin/pdftoppm"):
                    ctx["kwargs"]["shell"] = True
                    with self.assertRaisesRegex(ex.PdfRasterTempDenied, "SHELL_FORBIDDEN"):
                        ex._prepare(ctx)
                    ctx["kwargs"]["shell"] = False
                    ctx["kwargs"]["env"] = {"X": "1"}
                    with self.assertRaisesRegex(ex.PdfRasterTempDenied, "CUSTOM_ENV_FORBIDDEN"):
                        ex._prepare(ctx)
            finally:
                td.cleanup()

    def test_output_validator_accepts_only_png_files(self):
        with tempfile.TemporaryDirectory(prefix="project-brain-ocr-") as td:
            root = pathlib.Path(td)
            (root / "page-1.png").write_bytes(ex.PNG_MAGIC + b"x")
            self.assertEqual(len(ex._validate_outputs(root)), 1)
            (root / "oops.txt").write_text("x")
            with self.assertRaisesRegex(ex.PdfRasterTempDenied, "UNEXPECTED_OUTPUT_NAME"):
                ex._validate_outputs(root)

    def test_mocked_executor_preserves_completedprocess_semantics(self):
        with tempfile.TemporaryDirectory() as root_s:
            root = pathlib.Path(root_s)
            td, out_dir, ctx = _context(root)
            try:
                def fake_run(prepared, popen_impl):
                    (out_dir / "page-1.png").write_bytes(ex.PNG_MAGIC + b"x")
                    return {
                        "timed_out": False,
                        "returncode": 0,
                        "stdout_b64": "",
                        "stderr_b64": "",
                    }
                with patch.object(ex.shutil, "which", side_effect=lambda n: "/usr/bin/pdftoppm" if n == "pdftoppm" else "/usr/bin/" + n), \
                     patch.object(ex, "_run_confined", side_effect=fake_run):
                    fn = ex.make_executor(popen_impl=lambda *a, **kw: None)
                    cp = fn(ctx)
                self.assertIsInstance(cp, subprocess.CompletedProcess)
                self.assertEqual(cp.returncode, 0)
                self.assertTrue((out_dir / "page-1.png").is_file())
            finally:
                td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
