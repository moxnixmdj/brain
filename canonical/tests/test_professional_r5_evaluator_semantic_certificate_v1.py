from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r5_evaluator_semantic_certificate_v1 as cert

ROOT = Path(__file__).resolve().parents[2]
UNCERTAINTY = ROOT / "canonical/governance/GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_20261008_V1.json"
MECHANICS = ROOT / "canonical/verification/GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_SPRITE_VERIFICATION_20261008_V1.json"
INFO_CUT = ROOT / "canonical/governance/GDPVAL_EVALUATION_LAW_MINIMUM_INFORMATION_CUT_20261008_V1.json"


def docs():
    return tuple(json.loads(p.read_text(encoding="utf-8")) for p in (UNCERTAINTY, MECHANICS, INFO_CUT))


def binding(u, m, i):
    return {
        "root_id": cert.ROOT_ID,
        "claim_kind": cert.CLAIM_KIND,
        "uncertainty_sha256": cert.digest(u),
        "mechanics_sha256": cert.digest(m),
        "information_cut_sha256": cert.digest(i),
        "semantic_roles": dict(cert.SEMANTIC_ROLES),
        "boundaries": {
            "true_owner_evaluator_identified": False,
            "public_rubric_owner_monotonicity_proved": False,
            "global_r5_semantic_leaf_closed": False,
            "gdpval_acceptance_closed": False,
            "terminal_acceptance": False,
            "unresolved_owner_reference_stays_open": True,
            "stronger_brain_side_certificate_may_bypass": True,
        },
    }


class ProfessionalR5EvaluatorSemanticCertificateV1Tests(unittest.TestCase):
    def test_current_sources_bind_bounded_r5_semantics(self):
        u, m, i = docs()
        out = cert.certify(u, m, i, binding(u, m, i))
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["semantic_leaf_credit"])
        self.assertFalse(out["global_leaf_closure"])
        self.assertIn(
            "NO_TRUE_CURRENT_OWNER_EVALUATOR_IDENTIFICATION",
            out["claim_scope"]["limitations"],
        )

    def test_public_rubric_cannot_be_promoted_to_owner_semantics(self):
        u, m, i = docs()
        bad = copy.deepcopy(u)
        bad["soundness_firewall"]["forbidden_as_semantic_containment_proof"].remove(
            "PUBLIC_RUBRIC_ONLY"
        )
        out = cert.certify(bad, m, i, binding(bad, m, i))
        self.assertFalse(out["pass"])
        self.assertIn("FORBIDDEN_PROOF_CLASSES_MISSING", out["errors"])

    def test_mechanics_without_semantic_boundary_fails_closed(self):
        u, m, i = docs()
        bad = copy.deepcopy(m)
        bad["verification_boundary"] = []
        out = cert.certify(u, bad, i, binding(u, bad, i))
        self.assertFalse(out["pass"])
        self.assertIn("MECHANICS_BOUNDARY_MISSING", out["errors"])

    def test_countermodel_must_preserve_observable_equivalence(self):
        u, m, i = docs()
        bad = copy.deepcopy(i)
        bad["constructive_countermodel"]["observable_equivalence"] = "DIFFERENT"
        out = cert.certify(u, m, bad, binding(u, m, bad))
        self.assertFalse(out["pass"])
        self.assertIn("COUNTERMODEL_OBSERVABLE_EQUIVALENCE_MISSING", out["errors"])

    def test_minimum_separator_class_cannot_be_deleted(self):
        u, m, i = docs()
        bad = copy.deepcopy(i)
        bad["minimum_separator_cut"]["admissible_classes"].remove(
            "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_DOMINANCE"
        )
        out = cert.certify(u, m, bad, binding(u, m, bad))
        self.assertFalse(out["pass"])
        self.assertIn("MINIMUM_SEPARATOR_CLASSES_MISSING", out["errors"])

    def test_owner_identity_overclaim_fails_closed(self):
        u, m, i = docs()
        b = binding(u, m, i)
        b["boundaries"]["true_owner_evaluator_identified"] = True
        out = cert.certify(u, m, i, b)
        self.assertFalse(out["pass"])
        self.assertIn("OWNER_EVALUATOR_IDENTITY_OVERCLAIM", out["errors"])

    def test_unresolved_owner_reference_must_stay_open(self):
        u, m, i = docs()
        b = binding(u, m, i)
        b["boundaries"]["unresolved_owner_reference_stays_open"] = False
        out = cert.certify(u, m, i, b)
        self.assertFalse(out["pass"])
        self.assertIn("UNRESOLVED_OWNER_REFERENCE_BOUNDARY_MISSING", out["errors"])

    def test_source_digest_drift_fails_closed(self):
        u, m, i = docs()
        b = binding(u, m, i)
        b["information_cut_sha256"] = "0" * 64
        out = cert.certify(u, m, i, b)
        self.assertFalse(out["pass"])
        self.assertIn("INFO_CUT_DIGEST_MISMATCH", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
