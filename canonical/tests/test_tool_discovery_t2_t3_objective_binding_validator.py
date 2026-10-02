from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime.tool_discovery_t2_t3_objective_binding_validator import validate


class ToolDiscoveryObjectiveBindingValidatorTests(unittest.TestCase):
    def test_live_binding_passes(self):
        out=validate(Path("."))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["diagnostic_case_count"],60)
        self.assertTrue(out["diagnostic_all_pass"])
        self.assertEqual(out["terminal_results_observed"],0)
        self.assertEqual(out["fresh_terminal_evidence_consumed"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
