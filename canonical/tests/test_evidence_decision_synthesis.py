#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
BOUND=CANONICAL_ROOT/"runtime"/"bound_capabilities"

def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,BOUND/filename)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

producer=load("decision_producer","evidence_decision_synthesis.py")
verifier=load("decision_verifier","evidence_decision_verify.py")


def base_problem():
    return {
      "schema":"PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
      "decision_id":"TEST",
      "question":"Which route should execute?",
      "alternatives":[{"id":"A","label":"A"},{"id":"B","label":"B"}],
      "constraints":[
        {"id":"a-zero","alternative":"A","required":True,"state":"SATISFIED","description":"zero spend","provenance":[{"source":"test","ref":"a"}]},
        {"id":"b-zero","alternative":"B","required":True,"state":"SATISFIED","description":"zero spend","provenance":[{"source":"test","ref":"b"}]},
      ],
      "evidence":[
        {"id":"a1","alternative":"A","relation":"SUPPORTS","confidence":0.9,"strength":1.0,"independence_group":"s1","claim":"ready","provenance":[{"source":"test","ref":"a1"}]},
        {"id":"b1","alternative":"B","relation":"SUPPORTS","confidence":0.6,"strength":1.0,"independence_group":"s2","claim":"maybe","provenance":[{"source":"test","ref":"b1"}]},
      ],
      "policy":{"minimum_support_ratio":0.6,"maximum_conflict_ratio":0.5,"minimum_independent_support_groups":1,"minimum_net_margin":0.1}
    }


class Tests(unittest.TestCase):
    def test_selects_best_admissible_supported_alternative(self):
        p=base_problem(); r=producer.synthesize(p)
        self.assertEqual(r["status"],"DECIDED")
        self.assertEqual(r["selected_alternative"],"A")
        ok,reason=verifier.verify(p,r)
        self.assertTrue(ok,reason)

    def test_unknown_required_constraint_forces_insufficient_when_no_resolved_admissible(self):
        p=base_problem()
        for c in p["constraints"]: c["state"]="UNKNOWN"
        r=producer.synthesize(p)
        self.assertEqual(r["status"],"INSUFFICIENT")
        self.assertIsNone(r["selected_alternative"])

    def test_all_violated_yields_no_admissible(self):
        p=base_problem()
        for c in p["constraints"]: c["state"]="VIOLATED"
        r=producer.synthesize(p)
        self.assertEqual(r["status"],"NO_ADMISSIBLE_ALTERNATIVE")

    def test_internal_evidence_conflict_blocks_decision(self):
        p=base_problem()
        p["evidence"].append({"id":"a2","alternative":"A","relation":"CONTRADICTS","confidence":0.9,"strength":1.0,"independence_group":"s3","claim":"not ready","provenance":[{"source":"test","ref":"a2"}]})
        p["evidence"].append({"id":"b2","alternative":"B","relation":"CONTRADICTS","confidence":0.6,"strength":1.0,"independence_group":"s4","claim":"not ready","provenance":[{"source":"test","ref":"b2"}]})
        r=producer.synthesize(p)
        self.assertEqual(r["status"],"CONFLICTED")

    def test_same_independence_group_cannot_double_count_support(self):
        p=base_problem()
        p["evidence"].append({"id":"a-dup","alternative":"A","relation":"SUPPORTS","confidence":0.8,"strength":1.0,"independence_group":"s1","claim":"duplicate report","provenance":[{"source":"test","ref":"dup"}]})
        r=producer.synthesize(p)
        a=next(x for x in r["rankings"] if x["alternative"]=="A")
        self.assertAlmostEqual(a["support_score"],0.9)
        self.assertEqual(a["independent_support_groups"],["s1"])

    def test_verifier_detects_tampering(self):
        p=base_problem(); r=producer.synthesize(p)
        r["selected_alternative"]="B"
        ok,reason=verifier.verify(p,r)
        self.assertFalse(ok)
        self.assertEqual(reason,"SELECTED_ALTERNATIVE_MISMATCH")

    def test_two_real_tasks_same_unchanged_route(self):
        fixtures=[
          ("MODEL_INDEPENDENT_EVIDENCE_DECISION_REAL_TASK_A_CARRIER_20260930_INPUT.json","PUBLIC_GITHUB_ACTIONS"),
          ("MODEL_INDEPENDENT_EVIDENCE_DECISION_REAL_TASK_B_CLICK_REPAIR_20260930_INPUT.json","UPSTREAM_HISTORY_REUSE"),
        ]
        base=CANONICAL_ROOT/"capabilities"/"obsolescence"
        for filename,expected in fixtures:
            p=json.loads((base/filename).read_text(encoding="utf-8"))
            r=producer.synthesize(p)
            self.assertEqual(r["status"],"DECIDED")
            self.assertEqual(r["selected_alternative"],expected)
            self.assertEqual(r["model_dependency_count"],0)
            self.assertGreaterEqual(len(r["trace"]),4)
            ok,reason=verifier.verify(p,r)
            self.assertTrue(ok,reason)

    def test_run_writes_repository_local_result_and_verifier_accepts(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            p=base_problem()
            (root/"in.json").write_text(json.dumps(p),encoding="utf-8")
            out=producer.run({"input_path":"in.json","output_path":"out.json"},root)
            self.assertTrue(out["output_verified"])
            checked=verifier.run({"input_path":"in.json","result_path":"out.json"},root)
            self.assertTrue(checked["verified"],checked)

if __name__=="__main__": unittest.main(verbosity=2)
