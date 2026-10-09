import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
V49_PATH = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V49.json"
V50_PATH = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V50.json"
CURRENT_R2_PATH = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
CURRENT_TERMINAL_PATH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
BASEL_RECONCILIATION_PATH = ROOT / "canonical/governance/FIBO_Q2_2026_BASEL_DESIGNATION_AUTHORITY_RECONCILIATION_20261009_V1.json"
BASEL_VERIFY_PATH = ROOT / "canonical/verification/FIBO_Q2_2026_BASEL_DESIGNATION_AUTHORITY_VERIFY_20261009_V1.json"

V49_BLOB = "bb7df134a969d52dfee603c8ea16b9653ab11eba"
BASEL_RUNTIME_BLOB = "f30b189d68d500042aaed28f6cd4ae5279daecf4"
BASEL_EVIDENCE_BLOB = "ae11a0ddca613b25b7df37b1a3f99ade0836f6ee"
BASEL_VERIFY_BLOB = "101ae642a20adff27c4ac956caf79d83a3ab46fa"
BASEL_RECONCILIATION_BLOB = "fc3c11720b35a4de56430b66cd1f1b1c24e36f5f"

OLD_WAKE = "NEW_CONTENT_ADDRESSED_COMPLETE_FINANCE_SOURCE_OR_CONVENTION_SCOPE_BOUND_OUTSIDE_VERIFIED_FIBO_Q2_2026_CORE7_SCOPE"
NEW_WAKE = "NEW_CONTENT_ADDRESSED_COMPLETE_FINANCE_SOURCE_OR_CONVENTION_SCOPE_BOUND_OUTSIDE_VERIFIED_FIBO_Q2_2026_CORE7_AND_BASEL_III_DESIGNATION_FRAGMENT_SCOPES"
BASEL_REGION_ID = "FIBO_Q2_2026_BASEL_III_DESIGNATION_SOURCE_AUTHORITY_AND_EXPLICIT_TYPE_MEMBERSHIP"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class Tests(unittest.TestCase):
    def test_v50_is_monotone_scope_refinement_of_v49(self):
        prior = load(V49_PATH)
        cur = load(V50_PATH)

        self.assertEqual(
            cur["schema"],
            "PROJECT_BRAIN_ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V50",
        )
        self.assertEqual(
            cur["supersedes"],
            {
                "path": "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V49.json",
                "git_blob_sha": V49_BLOB,
                "reason": "BIND_VERIFIED_PINNED_FIBO_BASEL_III_DESIGNATION_SOURCE_AUTHORITY__REFINE_ONLY_THE_GENERIC_UNBOUND_FINANCE_SOURCE_WAKE_SCOPE",
            },
        )

        old_fin = prior["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        fin = cur["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertIn(OLD_WAKE, old_fin["wake_on"])
        self.assertNotIn(OLD_WAKE, fin["wake_on"])
        self.assertIn(NEW_WAKE, fin["wake_on"])

        self.assertEqual(
            cur["reconciliation"]["activation_route_count"],
            prior["reconciliation"]["activation_route_count"],
        )
        self.assertEqual(
            cur["reconciliation"]["activation_bounded_family_count"],
            prior["reconciliation"]["activation_bounded_family_count"],
        )
        self.assertEqual(
            cur["scheduler_result"]["direct_route_count"],
            prior["scheduler_result"]["direct_route_count"],
        )
        self.assertEqual(
            cur["scheduler_result"]["bounded_family_count"],
            prior["scheduler_result"]["bounded_family_count"],
        )
        self.assertEqual(
            cur["scheduler_result"]["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"],
            1,
        )
        self.assertEqual(cur["accounting"]["terminal_credit_delta"], 0)

    def test_v50_binds_only_verified_basel_scope_and_preserves_open_world_boundary(self):
        cur = load(V50_PATH)
        fin = cur["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]

        region = next(
            x for x in fin["verified_positive_subregions"]
            if x["id"] == BASEL_REGION_ID
        )
        self.assertEqual(
            region["verification"],
            "canonical/verification/FIBO_Q2_2026_BASEL_DESIGNATION_AUTHORITY_VERIFY_20261009_V1.json",
        )
        self.assertFalse(region["direct_adequacy_route"])
        self.assertFalse(region["contextual_identity_from_label_or_abbreviation"])
        self.assertFalse(region["open_world_ontology_complete"])
        self.assertFalse(region["policy_adequacy_authority"])

        self.assertIn(
            "REUSE_PINNED_FIBO_Q2_2026_BASEL_III_DESIGNATION_SOURCE_AUTHORITY",
            fin["required_action"],
        )
        self.assertIn(
            "OPEN_WORLD_ONTOLOGY_MAPPING_WITHOUT_AUTHENTICATED_BOUNDED_AUTHORITY",
            fin["remaining_boundary"],
        )

        satisfied = next(
            x for x in fin["satisfied_wake_conditions"]
            if x["condition"] == "NEW_CONTENT_ADDRESSED_COMPLETE_FINANCE_SOURCE_OR_CONVENTION_SCOPE_BOUND"
        )
        self.assertEqual(
            satisfied["status"],
            "SATISFIED__BOUNDED_FIBO_Q2_2026_CORE7_PLUS_BASEL_III_DESIGNATION_FRAGMENT_SCOPES__GENERIC_WAKE_REFINED_NOT_GLOBALLY_DELETED",
        )
        self.assertEqual(
            satisfied["basel_designation_runtime_git_blob_sha"],
            BASEL_RUNTIME_BLOB,
        )
        self.assertEqual(
            satisfied["basel_designation_evidence_git_blob_sha"],
            BASEL_EVIDENCE_BLOB,
        )
        self.assertEqual(
            satisfied["basel_designation_verification_git_blob_sha"],
            BASEL_VERIFY_BLOB,
        )
        self.assertFalse(satisfied["global_finance_semantic_tail_closed"])

    def test_current_r2_binds_exact_v50_and_basel_authority(self):
        cur = load(V50_PATH)
        r2 = load(CURRENT_R2_PATH)
        v50_blob = git_blob_sha(V50_PATH)

        self.assertIn("__V50__", r2["status"])
        self.assertEqual(
            r2["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V50.json",
        )
        self.assertEqual(r2["scheduler_cut"]["git_blob_sha"], v50_blob)
        self.assertEqual(
            r2["current_cell_classifications"],
            cur["current_cell_classifications"],
        )
        self.assertEqual(r2["scheduler_result"], cur["scheduler_result"])

        frontier = r2["fibo_q2_2026_basel_designation_authority_frontier"]
        self.assertEqual(frontier["runtime_git_blob_sha"], BASEL_RUNTIME_BLOB)
        self.assertEqual(frontier["evidence_git_blob_sha"], BASEL_EVIDENCE_BLOB)
        self.assertEqual(frontier["verification_git_blob_sha"], BASEL_VERIFY_BLOB)
        self.assertEqual(
            frontier["reconciliation_git_blob_sha"],
            BASEL_RECONCILIATION_BLOB,
        )
        self.assertFalse(frontier["contextual_identity_from_label_or_abbreviation"])
        self.assertFalse(frontier["open_world_finance_ontology_complete"])
        self.assertEqual(frontier["terminal_credit_delta"], 0)

        recon = r2["r2_v50_fibo_basel_designation_reconciliation"]
        self.assertEqual(recon["predecessor"], "V49")
        self.assertEqual(recon["scheduler_cut_git_blob_sha"], v50_blob)
        self.assertEqual(recon["direct_route_count_delta"], 0)
        self.assertEqual(recon["bounded_family_count_delta"], 0)
        self.assertEqual(recon["primary_unsolved_cell_count"], 1)
        self.assertEqual(recon["terminal_credit_delta"], 0)

    def test_current_terminal_binds_exact_current_r2_and_v50_without_terminal_upgrade(self):
        r2 = load(CURRENT_R2_PATH)
        term = load(CURRENT_TERMINAL_PATH)
        r2_blob = git_blob_sha(CURRENT_R2_PATH)
        v50_blob = git_blob_sha(V50_PATH)

        self.assertIn("TERMINAL_FALSE", term["status"])
        self.assertEqual(
            term["authoritative_sources"]["current_r2_decision_intelligence"]["path"],
            "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
        )
        self.assertEqual(
            term["authoritative_sources"]["current_r2_decision_intelligence"]["git_blob_sha"],
            r2_blob,
        )
        self.assertEqual(
            term["authoritative_sources"]["current_r2_decision_intelligence"]["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V50.json",
        )
        self.assertEqual(
            term["authoritative_sources"]["current_r2_decision_intelligence"]["scheduler_cut"]["git_blob_sha"],
            v50_blob,
        )
        self.assertEqual(
            term["live_truth"]["current_r2_scheduler_cut"],
            "ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V50",
        )
        self.assertEqual(
            term["r2_scheduler_precedence"]["current_scheduler_path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V50.json",
        )
        self.assertIn(
            "PINNED_FIBO_Q2_2026_BASEL_III_DESIGNATION_SOURCE_AUTHORITY_BOUND",
            term["r2_scheduler_precedence"]["rule"],
        )
        self.assertEqual(
            term["r2_v50_fibo_basel_designation_reconciliation"]["terminal_credit_delta"],
            0,
        )

    def test_bound_basel_artifacts_are_exact_main_blobs(self):
        self.assertEqual(
            git_blob_sha(ROOT / "canonical/runtime/fibo_q2_2026_basel_designation_authority_v1.py"),
            BASEL_RUNTIME_BLOB,
        )
        self.assertEqual(
            git_blob_sha(ROOT / "canonical/evidence/FIBO_Q2_2026_BASEL_DESIGNATIONS_V1.json"),
            BASEL_EVIDENCE_BLOB,
        )
        self.assertEqual(git_blob_sha(BASEL_VERIFY_PATH), BASEL_VERIFY_BLOB)
        self.assertEqual(
            git_blob_sha(BASEL_RECONCILIATION_PATH),
            BASEL_RECONCILIATION_BLOB,
        )


    def test_current_terminal_preserves_coding_v5_reconciliation(self):
        term = load(CURRENT_TERMINAL_PATH)
        self.assertEqual(
            term["coding_v5_positive_adequacy_gate_reconciliation_20261009_v1"],
            {
                "result": "GATE_VERIFIED__CURRENT_CERTIFICATE_NOT_READY__NEXT_EVIDENCE_CLASS_BOUND",
                "gate_blob_sha": "c777c4a2c9e34cb3e37ae8ed75565c5a3aefa390",
                "verification_blob_sha": "ec006e826547d810aa3fe61e77871ed0dc35e131",
                "boundary_blob_sha": "ab28e64d73392bd7810a579ce5a1ed346c9e2925",
                "acceptance_credit_delta": 0,
                "terminal_credit_delta": 0,
            },
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
