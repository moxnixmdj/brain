import sys, json, time, pathlib
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
g=sys.argv[1]; tid=sys.argv[2]
t0=time.time()
r=adm.solve({"task_id":tid,"goal":g})
print(json.dumps({"status":r.get("status"),"pass":r.get("pass"),"cap":r.get("compiled_capability_id"),
                  "reason":str(r.get("reason"))[:120],"ms":round((time.time()-t0)*1000)}))
