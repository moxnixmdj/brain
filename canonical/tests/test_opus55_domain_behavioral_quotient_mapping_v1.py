from __future__ import annotations

import copy
import json
import pathlib
import unittest

from canonical.runtime.opus55_domain_behavioral_quotient_mapping_v1 import (
    MappingError,
    verify_mapping,
    verify_repository,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAPPING = json.loads((ROOT / "canonical/governance/OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_V1.json").read_text(encoding="utf-8"))
PROTOCOLS = json.loads((ROOT / "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json").read_text(encoding="utf-8"))
FIRST_PARTY = json.loads((ROOT / "canonical/governance/OPUS55_FIRST_PARTY_OBSERVABLE_SURFACE_COVERAGE_AUDIT_20261005_V1.json").read_text(encoding="utf-8"))
META = json.loads((ROOT / "canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V5.json").read_text(encoding="utf-8"))


class DomainBehavioralQuotientMappingTests(unittest.TestCase):
    def test_current_repository_mapping_passes_structurally(self):
        out = verify_repository(ROOT)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["mapped_surface_count"], 5)
        self.assertEqual(out["canonical_family_count"], 19)
        self.assertFalse(out["domain_acceptance_parity_proved"])
        self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_domain_label_cannot_create_unknown_family(self):
        candidate = copy.deepcopy(MAPPING)
        candidate["mappings"][0]["existing_family_union"].append("CYBERSECURITY")
        with self.assertRaisesRegex(MappingError, "UNKNOWN_FAMILY"):
            verify_mapping(candidate, PROTOCOLS, FIRST_PARTY, META)

    def test_arxivmath_cannot_inherit_hle_only_acceptance(self):
        candidate = copy.deepcopy(MAPPING)
        row = next(x for x in candidate["mappings"] if x["surface"] == "MATHEMATICAL_REASONING_ARXIVMATH")
        row["acceptance_scope_bridge_required"] = False
        with self.assertRaisesRegex(MappingError, "ARXIVMATH_SCOPE_BRIDGE_NOT_REQUIRED"):
            verify_mapping(candidate, PROTOCOLS, FIRST_PARTY, META)

    def test_mapping_cannot_claim_acceptance(self):
        candidate = copy.deepcopy(MAPPING)
        candidate["mapping_result"]["terminal_acceptance_credit_delta"] = 1
        with self.assertRaisesRegex(MappingError, "TERMINAL_CREDIT_FORBIDDEN"):
            verify_mapping(candidate, PROTOCOLS, FIRST_PARTY, META)

    def test_exact_five_surface_frontier_is_load_bearing(self):
        candidate = copy.deepcopy(MAPPING)
        candidate["mappings"] = candidate["mappings"][:-1]
        with self.assertRaisesRegex(MappingError, "SURFACE_SET_DRIFT"):
            verify_mapping(candidate, PROTOCOLS, FIRST_PARTY, META)


if __name__ == "__main__":
    unittest.main(verbosity=2)
