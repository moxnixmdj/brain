from __future__ import annotations
import unittest
from canonical.runtime import professional_task_fulfillment_bridge_v1 as f

class Tests(unittest.TestCase):
    def test_bad_bundle_fails_closed(self):
        out=f.verify(None,repo_root=".")
        self.assertFalse(out["pass"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_obligation_digest_requires_nonempty_required_semantics(self):
        with self.assertRaises(ValueError):
            f.obligation_universe_digest([])
        with self.assertRaises(ValueError):
            f.obligation_universe_digest([{"obligation_id":"O1","semantics":"","required":True}])
        with self.assertRaises(ValueError):
            f.obligation_universe_digest([{"obligation_id":"O1","semantics":"x","required":False}])

if __name__=="__main__":
    unittest.main()
