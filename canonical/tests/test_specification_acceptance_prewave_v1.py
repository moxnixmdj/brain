import tempfile,unittest
from pathlib import Path
from canonical.runtime.verify_specification_acceptance_prewave_v1 import verify

class Tests(unittest.TestCase):
    def test_live_tree_passes(self):
        out=verify(Path("."))
        self.assertEqual(out["status"],"PASS",out)
        self.assertFalse(out["execution_authority"])

if __name__=="__main__": unittest.main()
