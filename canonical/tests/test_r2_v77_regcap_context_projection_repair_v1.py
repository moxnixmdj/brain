from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

R2 = "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERMINAL = "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
ROOT2 = "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V65.json"
VERIFY = "canonical/verification/REGCAP_NO_DESCRIPTOR_CONTEXT_TRUTH_VERIFY_20261010_V2.json"
DOMAIN_RUNTIME = "canonical/runtime/domain_mapping_truth_certificate_v1.py"
CONTEXT_COMPILER = "canonical/runtime/regcap_contextual_observation_compiler_v1.py"
CONTEXT_RESOLVER = "canonical/runtime/regcap_contextual_resolution_v1.py"
REMOVED_RUNTIME = "canonical/runtime/regcap_contextual_fact_compiler_v1.py"
REMOVED_TEST = "canonical/tests/test_regcap_contextual_fact_compiler_v1.py"

SUBREGION_ID = (
    "REGCAP_AUTHENTICATED_THREE_RIVAL_DIRECT_SIGNATURE_CONTEXT_"
    "WITHOUT_DESCRIPTOR_LOGICAL_EQUIVALENCE"
)


def git_blob(path: str) -> str:
    raw = (ROOT / path).read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def setUp(self):
        self.r2 = load(R2)
        self.terminal = load(TERMINAL)
        tail = self.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        rows = tail["verified_positive_subregions"]
        self.assertIsInstance(rows, list)
        self.row = next(
            x for x in rows
            if isinstance(x, dict) and x.get("id") == SUBREGION_ID
        )

    def test_r2_remains_v77_with_same_route_and_residual_shape(self):
        status = self.r2["status"]
        self.assertIn("V77", status)
        self.assertIn("FORTY_DIRECT_ROUTES", status)
        self.assertIn("THIRTY_SIX_BOUNDED_FAMILIES", status)
        self.assertIn("ONE_PRIMARY_FINANCE_SEMANTIC_RESIDUAL_REMAINS", status)

    def test_subregion_binds_exact_current_runtime_compiler_resolver_and_v2_receipt(self):
        self.assertEqual(self.row["runtime"], DOMAIN_RUNTIME)
        self.assertEqual(self.row["runtime_git_blob_sha"], git_blob(DOMAIN_RUNTIME))
        self.assertEqual(self.row["context_compiler"], CONTEXT_COMPILER)
        self.assertEqual(
            self.row["context_compiler_git_blob_sha"],
            git_blob(CONTEXT_COMPILER),
        )
        self.assertEqual(self.row["context_resolver"], CONTEXT_RESOLVER)
        self.assertEqual(
            self.row["context_resolver_git_blob_sha"],
            git_blob(CONTEXT_RESOLVER),
        )
        self.assertEqual(self.row["verification"], VERIFY)
        self.assertEqual(
            self.row["verification_git_blob_sha"],
            git_blob(VERIFY),
        )

    def test_v2_receipt_is_the_verified_82_test_canonicalization(self):
        receipt = load(VERIFY)
        self.assertIn("82_OF_82", receipt["status"])
        self.assertEqual(
            receipt["verification"]["total_focused_tests"],
            82,
        )
        live = receipt["verification"]["live_primary_source_replay"]
        self.assertEqual(live["result"], "PASS")
        self.assertEqual(set(live["cases"]), {"CCOB", "CCYB", "TLAC"})
        self.assertTrue(
            all("SELECTED_REGCAP_" in value for value in live["cases"].values())
        )
        self.assertEqual(receipt["accounting"]["terminal_credit_delta"], 0)

    def test_root2_v65_binding_is_exact(self):
        cut = self.r2["scheduler_cut"]
        self.assertEqual(cut["path"], ROOT2)
        self.assertEqual(cut["git_blob_sha"], git_blob(ROOT2))

    def test_terminal_projects_current_r2_v77_and_root2_v65(self):
        projected = self.terminal["authoritative_sources"]["current_r2_decision_intelligence"]
        self.assertEqual(projected["path"], R2)
        self.assertEqual(projected["status"], self.r2["status"])
        self.assertEqual(projected["scheduler_cut"]["path"], ROOT2)
        self.assertEqual(
            projected["scheduler_cut"]["git_blob_sha"],
            git_blob(ROOT2),
        )
        self.assertIn("CURRENT_R2_V77", self.terminal["status"])
        self.assertNotIn("CURRENT_R2_V76", self.terminal["status"])

    def test_terminal_scheduler_precedence_matches_r2(self):
        p = self.terminal["r2_scheduler_precedence"]
        self.assertEqual(p["current_authority_path"], R2)
        self.assertEqual(p["current_scheduler_path"], ROOT2)
        self.assertEqual(p["current_scheduler_git_blob_sha"], git_blob(ROOT2))
        self.assertIn("CURRENT_R2_V77_OVERLAYS_ROOT2_V65", p["rule"])
        self.assertTrue(p["current_authority_pointer_mutable"])
        self.assertTrue(p["current_authority_pointer_blob_is_not_load_bearing"])
        self.assertEqual(p["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"], 1)

    def test_authority_boundaries_remain_fail_closed(self):
        self.assertFalse(self.row["global_semantic_identity_authority"])
        self.assertFalse(self.row["open_world_candidate_universe_complete"])
        self.assertFalse(self.row["policy_adequacy_authority"])
        self.assertFalse(self.row["terminal_authority"])

    def test_redundant_parallel_parser_is_absent(self):
        self.assertFalse((ROOT / REMOVED_RUNTIME).exists())
        self.assertFalse((ROOT / REMOVED_TEST).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
