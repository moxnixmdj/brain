import json
import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

# Minimum versions that the Bytes wiring depends on. The test reads the LIVE
# pointer and asserts the bound version is >= the minimum, so a canonical
# pointer bump (V9 -> V10 -> ...) can never make this test stale again, while a
# regression to a superseded version still fails closed.
MIN_VERSIONS = {
    "capability_realization_law_path": ("FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK", 9),
    "capability_acquisition_engine_law_path": ("CAPABILITY_ACQUISITION_ENGINE_LAW", 8),
    "white_box_capability_harvesting_law_path": ("WHITE_BOX_CAPABILITY_HARVESTING_LAW", 2),
    "white_box_capability_capsule_schema_path": ("WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA", 2),
}


def _version_of(path: str, stem: str) -> int:
    match = re.search(rf"{re.escape(stem)}_V(\d+)\.(md|json)$", path)
    if not match:
        raise AssertionError(f"{path!r} does not look like a versioned {stem} artifact")
    return int(match.group(1))


class BytesCanonicalWiringTests(unittest.TestCase):
    def _pointer(self):
        return json.loads((ROOT / "canonical" / "CANONICAL_POINTER.json").read_text(encoding="utf-8"))

    def test_bytes_authorities_are_live_and_exist(self):
        pointer = self._pointer()
        boot = pointer["boot_requirements"]
        mandatory = set(pointer["mandatory_laws"])

        # Every boot-bound law must also be a mandatory law and be at least the minimum version.
        for key, (stem, minimum) in MIN_VERSIONS.items():
            bound = boot[key]
            self.assertGreaterEqual(_version_of(bound, stem), minimum, f"{key} regressed below V{minimum}: {bound}")
            if bound.endswith(".md"):
                self.assertIn(bound, mandatory, f"{key} is boot-bound but not in mandatory_laws: {bound}")

        # The arbitrage strategy is mandatory even though it is not a boot key.
        arbitrage = [law for law in mandatory if "CAPABILITY_INTERNALIZATION_ARBITRAGE_STRATEGY_V" in law]
        self.assertTrue(arbitrage, "no CAPABILITY_INTERNALIZATION_ARBITRAGE_STRATEGY law is mandatory")
        self.assertGreaterEqual(max(_version_of(p, "CAPABILITY_INTERNALIZATION_ARBITRAGE_STRATEGY") for p in arbitrage), 8)

        self.assertIn("canonical/laws/RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW_V1.md", mandatory)
        self.assertIs(boot["resource_bounded_capability_bytes_required"], True)
        self.assertEqual(boot["exact_minimum_claim_scope"], "FINITE_ENUMERATED_VERIFIED_MECHANISM_LIBRARY_ONLY")

        for rel in [
            *mandatory,
            boot["white_box_capability_capsule_schema_path"],
            boot["resource_bounded_capability_bytes_law_path"],
            boot["verified_mechanism_cover_optimizer_path"],
            boot["bytes_research_checkpoint_path"],
        ]:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_no_superseded_bytes_boot_authorities_remain(self):
        pointer = self._pointer()
        boot = pointer["boot_requirements"]
        mandatory = set(pointer["mandatory_laws"])
        # For every versioned boot authority, no OLDER version of the same stem may remain
        # bound anywhere in mandatory_laws or boot_requirements.
        bound_text = json.dumps({"mandatory_laws": sorted(mandatory), "boot_requirements": boot}, sort_keys=True)
        for key, (stem, _minimum) in MIN_VERSIONS.items():
            live = _version_of(boot[key], stem)
            for older in range(1, live):
                self.assertNotIn(f"{stem}_V{older}.", bound_text, f"superseded {stem}_V{older} still bound")

    def test_checkpoint_is_non_promotional_until_repo_artifacts_exist(self):
        checkpoint = json.loads(
            (ROOT / "canonical" / "obsolescence" / "BYTES_RESEARCH_CHECKPOINT_20261009_V1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(checkpoint["capability_credit_delta"], 0)
        self.assertTrue(checkpoint["status"].startswith("PERSISTED_RESEARCH_CHECKPOINT"))
        missing = checkpoint["repo_reconciliation"]["missing_from_repo_at_time_of_reconciliation"]
        self.assertIn("REPORTED_7_044_219_BYTE_SLICED_CAPSULE_BYTES", missing)

    def test_live_capsule_schema_is_transfer_safe_and_fail_closed(self):
        # The live schema (V3, superseding V2) is a transfer-safety schema. V2's byte/resource
        # accounting fields were NOT carried into V3; byte accounting is now carried by the
        # mandatory RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW_V1 + verified_mechanism_cover_optimizer +
        # bytes_research_checkpoint (asserted in test_bytes_authorities_are_live_and_exist).
        pointer = self._pointer()
        schema_path = pointer["boot_requirements"]["white_box_capability_capsule_schema_path"]
        schema = json.loads((ROOT / schema_path).read_text(encoding="utf-8"))
        required = set(schema["required_fields"])
        self.assertTrue(
            {
                "donor_runtime_dependency_count",
                "external_model_runtime_dependency_count",
                "online_teacher_call_count",
                "teacher_fallback_path_count",
                "donor_deletion_evidence",
                "independent_heldout_qualification",
                "full_runtime_dependency_inventory_complete",
                "promotion_status",
            }
            <= required,
            sorted(required),
        )
        rules = schema["hard_rules"]
        for key in (
            "donor_runtime_dependency_count_must_equal",
            "external_model_runtime_dependency_count_must_equal",
            "online_teacher_call_count_must_equal",
            "teacher_fallback_path_count_must_equal",
        ):
            self.assertEqual(rules[key], 0, key)
        self.assertIs(rules["copied_or_rehosted_external_model_is_not_transfer"], True)
        self.assertIs(rules["unknown_transfer_classification_fails_closed"], True)
        self.assertIs(schema["promotion_requires_transfer_gate_pass"], True)
        self.assertTrue((ROOT / schema["transfer_gate"]).is_file(), schema["transfer_gate"])

    def test_superseded_v2_capsule_schema_retains_byte_accounting_reference(self):
        # Historical reference only: the superseded V2 schema is the last place the capsule-level
        # byte/resource accounting contract was written down. Keep it readable until a V3+ schema
        # or the bytes law re-binds those fields explicitly.
        schema = json.loads(
            (ROOT / "canonical" / "governance" / "WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V2.json").read_text(encoding="utf-8")
        )
        self.assertIs(schema["byte_accounting"]["shared_artifacts_count_once"], True)
        self.assertIs(schema["mechanism_cover_membership"]["universal_shortest_program_claim_forbidden"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
