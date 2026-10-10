from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r3_realization_semantic_certificate_v1 as cert

ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = ROOT / "canonical/governance/NATIVE_ARTIFACT_RENDER_PRESERVATION_PREFLIGHT_V1.json"
VERIFY_PATH = ROOT / "canonical/verification/NATIVE_ARTIFACT_RENDER_PRESERVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"


def docs():
    return (
        json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8")),
        json.loads(VERIFY_PATH.read_text(encoding="utf-8")),
    )


def binding(preflight, verification):
    return {
        "root_id": cert.ROOT_ID,
        "claim_kind": cert.CLAIM_KIND,
        "preflight_sha256": cert.digest(preflight),
        "verification_sha256": cert.digest(verification),
        "semantic_roles": dict(cert.SEMANTIC_ROLES),
        "boundaries": {
            "arbitrary_semantic_target_correctness": False,
            "whole_contract_scope_equivalence": False,
            "terminal_acceptance": False,
            "all_renderer_environment_invariance": False,
            "global_r3_semantic_leaf_closed": False,
            "outside_bounded_generated_edit_scope_stays_open": True,
        },
    }


class ProfessionalR3RealizationSemanticCertificateV1Tests(unittest.TestCase):
    def test_exact_current_r3_preflight_binds_semantics(self):
        preflight, verification = docs()
        out = cert.certify(preflight, verification, binding(preflight, verification))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["claim_scope"]["formats"], ["docx", "xlsx", "pptx", "pdf"])
        self.assertFalse(out["semantic_leaf_credit"])
        self.assertFalse(out["global_leaf_closure"])
        self.assertFalse(out["terminal_authority"])

    def test_acceptance_threshold_mutation_fails_closed(self):
        preflight, verification = docs()
        bad = copy.deepcopy(preflight)
        bad["acceptance"]["max_changed_pixel_fraction"] = 0.5
        out = cert.certify(bad, verification, binding(bad, verification))
        self.assertFalse(out["pass"])
        self.assertIn(
            "ACCEPTANCE_FIELD_INVALID:max_changed_pixel_fraction",
            out["errors"],
        )

    def test_verification_missing_render_property_fails_closed(self):
        preflight, verification = docs()
        bad = copy.deepcopy(verification)
        bad["verified"].remove("AT_LEAST_ONE_PAGE_MUST_VISIBLY_CHANGE")
        out = cert.certify(preflight, bad, binding(preflight, bad))
        self.assertFalse(out["pass"])
        self.assertIn("VERIFICATION_REQUIRED_PROPERTIES_MISSING", out["errors"])

    def test_arbitrary_semantic_target_overclaim_fails_closed(self):
        preflight, verification = docs()
        b = binding(preflight, verification)
        b["boundaries"]["arbitrary_semantic_target_correctness"] = True
        out = cert.certify(preflight, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("ARBITRARY_SEMANTIC_TARGET_OVERCLAIM", out["errors"])

    def test_whole_contract_overclaim_fails_closed(self):
        preflight, verification = docs()
        b = binding(preflight, verification)
        b["boundaries"]["whole_contract_scope_equivalence"] = True
        out = cert.certify(preflight, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("WHOLE_CONTRACT_OVERCLAIM", out["errors"])

    def test_renderer_invariance_overclaim_fails_closed(self):
        preflight, verification = docs()
        b = binding(preflight, verification)
        b["boundaries"]["all_renderer_environment_invariance"] = True
        out = cert.certify(preflight, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("RENDERER_INVARIANCE_OVERCLAIM", out["errors"])

    def test_preflight_digest_drift_fails_closed(self):
        preflight, verification = docs()
        b = binding(preflight, verification)
        b["preflight_sha256"] = "0" * 64
        out = cert.certify(preflight, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("PREFLIGHT_DIGEST_MISMATCH", out["errors"])

    def test_outside_bounded_scope_must_remain_open(self):
        preflight, verification = docs()
        b = binding(preflight, verification)
        b["boundaries"]["outside_bounded_generated_edit_scope_stays_open"] = False
        out = cert.certify(preflight, verification, b)
        self.assertFalse(out["pass"])
        self.assertIn("OUTSIDE_SCOPE_OPEN_BOUNDARY_MISSING", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
