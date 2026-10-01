import hashlib, json, pathlib
from datetime import datetime, timezone, timedelta
from canonical.runtime.continuous_obs_runtime import validate_context

REQ=(
 "canonical/CANONICAL_POINTER.json",
 "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json",
 "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json",
)

def put(root, rel, obj):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,sort_keys=True)+"\n",encoding="utf-8")
    return hashlib.sha256(p.read_bytes()).hexdigest()

def ctx(tmp_path, now):
    hashes={}
    hashes[REQ[0]]=put(tmp_path,REQ[0],{"canonical_generation":"g1"})
    hashes[REQ[1]]=put(tmp_path,REQ[1],{"x":1})
    hashes[REQ[2]]=put(tmp_path,REQ[2],{"x":2})
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

def test_current_context_passes(tmp_path):
    now=datetime(2026,10,1,20,0,tzinfo=timezone.utc)
    assert validate_context(ctx(tmp_path,now),root=tmp_path,now=now)["pass"] is True

def test_stale_world_dependency_fails(tmp_path):
    now=datetime(2026,10,1,20,10,tzinfo=timezone.utc)
    c=ctx(tmp_path,now-timedelta(minutes=10))
    out=validate_context(c,root=tmp_path,now=now)
    assert out["pass"] is False
    assert any(x.startswith("VOLATILE_DEPENDENCY_STALE") for x in out["errors"])

def test_canonical_state_change_fails(tmp_path):
    now=datetime(2026,10,1,20,0,tzinfo=timezone.utc)
    c=ctx(tmp_path,now)
    put(tmp_path,REQ[1],{"x":"changed"})
    out=validate_context(c,root=tmp_path,now=now)
    assert "CANONICAL_STATE_CHANGED:"+REQ[1] in out["errors"]

def test_unknown_material_dependency_fails(tmp_path):
    now=datetime(2026,10,1,20,0,tzinfo=timezone.utc)
    c=ctx(tmp_path,now); c["unknown_material_dependencies"]=["mystery"]
    assert validate_context(c,root=tmp_path,now=now)["pass"] is False

def test_incomplete_world_inventory_fails(tmp_path):
    now=datetime(2026,10,1,20,0,tzinfo=timezone.utc)
    c=ctx(tmp_path,now); c["material_world_state_dependencies_complete"]=False
    assert validate_context(c,root=tmp_path,now=now)["pass"] is False
