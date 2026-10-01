import unittest
from canonical.runtime.engineering_feature_notation import parse_feature_notation

class EngineeringFeatureNotationTests(unittest.TestCase):
    def test_quantity_thru_hole(self):
        o=parse_feature_notation("2X Ø10 THRU")
        self.assertEqual(o["status"],"PARSED")
        self.assertEqual(o["quantity"],2)
        self.assertTrue(o["through"])
        self.assertEqual(o["diameter"],10.0)

    def test_counterbore_depth(self):
        o=parse_feature_notation("Ø20 CBORE 30 DEPTH 5")
        self.assertEqual(o["status"],"PARSED")
        self.assertEqual(o["counterbore"]["diameter"],30.0)
        self.assertEqual(o["counterbore"]["depth"],5.0)

    def test_countersink_angle(self):
        o=parse_feature_notation("Ø10 CSK 20 X 90°")
        self.assertEqual(o["status"],"PARSED")
        self.assertEqual(o["countersink"]["angle_deg"],90.0)

    def test_thread_depth(self):
        o=parse_feature_notation("M8x1.25 DEPTH 12")
        self.assertEqual(o["status"],"PARSED")
        self.assertEqual(o["major_diameter"],8.0)
        self.assertEqual(o["pitch"],1.25)
        self.assertEqual(o["depth"],12.0)

    def test_position_frame(self):
        o=parse_feature_notation("POSITION | DIA 0.10 | A | B | C")
        self.assertEqual(o["status"],"PARSED")
        self.assertEqual(o["kind"],"gdt")
        self.assertEqual(o["characteristic"],"position")
        self.assertTrue(o["diametrical_zone"])
        self.assertEqual(o["datums"],["A","B","C"])

    def test_flatness_disallows_datum(self):
        o=parse_feature_notation("FLATNESS | 0.05 | A")
        self.assertEqual(o["status"],"FAIL_CLOSED")

    def test_perpendicularity_requires_datum(self):
        o=parse_feature_notation("PERPENDICULARITY | 0.10")
        self.assertEqual(o["status"],"FAIL_CLOSED")

    def test_datum(self):
        o=parse_feature_notation("DATUM | A")
        self.assertEqual(o["status"],"PARSED")
        self.assertEqual(o["datum"],"A")

    def test_unknown_fails_closed(self):
        o=parse_feature_notation("MAGIC TOLERANCE 7")
        self.assertEqual(o["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
