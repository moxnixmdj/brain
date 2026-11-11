from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V1 = "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json"
V2 = "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V2.json"
CERT = "canonical/governance/AGENCY_SUPERPORTFOLIO_UNRECOVERED_FAILURE_TRUTH_REPAIR_20261005_V1.json"

EXPECTED = {
    V1: "d9ac894594ebcd2883520f7b7977a3548420541c",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":
        "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json":
        "72a5cd689f55df84de73693371264f02ef4e7226",
}


def blob_sha(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def family(doc: dict, name: str) -> dict:
    return next(row for row in doc["core_families"] if row["family"] == name)


class AgencySuperportfolioTruthRepairTests(unittest.TestCase):
    def test_source_blobs_exact(self):
        for rel, expected in EXPECTED.items():
            self.assertEqual(blob_sha(rel), expected, rel)

    def test_v1_omission_is_real_against_all_frozen_sources(self):
        v1 = load(V1)
        protocol = load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
        registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        norm = load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json")

        agency_protocol = next(
            row for row in protocol["protocols"]
            if row["family"] == "COMPLEX_MULTI_TOOL_AGENCY"
        )
        self.assertIn("unrecovered_failure_rate", agency_protocol["primary_metrics"])

        predicate = next(
            row for row in registry["predicates"]
            if row["id"] == "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION"
        )
        self.assertIn("unrecovered-failure", predicate["acceptance"])

        target = next(
            row for row in norm["targets"]
            if row["predicate_id"] == "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION"
        )
        atoms = {row["atom"] for row in target["atom_sources"]}
        self.assertIn("invariant:unrecovered_failure_no_material_regression", atoms)

        self.assertNotIn("unrecovered_failure_rate", family(v1, "COMPLEX_MULTI_TOOL_AGENCY")["metrics"])

    def test_v2_restores_exact_missing_agency_metric(self):
        v1 = load(V1)
        v2 = load(V2)
        a1 = family(v1, "COMPLEX_MULTI_TOOL_AGENCY")
        a2 = family(v2, "COMPLEX_MULTI_TOOL_AGENCY")
        self.assertEqual(
            a2["metrics"],
            a1["metrics"] + ["unrecovered_failure_rate"],
        )
        self.assertIn("UNRECOVERED_FAILURE", a2["rule"])

    def test_other_family_rows_are_unchanged(self):
        v1 = load(V1)
        v2 = load(V2)
        old = {row["family"]: row for row in v1["core_families"]}
        new = {row["family"]: row for row in v2["core_families"]}
        self.assertEqual(set(old), set(new))
        for name in old:
            if name != "COMPLEX_MULTI_TOOL_AGENCY":
                self.assertEqual(old[name], new[name])

    def test_no_case_exposure_or_threshold_relaxation(self):
        v1 = load(V1)
        v2 = load(V2)
        self.assertFalse(v1["case_generation"]["generated_now"])
        self.assertFalse(v1["case_generation"]["exposed_now"])
        self.assertFalse(v2["case_generation"]["generated_now"])
        self.assertFalse(v2["case_generation"]["exposed_now"])
        self.assertFalse(v2["case_generation"]["beacon_known_now"])
        self.assertEqual(v1["comparator_admissibility"], v2["comparator_admissibility"])
        self.assertEqual(v1["optional_scope_extensions"], v2["optional_scope_extensions"])

    def test_truth_repair_certificate_is_zero_credit(self):
        cert = load(CERT)
        self.assertEqual(cert["defect"]["omitted_load_bearing_metric"], "unrecovered_failure_rate")
        self.assertEqual(cert["accounting"]["acceptance_credit_delta"], 0)
        self.assertEqual(cert["accounting"]["capability_credit_delta"], 0)
        self.assertFalse(cert["fresh_reality_authority"])
        self.assertTrue(cert["independent_verification_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
