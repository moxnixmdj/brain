from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import r2_direct_live_admission_v1 as live
from canonical.runtime import r2_cross_document_field_proof_discovery_direct_adequacy_v1 as direct
from canonical.tests.test_r2_cross_document_field_proof_discovery_direct_v1 import (
    case,
    goal,
    write_case,
)


def row():
    return {
        "route_id":direct.ROUTE_ID,
        "capability_id":direct.CAPABILITY_ID,
        "runtime_path":"canonical/runtime/r2_cross_document_field_proof_discovery_direct_adequacy_v1.py",
        "runtime_git_blob_sha":"0"*40,
        "preflight_callable":"preflight",
        "run_callable":"run",
        "verification_path":"canonical/verification/fake.json",
        "verification_git_blob_sha":"1"*40,
        "scope":"FINITE_AUTHENTICATED_FIELD_PROOF_DISCOVERY",
        "selection_class":"UNIQUE_MATCH_REQUIRED",
        "active":True,
        "automatic_live_admission":True,
    }


class DynamicAdmissionIntegrationTests(unittest.TestCase):
    def test_unique_dynamic_match_selected_over_idle_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case())
            with patch.object(
                live.admission,"load_current_admissions",
                return_value={"admissions":[row()]},
            ), patch.object(
                live.legacy,"preflight",
                return_value={"matched":False,"status":"NO_DIRECT_ADEQUACY_ROUTE"},
            ) as legacy:
                out=live.preflight(
                    {"task_id":"x","goal":goal()},repo_root=root
                )
            self.assertTrue(out["matched"],out)
            self.assertEqual(out["route_id"],direct.ROUTE_ID)
            legacy.assert_called_once()

    def test_dynamic_semantic_open_preserved_without_legacy_fallthrough(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case(leave_conditions_open=True))
            with patch.object(
                live.admission,"load_current_admissions",
                return_value={"admissions":[row()]},
            ), patch.object(live.legacy,"preflight") as legacy:
                out=live.preflight(
                    {"task_id":"x","goal":goal()},repo_root=root
                )
            self.assertFalse(out["matched"])
            self.assertTrue(out["direct_route_semantic_open"],out)
            self.assertEqual(out["route_id"],direct.ROUTE_ID)
            self.assertFalse(out["dynamic_semantic_open_hint_authority"])
            legacy.assert_not_called()

    def test_live_run_executes_real_dynamic_route_not_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case())
            with patch.object(
                live.admission,"load_current_admissions",
                return_value={"admissions":[row()]},
            ), patch.object(
                live.legacy,"preflight",
                return_value={"matched":False,"status":"NO_DIRECT_ADEQUACY_ROUTE"},
            ), patch.object(live.legacy,"run") as legacy_run:
                out=live.run(
                    {"task_id":"x","goal":goal()},repo_root=root
                )
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["route_id"],direct.ROUTE_ID)
            self.assertEqual(out["effective_value"],"10")
            legacy_run.assert_not_called()


if __name__=="__main__":
    unittest.main()
