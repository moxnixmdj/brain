from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.verify_opus55_b2_creative_diagram_minimum_semantic_repair_v1 import (
    VerificationError,
    verify,
)

ROOT = Path(__file__).resolve().parents[2]


class MinimumSemanticRepairVerifierTests(unittest.TestCase):
    def _copy(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        for rel in [
            "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json",
            "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
            "canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json",
            "canonical/governance/OPUS55_OBSERVABLE_BEHAVIOR_FUNCTIONAL_BASIS_CHARACTERIZATION_20261005_V1.json",
            "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
            "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json",
            "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_ACTIVATION_V1.json",
            "canonical/governance/OPUS55_B2_CREATIVE_DIAGRAM_MINIMUM_SEMANTIC_REPAIR_20261005_V1.json",
        ]:
            src = ROOT / rel
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return td, root

    def test_current_tree_passes(self) -> None:
        out = verify(ROOT)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["projected_if_integrated"], "19_FAMILIES_39_ATOMS_14_PROVED_25_UNRESOLVED")
        self.assertEqual(out["credit_delta"], 0)
        self.assertFalse(out["fresh_reality"])

    def test_blob_drift_fails_closed(self) -> None:
        td, root = self._copy()
        with td:
            p = root / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
            p.write_text(p.read_text() + "\n", encoding="utf-8")
            with self.assertRaisesRegex(VerificationError, "BOUND_BLOB_DRIFT"):
                verify(root)

    def test_diagram_atom_preexistence_fails(self) -> None:
        td, root = self._copy()
        with td:
            p = root / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
            doc = json.loads(p.read_text())
            doc["predicates"].append({"id": "DIAGRAM_OUTPUT_SCOPE_QUALITY_NONINFERIOR"})
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(VerificationError):
                verify(root)

    def test_execution_authority_mutation_fails(self) -> None:
        td, root = self._copy()
        with td:
            p = root / "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_ACTIVATION_V1.json"
            doc = json.loads(p.read_text())
            doc["authority"]["execution"] = True
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(VerificationError):
                verify(root)

    def test_candidate_credit_mutation_fails(self) -> None:
        td, root = self._copy()
        with td:
            p = root / "canonical/governance/OPUS55_B2_CREATIVE_DIAGRAM_MINIMUM_SEMANTIC_REPAIR_20261005_V1.json"
            doc = json.loads(p.read_text())
            doc["accounting"]["acceptance_credit_delta"] = 1
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaisesRegex(VerificationError, "CANDIDATE_ACCOUNTING_NONZERO"):
                verify(root)


if __name__ == "__main__":
    unittest.main()
