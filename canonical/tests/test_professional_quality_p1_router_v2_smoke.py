import unittest
from canonical.runtime import professional_quality_p1_router_v2 as r
class T(unittest.TestCase):
    def test_empty_abstains(self):
        self.assertEqual(r.route({})['status'],'ABSTAIN__P1_INCOMPLETE')
