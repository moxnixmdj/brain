from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.tests.test_oewn_effect_field_registry_v5_integration_v1 import _problem
from canonical.runtime import r2_cross_document_oewn_semantic_registry_v5_lattice_direct_adequacy_v1 as d


def _goal():
    return (
        "Using the OEWN-mapped semantic-edge cross-document effect lattice case at "
        "canonical/tmp/oewn.json, compute and independently verify the effective "
        "value and save it to canonical/tmp/out.json."
    )


def _write(root:Path,*,terminally_equivalent=True):
    p=root/"canonical/tmp"
    p.mkdir(parents=True,exist_ok=True)
    (p/"oewn.json").write_text(
        json.dumps(_problem(terminally_equivalent=terminally_equivalent)),
        encoding="utf-8",
    )


class R2OewnSemanticRegistryV5LatticeDirectAdequacyV1Tests(unittest.TestCase):
    def test_closed_case_matches_preflight_without_side_effect(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _write(root)
            outpath=root/"canonical/tmp/out.json"
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["route_id"],d.ROUTE_ID)
            self.assertEqual(pf["effective_value"],"10")
            self.assertFalse(outpath.exists())

    def test_closed_case_runs_transactionally(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _write(root)
            out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")
            self.assertTrue(out["source_immutability_verified"])
            self.assertTrue((root/"canonical/tmp/out.json").is_file())

    def test_action_changing_senses_remain_semantic_open(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _write(root,terminally_equivalent=False)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            atoms=[
                x for x in pf["open_lattice_atoms"]
                if x.get("effect_id")=="E.t" and x.get("field")=="effect_class"
            ]
            self.assertEqual(len(atoms),1)

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _write(root)
            op=root/"canonical/tmp/out.json"
            op.write_text('{"old":true}\n',encoding="utf-8")
            old=op.read_bytes()
            original=d.verifier.verify
            calls={"n":0}

            def injected(problem,result,*args,**kwargs):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(problem,result,*args,**kwargs)

            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)

    def test_nonmatching_goal_has_no_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            out=d.preflight({"task_id":"x","goal":"Analyze this."},repo_root=root)
            self.assertFalse(out["matched"])
            self.assertEqual(out["status"],"NOT_APPLICABLE")


if __name__=="__main__":
    unittest.main()
