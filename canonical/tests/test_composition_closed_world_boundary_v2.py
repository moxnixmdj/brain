from __future__ import annotations

import copy
import hashlib
import pathlib
import tempfile
import unittest

from canonical.runtime.composition_closed_world_boundary_v2 import (
    SCHEMA,
    verify_closed_world_boundary,
    verify_repository_bound_closed_world_boundary,
)


def _receipt(name, fields):
    return {
        "path": f"canonical/verification/{name}.json",
        "git_blob_sha": "0123456789abcdef0123456789abcdef01234567",
        **{field: True for field in fields},
    }


def base():
    return {
        "schema": SCHEMA,
        "frozen_scope_receipt": _receipt(
            "scope",
            (
                "scope_complete_for_frozen_composition_claim",
                "independent_or_objective",
            ),
        ),
        "ephemeral_confinement_receipt": _receipt(
            "confinement",
            (
                "fresh_child_domain_per_macrostep",
                "child_destroyed_before_next_macrostep",
                "no_parent_mutable_state_injection_except_declared_boundary",
                "workspace_overlay_discarded_or_exported_through_boundary",
                "process_tree_reaped_before_boundary_commit",
                "browser_profile_ephemeral_or_exported_through_boundary",
                "independent_or_objective",
                "scope_complete",
            ),
        ),
        "capsule_mediation_receipt": _receipt(
            "capsule",
            (
                "all_cross_role_state_and_evidence_exports_content_bound",
                "all_later_role_state_reads_projected_from_capsule",
                "capsule_head_checked_on_resume",
                "no_raw_prior_result_channel",
                "independent_or_objective",
                "scope_complete",
            ),
        ),
        "effect_broker_carrier_receipt": _receipt(
            "broker",
            (
                "all_external_information_reads_are_content_bound_or_brokered",
                "all_external_mutations_are_brokered",
                "all_host_persistent_effects_are_brokered",
                "grant_bound_to_exact_capsule_head_and_request",
                "carrier_enforces_deny_by_default",
                "receipt_bytes_verified_before_allow",
                "independent_or_objective",
                "scope_complete",
            ),
        ),
        "rollback_receipt": _receipt(
            "rollback",
            (
                "rollback_restores_exact_capsule_prefix",
                "rollback_discards_current_child_domain",
                "rollback_leaves_no_unbrokered_persistent_effect",
                "resume_requires_revalidated_capsule_head",
                "independent_or_objective",
                "scope_complete",
            ),
        ),
        "allowed_cross_macrostep_channels": [
            "COMPOSITION_STATE_CAPSULE_V2_OR_STRONGER",
            "PROOF_CARRYING_EFFECT_BROKER",
        ],
        "forbidden_parallel_channels": [
            "RAW_PRIOR_STEP_RESULT_INJECTION",
            "SHARED_MUTABLE_WORKSPACE_OUTSIDE_BROKER",
            "PERSISTENT_CHILD_PROCESS_STATE",
            "PERSISTENT_BROWSER_PROFILE_OUTSIDE_BOUNDARY",
            "UNBROKERED_NETWORK_OR_EXTERNAL_MUTATION",
            "UNCONTENT_ADDRESSED_EXTERNAL_INFORMATION_INPUT",
        ],
    }


class Tests(unittest.TestCase):
    def test_complete_two_channel_certificate_passes(self):
        out = verify_closed_world_boundary(base())
        self.assertEqual(out["status"], "PASS", out)
        self.assertTrue(out["c1_closed_world_capsule_mediation_totality"])
        self.assertFalse(out["ambient_internal_channel_enumeration_required"])

    def test_raw_prior_result_channel_fails(self):
        cert = base()
        cert["capsule_mediation_receipt"]["no_raw_prior_result_channel"] = False
        out = verify_closed_world_boundary(cert)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("NO_RAW_PRIOR_RESULT_CHANNEL_NOT_TRUE", out["reason"])

    def test_persistent_workspace_without_boundary_fails(self):
        cert = base()
        cert["ephemeral_confinement_receipt"][
            "workspace_overlay_discarded_or_exported_through_boundary"
        ] = False
        self.assertEqual(
            verify_closed_world_boundary(cert)["status"],
            "FAIL_CLOSED",
        )

    def test_persistent_process_tree_fails(self):
        cert = base()
        cert["ephemeral_confinement_receipt"][
            "process_tree_reaped_before_boundary_commit"
        ] = False
        self.assertEqual(
            verify_closed_world_boundary(cert)["status"],
            "FAIL_CLOSED",
        )

    def test_browser_profile_escape_fails(self):
        cert = base()
        cert["ephemeral_confinement_receipt"][
            "browser_profile_ephemeral_or_exported_through_boundary"
        ] = False
        self.assertEqual(
            verify_closed_world_boundary(cert)["status"],
            "FAIL_CLOSED",
        )

    def test_unbrokered_external_mutation_fails(self):
        cert = base()
        cert["effect_broker_carrier_receipt"][
            "all_external_mutations_are_brokered"
        ] = False
        self.assertEqual(
            verify_closed_world_boundary(cert)["status"],
            "FAIL_CLOSED",
        )

    def test_precommit_without_carrier_enforcement_fails(self):
        cert = base()
        cert["effect_broker_carrier_receipt"][
            "carrier_enforces_deny_by_default"
        ] = False
        out = verify_closed_world_boundary(cert)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("CARRIER_ENFORCES_DENY_BY_DEFAULT_NOT_TRUE", out["reason"])

    def test_broker_receipt_bytes_must_be_verified(self):
        cert = base()
        cert["effect_broker_carrier_receipt"][
            "receipt_bytes_verified_before_allow"
        ] = False
        self.assertEqual(
            verify_closed_world_boundary(cert)["status"],
            "FAIL_CLOSED",
        )

    def test_rollback_must_discard_child_domain(self):
        cert = base()
        cert["rollback_receipt"]["rollback_discards_current_child_domain"] = False
        self.assertEqual(
            verify_closed_world_boundary(cert)["status"],
            "FAIL_CLOSED",
        )

    def test_scope_completeness_is_load_bearing(self):
        cert = base()
        cert["frozen_scope_receipt"][
            "scope_complete_for_frozen_composition_claim"
        ] = False
        self.assertEqual(
            verify_closed_world_boundary(cert)["status"],
            "FAIL_CLOSED",
        )

    def test_third_cross_macrostep_channel_fails(self):
        cert = base()
        cert["allowed_cross_macrostep_channels"].append("RAW_SHELL_ENVIRONMENT")
        out = verify_closed_world_boundary(cert)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("EXACT_TWO_CHANNEL_CUT", out["reason"])

    def test_missing_forbidden_channel_class_fails(self):
        cert = base()
        cert["forbidden_parallel_channels"].remove(
            "PERSISTENT_BROWSER_PROFILE_OUTSIDE_BOUNDARY"
        )
        self.assertEqual(
            verify_closed_world_boundary(cert)["status"],
            "FAIL_CLOSED",
        )

    def test_unbound_receipt_fields_fail(self):
        cert = base()
        cert["capsule_mediation_receipt"]["self_certified"] = True
        out = verify_closed_world_boundary(cert)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("UNBOUND_FIELDS", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
