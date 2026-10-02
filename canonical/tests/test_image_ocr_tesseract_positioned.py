from __future__ import annotations

import unittest

from canonical.runtime.bound_capabilities.image_ocr_tesseract_positioned import (
    parse_tsv_positioned,
)


HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


def tsv(*rows: str) -> str:
    return HEADER + "\n".join(rows) + "\n"


class PositionedOCRBridgeTests(unittest.TestCase):
    def test_deterministic_line_grouping_and_exclusive_box(self):
        raw = tsv(
            "1\t1\t0\t0\t0\t0\t0\t0\t200\t100\t-1\t",
            "5\t1\t1\t1\t1\t2\t30\t10\t20\t10\t91.0\tmm",
            "5\t1\t1\t1\t1\t1\t10\t10\t15\t10\t92.0\t25",
            "5\t1\t1\t1\t2\t1\t15\t40\t30\t12\t88.0\tDEPTH",
        )
        out = parse_tsv_positioned(raw)
        self.assertEqual(out["word_count"], 3)
        self.assertEqual(out["line_count"], 2)
        self.assertEqual(out["text_items"][0]["text"], "25 mm")
        self.assertEqual(
            out["text_items"][0]["box"],
            {"x0": 10, "y0": 10, "x1_exclusive": 50, "y1_exclusive": 20},
        )
        self.assertEqual(out["text_items"][1]["text"], "DEPTH")
        self.assertFalse(out["terminal_semantic_authority"])

    def test_out_of_bounds_box_fails_closed(self):
        raw = tsv(
            "1\t1\t0\t0\t0\t0\t0\t0\t100\t50\t-1\t",
            "5\t1\t1\t1\t1\t1\t90\t10\t20\t10\t90\tBAD",
        )
        with self.assertRaisesRegex(RuntimeError, "TSV_BOX_OUT_OF_BOUNDS"):
            parse_tsv_positioned(raw)

    def test_missing_page_row_fails_closed(self):
        raw = tsv(
            "5\t1\t1\t1\t1\t1\t10\t10\t20\t10\t90\tTEXT",
        )
        with self.assertRaisesRegex(RuntimeError, "TSV_PAGE_COUNT_INVALID"):
            parse_tsv_positioned(raw)

    def test_noninteger_coordinate_fails_closed(self):
        raw = tsv(
            "1\t1\t0\t0\t0\t0\t0\t0\t100\t50\t-1\t",
            "5\t1\t1\t1\t1\t1\t1.5\t10\t20\t10\t90\tTEXT",
        )
        with self.assertRaisesRegex(RuntimeError, "TSV_INTEGER_INVALID:left"):
            parse_tsv_positioned(raw)

    def test_nonfinite_confidence_fails_closed(self):
        raw = tsv(
            "1\t1\t0\t0\t0\t0\t0\t0\t100\t50\t-1\t",
            "5\t1\t1\t1\t1\t1\t10\t10\t20\t10\tnan\tTEXT",
        )
        with self.assertRaisesRegex(RuntimeError, "TSV_CONFIDENCE_NONFINITE"):
            parse_tsv_positioned(raw)

    def test_empty_text_is_ignored_without_fabrication(self):
        raw = tsv(
            "1\t1\t0\t0\t0\t0\t0\t0\t100\t50\t-1\t",
            "5\t1\t1\t1\t1\t1\t10\t10\t20\t10\t90\t   ",
        )
        out = parse_tsv_positioned(raw)
        self.assertEqual(out["text_items"], [])
        self.assertEqual(out["word_count"], 0)


if __name__ == "__main__":
    unittest.main()
