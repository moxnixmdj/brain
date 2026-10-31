import sys, pathlib, faulthandler
sys.path.insert(0,'.')
faulthandler.dump_traceback_later(40, exit=True)
from canonical.runtime import live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/hang"); 
g=f"Repair {B}/calc.py so the unit test in {B}/test_calc.py passes."
r=adm.solve({"task_id":"HANG","goal":g})
print("status", r.get("status"))
