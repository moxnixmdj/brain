#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
BOUND=RUNTIME/"bound_capabilities"
sys.path.insert(0,str(RUNTIME))

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+str(path))
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

class BroadObjectiveRoleBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grounding=load(BOUND/"plain_goal_bound_grounding.py","role_grounding")
        cls.compiler=load(RUNTIME/"goal_compiler.py","role_goal_compiler")
        cls.binder=load(RUNTIME/"capability_proposal_generators.py","role_proposal_binder")
        raw=json.loads((RUNTIME/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))
        cls.registry=cls.compiler._platform_admissible_registry(raw["capabilities"])

    def test_source_discovery_role_binds_to_qualified_local_primitive(self):
        objective=(
          "Assess whether two independently reported physical measurements support "
          "the same directional conclusion while preserving authoritative provenance, "
          "quantitative comparison, limitations, and independent verification."
        )
        out=self.grounding.ground(
            objective,self.registry,
            compiler=self.compiler,proposal_binder=self.binder,root=ROOT,
            enforce_bindability=True,
        )
        self.assertTrue(out["broad_objective_decomposition_available"],out)
        rg=out.get("broad_objective_role_grounding")
        self.assertIsInstance(rg,dict,out)
        clauses=rg.get("clauses") or []
        self.assertEqual(len(clauses),5,rg)
        source=clauses[0]
        ids=[x.get("capability_id") for x in source.get("candidates") or []]
        self.assertIn("research.source_candidates.discover.open_web",ids,rg)
        self.assertNotEqual(source.get("status"),"UNRESOLVED",rg)
        for item in source.get("candidates") or []:
            cid=item.get("capability_id")
            self.assertEqual(self.registry[cid].get("status"),"VERIFIED_BOUND_CAPABILITY")
            self.assertEqual(float(self.registry[cid].get("incremental_spend_usd",0) or 0),0.0)
        print("BROAD_ROLE_BINDING_DIAGNOSTIC="+json.dumps({
          "grounded_clause_count":rg.get("grounded_clause_count"),
          "unresolved_clause_indexes":rg.get("unresolved_clause_indexes"),
          "candidate_capability_ids":rg.get("candidate_capability_ids"),
          "clauses":[
            {"index":x.get("index"),"text":x.get("text"),"status":x.get("status"),
             "candidates":[y.get("capability_id") for y in x.get("candidates") or []],
             "rejected":x.get("rejected_unbindable_candidates")}
            for x in clauses
          ],
        },sort_keys=True))

    def test_discovery_adapter_writes_provenance_bearing_unverified_candidates(self):
        mod=load(BOUND/"open_web_source_candidate_discovery.py","bound_source_discovery")
        out=mod.run({
          "goal":"RFC 9110 HTTP semantics official specification",
          "output_path":"canonical/astra_runtime/tmp/role_binding_source_discovery_test.json",
          "limit":8,"timeout":20,
        },ROOT)
        self.assertTrue(out["output_verified"],out)
        self.assertGreater(out["candidate_count"],0,out)
        self.assertEqual(out["authority_verification"],"NOT_PERFORMED")
        self.assertEqual(out["model_dependency_count"],0)
        self.assertEqual(out["incremental_spend_usd"],0)
        self.assertTrue((ROOT/out["output_path"]).is_file())

if __name__=="__main__":
    unittest.main(verbosity=2)
