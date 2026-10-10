from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
import types

legacy=types.ModuleType("canonical.runtime.r2_direct_end_to_end_adequacy_v21")
legacy.ROUTES={}
legacy.preflight=lambda request, **kwargs: {
    "matched":False,"pass":False,"status":"NOT_APPLICABLE"
}
legacy.run=lambda request, **kwargs: {
    "matched":False,"pass":False,"status":"NOT_APPLICABLE"
}
sys.modules["canonical.runtime.r2_direct_end_to_end_adequacy_v21"]=legacy

from canonical.runtime import r2_direct_live_admission_v1 as live
from canonical.runtime import r2_cross_document_natural_entailment_lattice_direct_adequacy_v1 as route
from canonical.tests.test_r2_natural_entailment_lattice_v22 import _problem, _goal


def _row():
    return {
        "route_id":route.ROUTE_ID,
        "runtime_path":"canonical/runtime/r2_cross_document_natural_entailment_lattice_direct_adequacy_v1.py",
        "preflight_callable":"preflight",
        "run_callable":"run",
    }


def _write(root:Path,problem):
    p=root/"canonical/tmp"
    p.mkdir(parents=True,exist_ok=True)
    (p/"case.json").write_text(json.dumps(problem),encoding="utf-8")


class Tests(unittest.TestCase):
    def test_unique_dynamic_match_selected_when_legacy_idle(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _write(root,_problem())
            request={"task_id":"x","goal":_goal()}
            with patch.object(live,"_dynamic_rows",return_value=[_row()]), patch.object(
                live.legacy,"preflight",
                return_value={"matched":False,"pass":False,"status":"NOT_APPLICABLE"},
            ):
                out=live.preflight(request,repo_root=root)
            self.assertTrue(out["matched"],out)
            self.assertEqual(out["route_id"],route.ROUTE_ID)

    def test_live_wrapper_executes_real_dynamic_route(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _write(root,_problem())
            request={"task_id":"x","goal":_goal()}
            with patch.object(live,"_dynamic_rows",return_value=[_row()]), patch.object(
                live.legacy,"preflight",
                return_value={"matched":False,"pass":False,"status":"NOT_APPLICABLE"},
            ), patch.object(
                live.legacy,"run",
                side_effect=AssertionError("legacy must not execute"),
            ):
                out=live.run(request,repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["route_id"],route.ROUTE_ID)
            self.assertEqual(out["effective_value"],"12")

    def test_dynamic_match_plus_legacy_match_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _write(root,_problem())
            request={"task_id":"x","goal":_goal()}
            with patch.object(live,"_dynamic_rows",return_value=[_row()]), patch.object(
                live.legacy,"preflight",
                return_value={
                    "matched":True,
                    "pass":True,
                    "status":"LEGACY_MATCH",
                    "route_id":"LEGACY_ROUTE",
                },
            ):
                out=live.preflight(request,repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertEqual(out["status"],"FAIL_CLOSED__DIRECT_ROUTE_COLLISION")

    def test_dynamic_semantic_open_is_preserved_as_zero_authority_hint(self):
        problem=_problem()
        claims=problem["source_documents"][0]["claims"]
        problem["source_documents"][0]["claims"]=[
            row for row in claims if row.get("claim_id")!="value-edge"
        ]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _write(root,problem)
            request={"task_id":"x","goal":_goal()}
            with patch.object(live,"_dynamic_rows",return_value=[_row()]), patch.object(
                live.legacy,"preflight",
                side_effect=AssertionError("legacy preflight must not run"),
            ):
                out=live.preflight(request,repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["direct_route_semantic_open"])
            self.assertEqual(out["route_id"],route.ROUTE_ID)
            self.assertFalse(out["dynamic_semantic_open_hint_authority"])
            self.assertEqual(
                out["status"],
                "FAIL_CLOSED__DYNAMIC_SEMANTIC_OPEN_REQUIRES_PRECEDENCE_AUTHORITY",
            )


if __name__=="__main__":
    unittest.main()
