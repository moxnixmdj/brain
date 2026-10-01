import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from canonical.runtime.continuous_obs_runtime import validate_context

REQ=(
 "canonical/CANONICAL_POINTER.json",
 "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json",
 "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json",
)

def put(root, rel, obj):
    p=root/rel
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,sort_keys=True)+"\n",encoding="utf-8")
    return hashlib.sha256(p.read_bytes()).hexdigest()

def make_context(root, now):
    hashes={}
    hashes[REQ[0]]=put(root,REQ[0],{"canonical_generation":"g1"})
    hashes[REQ[1]]=put(root,REQ[1],{"x":1})
    hashes[REQ[2]]=put(root,REQ[2],{"x":2})
    return {
      "schema":"PROJECT_BRAIN_CONTINUOUS_OBS_CONTEXT_V1",
      "status":"CURRENT","canonical_generation":"g1",
      "dependency_inventory_complete":True,
      "material_world_state_dependencies_complete":True,
      "unknown_material_dependencies":[],
      "stale_authority_absent":True,
      "valid_proof_action_priority":True,
      "obs_layers_current":{k:True for k in ("goal","capability","blocker","solution","verification","inherited_system","obs_process")},
      "canonical_state_dependencies":[{"path":p,"sha256":h} for p,h in hashes.items()],
      "dependencies":[{
        "dependency_id":"runner","class":"EXECUTION_SURFACE","material":True,
        "volatility":"VOLATILE","scope":"GLOBAL","status":"READY",
        "observed_at_utc":now.isoformat(),"max_age_seconds":300,
        "evidence":["direct probe"]
      }]
    }

class ContinuousObsRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.now=datetime(2026,10,1,20,0,tzinfo=timezone.utc)
    def tearDown(self):
        self.tmp.cleanup()
    def test_current_context_passes(self):
        self.assertTrue(validate_context(make_context(self.root,self.now),root=self.root,now=self.now)["pass"])
    def test_stale_world_dependency_fails(self):
        c=make_context(self.root,self.now-timedelta(minutes=10))
        out=validate_context(c,root=self.root,now=self.now)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("VOLATILE_DEPENDENCY_STALE") for x in out["errors"]))
    def test_canonical_state_change_fails(self):
        c=make_context(self.root,self.now)
        put(self.root,REQ[1],{"x":"changed"})
        out=validate_context(c,root=self.root,now=self.now)
        self.assertIn("CANONICAL_STATE_CHANGED:"+REQ[1],out["errors"])
    def test_unknown_material_dependency_fails(self):
        c=make_context(self.root,self.now)
        c["unknown_material_dependencies"]=["mystery"]
        self.assertFalse(validate_context(c,root=self.root,now=self.now)["pass"])
    def test_incomplete_world_inventory_fails(self):
        c=make_context(self.root,self.now)
        c["material_world_state_dependencies_complete"]=False
        self.assertFalse(validate_context(c,root=self.root,now=self.now)["pass"])

if __name__=="__main__":
    unittest.main()
