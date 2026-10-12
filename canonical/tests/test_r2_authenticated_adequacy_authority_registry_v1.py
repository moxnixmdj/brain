from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r2_authenticated_adequacy_authority_registry_v1 as reg


class AuthenticatedAdequacyAuthorityRegistryV1Tests(unittest.TestCase):
    def test_p2_self_authenticated_match_is_admitted(self):
        p2 = {
            "pass": True,
            "status": "PASS__AUTHENTICATED_P2_TOP_LAW_POLICY_SELECTED",
            "raw_source_sha256": reg.sha256(b"x").hexdigest(),
            "policy_id": "p2.policy",
            "policy_adequacy": {
                "pass": True,
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
                "membership_recognizer_git_blob_sha": "a" * 40,
            },
            "policy_result": {"selected_edits": ["e1"], "terminal_authority": False},
            "terminal_authority": False,
        }
        with patch.object(reg, "execute_p2_top_law", return_value=p2), \
             patch.object(reg, "compile_p3_binary_membership", return_value={"pass": False}):
            out = reg.discover("x", source_id="user")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["authority_id"], reg.P2_AUTHORITY_ID)
        self.assertEqual(out["policy_id"], "p2.policy")
        self.assertTrue(out["selected_policy_adequacy_verified"])
        self.assertFalse(out["actual_goal_satisfaction_verified"])
        self.assertFalse(out["terminal_authority"])

    def test_p3_strict_binary_match_requires_region_verification(self):
        policy = {
            "pass": True,
            "rendered_text": "Decision result",
            "bound_cell_required_decision_coverage_complete": True,
            "decision_expression_covered": True,
            "policy_adequacy_authority": False,
            "terminal_authority": False,
        }
        membership = {
            "pass": True,
            "raw_source_sha256": reg.sha256(b"x").hexdigest(),
            "selected_class_membership_authenticated": True,
            "membership_self_assertion_permitted": False,
            "policy_receipt": policy,
        }
        region = {
            "pass": True,
            "parameterized_D_B_region_candidate": True,
            "terminal": False,
            "terminal_credit_delta": 0,
        }
        with patch.object(reg, "execute_p2_top_law", return_value={"pass": False}), \
             patch.object(reg, "compile_p3_binary_membership", return_value=membership), \
             patch.object(reg, "verify_p3_binary_region", return_value=region):
            out = reg.discover("x", source_id="user")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["authority_id"], reg.P3_BINARY_AUTHORITY_ID)
        self.assertEqual(out["policy_id"], reg.P3_BINARY_POLICY_ID)
        self.assertEqual(out["realization"]["rendered_text"], "Decision result")

    def test_p3_membership_alone_cannot_mint_adequacy(self):
        membership = {
            "pass": True,
            "raw_source_sha256": reg.sha256(b"x").hexdigest(),
            "selected_class_membership_authenticated": True,
            "membership_self_assertion_permitted": False,
            "policy_receipt": {
                "pass": True,
                "rendered_text": "Decision result",
                "bound_cell_required_decision_coverage_complete": True,
                "decision_expression_covered": True,
                "policy_adequacy_authority": False,
                "terminal_authority": False,
            },
        }
        with patch.object(reg, "execute_p2_top_law", return_value={"pass": False}), \
             patch.object(reg, "compile_p3_binary_membership", return_value=membership), \
             patch.object(reg, "verify_p3_binary_region", return_value={"pass": False}):
            out = reg.discover("x", source_id="user")
        self.assertFalse(out["pass"])
        self.assertFalse(out["policy_selection_authorized"])

    def test_no_match_is_unresolved_not_negative_impossibility(self):
        with patch.object(reg, "execute_p2_top_law", return_value={"pass": False}), \
             patch.object(reg, "compile_p3_binary_membership", return_value={"pass": False}):
            out = reg.discover("ordinary free form goal", source_id="user")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_SELF_AUTHENTICATING_ADEQUACY_AUTHORITY_MATCHED",
        )
        self.assertNotIn("no adequate policy exists", str(out).lower())

    def test_multiple_matching_authorities_fail_closed(self):
        source_sha = reg.sha256(b"x").hexdigest()
        p2 = {
            "pass": True,
            "raw_source_sha256": source_sha,
            "policy_id": "p2",
            "policy_adequacy": {
                "pass": True,
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
                "membership_recognizer_git_blob_sha": "a" * 40,
            },
            "policy_result": {"terminal_authority": False},
            "terminal_authority": False,
        }
        membership = {
            "pass": True,
            "raw_source_sha256": source_sha,
            "selected_class_membership_authenticated": True,
            "membership_self_assertion_permitted": False,
            "policy_receipt": {
                "pass": True,
                "rendered_text": "r",
                "bound_cell_required_decision_coverage_complete": True,
                "decision_expression_covered": True,
                "policy_adequacy_authority": False,
                "terminal_authority": False,
            },
        }
        region = {
            "pass": True,
            "parameterized_D_B_region_candidate": True,
            "terminal": False,
            "terminal_credit_delta": 0,
        }
        with patch.object(reg, "execute_p2_top_law", return_value=p2), \
             patch.object(reg, "compile_p3_binary_membership", return_value=membership), \
             patch.object(reg, "verify_p3_binary_region", return_value=region):
            out = reg.discover("x", source_id="user")
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "MULTIPLE_SELF_AUTHENTICATING_ADEQUACY_AUTHORITIES_MATCHED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
