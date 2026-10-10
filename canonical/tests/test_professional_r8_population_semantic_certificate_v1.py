from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r8_population_semantic_certificate_v1 as cert

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"canonical/verification/DELEGATION_TERMINAL_POPULATION_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"


def source():
    return json.loads(SOURCE.read_text())


def binding(s):
    return {
        "source_sha256":cert.digest(s),
        "semantic_claim":{
            "behavior_id":"TASK_TO_DELEGATION_GRAPH_001",
            "route_population_version":"DELEGATION_WHOLE_SCOPE_TERMINAL_POP_V1",
            "sample_count":512,
            "slot_generation":"DETERMINISTIC_COMMITMENT_BEACON_INDEX_DERIVATION",
            "required_case_classes":sorted(cert.REQUIRED_CLASSES),
            "acceptance_rule":"ALL_512_CASES_EXACT_PASS_AND_ALL_SIX_FROZEN_DELEGATION_CASE_CLASSES_PRESENT",
            "case_replacement":False,
            "adaptive_case_selection":False,
            "replay_for_tuning":False,
            "post_freeze_terminal_result_claimed":False,
        },
        "hard_nonclaims":[
            "NO_CONSTITUENCY_SUPPORT_CLAIM",
            "NO_PRESENTER_OR_OPERATOR_GENERALIZATION",
            "NO_MEASUREMENT_INVARIANCE_CLAIM",
            "NO_SOCIAL_INFLUENCE_OR_REACTIVITY_CLOSURE",
            "NO_GLOBAL_R8_SEMANTIC_LEAF_CLOSURE",
            "NO_GLOBAL_R8_ROOT_CLOSURE",
        ],
    }


class ProfessionalR8PopulationSemanticCertificateV1Tests(unittest.TestCase):
    def test_exact_frozen_population_semantics_pass_bounded(self):
        s=source()
        out=cert.certify(s,binding(s))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["claim_scope"]["kind"],"FROZEN_512_CASE_DELEGATION_POPULATION_SEMANTICS")
        self.assertFalse(out["semantic_leaf_credit"])
        self.assertFalse(out["terminal_authority"])

    def test_population_size_drift_fails(self):
        s=source()
        b=binding(s)
        b["semantic_claim"]["sample_count"]=511
        out=cert.certify(s,b)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_POLICY_INVALID:sample_count",out["errors"])

    def test_missing_case_class_fails(self):
        s=source()
        b=binding(s)
        b["semantic_claim"]["required_case_classes"]=sorted(cert.REQUIRED_CLASSES-{"RESOURCE_CONFLICT"})
        out=cert.certify(s,b)
        self.assertFalse(out["pass"])
        self.assertIn("REQUIRED_CASE_CLASSES_INVALID",out["errors"])

    def test_adaptive_selection_overclaim_fails(self):
        s=source()
        b=binding(s)
        b["semantic_claim"]["adaptive_case_selection"]=True
        out=cert.certify(s,b)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_POLICY_INVALID:adaptive_case_selection",out["errors"])

    def test_terminal_result_overclaim_fails(self):
        s=source()
        b=binding(s)
        b["semantic_claim"]["post_freeze_terminal_result_claimed"]=True
        out=cert.certify(s,b)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_POLICY_INVALID:post_freeze_terminal_result_claimed",out["errors"])

    def test_source_drift_fails(self):
        s=source()
        b=binding(s)
        b["source_sha256"]="0"*64
        out=cert.certify(s,b)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_DIGEST_MISMATCH",out["errors"])


if __name__=="__main__":
    unittest.main()
