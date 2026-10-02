import unittest
from pathlib import Path
from canonical.runtime.verify_structured_method_terminal_binding_v1 import verify
class Tests(unittest.TestCase):
 def test_live(self):
  o=verify(Path(".")); self.assertEqual(o["status"],"PASS",o)
if __name__=="__main__": unittest.main()
