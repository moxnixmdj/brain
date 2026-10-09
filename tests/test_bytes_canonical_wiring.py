import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BytesCanonicalWiringTests(unittest.TestCase):
    def test_bytes_authorities_are_live_and_exist(self):
        pointer = json.loads((ROOT / "canonical" / "CANONICAL_POINTER.json").read_text(encoding="utf-8"))
        required = {
            "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V9.md",
            "canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V8.md",
            "canonical/laws/CAPABILITY_INTERNALIZATION_ARBITRAGE_STRATEGY_V8.md",
            "canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V2.md",
            "canonical/laws/RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW_V1.md",
        }
        self.assertTrue(required <= set(pointer["mandatory_laws"]))

        boot = pointer["boot_requirements"]
        self.assertTrue(boot["capability_realization_law_path"].endswith("MISSION_LOCK_V9.md"))
        self.assertTrue(boot["capability_acquisition_engine_law_path"].endswith("ENGINE_LAW_V8.md"))
        self.assertTrue(boot["white_box_capability_harvesting_law_path"].endswith("HARVESTING_LAW_V2.md"))
        self.assertTrue(boot["white_box_capability_capsule_schema_path"].endswith("CAPSULE_SCHEMA_V2.json"))
        self.assertIs(boot["resource_bounded_capability_bytes_required"], True)
        self.assertEqual(boot["exact_minimum_claim_scope"], "FINITE_ENUMERATED_VERIFIED_MECHANISM_LIBRARY_ONLY")

        for rel in [
            *required,
            boot["white_box_capability_capsule_schema_path"],
            boot["resource_bounded_capability_bytes_law_path"],
            boot["verified_mechanism_cover_optimizer_path"],
            boot["bytes_research_checkpoint_path"],
        ]:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_no_superseded_bytes_boot_authorities_remain(self):
        pointer_text = (ROOT / "canonical" / "CANONICAL_POINTER.json").read_text(encoding="utf-8")
        for stale in [
            "FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V7.md",
            "CAPABILITY_ACQUISITION_ENGINE_LAW_V7.md",
            "CAPABILITY_INTERNALIZATION_ARBITRAGE_STRATEGY_V7.md",
            "WHITE_BOX_CAPABILITY_HARVESTING_LAW_V1.md",
            "WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V1.json",
        ]:
            self.assertNotIn(stale, pointer_text)

    def test_checkpoint_is_non_promotional_until_repo_artifacts_exist(self):
        checkpoint = json.loads(
            (ROOT / "canonical" / "obsolescence" / "BYTES_RESEARCH_CHECKPOINT_20261009_V1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(checkpoint["capability_credit_delta"], 0)
        self.assertTrue(checkpoint["status"].startswith("PERSISTED_RESEARCH_CHECKPOINT"))
        missing = checkpoint["repo_reconciliation"]["missing_from_repo_at_time_of_reconciliation"]
        self.assertIn("REPORTED_7_044_219_BYTE_SLICED_CAPSULE_BYTES", missing)

    def test_capsule_schema_requires_byte_and_resource_accounting(self):
        schema = json.loads(
            (ROOT / "canonical" / "governance" / "WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V2.json").read_text(encoding="utf-8")
        )
        required = set(schema["required_fields"])
        self.assertTrue({"byte_accounting", "resource_bounds", "elicitation_scan_evidence", "mechanism_cover_membership"} <= required)
        self.assertIs(schema["byte_accounting"]["shared_artifacts_count_once"], True)
        self.assertIs(schema["mechanism_cover_membership"]["universal_shortest_program_claim_forbidden"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
