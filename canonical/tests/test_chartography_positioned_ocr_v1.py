from __future__ import annotations

import unittest

from canonical.runtime.chartography_positioned_ocr_v1 import PositionedOCRError, parse_tsv


HEADER="level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


class PositionedOCRTests(unittest.TestCase):
    def test_parses_coordinates_and_text(self):
        raw=HEADER+"5\t1\t2\t1\t3\t1\t10\t20\t30\t12\t96.5\t42.0\n"
        rows=parse_tsv(raw,min_confidence=50)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["text"],"42.0")
        self.assertEqual(rows[0]["cx"],25.0)
        self.assertEqual(rows[0]["cy"],26.0)
        self.assertEqual(rows[0]["line_num"],3)

    def test_confidence_filter(self):
        raw=HEADER+"5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t20\tnoise\n"
        self.assertEqual(parse_tsv(raw,min_confidence=50),[])

    def test_schema_fails_closed(self):
        with self.assertRaisesRegex(PositionedOCRError,"SCHEMA"):
            parse_tsv("text\nhello\n")


if __name__=="__main__":
    unittest.main()
