from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.verify_opus55_b2_creative_diagram_minimum_semantic_repair_v2 import VerifyError, verify

ROOT = Path(__file__).resolve().parents[2]

COPY = [
    "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
    "canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json",
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15.json",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15_ACTIVATION_V1.json",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_ACTIVATION_V1.json",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json",
    "canonical/governance/OPUS55_FUNCTIONAL_ROLE_BASIS_TARGET_DISCOVERY_FALSIFICATION_ACTIVATION_20261005_V1.json",
    "canonical/governance/OPUS55_TARGET_DISCOVERY_COMPLETENESS_CERTIFICATE_V1_ACTIVATION_V1.json",
    "canonical/governance/TERMINAL_FRONTIER_COMPILER_V2.json",
    "canonical/runtime/html_svg_diagram_mechanics_v1.py",
    "canonical/governance/OPUS55_B2_CREATIVE_DIAGRAM_MINIMUM_SEMANTIC_REPAIR_20261005_V2.json",
]


class RepairV2Tests(unittest.TestCase):
    def clone(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        for rel in COPY:
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
        return td, root

    def test_live_candidate_passes_current_state_gate(self):
        out = verify(ROOT)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["candidate_projection_if_later_integrated"], "19_FAMILIES__39_ATOMS__14_PROVED__25_UNRESOLVED")
        self.assertEqual(out["credit_delta"], 0)

    def test_bound_blob_drift_fails(self):
        td, root = self.clone()
        with td:
            p = root / "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15.json"
            p.write_text(p.read_text() + "\n", encoding="utf-8")
            with self.assertRaisesRegex(VerifyError, "BLOB_DRIFT"):
                verify(root)

    def test_matched_execution_release_fails(self):
        td, root = self.clone()
        with td:
            p = root / "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15.json"
            d = json.loads(p.read_text())
            for row in d["current_information_positive_action_groups"]:
                if row["id"] == "F_SYNTHESIS_COMPARATOR_CAPACITY_OR_STRONGER_PROOF":
                    row["action"] = row["action"].replace("__NO_MATCHED_CASE_EXECUTION_YET", "")
            p.write_text(json.dumps(d), encoding="utf-8")
            with self.assertRaises(VerifyError):
                verify(root)

    def test_w4_promoted_to_literal_finality_fails(self):
        td, root = self.clone()
        with td:
            p = root / "canonical/governance/TERMINAL_FRONTIER_COMPILER_V2.json"
            d = json.loads(p.read_text())
            d["current_recomputed_truth"]["target_discovery_complete"] = True
            p.write_text(json.dumps(d), encoding="utf-8")
            with self.assertRaises(VerifyError):
                verify(root)

    def test_diagram_mechanics_scope_widening_fails(self):
        td, root = self.clone()
        with td:
            p = root / "canonical/runtime/html_svg_diagram_mechanics_v1.py"
            p.write_text(p.read_text().replace(
                "Content selection, layout quality, and presentation quality are explicitly outside scope.",
                "All diagram quality is covered."
            ), encoding="utf-8")
            with self.assertRaises(VerifyError):
                verify(root)

    def test_candidate_credit_leak_fails(self):
        td, root = self.clone()
        with td:
            p = root / "canonical/governance/OPUS55_B2_CREATIVE_DIAGRAM_MINIMUM_SEMANTIC_REPAIR_20261005_V2.json"
            d = json.loads(p.read_text())
            d["accounting"]["acceptance_credit_delta"] = 1
            p.write_text(json.dumps(d), encoding="utf-8")
            with self.assertRaisesRegex(VerifyError, "CANDIDATE_ACCOUNTING_NONZERO"):
                verify(root)


if __name__ == "__main__":
    unittest.main()
