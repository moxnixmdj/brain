from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_candidate_search_semantic_certificate_v1 as cert

ROOT = Path(__file__).resolve().parents[2]
SCOPE_PATH = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_SCOPE_20261010_V1.json"
VERIFY_PATH = ROOT / "canonical/verification/PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_VERIFY_20261010_V1.json"


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
            "global_candidate_search_complete": False,
            "escape_progress_totality": False,
            "open_world_hypothesis_complete": False,
            "policy_generation_complete": False,
            "discriminator_plan_authorizes_u_subtraction": False,
            "unresolved_outside_bound_scope_stays_open": True,
        },
    }


class ProfessionalCandidateSearchSemanticCertificateV1Tests(unittest.TestCase):
    def test_exact_current_r2_scope_binds_semantics(self):
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

    def test_missing_scope_guarantee_fails_closed(self):
        scope, verification = docs()
        bad = copy.deepcopy(scope)
        bad["guarantees"].remove(
            "U_SUBTRACTION_IS_NOT_AUTHORIZED_BY_A_DISCRIMINATOR_PLAN_ALONE"
        )
        out = cert.certify(bad, verification, binding(bad, verification))
        self.assertFalse(out["pass"])
        self.assertIn("SCOPE_REQUIRED_GUARANTEES_MISSING", out["errors"])

    def test_wrong_semantic_role_fails_closed(self):
        scope, verification = docs()
        b = binding(scope, verification)
        b["semantic_roles"]["candidate_scope"] = "OPEN_WORLD_ALL_FUTURE_CANDIDATES"
        out = cert.certify(scope, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_ROLE_INVALID:candidate_scope", out["errors"])

    def test_global_search_completeness_overclaim_fails_closed(self):
        scope, verification = docs()
        b = binding(scope, verification)
        b["boundaries"]["global_candidate_search_complete"] = True
        out = cert.certify(scope, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("GLOBAL_SEARCH_COMPLETENESS_OVERCLAIM", out["errors"])

    def test_discriminator_cannot_self_authorize_u_subtraction(self):
        scope, verification = docs()
        b = binding(scope, verification)
        b["boundaries"]["discriminator_plan_authorizes_u_subtraction"] = True
        out = cert.certify(scope, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("DISCRIMINATOR_U_SUBTRACTION_OVERCLAIM", out["errors"])

    def test_verification_must_preserve_global_nonclaims(self):
        scope, verification = docs()
        bad = copy.deepcopy(verification)
        bad["not_proved"].remove("GLOBAL_CANDIDATE_SEARCH_COMPLETENESS")
        out = cert.certify(scope, bad, binding(scope, bad))
        self.assertFalse(out["pass"])
        self.assertIn("VERIFICATION_REQUIRED_NONCLAIMS_MISSING", out["errors"])

    def test_outside_scope_must_remain_open(self):
        scope, verification = docs()
        b = binding(scope, verification)
        b["boundaries"]["unresolved_outside_bound_scope_stays_open"] = False
        out = cert.certify(scope, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("OUTSIDE_SCOPE_FAIL_CLOSED_RULE_MISSING", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
