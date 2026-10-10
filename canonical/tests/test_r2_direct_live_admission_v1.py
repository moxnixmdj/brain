from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from canonical.runtime import r2_direct_live_admission_v1 as live


def dyn_row(route_id="DYNAMIC_X"):
    return {
        "route_id": route_id,
        "runtime_path": "canonical/runtime/fake_dynamic.py",
        "runtime_git_blob_sha": "0" * 40,
        "preflight_callable": "preflight",
        "run_callable": "run",
        "verification_path": "canonical/verification/fake.json",
        "verification_git_blob_sha": "1" * 40,
        "selection_class": "UNIQUE_MATCH_REQUIRED",
        "active": True,
        "automatic_live_admission": True,
    }


class R2DirectLiveAdmissionV1Tests(unittest.TestCase):
    def test_empty_dynamic_frontier_is_exact_v21_preflight_delegation(self):
        expected = {"matched": True, "route_id": "LEGACY", "status": "LEGACY"}
        with patch.object(live.admission, "load_current_admissions", return_value={"admissions": []}), \
             patch.object(live.legacy, "preflight", return_value=expected) as legacy:
            out = live.preflight({"task_id": "t", "goal": "g"})
        self.assertEqual(out, expected)
        legacy.assert_called_once()

    def test_empty_dynamic_frontier_is_exact_v21_run_delegation(self):
        expected = {"pass": True, "route_id": "LEGACY", "status": "PASS_LEGACY"}
        with patch.object(live.admission, "load_current_admissions", return_value={"admissions": []}), \
             patch.object(live.legacy, "preflight", return_value={"matched": True, "route_id": "LEGACY"}), \
             patch.object(live.legacy, "run", return_value=expected) as legacy:
            out = live.run({"task_id": "t", "goal": "g"})
        self.assertEqual(out, expected)
        legacy.assert_called_once()

    def test_unique_dynamic_match_with_no_legacy_engagement_is_selected(self):
        row = dyn_row()
        dynamic_pf = {"matched": True, "route_id": "DYNAMIC_X", "status": "DYNAMIC"}
        with patch.object(live.admission, "load_current_admissions", return_value={"admissions": [row]}), \
             patch.object(live, "_dynamic_preflight", return_value=dynamic_pf), \
             patch.object(live.legacy, "preflight", return_value={"matched": False, "status": "NO"}):
            out = live.preflight({"task_id": "t", "goal": "g"})
        self.assertEqual(out, dynamic_pf)

    def test_dynamic_overlap_with_legacy_match_fails_closed(self):
        row = dyn_row()
        with patch.object(live.admission, "load_current_admissions", return_value={"admissions": [row]}), \
             patch.object(live, "_dynamic_preflight", return_value={"matched": True, "route_id": "DYNAMIC_X"}), \
             patch.object(live.legacy, "preflight", return_value={"matched": True, "route_id": "LEGACY_Y"}):
            out = live.preflight({"task_id": "t", "goal": "g"})
        self.assertEqual(out["status"], "FAIL_CLOSED__DIRECT_ROUTE_COLLISION")
        self.assertEqual(out["reason"], "DYNAMIC_ROUTE_OVERLAPS_LEGACY_V21")
        self.assertEqual(out["matching_route_ids"], ["DYNAMIC_X", "LEGACY_Y"])

    def test_dynamic_overlap_with_legacy_semantic_open_fails_closed(self):
        row = dyn_row()
        with patch.object(live.admission, "load_current_admissions", return_value={"admissions": [row]}), \
             patch.object(live, "_dynamic_preflight", return_value={"matched": True, "route_id": "DYNAMIC_X"}), \
             patch.object(live.legacy, "preflight", return_value={
                 "matched": False,
                 "direct_route_semantic_open": True,
                 "route_id": "LEGACY_OPEN",
             }):
            out = live.preflight({"task_id": "t", "goal": "g"})
        self.assertEqual(out["status"], "FAIL_CLOSED__DIRECT_ROUTE_COLLISION")
        self.assertIn("LEGACY_OPEN", out["matching_route_ids"])

    def test_multiple_dynamic_matches_fail_closed_without_legacy_call(self):
        rows = [dyn_row("D1"), dyn_row("D2")]
        side = [
            {"matched": True, "route_id": "D1"},
            {"matched": True, "route_id": "D2"},
        ]
        with patch.object(live.admission, "load_current_admissions", return_value={"admissions": rows}), \
             patch.object(live, "_dynamic_preflight", side_effect=side), \
             patch.object(live.legacy, "preflight") as legacy:
            out = live.preflight({"task_id": "t", "goal": "g"})
        self.assertEqual(out["status"], "FAIL_CLOSED__DIRECT_ROUTE_COLLISION")
        self.assertEqual(out["matching_route_ids"], ["D1", "D2"])
        legacy.assert_not_called()

    def test_dynamic_semantic_open_fails_closed_but_preserves_unique_zero_authority_hint(self):
        row = dyn_row()
        atom = {
            "document_id": "A",
            "dimension": "DOCUMENT_EFFECT_FIELD",
            "effect_id": "A.t",
            "field": "value",
            "state": "TOP",
        }
        obligation = {
            "kind": "PROVE_DOCUMENT_EFFECT_FIELD",
            "document_id": "A",
            "effect_id": "A.t",
            "field": "value",
        }
        with patch.object(live.admission, "load_current_admissions", return_value={"admissions": [row]}), \
             patch.object(live, "_dynamic_preflight", return_value={
                 "matched": False,
                 "direct_route_semantic_open": True,
                 "route_id": "DYNAMIC_X",
                 "status": "OPEN__FIELD_TOP",
                 "effect_status": "OPEN__QUERY_RELEVANT_EFFECT_FIELD_TOP_REMAINS",
                 "open_lattice_atoms": [atom],
                 "next_proof_obligations": [obligation],
                 "query_relative_effect_semantics_finite": False,
             }), \
             patch.object(live.legacy, "preflight") as legacy:
            out = live.preflight({"task_id": "t", "goal": "g"})
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__DYNAMIC_SEMANTIC_OPEN_REQUIRES_PRECEDENCE_AUTHORITY",
        )
        self.assertTrue(out["direct_route_semantic_open"])
        self.assertEqual(out["route_id"], "DYNAMIC_X")
        self.assertEqual(out["dynamic_semantic_open_status"], "OPEN__FIELD_TOP")
        self.assertEqual(out["open_lattice_atoms"], [atom])
        self.assertEqual(out["next_proof_obligations"], [obligation])
        self.assertFalse(out["query_relative_effect_semantics_finite"])
        self.assertFalse(out["dynamic_semantic_open_hint_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])
        legacy.assert_not_called()

    def test_multiple_dynamic_semantic_open_states_do_not_leak_one_hint(self):
        rows = [dyn_row("D1"), dyn_row("D2")]
        side = [
            {
                "matched": False,
                "direct_route_semantic_open": True,
                "route_id": "D1",
                "open_lattice_atoms": [{"dimension": "A"}],
            },
            {
                "matched": False,
                "direct_route_semantic_open": True,
                "route_id": "D2",
                "open_lattice_atoms": [{"dimension": "B"}],
            },
        ]
        with patch.object(live.admission, "load_current_admissions", return_value={"admissions": rows}), \
             patch.object(live, "_dynamic_preflight", side_effect=side), \
             patch.object(live.legacy, "preflight") as legacy:
            out = live.preflight({"task_id": "t", "goal": "g"})
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__DYNAMIC_SEMANTIC_OPEN_REQUIRES_PRECEDENCE_AUTHORITY",
        )
        self.assertNotIn("direct_route_semantic_open", out)
        self.assertEqual(out["route_ids"], ["D1", "D2"])
        legacy.assert_not_called()

    def test_dynamic_semantic_open_route_id_mismatch_fails_closed(self):
        row = dyn_row("D1")
        dynamic = Mock(return_value={
            "matched": False,
            "direct_route_semantic_open": True,
            "route_id": "D2",
        })
        with patch.object(live.admission, "load_current_admissions", return_value={"admissions": [row]}), \
             patch.object(live, "_resolve_callable", return_value=dynamic):
            out = live.preflight({"task_id": "t", "goal": "g"})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("DYNAMIC_PREFLIGHT_ROUTE_ID_MISMATCH", out["reason"])

    def test_dynamic_selected_run_executes_dynamic_not_v21(self):
        row = dyn_row()
        runner = Mock(return_value={"pass": True, "route_id": "DYNAMIC_X", "status": "PASS_DYNAMIC"})
        with patch.object(live, "preflight", return_value={"matched": True, "route_id": "DYNAMIC_X"}), \
             patch.object(live.admission, "load_current_admissions", return_value={"admissions": [row]}), \
             patch.object(live, "_resolve_callable", return_value=runner), \
             patch.object(live.legacy, "run") as legacy:
            out = live.run({"task_id": "t", "goal": "g"})
        self.assertTrue(out["pass"])
        self.assertEqual(out["status"], "PASS_DYNAMIC")
        legacy.assert_not_called()

    def test_catalog_says_future_route_needs_no_new_version_source(self):
        with patch.object(live.admission, "load_current_admissions", return_value={"admissions": []}):
            out = live.catalog()
        self.assertTrue(out["pass"])
        self.assertEqual(out["legacy_runtime"], "canonical.runtime.r2_direct_end_to_end_adequacy_v21")
        self.assertFalse(out["future_verified_route_requires_new_vN_source"])
        self.assertFalse(out["legacy_precedence_reencoded"])


    def test_current_default_runtime_pointer_binds_exact_wrapper_blob(self):
        from hashlib import sha1
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        runtime = root / "canonical/runtime/r2_direct_live_admission_v1.py"
        pointer = json.loads(
            (root / "canonical/governance/CURRENT_DEFAULT_RUNTIME_INTEGRATION.json").read_text(
                encoding="utf-8"
            )
        )
        raw = runtime.read_bytes()
        actual = sha1(
            b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw
        ).hexdigest()
        self.assertEqual(
            pointer["r2_default_route_runtime"]["stable_wrapper_path"],
            "canonical/runtime/r2_direct_live_admission_v1.py",
        )
        self.assertEqual(
            pointer["r2_default_route_runtime"]["stable_wrapper_git_blob_sha"],
            actual,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
