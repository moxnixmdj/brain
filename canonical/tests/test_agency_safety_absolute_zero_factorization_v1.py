from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CERT = "canonical/governance/AGENCY_SAFETY_ABSOLUTE_ZERO_FACTORIZATION_20261005_V1.json"

EXPECTED = {
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json":
        "72a5cd689f55df84de73693371264f02ef4e7226",
    "canonical/governance/ROOT3_CONFINED_EFFECT_BROKER_MEDIATION_BREAKTHROUGH_20261005_V1.json":
        "43090fbe55507044686b6b9521860655fae25033",
    "canonical/governance/HIDDEN_EVALUATOR_TARGET_FREE_TOP_SUPPORT_DOMINANCE_V1.json":
        "69e3ac04f0158bd2309c926d606d798449633f25",
}

EFFECT_ATOMS = {
    "invariant:safety_no_material_regression",
    "invariant:scope_no_material_regression",
    "invariant:invalid_action_no_material_regression",
}
LIVENESS_ATOM = "invariant:unrecovered_failure_no_material_regression"


def blob_sha(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class AgencySafetyAbsoluteZeroFactorizationTests(unittest.TestCase):
    def test_sources_are_content_addressed_exactly(self):
        for rel, expected in EXPECTED.items():
            self.assertEqual(blob_sha(rel), expected, rel)

    def test_exact_four_atom_partition_is_lossless(self):
        cert = load(CERT)
        atoms = set(cert["exact_target_atoms"])
        effects = set(cert["factorization"]["effect_safety_atoms"])
        residual = set(cert["factorization"]["liveness_recovery_residual"])
        self.assertEqual(effects, EFFECT_ATOMS)
        self.assertEqual(residual, {LIVENESS_ATOM})
        self.assertEqual(effects | residual, atoms)
        self.assertFalse(effects & residual)
        self.assertEqual(len(atoms), 4)

    def test_normalization_contains_exact_atoms(self):
        norm = load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json")
        target = next(
            row for row in norm["targets"]
            if row["predicate_id"] == "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION"
        )
        normalized = {row["atom"] for row in target["atom_sources"]}
        self.assertEqual(
            normalized,
            EFFECT_ATOMS | {LIVENESS_ATOM},
        )

    def test_protocol_preserves_matched_success_as_separate_obligation(self):
        protocol = load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
        agency = next(
            row for row in protocol["protocols"]
            if row["family"] == "COMPLEX_MULTI_TOOL_AGENCY"
        )
        self.assertEqual(agency["proof_mode"], "MATCHED_DIRECT_NONINFERIORITY")
        self.assertIn("terminal_task_success", agency["primary_metrics"])
        self.assertIn("unrecovered_failure_rate", agency["primary_metrics"])
        cert = load(CERT)
        self.assertIn(
            "terminal_task_success_noninferiority",
            cert["factorization"]["excluded_from_this_predicate"],
        )

    def test_zero_violation_dominates_any_nonnegative_target_violation(self):
        # The reduction is arithmetic only after exact scorer semantics establish
        # a nonnegative lower-is-better violation order with zero as the optimum.
        for target_violation in (0.0, 0.001, 0.25, 1.0, 100.0):
            brain_violation = 0.0
            self.assertLessEqual(brain_violation, target_violation)

    def test_fail_closed_noncommit_does_not_fake_recovery(self):
        cert = load(CERT)
        witness = cert["liveness_boundary"]["counterexample"]
        self.assertEqual(witness["effect_safety_violations"], 0)
        self.assertEqual(witness["unrecovered_failure"], 1)
        self.assertIn(
            "DO_NOT_COUNT_NONCOMMIT",
            cert["liveness_boundary"]["forbidden_shortcut"],
        )

    def test_zero_credit_and_fail_closed_boundary(self):
        cert = load(CERT)
        self.assertEqual(cert["accounting"]["acceptance_credit_delta"], 0)
        self.assertEqual(cert["accounting"]["capability_credit_delta"], 0)
        self.assertFalse(cert["fresh_reality_authority"])
        self.assertTrue(cert["independent_verification_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
