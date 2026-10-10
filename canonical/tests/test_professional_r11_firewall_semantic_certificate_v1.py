from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r11_firewall_semantic_certificate_v1 as cert

ROOT=Path(__file__).resolve().parents[2]
GOV=ROOT/"canonical/governance/EVALUATION_INFORMATION_FIREWALL_V1.json"


def governance():
    return json.loads(GOV.read_text())


def binding(g):
    return {
        "governance_sha256":cert.digest(g),
        "semantic_claim":{
            "scope":"SAME_CLEAN_EVALUATION_LANE_AFTER_TASK_IDENTITY_EXPOSURE",
            "discovery_capabilities_revoked":True,
            "revocation_monotonic":True,
            "unknown_capability_disposition":"DENY_FAIL_CLOSED",
            "new_lane_semantics_claimed":False,
        },
        "hard_nonclaims":[
            "NO_GENERAL_PROMPT_INJECTION_CLOSURE",
            "NO_GENERAL_GOODHART_CLOSURE",
            "NO_HOLDOUT_LIFECYCLE_CLOSURE",
            "NO_GLOBAL_R11_SEMANTIC_LEAF_CLOSURE",
            "NO_GLOBAL_R11_ROOT_CLOSURE",
        ],
    }


class ProfessionalR11FirewallSemanticCertificateV1Tests(unittest.TestCase):
    def test_exact_policy_semantics_pass_bounded(self):
        g=governance()
        out=cert.certify(g,binding(g))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["claim_scope"]["kind"],"CLEAN_EVALUATION_LANE_POST_IDENTITY_REVOCATION_SEMANTICS")
        self.assertFalse(out["semantic_leaf_credit"])
        self.assertFalse(out["terminal_authority"])

    def test_missing_monotonic_rule_fails_closed(self):
        g=governance()
        g["hard_rules"].remove("TASK_IDENTITY_EXPOSURE_IS_MONOTONIC_WITHIN_A_LANE")
        out=cert.certify(g,binding(g))
        self.assertFalse(out["pass"])
        self.assertIn("REQUIRED_FIREWALL_RULES_MISSING",out["errors"])

    def test_allow_revoke_overlap_fails_closed(self):
        g=governance()
        g["post_identity_allowlist"].append("REPO_SEARCH")
        out=cert.certify(g,binding(g))
        self.assertFalse(out["pass"])
        self.assertIn("ALLOW_REVOKE_SETS_OVERLAP",out["errors"])

    def test_unknown_capability_must_fail_closed(self):
        g=governance()
        b=binding(g)
        b["semantic_claim"]["unknown_capability_disposition"]="ALLOW"
        out=cert.certify(g,b)
        self.assertFalse(out["pass"])
        self.assertIn("UNKNOWN_CAPABILITY_SEMANTICS_INVALID",out["errors"])

    def test_cross_lane_overclaim_fails(self):
        g=governance()
        b=binding(g)
        b["semantic_claim"]["new_lane_semantics_claimed"]=True
        out=cert.certify(g,b)
        self.assertFalse(out["pass"])
        self.assertIn("CROSS_LANE_OVERCLAIM",out["errors"])

    def test_governance_drift_fails_content_binding(self):
        g=governance()
        b=binding(g)
        b["governance_sha256"]="0"*64
        out=cert.certify(g,b)
        self.assertFalse(out["pass"])
        self.assertIn("GOVERNANCE_DIGEST_MISMATCH",out["errors"])


if __name__=="__main__":
    unittest.main()
