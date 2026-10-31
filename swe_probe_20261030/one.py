import sys, json, time, pathlib
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
tag, goal = sys.argv[1], sys.argv[2]
t0=time.time()
try:
    r=adm.solve({"task_id":tag,"goal":goal})
    print(json.dumps({"tag":tag,"pass":r.get("pass"),"status":str(r.get("status"))[:70],
                      "cap":r.get("compiled_capability_id"),"ms":round((time.time()-t0)*1000)}), flush=True)
except Exception as e:
    print(json.dumps({"tag":tag,"exc":type(e).__name__+":"+str(e)[:80],"ms":round((time.time()-t0)*1000)}), flush=True)
