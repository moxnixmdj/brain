import json, sys, pathlib
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm, swe_typed_plan_v1 as tp
BASE = pathlib.Path("canonical/astra_runtime/tmp/swe2")
cases = {
 "repair_full": "Repair the python source {D}/pkg/calc.py so that the unit test in {D}/pkg/test_calc.py passes, and save the repair report to {D}/a.json.",
 "rename_param": "Rename the parameter a to x in the python module {D}/pkg/util.py and save the report to {D}/r.json.",
 "fix_broken": "the add function in {D}/pkg/calc.py is broken, fix it so its tests pass",
}
for k,t in cases.items():
    g = t.format(D=f"{BASE}/{k}")
    plan = tp.build_plan(g, pathlib.Path('.').resolve())
    print('='*20,k,'plan:', 'None' if plan is None else plan[2].get('selected_capability'))
    if plan is None: continue
    r = adm._solve_body({"task_id":k+"_forced","goal":g,"_typed_swe_plan":plan})
    keep = {kk: r.get(kk) for kk in ('status','pass','reason','executed','compiled_capability_id','tool_truth_errors','route_admission')}
    print(json.dumps(keep, indent=1, default=str)[:2500])
