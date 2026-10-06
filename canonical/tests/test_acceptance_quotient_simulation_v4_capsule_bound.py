from __future__ import annotations

import copy
import unittest

from canonical.runtime.acceptance_cutpoint_capsule_quotient_v1 import (
    compile_brain_cutpoint,
)
from canonical.runtime.acceptance_quotient_simulation_v4_capsule_bound import (
    verify_acceptance_quotient_certificate_v4,
)
from canonical.runtime.composition_state_capsule_v2 import (
    append_macrostep,
    empty_capsule,
)


CHANNEL = {
    "path": "canonical/verification/channel-mincut.json",
    "git_blob_sha": "f" * 40,
    "scope_complete": True,
    "cross_role_state_edges_capsule_dominated": True,
    "acceptance_relevant_evidence_edges_capsule_dominated": True,
    "unknown_dynamic_edges_fail_closed": True,
    "exact_runtime_identity_bound": True,
    "independent_or_objective": True,
}


def receipt(seed: str, **truths):
    return {
        "path": f"canonical/verification/{seed}.json",
        "git_blob_sha": (seed[0] if seed else "a") * 40,
        **truths,
    }


def cutpoint(capsule, terminal):
    return compile_brain_cutpoint(
        capsule=capsule,
        acceptance_facts={"quality_floor_met": True},
        scope_authority_facts={"authorized": True, "scope": "terminal"},
        terminal_facts={"terminal": terminal},
        channel_receipt=CHANNEL,
    )


def cap1():
    return append_macrostep(
        empty_capsule(),
        producer_ref="worker-a",
        producer_descriptor={"worker_id": "worker-a", "role": "research"},
        action_ref="act:1",
        action_descriptor={"tool": "planner", "args": {"step": 1}},
        requires=[],
        provides=["state"],
        values={"state": {"progress": 1}},
        evidence_values={},
        lineage={"state": ["action:act:1", "producer:worker-a"]},
    )


def base():
    scope = receipt(
        "s",
        invariant_holds=True,
        scope_complete=True,
        universal_over_realizations=True,
        independent_or_objective=True,
    )
    edge_policy = receipt(
        "p",
        induced_by_bound_policy=True,
        choice_uses_current_or_past_information_only=True,
        no_target_edge_or_future_branch_oracle=True,
        scope_complete=True,
        independent_or_objective=True,
    )
    cert = {
        "target_states": ["T0", "T1"],
        "brain_states": ["B0", "B1"],
        "initial_target_states": ["T0"],
        "initial_brain_states": ["B0"],
        "terminal_target_states": ["T1"],
        "terminal_brain_states": ["B1"],
        "relation": [["T0", "B0"], ["T1", "B1"]],
        "target_cut_edges": [{"id": "E", "from": "T0", "to": "T1"}],
        "brain_macro_edges": [{
            "from": "B0",
            "to": "B1",
            "covers_target_edge_ids": ["E"],
            "scope_authority_receipt": scope,
            "scope_authority_invariant": False,
            "causal_policy_binding_receipt": edge_policy,
            "realizability_receipt": receipt(
                "r",
                scope_complete=True,
                universal_from_abstract_class=True,
                independent_or_objective=True,
            ),
        }],
        "abstraction_receipt": receipt(
            "a",
            acceptance_complete=True,
            load_bearing_observations_complete=True,
            target_conservative_coverage=True,
            independent_or_objective=True,
        ),
        "relation_soundness_receipt": receipt(
            "q",
            acceptance_preorder_sound=True,
            load_bearing_dimensions_complete=True,
            scope_complete=True,
            independent_or_objective=True,
        ),
        "terminal_acceptance_receipt": receipt(
            "t",
            terminal_noninferiority_sound=True,
            scope_complete=True,
            independent_or_objective=True,
        ),
        "causal_strategy_receipt": receipt(
            "c",
            single_owned_policy=True,
            complete_on_claimed_domain=True,
            history_adapted=True,
            no_future_or_target_oracle=True,
            existential_matches_induced_by_policy=True,
            independent_or_objective=True,
        ),
    }
    cert["brain_cutpoints"] = {
        "B0": cutpoint(empty_capsule(), False),
        "B1": cutpoint(cap1(), True),
    }
    return cert


class Tests(unittest.TestCase):
    def test_pass_when_every_brain_state_has_full_capsule_cutpoint(self):
        verdict = verify_acceptance_quotient_certificate_v4(base())
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertTrue(verdict["full_capsule_retained_at_every_brain_quotient_state"])
        self.assertEqual(verdict["brain_cutpoint_count"], 2)

    def test_missing_brain_cutpoint_fails_closed(self):
        cert = base()
        cert["brain_cutpoints"].pop("B1")
        verdict = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("BRAIN_CUTPOINT_COVERAGE_MISMATCH", verdict["reason"])

    def test_extra_brain_cutpoint_fails_closed(self):
        cert = base()
        cert["brain_cutpoints"]["BX"] = copy.deepcopy(cert["brain_cutpoints"]["B0"])
        verdict = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("BRAIN_CUTPOINT_COVERAGE_MISMATCH", verdict["reason"])

    def test_tampered_cutpoint_fails_closed(self):
        cert = base()
        cert["brain_cutpoints"]["B1"]["quotient"]["composition_capsule_v2"][
            "records"
        ][0]["values"]["state"]["progress"] = 999
        verdict = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("BRAIN_CUTPOINT_INVALID", verdict["reason"])

    def test_channel_receipt_must_be_uniform_across_brain_states(self):
        cert = base()
        other = copy.deepcopy(CHANNEL)
        other["git_blob_sha"] = "e" * 40
        cert["brain_cutpoints"]["B1"] = compile_brain_cutpoint(
            capsule=cap1(),
            acceptance_facts={"quality_floor_met": True},
            scope_authority_facts={"authorized": True, "scope": "terminal"},
            terminal_facts={"terminal": True},
            channel_receipt=other,
        )
        verdict = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("CHANNEL_RECEIPT_BINDING_DRIFT", verdict["reason"])

    def test_v3_causal_strategy_failure_still_fails(self):
        cert = base()
        cert["causal_strategy_receipt"]["history_adapted"] = False
        verdict = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("V3_SEMANTIC_CAUSAL_CHECK_FAILED", verdict["reason"])

    def test_v3_semantic_relation_failure_still_fails(self):
        cert = base()
        cert["relation_soundness_receipt"]["acceptance_preorder_sound"] = False
        verdict = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("V3_SEMANTIC_CAUSAL_CHECK_FAILED", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
