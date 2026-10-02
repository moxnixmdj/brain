from __future__ import annotations

import pathlib
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import positioned_ocr_tesseract_bridge as bridge


TSV = """level	page_num	block_num	par_num	line_num	word_num	left	top	width	height	conf	text
1	1	0	0	0	0	0	0	640	480	-1	
5	1	1	1	1	1	10	20	30	10	95.0	DIA
5	1	1	1	1	2	45	20	20	10	90.0	20
5	1	1	1	2	1	100	100	40	12	88.5	DEPTH
5	1	1	1	2	2	145	100	15	12	87.5	8
"""


class Proc:
    returncode = 0
    stdout = TSV
    stderr = ""


class PositionedOcrBridgeTests(unittest.TestCase):
    def test_parse_and_group_contract(self):
        extent, words = bridge._parse_tsv(TSV)
        self.assertEqual(extent, (640, 480))
        self.assertEqual(len(words), 4)
        lines = bridge._group_lines(words)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["text"], "DIA 20")
        self.assertEqual(
            lines[0]["box"],
            {"x0": 10, "y0": 20, "x1_exclusive": 65, "y1_exclusive": 30},
        )
        self.assertEqual(lines[1]["text"], "DEPTH 8")

    def test_malformed_header_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "OCR_TSV_HEADER_INVALID"):
            bridge._parse_tsv("foo\tbar\n1\t2\n")

    def test_out_of_bounds_box_fails_closed(self):
        bad = TSV.replace(
            "5\t1\t1\t1\t2\t2\t145\t100\t15\t12\t87.5\t8",
            "5\t1\t1\t1\t2\t2\t635\t100\t15\t12\t87.5\t8",
        )
        with self.assertRaisesRegex(RuntimeError, "OCR_TSV_WORD_BOX_OUT_OF_BOUNDS"):
            bridge._parse_tsv(bad)

    def test_negative_confidence_word_fails_closed(self):
        bad = TSV.replace("95.0\tDIA", "-1\tDIA")
        with self.assertRaisesRegex(RuntimeError, "OCR_TSV_CONFIDENCE_OUT_OF_RANGE"):
            bridge._parse_tsv(bad)

    def test_extract_uses_pinned_surface_and_emits_pipeline_items(self):
        with tempfile.TemporaryDirectory() as td:
            src = pathlib.Path(td) / "drawing.png"
            src.write_bytes(b"not-a-real-image-needed-for-mocked-tesseract")
            with patch.object(
                bridge,
                "verify_dependency_surface",
                return_value={"status": "PINNED_DEPENDENCY_SURFACE_VERIFIED"},
            ), patch.object(bridge.subprocess, "run", return_value=Proc()):
                out = bridge.extract_positioned_text(src, psm="6")
        self.assertEqual(out["status"], "EXTRACTED")
        self.assertFalse(out["terminal_semantic_authority"])
        self.assertEqual(out["word_count"], 4)
        self.assertEqual(len(out["text_items"]), 2)
        for item in out["text_items"]:
            self.assertEqual(
                set(item["box"]),
                {"x0", "y0", "x1_exclusive", "y1_exclusive"},
            )

    def test_unsupported_psm_fails_before_execution(self):
        with self.assertRaisesRegex(RuntimeError, "OCR_PSM_OUTSIDE_VERIFIED_SCOPE"):
            bridge.extract_positioned_text("/does/not/matter", psm="13")


if __name__ == "__main__":
    unittest.main(verbosity=2)
