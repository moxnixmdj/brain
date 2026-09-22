#!/usr/bin/env python3
import json, tempfile, unittest
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("auditor", HERE.parent/"runtime"/"capability_reality_auditor.py")
auditor=importlib.util.module_from_spec(spec); spec.loader.exec_module(auditor)

def writej(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj),encoding="utf-8")

class AuditTests(unittest.TestCase):
    def base_pointer(self):
        return {
          "canonical_generation":"test-good",
          "mandatory_laws":[
            "canonical/laws/TRUTH_FIRST_AND_NO_DUPLICATE_EXECUTION_LAW_V1.md",
            "canonical/laws/CAPABILITY_REALIZATION_MISSION_LOCK_V1.md"
          ],
          "mission_lock":{
            "terminal_objective":"MAKE_REAL_CAPABILITIES",
            "predicates_role":"SUBORDINATE_EVIDENCE_ONLY",
            "benchmarks_role":"SUBORDINATE_DIAGNOSTIC_ONLY"
          },
          "active_agent":{
            "full_astra_claim":False,
            "external_astra_parity":"UNVERIFIED",
            "astra_qualification_scope":"PROJECT_BRAIN_DECLARED_61_PREDICATE_SUITE_ONLY"
          },
          "provider_rules":{"val_town":"UNAVAILABLE__NONCANONICAL__DO_NOT_USE"},
          "execution_governance":{"only_current_allowed_frontier_actions":["build_integrated_capability_worker"]},
          "active_superworkers":[],
          "current_frontier":{
            "superworker_real":0,
            "superworker_truth_scope":"NO_SINGLE_INTEGRATED_COGNITIVE_SUPERWORKER_PROVEN",
            "critical_blocker":"NO_SINGLE_IDENTITY_FULL_LOOP",
            "next_step":"CREATE_ONE_INTEGRATED_COGNITIVE_WORKER_AND_RUN_REAL_END_TO_END_MISSION"
          }
        }

    def make_root(self,pointer,real_ids=False):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        writej(root/"canonical"/"CANONICAL_POINTER.json",pointer)
        writej(root/"canonical"/"qualification"/"SUPERWORKER_COMPOSITION_ERROR_CORRECTION_V1.json",{"status":"CANONICAL_CORRECTION"})
        for n in (1,2):
            writej(root/"canonical"/"agents"/f"SUPERWORKER_INTEGRATED_{n}.json",{
              "agent_id":f"SUPERWORKER-INTEGRATED-{n}",
              "counts_as_real_superworker":real_ids
            })
        return td,root

    def test_good_state_passes(self):
        td,root=self.make_root(self.base_pointer(),False)
        try:
            r=auditor.audit(root)
            self.assertEqual(r["status"],"PASS",r)
        finally: td.cleanup()

    def test_bad_proxy_and_composition_fail(self):
        p=self.base_pointer()
        p["active_agent"]["full_astra_claim"]=True
        p["active_agent"]["external_astra_parity"]="VERIFIED"
        p["current_frontier"]["superworker_real"]=2
        p["current_frontier"]["next_step"]="SCALE_TO_100_AFTER_61_OF_61"
        p["active_superworkers"]=[
          {"counts_as_real_superworker":True},{"counts_as_real_superworker":True}
        ]
        p["provider_rules"]["val_town"]="ACTIVE"
        p["execution_governance"]["only_current_allowed_frontier_actions"]=["use_val_town"]
        td,root=self.make_root(p,True)
        try:
            r=auditor.audit(root)
            self.assertEqual(r["status"],"FAIL")
            failed={c["id"] for c in r["checks"] if not c["ok"]}
            self.assertIn("NO_INTERNAL_TO_EXTERNAL_ASTRA_PARITY",failed)
            self.assertIn("NO_COMPOSITE_WORKER_PROMOTION",failed)
            self.assertIn("VAL_TOWN_FORBIDDEN",failed)
            self.assertIn("FRONTIER_NOT_PROXY_GOAL",failed)
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main()
