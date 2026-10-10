from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime import professional_target_semantic_certificate_v1 as cert

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json"


def contract():
    data=json.loads(REGISTRY.read_text())
    for row in data["active_contracted_residuals"]:
        if row.get("behavior_id")==cert.BEHAVIOR_ID:
            return row
    raise AssertionError("target behavior missing")


def binding(c):
    roles={
        "objective":"required_output_or_action",
        "audience":"inputs",
        "hard_constraints":"allowed_information",
        "success_semantics":"success_condition",
        "failure_semantics":"failure_condition",
        "target_construct":"success_condition",
        "claim_scope":"scope",
        "evidence_boundary":"dependency_boundary",
    }
    return {
        "behavior_id":cert.BEHAVIOR_ID,
        "contract_sha256":cert.digest(c),
        "role_bindings":{
            role:{
                "source_field":field,
                "source_value_sha256":cert.digest(c[field]),
            }
            for role,field in roles.items()
        },
        "ambiguity_policy":{
            "unique_optimum_claimed":False,
            "admissible_plan_definition":"ANY_PLAN_SATISFYING_SUCCESS_AND_AVOIDING_FAILURE_WITHIN_DECLARED_SCOPE",
            "unresolved_runtime_task_ambiguity_must_remain_open":True,
        },
        "hard_nonclaims":[
            "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
            "NO_SOURCE_EXTRACTION_COMPLETENESS",
            "NO_UNIQUE_BEST_PLAN",
            "NO_GLOBAL_R1_SEMANTIC_LEAF_CLOSURE",
            "NO_GLOBAL_R1_ROOT_CLOSURE",
        ],
    }


class ProfessionalTargetSemanticCertificateV1Tests(unittest.TestCase):
    def test_exact_canonical_behavior_binds_bounded_target_semantics(self):
        c=contract()
        out=cert.certify(c,binding(c))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["claim_scope"]["kind"],"EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS")
        self.assertFalse(out["global_leaf_closure"])
        self.assertFalse(out["semantic_leaf_credit"])
        self.assertFalse(out["terminal_authority"])

    def test_missing_audience_parameter_fails_closed(self):
        c=dict(contract())
        c["inputs"]=c["inputs"].replace("audience","recipient")
        b=binding(c)
        out=cert.certify(c,b)
        self.assertFalse(out["pass"])
        self.assertIn("TARGET_PARAMETER_ANCHOR_MISSING:audience",out["errors"])

    def test_contract_drift_fails_content_binding(self):
        c=contract()
        b=binding(c)
        b["contract_sha256"]="0"*64
        out=cert.certify(c,b)
        self.assertFalse(out["pass"])
        self.assertIn("CONTRACT_DIGEST_MISMATCH",out["errors"])

    def test_unique_optimum_overclaim_fails_closed(self):
        c=contract()
        b=binding(c)
        b["ambiguity_policy"]["unique_optimum_claimed"]=True
        out=cert.certify(c,b)
        self.assertFalse(out["pass"])
        self.assertIn("UNIQUE_OPTIMUM_OVERCLAIM",out["errors"])

    def test_role_remap_to_wrong_field_fails_closed(self):
        c=contract()
        b=binding(c)
        b["role_bindings"]["claim_scope"]["source_field"]="success_condition"
        out=cert.certify(c,b)
        self.assertFalse(out["pass"])
        self.assertIn("ROLE_SOURCE_FIELD_INVALID:claim_scope",out["errors"])


if __name__=="__main__":
    unittest.main()
