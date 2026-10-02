from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.build_current_proof_coverage_manifest import build
from canonical.runtime.proof_coverage_compiler import evaluate


class DerivedProofCoverageManifestTests(unittest.TestCase):
    def write_basis(self, root: Path, contracts, admitted: int):
        p = root / "canonical/governance"
        p.mkdir(parents=True)
        (p / "ACTIVE_TERMINAL_PROOF_BASIS_V1.json").write_text(json.dumps({
            "date": "2026-10-02",
            "active_contract_count": len(contracts),
            "admissible_frozen_terminal_route_count": admitted,
            "contracts": contracts,
        }), encoding="utf-8")

    def test_builder_imports_only_canonical_admitted_routes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_basis(root, [
                {"behavior_id": "A", "proof_state": "TERMINAL_ROUTE_FROZEN_ADMISSIBLE", "blockers": []},
                {"behavior_id": "B", "proof_state": "OPEN", "blockers": ["X"]},
            ], admitted=1)
            manifest = build(root)
            self.assertEqual(manifest["required_obligations"], ["A", "B"])
            self.assertEqual([x["covers"] for x in manifest["routes"]], [["A"]])
            out = evaluate(manifest)
            self.assertEqual(out["status"], "INCOMPLETE_COVER")
            self.assertEqual(out["uncovered_obligations"], ["B"])

    def test_builder_fails_closed_on_declared_admission_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_basis(root, [
                {"behavior_id": "A", "proof_state": "TERMINAL_ROUTE_FROZEN_ADMISSIBLE", "blockers": []},
            ], admitted=0)
            with self.assertRaisesRegex(ValueError, "ADMISSIBLE_ROUTE_COUNT_MISMATCH"):
                build(root)

    def test_admitted_route_with_blockers_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_basis(root, [
                {"behavior_id": "A", "proof_state": "TERMINAL_ROUTE_FROZEN_ADMISSIBLE", "blockers": ["STALE"]},
            ], admitted=1)
            with self.assertRaisesRegex(ValueError, "ADMITTED_ROUTE_HAS_BLOCKERS"):
                build(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
