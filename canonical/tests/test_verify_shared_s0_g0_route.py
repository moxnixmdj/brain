import unittest
from canonical.runtime.verify_shared_s0_g0_route import verify_route
class Tests(unittest.TestCase):
    def test_route(self):
        out=verify_route()
        self.assertEqual(out["status"],"PASS",out)
if __name__=="__main__": unittest.main()
