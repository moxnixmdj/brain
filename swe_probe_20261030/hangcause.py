import sys, pathlib, faulthandler
sys.path.insert(0,'.')
faulthandler.dump_traceback_later(30, exit=True)
from canonical.runtime import live_brain_route_admission_v1 as adm
d=pathlib.Path("canonical/astra_runtime/tmp/hard30/compose").resolve()
g=(f"Extract the multiplication in line_total in {d}/app/models.py into a helper, update the caller in "
   f"{d}/app/service.py, and make the tests in {d}/tests pass.")
adm.solve({"task_id":"HC","goal":g})
print("finished")
