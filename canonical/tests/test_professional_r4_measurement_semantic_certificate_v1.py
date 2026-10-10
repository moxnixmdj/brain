from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r4_measurement_semantic_certificate_v1 as cert

ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_PATH = ROOT / "canonical/governance/ARTIFACT_MEASUREMENT_BINDING_20261007_V1.json"
VERIFY_PATH = ROOT / "canonical/verification/ARTIFACT_MEASUREMENT_VERIFY_20261007_V1.json"

MEASUREMENT_SHA = "4da88dc71e85874b6445988b792951fb3c36d62f"
ACCEPTANCE_SHA = "7cb47bbefa807e93007e13e84607b41e27245f62"


def docs():
    return (
        json.loads(GOVERNANCE_PATH.read_text(encoding="utf-8")),
        json.loads(VERIFY_PATH.read_text(encoding="utf-8")),
    )


def binding(governance, verification):
    return {
        "root_id": cert.ROOT_ID,
        "claim_kind": cert.CLAIM_KIND,
        "governance_sha256": cert.digest(governance),
        "verification_sha256": cert.digest(verification),
        "measurement_runtime_git_blob_sha": MEASUREMENT_SHA,
        "acceptance_runtime_git_blob_sha": ACCEPTANCE_SHA,
        "semantic_roles": dict(cert.SEMANTIC_ROLES),
        "boundaries": {
            "automatic_rubric_construct_alignment": False,
            "holistic_visual_quality_measured": False,
            "proposal_supplied_values_authoritative": False,
            "unsupported_measurement_kinds_allowed": False,
            "global_r4_semantic_leaf_closed": False,
            "outside_supported_mechanical_kinds_stays_open": True,
        },
    }


class ProfessionalR4MeasurementSemanticCertificateV1Tests(unittest.TestCase):
    def test_exact_current_r4_measurement_bridge_binds_semantics(self):
        governance, verification = docs()
        out = cert.certify(governance, verification, binding(governance, verification))
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["claim_scope"]["measurement_kinds"]),
            cert.SUPPORTED_KINDS,
        )
        self.assertFalse(out["semantic_leaf_credit"])
        self.assertFalse(out["global_leaf_closure"])

    def test_supported_measurement_kind_drift_fails_closed(self):
        governance, verification = docs()
        bad = copy.deepcopy(governance)
        bad["repair"]["supported_v1"].remove("PPTX_TEXT_CONTAINS")
        out = cert.certify(bad, verification, binding(bad, verification))
        self.assertFalse(out["pass"])
        self.assertIn("SUPPORTED_MEASUREMENT_KINDS_INVALID", out["errors"])

    def test_measurement_runtime_hash_mismatch_fails_closed(self):
        governance, verification = docs()
        b = binding(governance, verification)
        b["measurement_runtime_git_blob_sha"] = "0" * 40
        out = cert.certify(governance, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("MEASUREMENT_RUNTIME_HASH_MISMATCH", out["errors"])

    def test_rubric_construct_overclaim_fails_closed(self):
        governance, verification = docs()
        b = binding(governance, verification)
        b["boundaries"]["automatic_rubric_construct_alignment"] = True
        out = cert.certify(governance, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("RUBRIC_CONSTRUCT_OVERCLAIM", out["errors"])

    def test_holistic_quality_overclaim_fails_closed(self):
        governance, verification = docs()
        b = binding(governance, verification)
        b["boundaries"]["holistic_visual_quality_measured"] = True
        out = cert.certify(governance, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("HOLISTIC_QUALITY_OVERCLAIM", out["errors"])

    def test_proposal_values_cannot_become_artifact_facts(self):
        governance, verification = docs()
        b = binding(governance, verification)
        b["boundaries"]["proposal_supplied_values_authoritative"] = True
        out = cert.certify(governance, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("PROPOSAL_VALUE_AUTHORITY_OVERCLAIM", out["errors"])

    def test_missing_verified_property_fails_closed(self):
        governance, verification = docs()
        bad = copy.deepcopy(verification)
        bad["verified"].remove("PATH_ESCAPE_FAILS_CLOSED")
        out = cert.certify(governance, bad, binding(governance, bad))
        self.assertFalse(out["pass"])
        self.assertIn("VERIFICATION_REQUIRED_PROPERTIES_MISSING", out["errors"])

    def test_missing_governance_nonclaim_fails_closed(self):
        governance, verification = docs()
        bad = copy.deepcopy(governance)
        bad["hard_nonclaims"].remove(
            "NO_CLAIM_FIELD_TO_RUBRIC_SEMANTIC_ALIGNMENT_IS_AUTOMATIC"
        )
        out = cert.certify(bad, verification, binding(bad, verification))
        self.assertFalse(out["pass"])
        self.assertIn("GOVERNANCE_REQUIRED_NONCLAIMS_MISSING", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
