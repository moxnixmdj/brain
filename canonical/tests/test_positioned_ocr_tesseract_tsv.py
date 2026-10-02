import unittest

from canonical.runtime.positioned_ocr_tesseract_tsv import parse_tsv

HEADER="level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"

class PositionedOCRTSVTests(unittest.TestCase):
    def test_groups_words_and_emits_exclusive_boxes(self):
        tsv=HEADER + (
            "5\t1\t1\t1\t1\t1\t10\t20\t12\t8\t95.5\tDIA\n"
            "5\t1\t1\t1\t1\t2\t24\t20\t10\t8\t90\t10\n"
            "5\t1\t1\t1\t2\t1\t5\t40\t20\t7\t88\tTHRU\n"
        )
        o=parse_tsv(tsv,image_width=100,image_height=80)
        self.assertEqual(o["status"],"PARSED")
        self.assertEqual(o["line_count"],2)
        self.assertEqual(o["text_items"][0]["text"],"DIA 10")
        self.assertEqual(o["text_items"][0]["box"],{"x0":10,"y0":20,"x1_exclusive":34,"y1_exclusive":28})

    def test_skips_nonword_rows_and_low_confidence(self):
        tsv=HEADER + (
            "4\t1\t1\t1\t1\t0\t0\t0\t100\t20\t-1\t\n"
            "5\t1\t1\t1\t1\t1\t1\t1\t8\t8\t10\tNOISE\n"
            "5\t1\t1\t1\t1\t2\t10\t1\t8\t8\t91\tOK\n"
        )
        o=parse_tsv(tsv,image_width=50,image_height=20,min_confidence=50)
        self.assertEqual(o["status"],"PARSED")
        self.assertEqual(o["word_count"],1)
        self.assertEqual(o["text_items"][0]["text"],"OK")

    def test_out_of_bounds_fails_closed(self):
        tsv=HEADER+"5\t1\t1\t1\t1\t1\t95\t10\t10\t10\t90\tBAD\n"
        o=parse_tsv(tsv,image_width=100,image_height=100)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("BOX_OUT_OF_BOUNDS",o["errors"][0])

    def test_negative_box_fails_closed(self):
        tsv=HEADER+"5\t1\t1\t1\t1\t1\t-1\t10\t10\t10\t90\tBAD\n"
        o=parse_tsv(tsv,image_width=100,image_height=100)
        self.assertEqual(o["status"],"FAIL_CLOSED")

    def test_bad_schema_fails_closed(self):
        o=parse_tsv("text\nabc\n",image_width=10,image_height=10)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertEqual(o["error"],"TSV_SCHEMA_INVALID")

    def test_order_independent_line_keys_are_sorted(self):
        tsv=HEADER + (
            "5\t1\t1\t1\t2\t1\t5\t30\t5\t5\t90\tB\n"
            "5\t1\t1\t1\t1\t1\t5\t10\t5\t5\t90\tA\n"
        )
        o=parse_tsv(tsv,image_width=50,image_height=50)
        self.assertEqual([x["text"] for x in o["text_items"]],["A","B"])

if __name__=="__main__":
    unittest.main()
