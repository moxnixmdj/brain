from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from canonical.runtime import professional_quality_r10_constitution_cover_v1 as cover

ROOT = Path(__file__).resolve().parents[2]
CONSTITUTION = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_R10_DECISION_CONSTITUTION_20261010_V1.json"
MANIFEST = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"
CATALOG = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json"


class R10ConstitutionCoverV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.constitution = json.loads(CONSTITUTION.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.catalog = json.loads(CATALOG.read_text())

    def evaluate(self, *, constitution=None, manifest=None, catalog=None):
        return cover.evaluate(
            constitution=constitution or deepcopy(self.constitution),
            manifest=manifest or deepcopy(self.manifest),
            defeater_catalog=catalog or deepcopy(self.catalog),
        )

    def test_current_constitution_is_fully_mapped_without_truth_inflation(self):
        out = self.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["governing_law_count"], 11)
        self.assertEqual(out["mapped_governing_law_count"], 11)
        self.assertEqual(out["proof_slot_count"], 9)
        self.assertEqual(out["mapped_proof_slot_count"], 9)
        self.assertEqual(out["catalog_r10_defeater_count"], 17)
        self.assertEqual(out["guard_r10_defeater_count"], 17)
        self.assertEqual(out["missing_laws"], [])
        self.assertEqual(out["extra_unmapped_laws"], [])
        self.assertEqual(out["orphan_slots"], [])
        self.assertFalse(out["underlying_fact_truth_authority"])
        self.assertFalse(out["detection_completeness_proved"])
        self.assertFalse(out["whole_leaf_property_truth_proved"])
        self.assertFalse(out["terminal_authority"])

    def test_new_constitution_law_without_mechanism_fails_closed(self):
        c = deepcopy(self.constitution)
        c["governing_laws"]["novel_future_law"] = "NEW_LOAD_BEARING_REQUIREMENT"
        out = self.evaluate(constitution=c)
        self.assertFalse(out["pass"])
        self.assertIn("CONSTITUTION_LAW_UNMAPPED", out["errors"])
        self.assertEqual(out["extra_unmapped_laws"], ["novel_future_law"])

    def test_missing_constitution_law_fails_closed(self):
        c = deepcopy(self.constitution)
        c["governing_laws"].pop("stopping")
        out = self.evaluate(constitution=c)
        self.assertFalse(out["pass"])
        self.assertIn("CONSTITUTION_LAW_MISSING", out["errors"])
        self.assertEqual(out["missing_laws"], ["stopping"])

    def test_unjustified_new_proof_slot_fails_closed(self):
        with patch.object(
            cover.slots,
            "REQUIRED_SLOTS",
            tuple(cover.slots.REQUIRED_SLOTS) + ("invented_slot",),
        ):
            out = self.evaluate()
        self.assertFalse(out["pass"])
        self.assertIn("IMPLEMENTED_SLOT_NOT_JUSTIFIED_BY_CONSTITUTION", out["errors"])
        self.assertEqual(out["orphan_slots"], ["invented_slot"])

    def test_mapped_slot_removed_from_verifier_fails_closed(self):
        reduced = tuple(
            x for x in cover.slots.REQUIRED_SLOTS
            if x != "stopping_rule_precommitted"
        )
        with patch.object(cover.slots, "REQUIRED_SLOTS", reduced):
            out = self.evaluate()
        self.assertFalse(out["pass"])
        self.assertIn("MAPPED_SLOT_NOT_IMPLEMENTED", out["errors"])
        self.assertEqual(
            out["missing_slot_implementation"],
            ["stopping_rule_precommitted"],
        )

    def test_new_canonical_r10_defeater_without_guard_route_fails_closed(self):
        catalog = deepcopy(self.catalog)
        rows = catalog["defeaters"]
        rows.append({
            "id": "C999_NEW_R10_ATTACK",
            "root_ids": [cover.ROOT_ID],
            "attack": "new attack",
            "status": "OPEN",
            "terminal_pass_forbidden": True,
        })
        out = self.evaluate(catalog=catalog)
        self.assertFalse(out["pass"])
        self.assertIn("CATALOG_R10_DEFEATER_NOT_ENFORCED", out["errors"])
        self.assertEqual(out["missing_guard_defeaters"], ["C999_NEW_R10_ATTACK"])

    def test_guard_defeater_not_in_catalog_fails_closed(self):
        with patch.object(
            cover.guard,
            "KNOWN_R10_DEFEATERS",
            frozenset(set(cover.guard.KNOWN_R10_DEFEATERS) | {"C998_FOREIGN"}),
        ):
            out = self.evaluate()
        self.assertFalse(out["pass"])
        self.assertIn("GUARD_R10_DEFEATER_NOT_IN_CANONICAL_CATALOG", out["errors"])
        self.assertEqual(out["foreign_guard_defeaters"], ["C998_FOREIGN"])

    def test_root_contract_drift_fails_closed(self):
        manifest = deepcopy(self.manifest)
        root = next(x for x in manifest["roots"] if x["root_id"] == cover.ROOT_ID)
        root["contract"] = "weaker contract"
        out = self.evaluate(manifest=manifest)
        self.assertFalse(out["pass"])
        self.assertIn("R10_ROOT_CONTRACT_DRIFT", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
