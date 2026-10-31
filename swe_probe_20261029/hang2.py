import sys, pathlib, faulthandler
sys.path.insert(0,'.')
faulthandler.dump_traceback_later(25, exit=True)
from canonical.runtime import live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/comp").resolve()
r=adm.solve({"task_id":"RT","goal":f"Run the tests in {B} and save a pass-rate report to {B}/rate.json."})
print(r.get("status"), r.get("compiled_capability_id"))
