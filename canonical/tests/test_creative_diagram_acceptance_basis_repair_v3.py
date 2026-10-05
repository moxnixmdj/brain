from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.verify_creative_diagram_acceptance_basis_repair_v3 import (
    VerificationError,
    verify,
)

ROOT = Path(__file__).resolve().parents[2]

FILES = [
    "canonical/governance/CREATIVE_DIAGRAM_ACCEPTANCE_BASIS_REPAIR_V2_20261005.json",
    "canonical/governance/STATIC_SVG_DIAGRAM_MECHANICS_KERNEL_20261005_V1.json",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
    "canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json",
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "canonical/runtime/html_svg_diagram_mechanics_v1.py",
    "canonical/runtime/svg_diagram_render_oracle_v1.py",
    "canonical/governance/CREATIVE_DIAGRAM_ACCEPTANCE_BASIS_REPAIR_V3_20261005.json",
]


class CreativeDiagramAcceptanceBasisRepairV3Tests(unittest.TestCase):
    def _clone(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        for rel in FILES:
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
        return td, root

    def test_current_tree_passes(self):
        out = verify(ROOT)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["new_family_mutations"], 0)
        self.assertEqual(out["new_diagram_learned_primitives"], 0)
        self.assertEqual(out["new_diagram_acceptance_atoms"], 0)
        self.assertEqual(out["new_creative_text_acceptance_atoms"], 1)
        self.assertEqual(out["creative_atom"], "CREATIVE_TEXT_GENERATION_QUALITY_NONINFERIOR")
        self.assertEqual(
            out["projected_if_creative_atom_integrated_unproved"],
            "19_FAMILIES__39_ATOMS__14_PROVED__25_UNRESOLVED",
        )
        self.assertFalse(out["terminal"])

    def test_bound_predecessor_drift_fails_closed(self):
        td, root = self._clone()
        with td:
            p = root / "canonical/governance/CREATIVE_DIAGRAM_ACCEPTANCE_BASIS_REPAIR_V2_20261005.json"
            p.write_text(p.read_text() + "\n", encoding="utf-8")
            with self.assertRaisesRegex(VerificationError, "BOUND_BLOB_DRIFT"):
                verify(root)

    def test_kernel_drift_fails_closed(self):
        td, root = self._clone()
        with td:
            p = root / "canonical/governance/STATIC_SVG_DIAGRAM_MECHANICS_KERNEL_20261005_V1.json"
            doc = json.loads(p.read_text())
            doc["independent_verification_required"] = False
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(VerificationError):
                verify(root)

    def test_behavior_contract_mapping_drift_fails_closed(self):
        td, root = self._clone()
        with td:
            p = root / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
            doc = json.loads(p.read_text())
            doc["family_to_residual_contracts"]["ARTIFACT_CREATION"] = [
                x for x in doc["family_to_residual_contracts"]["ARTIFACT_CREATION"]
                if x != "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
            ]
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(VerificationError):
                verify(root)

    def test_synthesis_creative_dimension_change_fails_closed(self):
        td, root = self._clone()
        with td:
            p = root / "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json"
            doc = json.loads(p.read_text())
            doc["scorer_contract"]["dimensions"]["creative_originality"] = "0_TO_1"
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(VerificationError):
                verify(root)

    def test_creative_atom_preexistence_fails_closed(self):
        td, root = self._clone()
        with td:
            p = root / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
            doc = json.loads(p.read_text())
            doc["predicates"].append({"id": "CREATIVE_TEXT_GENERATION_QUALITY_NONINFERIOR"})
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(VerificationError):
                verify(root)

    def test_candidate_diagram_atom_regression_fails(self):
        td, root = self._clone()
        with td:
            p = root / "canonical/governance/CREATIVE_DIAGRAM_ACCEPTANCE_BASIS_REPAIR_V3_20261005.json"
            doc = json.loads(p.read_text())
            doc["minimality"]["new_diagram_acceptance_atoms"] = 1
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaisesRegex(VerificationError, "CANDIDATE_DIAGRAM_ATOM_NONZERO"):
                verify(root)

    def test_candidate_credit_leak_fails(self):
        td, root = self._clone()
        with td:
            p = root / "canonical/governance/CREATIVE_DIAGRAM_ACCEPTANCE_BASIS_REPAIR_V3_20261005.json"
            doc = json.loads(p.read_text())
            doc["accounting"]["acceptance_credit_delta"] = 1
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaisesRegex(VerificationError, "CANDIDATE_ACCOUNTING_NONZERO"):
                verify(root)


if __name__ == "__main__":
    unittest.main()
