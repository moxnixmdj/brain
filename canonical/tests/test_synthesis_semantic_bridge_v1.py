from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.synthesis_semantic_bridge_verifier_v1 import (
    BRIDGE,
    P3,
    TARGET,
    WAVE,
    P3V,
    evaluate,
)

ROOT = Path(__file__).resolve().parents[2]


class SynthesisSemanticBridgeTests(unittest.TestCase):
    def copy_fixture(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        for rel in (BRIDGE, P3, TARGET, WAVE, P3V):
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes((ROOT / rel).read_bytes())
        return root

    def test_live_candidate_passes(self):
        out = evaluate(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["qualitative_atom_count"], 6)
        self.assertEqual(out["matched_metric_atom_count_open"], 2)
        self.assertFalse(out["matched_population_noninferiority_proved"])

    def test_metric_atom_cannot_be_smuggled_into_supported_set(self):
        root = self.copy_fixture()
        path = root / BRIDGE
        doc = json.loads(path.read_text())
        doc["supported_target_atoms"].append("metric:matched_quality")
        doc["open_target_atoms"].remove("metric:matched_quality")
        path.write_text(json.dumps(doc, indent=2) + "\n")
        out = evaluate(root)
        self.assertFalse(out["pass"])
        self.assertIn("SUPPORTED_ATOM_SET", out["errors"])

    def test_missing_frozen_source_check_fails(self):
        root = self.copy_fixture()
        path = root / P3
        doc = json.loads(path.read_text())
        doc["evaluator"]["required_checks"].remove("MATERIAL_CONFLICT_AND_UNCERTAINTY_PRESERVED")
        path.write_text(json.dumps(doc, indent=2) + "\n")
        out = evaluate(root)
        self.assertFalse(out["pass"])
        self.assertTrue(
            "AUTHORITY_SHA:p3_binding" in out["errors"]
            or any(x.startswith("SOURCE_CHECK_NOT_FROZEN:") for x in out["errors"])
        )

    def test_contaminated_terminal_receipt_fails(self):
        root = self.copy_fixture()
        path = root / WAVE
        doc = json.loads(path.read_text())

        def mutate(x):
            if isinstance(x, dict):
                if (
                    x.get("behavior_id") == "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
                    and x.get("portfolio") == "T1"
                    and x.get("binding_blob")
                ):
                    x["tuning_replay"] = True
                    return True
                for v in x.values():
                    if mutate(v):
                        return True
            elif isinstance(x, list):
                for v in x:
                    if mutate(v):
                        return True
            return False

        self.assertTrue(mutate(doc))
        path.write_text(json.dumps(doc, indent=2) + "\n")
        out = evaluate(root)
        self.assertFalse(out["pass"])
        self.assertTrue(
            "AUTHORITY_SHA:terminal_wave" in out["errors"]
            or "TERMINAL_RECEIPT_FLAG:T1:tuning_replay" in out["errors"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
