import sys; sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
g="Repair the python source /tmp/outside30/app/m.py so that the unit test /tmp/outside30/t.py passes."
r=adm.solve({"task_id":"OUT","goal":g})
print("status:", r.get("status"), "| cap:", r.get("compiled_capability_id"), "| pass:", r.get("pass"))
