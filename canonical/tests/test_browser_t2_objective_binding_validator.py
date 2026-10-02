from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime.browser_t2_objective_binding_validator import validate


class BrowserT2ObjectiveBindingValidatorTests(unittest.TestCase):
    def test_live_binding_passes(self):
        out=validate(Path("."))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["diagnostic_case_count"],50)
        self.assertTrue(out["diagnostic_all_pass"])
        self.assertEqual(out["terminal_results_observed"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
