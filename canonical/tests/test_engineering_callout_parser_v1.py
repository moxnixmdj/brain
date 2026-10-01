import unittest
from canonical.runtime.engineering_callout_parser import parse_callout

class T(unittest.TestCase):
    def test_known(self):
        self.assertEqual(parse_callout('DIA 10 mm')['kind'],'diameter')
        self.assertEqual(parse_callout('R5')['kind'],'radius')
        self.assertEqual(parse_callout('M6x1')['kind'],'thread')
        self.assertEqual(parse_callout('20 +/- 0.1 mm')['kind'],'symmetric_tolerance')
    def test_unknown(self):
        self.assertEqual(parse_callout('FOO')['status'],'FAIL_CLOSED')

if __name__=='__main__': unittest.main()
