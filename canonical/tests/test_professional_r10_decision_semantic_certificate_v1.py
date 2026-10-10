from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r10_decision_semantic_certificate_v1 as cert

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"canonical/verification/PROFESSIONAL_QUALITY_R10_DECISION_SUFFICIENCY_SCOPED_VERIFY_20261010_V1.json"
HISTORY=ROOT/"canonical/verification/ONE_SHOT_DECISION_SUFFICIENT_GATE_VERIFY_20261009_V2.json"


def source():
    return json.loads(SOURCE.read_text())


def history():
    return json.loads(HISTORY.read_text())


def binding(s,h):
    return {
        "source_sha256":cert.digest(s),
        "history_sha256":cert.digest(h),
        "semantic_claim":{
            "baseline_representation":"LOSSLESS_IDENTITY_CONTENT_ADDRESSED",
            "omission_rule":"INDEPENDENT_OMISSION_CERTIFICATE_REQUIRED",
            "information_rule":"MINIMUM_POLICY_CHANGING_INFORMATION_FIRST",
            "broad_acquisition_rule":"FORBIDDEN_WITHOUT_MINIMALITY_PROOF",
            "empirical_evaluation_position":"LAST",
            "provider_verification_authority_mutation":False,
            "unchanged_frontier_progress":"FAIL_CLOSED",
        },
        "hard_nonclaims":[
            "NO_GENERAL_PROFESSIONAL_RISK_POLICY_CLOSURE",
            "NO_NORMATIVE_AGGREGATION_CLOSURE",
            "NO_MODEL_MULTIPLICITY_DECISION_CLOSURE",
            "NO_GENERAL_SEMANTIC_COMPRESSION_CLAIM",
            "NO_GLOBAL_R10_LEAF_OR_ROOT_CLOSURE",
        ],
    }


class ProfessionalR10DecisionSemanticCertificateV1Tests(unittest.TestCase):
    def test_exact_decision_semantics_pass_bounded(self):
        s,h=source(),history()
        out=cert.certify(s,h,binding(s,h))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["claim_scope"]["kind"],"LOSSLESS_MINIMUM_INFORMATION_DECISION_SUFFICIENCY_SEMANTICS")
        self.assertFalse(out["semantic_leaf_credit"])
        self.assertFalse(out["terminal_authority"])

    def test_source_drift_fails_closed(self):
        s,h=source(),history()
        b=binding(s,h)
        b["source_sha256"]="0"*64
        out=cert.certify(s,h,b)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_DIGEST_MISMATCH",out["errors"])

    def test_omission_without_certificate_semantics_fail(self):
        s,h=source(),history()
        b=binding(s,h)
        b["semantic_claim"]["omission_rule"]="OPTIONAL"
        out=cert.certify(s,h,b)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_POLICY_INVALID:omission_rule",out["errors"])

    def test_broad_acquisition_without_minimality_fails(self):
        s,h=source(),history()
        b=binding(s,h)
        b["semantic_claim"]["broad_acquisition_rule"]="ALLOWED"
        out=cert.certify(s,h,b)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_POLICY_INVALID:broad_acquisition_rule",out["errors"])

    def test_provider_authority_mutation_fails(self):
        s,h=source(),history()
        b=binding(s,h)
        b["semantic_claim"]["provider_verification_authority_mutation"]=True
        out=cert.certify(s,h,b)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_POLICY_INVALID:provider_verification_authority_mutation",out["errors"])

    def test_false_progress_must_fail_closed(self):
        s,h=source(),history()
        b=binding(s,h)
        b["semantic_claim"]["unchanged_frontier_progress"]="PASS"
        out=cert.certify(s,h,b)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_POLICY_INVALID:unchanged_frontier_progress",out["errors"])


if __name__=="__main__":
    unittest.main()
