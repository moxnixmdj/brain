from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import terminal_candidate_donor_independence_audit_v1 as audit


class TerminalCandidateDonorIndependenceAuditV1Tests(unittest.TestCase):
    def test_static_audit_never_grants_donor_independence_authority(self) -> None:
        with TemporaryDirectory() as tmp:
            out = audit.evaluate(Path(tmp))
            self.assertFalse(out["donor_independence_authority"])
            self.assertFalse(out["runtime_cognition_provenance_authority"])
            self.assertFalse(out["full_runtime_dependency_inventory_complete"])
            self.assertFalse(out["external_contribution_census_complete"])
            self.assertIsNone(out["model_dependency_count"])
            self.assertIsNone(out["external_model_runtime_dependency_count"])
            self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()
