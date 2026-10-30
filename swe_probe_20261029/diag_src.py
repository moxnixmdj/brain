import sys, pathlib, shutil, json
sys.path.insert(0,'.')
from canonical.runtime import swe_typed_plan_v1 as tp, live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/dgs")
if B.exists(): shutil.rmtree(B)
BUG="def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n"
T=("import unittest\nfrom app.calc import add, mul\n\nclass T(unittest.TestCase):\n"
   "    def test_add(self):\n        self.assertEqual(add(2,3),5)\n")
d=B
for rel,txt in {"src/app/__init__.py":"","src/app/calc.py":BUG,"tests/test_calc.py":T}.items():
    p=d/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt)
g=f"Repair the python source {d}/src/app/calc.py so that the unit test in {d}/tests/test_calc.py passes, and save the repair report to {d}/r.json."
print("plan:", json.dumps(tp.plan_report(g, pathlib.Path('.').resolve()))[:330])
r=adm.solve({"task_id":"S","goal":g})
print("status:", r.get("status"), "| cap:", r.get("compiled_capability_id"), "| reason:", str(r.get("reason"))[:140])
print("source fixed:", "return a + b" in (d/"src/app/calc.py").read_text())
print("stated errors:", (r.get("stated_acceptance_errors") or [None])[0])
