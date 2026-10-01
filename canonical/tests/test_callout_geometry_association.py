import unittest
from canonical.runtime.callout_geometry_association import associate_callout

class CalloutGeometryAssociationTests(unittest.TestCase):
    def test_unique_line(self):
        box={"x0":45,"y0":10,"x1_exclusive":55,"y1_exclusive":20}
        primitives={"lines":[{"x1":0,"y1":30,"x2":100,"y2":30},{"x1":200,"y1":200,"x2":250,"y2":200}],"circles":[]}
        out=associate_callout(box,primitives,max_distance=30,min_margin=1.5)
        self.assertEqual(out["status"],"ASSOCIATED")
        self.assertEqual(out["primitive_kind"],"line")
        self.assertEqual(out["primitive_index"],0)

    def test_ambiguous_lines_fail(self):
        box={"x0":45,"y0":45,"x1_exclusive":55,"y1_exclusive":55}
        primitives={"lines":[{"x1":0,"y1":40,"x2":100,"y2":40},{"x1":0,"y1":60,"x2":100,"y2":60}],"circles":[]}
        out=associate_callout(box,primitives,max_distance=30,min_margin=1.5)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"AMBIGUOUS_ASSOCIATION")

    def test_far_fails(self):
        box={"x0":0,"y0":0,"x1_exclusive":10,"y1_exclusive":10}
        primitives={"lines":[{"x1":200,"y1":200,"x2":250,"y2":200}],"circles":[]}
        out=associate_callout(box,primitives,max_distance=20)
        self.assertEqual(out["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
