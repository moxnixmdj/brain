from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v21 as v21
from canonical.runtime import r2_regcap_contextual_fact_direct_adequacy_v1 as direct

ROOT = Path(__file__).resolve().parents[2]

def goal():
    return (
        "Extract verified regulatory-capital contextual facts from "
        "canonical/tmp/source.txt and save them to canonical/tmp/facts.json."
    )

def write_source(root: Path):
    p = root / "canonical/tmp/source.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "a 2.5% buffer comprised of CET1 above the regulatory minimum",
        encoding="utf-8",
    )

class Router(unittest.TestCase):
    def test_v21_adds_exactly_one_route_over_v20(self):
        self.assertEqual(len(v21.ROUTES), len(v21.v20.ROUTES) + 1)
        self.assertIn(direct.ROUTE_ID, v21.ROUTES)

    def test_v21_selects_regcap_route_before_v20(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_source(root)
            with patch.object(v21.v20, "preflight") as prior:
                out = v21.preflight({"task_id": "x", "goal": goal()}, repo_root=root)
            self.assertTrue(out["matched"], out)
            self.assertEqual(out["route_id"], direct.ROUTE_ID)
            prior.assert_not_called()

    def test_v21_delegates_unrelated_goal_to_v20(self):
        expected = {"matched": False, "status": "V20"}
        with patch.object(v21.v20, "preflight", return_value=expected) as prior:
            out = v21.preflight({"task_id": "x", "goal": "unrelated"})
        self.assertEqual(out, expected)
        prior.assert_called_once()

    def test_fixed_point_front_door_imports_v21(self):
        text = (
            ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "from canonical.runtime import r2_direct_end_to_end_adequacy_v21 as direct_adequacy",
            text,
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
