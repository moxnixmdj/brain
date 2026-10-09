from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import oewn_decision_manifest_lattice_v1 as l
from canonical.runtime.oewn_release_sense_universe_v1 import (
    SCHEMA as OEWN_SCHEMA, RELEASE_ID, RELEASE_SHA256,
)
from canonical.runtime import r2_oewn_decision_manifest_lattice_direct_adequacy_v1 as d


def universe():
    return {
        "schema":OEWN_SCHEMA,"status":"PASS","pass":True,
        "release_id":RELEASE_ID,"archive_sha256":RELEASE_SHA256,
        "candidate_set_complete_relative_to_release":True,
        "open_world_english_sense_completeness_claimed":False,
        "lemma":"margin","requested_part_of_speech":"n",
        "senses":[
            {"sense_id":"margin-1","synset_id":"ewn-margin-1-n","part_of_speech":"n"},
            {"sense_id":"margin-2","synset_id":"ewn-margin-2-n","part_of_speech":"n"},
        ],
    }


def problem(text):
    return {
        "schema":l.SCHEMA,"scope_id":"finance-margin",
        "sense_universe":universe(),"source_id":"doc","source_text":text,
    }


def terminal(sid,policy): return f'Sense terminal {sid}: {{"policy":"{policy}"}}'
def obs(oid,sid,value): return f'Sense observation {oid} cost 1 for {sid}: "{value}"'
def observed(oid,value): return f'Sense observed {oid}: "{value}"'


def goal():
    return (
        "Using the OEWN decision manifest lattice case at canonical/tmp/sense.json, "
        "compute and independently verify the decision and save it to canonical/tmp/out.json."
    )


def write(root:Path,obj):
    p=root/"canonical/tmp";p.mkdir(parents=True,exist_ok=True)
    (p/"sense.json").write_text(json.dumps(obj),encoding="utf-8")


class R2OewnDecisionManifestLatticeDirectAdequacyV1Tests(unittest.TestCase):
    def test_closed_equivalent_case_matches_and_runs(self):
        case=problem("\n".join([
            terminal("margin-1","A"),terminal("margin-2","A"),
        ]))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);write(root,case)
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(set(out["surviving_sense_ids"]),{"margin-1","margin-2"})
            self.assertTrue(out["source_immutability_verified"])

    def test_observed_context_identifies_sense(self):
        case=problem("\n".join([
            terminal("margin-1","A"),terminal("margin-2","B"),
            obs("context-domain","margin-1","profit"),
            obs("context-domain","margin-2","collateral"),
            observed("context-domain","collateral"),
        ]))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);write(root,case)
            out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["identified_sense_id"],"margin-2")
            self.assertEqual(out["terminal_signature"],{"policy":"B"})

    def test_open_lattice_does_not_match(self):
        case=problem(terminal("margin-1","A"))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);write(root,case)
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertEqual(pf["status"],"NOT_APPLICABLE__DECISION_MANIFEST_LATTICE_OPEN")
            self.assertEqual(
                pf["next_proof_obligations"][0]["kind"],
                "PROVE_SENSE_TERMINAL_SIGNATURE",
            )

    def test_postwrite_verifier_failure_rolls_back(self):
        case=problem("\n".join([
            terminal("margin-1","A"),terminal("margin-2","A"),
        ]))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);write(root,case)
            op=root/"canonical/tmp/out.json";op.write_text('{"old":true}\n')
            old=op.read_bytes();orig=d.verifier.verify;calls={"n":0}
            def injected(problem,result):
                calls["n"]+=1
                if calls["n"]>=3:return {"verified":False,"errors":["forced"]}
                return orig(problem,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)

    def test_unrelated_goal_has_no_scope(self):
        with tempfile.TemporaryDirectory() as td:
            out=d.preflight({"task_id":"x","goal":"unrelated"},repo_root=Path(td))
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"],"NOT_APPLICABLE")


if __name__=="__main__":unittest.main()
