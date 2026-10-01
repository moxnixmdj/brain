import unittest
from canonical.runtime.orthographic_view_identity import assign_three_view_identity

def r(x0,y0,x1,y1):
    return {"x0":x0,"y0":y0,"x1_exclusive":x1,"y1_exclusive":y1}

class OrthographicViewIdentityTests(unittest.TestCase):
    def test_third_angle(self):
        regions=[r(100,100,180,180),r(100,10,180,80),r(220,100,300,180)]
        out=assign_three_view_identity(regions,convention="THIRD_ANGLE")
        self.assertEqual(out["status"],"ASSIGNED")
        self.assertEqual(out["front_region_index"],0)
        self.assertEqual(out["top_region_index"],1)
        self.assertEqual(out["right_region_index"],2)

    def test_first_angle(self):
        regions=[r(100,100,180,180),r(100,220,180,300),r(0,100,80,180)]
        out=assign_three_view_identity(regions,convention="FIRST_ANGLE")
        self.assertEqual(out["status"],"ASSIGNED")
        self.assertEqual(out["front_region_index"],0)
        self.assertEqual(out["top_region_index"],1)
        self.assertEqual(out["right_region_index"],2)

    def test_unknown_convention_fails(self):
        out=assign_three_view_identity([r(0,0,10,10)]*3,convention="AUTO")
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_mismatch_fails(self):
        regions=[r(100,100,180,180),r(100,10,180,80),r(220,100,300,180)]
        out=assign_three_view_identity(regions,convention="FIRST_ANGLE")
        self.assertEqual(out["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
