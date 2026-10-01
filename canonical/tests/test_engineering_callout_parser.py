import unittest
from canonical.runtime.engineering_callout_parser import parse_callout

class EngineeringCalloutParserTests(unittest.TestCase):
    def test_diameter_unicode(self):
        out=parse_callout("Ø10 mm")
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["kind"],"diameter")
        self.assertEqual(out["radius"],5.0)

    def test_radius(self):
        out=parse_callout("R 4.5 mm")
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["value"],4.5)

    def test_metric_thread(self):
        out=parse_callout("M8x1.25")
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["kind"],"thread")
        self.assertEqual(out["major_diameter"],8.0)
        self.assertEqual(out["pitch"],1.25)

    def test_symmetric_tolerance(self):
        out=parse_callout("20 ± 0.1 mm")
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["upper_deviation"],0.1)
        self.assertEqual(out["lower_deviation"],-0.1)

    def test_asymmetric_tolerance(self):
        out=parse_callout("20 +0.2 / -0.1 mm")
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["upper_deviation"],0.2)
        self.assertEqual(out["lower_deviation"],-0.1)

    def test_ambiguous_text_fails_closed(self):
        out=parse_callout("about ten millimeters")
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_compound_callout_fails_closed(self):
        out=parse_callout("Ø10 THRU 2 PLCS")
        self.assertEqual(out["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
