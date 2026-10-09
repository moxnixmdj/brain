from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class R2V60LiveProjectionCoherenceV1Tests(unittest.TestCase):
    def test_current_r2_binds_exact_live_v21_bytes_and_counts(self):
        r2 = _load(R2)
        direct = r2["direct_adequacy"]
        overlay = direct["successor_route_overlay"]

        self.assertIn("V60", r2["status"])
        self.assertEqual(r2["controller"]["fixed_point_git_blob_sha"], _git_blob_sha(
            ROOT / r2["controller"]["path"]
        ))
        self.assertEqual(
            direct["direct_runtime_path"],
            "canonical/runtime/r2_direct_end_to_end_adequacy_v21.py",
        )
        self.assertEqual(
            direct["direct_runtime_git_blob_sha"],
            _git_blob_sha(ROOT / direct["direct_runtime_path"]),
        )

        basis = _load(ROOT / overlay["basis_activation_path"])
        self.assertEqual(len(basis["current_routes"]), overlay["basis_route_count"])
        self.assertEqual(overlay["basis_route_count"], 39)
        self.assertEqual(overlay["added_route_count"], 2)

        route_ids = [row["route_id"] for row in overlay["added_verified_successors"]]
        self.assertEqual(len(route_ids), len(set(route_ids)))
        self.assertEqual(set(route_ids), {
            "DIRECT_ADEQUACY::CROSS_DOCUMENT_COMPOSITIONAL_LATTICE_V6",
            "DIRECT_ADEQUACY::CROSS_DOCUMENT_SEMANTIC_REGISTRY_V2_LATTICE_V7",
        })
        for row in overlay["added_verified_successors"]:
            self.assertEqual(
                row["runtime_git_blob_sha"],
                _git_blob_sha(ROOT / row["runtime_path"]),
            )
            self.assertEqual(
                row["route_runtime_git_blob_sha"],
                _git_blob_sha(ROOT / row["route_runtime_path"]),
            )
            self.assertEqual(
                row["verification_git_blob_sha"],
                _git_blob_sha(ROOT / row["verification_path"]),
            )

        expected = overlay["basis_route_count"] + overlay["added_route_count"]
        self.assertEqual(expected, 41)
        self.assertEqual(direct["current_route_count"], expected)
        self.assertEqual(direct["exact_cell_count"], 3)
        self.assertEqual(direct["bounded_family_count"], expected - 3)
        self.assertEqual(overlay["live_route_count"], expected)
        self.assertEqual(overlay["bounded_family_count"], expected - 3)

    def test_terminal_projection_is_exactly_bound_to_current_r2(self):
        r2 = _load(R2)
        terminal = _load(TERMINAL)
        current = terminal["authoritative_sources"]["current_r2_decision_intelligence"]
        truth = terminal["live_truth"]
        rec = terminal["r2_v60_source_implication_projection_reconciliation_20261009_v1"]

        r2_sha = _git_blob_sha(R2)
        self.assertEqual(current["status"], r2["status"])
        self.assertEqual(truth["current_r2_pointer_git_blob_sha"], r2_sha)
        self.assertEqual(truth["r2_direct_adequacy_route_count"], 41)
        self.assertEqual(truth["r2_direct_adequacy_exact_cell_count"], 3)
        self.assertEqual(truth["r2_direct_adequacy_bounded_family_count"], 38)
        self.assertIn("V60_V21", truth["current_r2_semantic_revision"])

        self.assertEqual(rec["current_r2_pointer_git_blob_sha"], r2_sha)
        self.assertEqual(
            rec["fixed_point_runtime_git_blob_sha"],
            _git_blob_sha(ROOT / rec["fixed_point_runtime_path"]),
        )
        self.assertEqual(
            rec["direct_runtime_git_blob_sha"],
            _git_blob_sha(ROOT / rec["direct_runtime_path"]),
        )
        self.assertEqual(rec["live_route_count"], 41)
        self.assertEqual(rec["bounded_family_count"], 38)
        self.assertEqual(rec["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
