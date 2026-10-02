from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime.delegation_t2_objective_binding_validator import (
    MANIFEST, EXPECTED_CYCLE, validate,
)

class DelegationT2ObjectiveBindingValidatorTests(unittest.TestCase):
    def test_live_repo_binding_passes(self):
        root = Path(__file__).resolve().parents[2]
        out = validate(root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["diagnostic_class_count"], 11)
        self.assertEqual([x["class"] for x in out["diagnostic"]], EXPECTED_CYCLE)
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["terminal_results_observed"], 0)

    def test_hidden_oracle_boundary_fails_closed(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
        data["information_boundary"]["candidate_receives_hidden_oracle"] = True
        with tempfile.TemporaryDirectory() as td:
            shadow = Path(td)
            (shadow / "canonical/governance").mkdir(parents=True)
            (shadow / MANIFEST).write_text(json.dumps(data), encoding="utf-8")
            # Bound paths intentionally absent too; boundary failure must still be explicit.
            out = validate(shadow)
        self.assertFalse(out["pass"])
        self.assertIn("INFORMATION_BOUNDARY_INVALID", out["errors"])

    def test_terminal_selector_cannot_be_adaptive(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
        data["selector"]["adaptive_case_selection"] = True
        with tempfile.TemporaryDirectory() as td:
            shadow = Path(td)
            (shadow / "canonical/governance").mkdir(parents=True)
            (shadow / MANIFEST).write_text(json.dumps(data), encoding="utf-8")
            out = validate(shadow)
        self.assertFalse(out["pass"])
        self.assertIn("SELECTOR_ADAPTIVE_CASE_SELECTION_INVALID", out["errors"])

if __name__ == "__main__":
    unittest.main()
