from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r9_temporal_semantic_certificate_v1 as cert

ROOT = Path(__file__).resolve().parents[2]
SCOPE_PATH = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_R9_CONSERVATIVE_CENSORING_SCOPE_20261010_V1.json"
VERIFY_PATH = ROOT / "canonical/verification/PROFESSIONAL_QUALITY_R9_CONSERVATIVE_CENSORING_VERIFY_20261010_V1.json"


def docs():
    return (
        json.loads(SCOPE_PATH.read_text(encoding="utf-8")),
        json.loads(VERIFY_PATH.read_text(encoding="utf-8")),
    )


def binding(scope, verification):
    return {
        "root_id": cert.ROOT_ID,
        "claim_kind": cert.CLAIM_KIND,
        "scope_sha256": cert.digest(scope),
        "verification_sha256": cert.digest(verification),
        "semantic_roles": dict(cert.SEMANTIC_ROLES),
        "boundaries": {
            "multihorizon_deployment_validity": False,
            "rare_event_coverage": False,
            "distribution_shift_transport": False,
            "performative_equilibrium_stability": False,
            "global_r9_semantic_leaf_closed": False,
            "unobserved_final_slots_may_create_positive_credit": False,
            "outside_frozen_population_stays_unclaimed": True,
        },
    }


class ProfessionalR9TemporalSemanticCertificateV1Tests(unittest.TestCase):
    def test_exact_current_r9_scope_binds_semantics(self):
        scope, verification = docs()
        out = cert.certify(scope, verification, binding(scope, verification))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["claim_scope"]["kind"], cert.CLAIM_KIND)
        self.assertFalse(out["semantic_leaf_credit"])
        self.assertFalse(out["global_leaf_closure"])
        self.assertFalse(out["terminal_authority"])

    def test_scope_digest_drift_fails_closed(self):
        scope, verification = docs()
        b = binding(scope, verification)
        b["scope_sha256"] = "0" * 64
        out = cert.certify(scope, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("SCOPE_DIGEST_MISMATCH", out["errors"])

    def test_only_exact_success_can_be_positive(self):
        scope, verification = docs()
        b = binding(scope, verification)
        b["semantic_roles"]["positive_outcome"] = "TIMEOUT_MAY_COUNT_PARTIAL_POSITIVE"
        out = cert.certify(scope, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_ROLE_INVALID:positive_outcome", out["errors"])

    def test_final_missing_slots_cannot_create_positive_credit(self):
        scope, verification = docs()
        b = binding(scope, verification)
        b["boundaries"]["unobserved_final_slots_may_create_positive_credit"] = True
        out = cert.certify(scope, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("MISSING_SLOT_POSITIVE_CREDIT_OVERCLAIM", out["errors"])

    def test_multihorizon_overclaim_fails_closed(self):
        scope, verification = docs()
        b = binding(scope, verification)
        b["boundaries"]["multihorizon_deployment_validity"] = True
        out = cert.certify(scope, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("MULTIHORIZON_OVERCLAIM", out["errors"])

    def test_distribution_shift_overclaim_fails_closed(self):
        scope, verification = docs()
        b = binding(scope, verification)
        b["boundaries"]["distribution_shift_transport"] = True
        out = cert.certify(scope, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("DISTRIBUTION_SHIFT_OVERCLAIM", out["errors"])

    def test_verification_must_preserve_global_nonclaims(self):
        scope, verification = docs()
        bad = copy.deepcopy(verification)
        bad["not_proved"].remove("RARE_EVENT_COVERAGE")
        out = cert.certify(scope, bad, binding(scope, bad))
        self.assertFalse(out["pass"])
        self.assertIn("VERIFICATION_REQUIRED_NONCLAIMS_MISSING", out["errors"])

    def test_outside_frozen_population_must_remain_unclaimed(self):
        scope, verification = docs()
        b = binding(scope, verification)
        b["boundaries"]["outside_frozen_population_stays_unclaimed"] = False
        out = cert.certify(scope, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("OUTSIDE_FROZEN_POPULATION_BOUNDARY_MISSING", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
