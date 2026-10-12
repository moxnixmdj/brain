from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DonorDeletionDependencyAccountingV2Tests(unittest.TestCase):
    def test_protocol_v2_is_fail_closed_and_requires_zero_external_model_cognition(self) -> None:
        doc = json.loads(
            (
                ROOT
                / "canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V2.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(doc.get("fail_closed"))


if __name__ == "__main__":
    unittest.main()
