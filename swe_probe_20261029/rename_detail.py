import sys, pathlib, json, shutil
sys.path.insert(0,'.')
from canonical.runtime import swe_typed_plan_v1 as tp
from canonical.runtime import live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/rn"); 
if B.exists(): shutil.rmtree(B)
(B/"pkg").mkdir(parents=True)
(B/"pkg/util.py").write_text("def add(a,b):\n    return a+b\n\n\ndef caller():\n    return add(1,2)\n")
goals={
 "pkg": f"Rename the parameter a to x in the python module {B}/pkg/util.py and save the report to {B}/r.json.",
 "flat": f"Rename the parameter a to x in the python module {B}/pkg/util.py.",
 "sym": f"Rename the function add to plus in {B}/pkg/util.py and save the report to {B}/s.json.",
}
for k,g in goals.items():
    print('==',k, json.dumps(tp.plan_report(g, pathlib.Path('.').resolve()))[:260])
    r=adm.solve({"task_id":k,"goal":g})
    print('   solve:', r.get("status"), '|', r.get("compiled_capability_id"), '|', str(r.get("reason"))[:80])
