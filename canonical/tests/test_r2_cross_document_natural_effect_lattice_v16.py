from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v3 as l
from canonical.runtime import r2_cross_document_natural_effect_lattice_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v16 as v16


def define_source(*,include_end=True):
    lines=[
        "The only effects on threshold are A.t.",
        "Effect A.t defines threshold as 10.",
        "Effect A.t is unconditional.",
        "Effect A.t has no start date.",
    ]
    if include_end:
        lines.append("Effect A.t has no end date.")
    lines.append("Effect A.t supersedes nothing.")
    return "\n".join(lines)


def case(source):
    return {
        "schema":l.SCHEMA,
        "case_id":"natural-direct",
        "source_documents":[{
            "document_id":"A",
            "source_id":"A",
            "source_text":source,
            "claims":[],
        }],
        "query":{
            "target_id":"threshold",
            "as_of":"2026-10-09",
            "context":{},
        },
    }


def goal():
    return (
        "Using the bounded-natural cross-document effect lattice case at "
        "canonical/tmp/natural.json, compute and independently verify the "
        "effective value and save it to canonical/tmp/out.json."
    )


def write(root:Path,source):
    p=root/"canonical/tmp"
    p.mkdir(parents=True,exist_ok=True)
    (p/"natural.json").write_text(json.dumps(case(source)),encoding="utf-8")


class NaturalEffectLatticeDirectRouteV1Tests(unittest.TestCase):
    def test_closed_natural_source_matches_and_runs_without_claims(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,define_source())
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertTrue(pf["query_relative_effect_semantics_finite"])
            out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],10)
            self.assertTrue(out["source_immutability_verified"])

    def test_missing_natural_coordinate_is_unmatched_top(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,define_source(include_end=False))
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            atom=pf["open_lattice_atoms"][0]
            self.assertEqual(atom["dimension"],"DOCUMENT_EFFECT_FIELD")
            self.assertEqual(atom["field"],"valid_until")

    def test_unrecognized_prose_is_unmatched_inventory_top(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,"The threshold probably changed.")
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertEqual(
                pf["open_lattice_atoms"][0]["dimension"],
                "EFFECT_ID_INVENTORY",
            )

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,define_source())
            op=root/"canonical/tmp/out.json"
            op.write_text('{"old":true}\n',encoding="utf-8")
            old=op.read_bytes()
            original=d.verifier.verify
            calls={"n":0}
            def injected(problem,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(problem,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)


class DirectEndToEndAdequacyV16Tests(unittest.TestCase):
    def test_v16_selects_natural_route_before_v15(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,define_source())
            with patch.object(v16.v15,"preflight") as prior:
                pf=v16.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["route_id"],d.ROUTE_ID)
            prior.assert_not_called()

    def test_v16_preserves_open_natural_top_without_v15_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,define_source(include_end=False))
            with patch.object(v16.v15,"preflight") as prior:
                pf=v16.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"])
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["open_lattice_atoms"][0]["field"],"valid_until")
            prior.assert_not_called()

    def test_v16_delegates_unrelated_request_to_v15(self):
        expected={"matched":False,"pass":False,"status":"V15_FALLBACK"}
        with patch.object(v16.v15,"preflight",return_value=expected) as prior:
            out=v16.preflight({"task_id":"x","goal":"unrelated"})
        self.assertEqual(out,expected)
        prior.assert_called_once()


if __name__=="__main__":
    unittest.main()
