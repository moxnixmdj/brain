import sys, pathlib, shutil, json, os
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/st")
if B.exists(): shutil.rmtree(B)
def mk(n, extra=None):
    d=B/n; d.mkdir(parents=True)
    (d/"calc.py").write_text("def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n")
    if extra: (d/"report.json").write_text('{"x":1}')
    return d
G=lambda d: f"Find every caller of the function add in {d}/calc.py"
for n,extra in (("clean",None),("withfile","yes")):
    d=mk(n, extra)
    r1=adm.solve({"task_id":"A"+n,"goal":G(d)})
    r2=adm.solve({"task_id":"B"+n,"goal":G(d)})
    print(f"{n:9s} first={r1.get('status')[:44]:46s} second={r2.get('status')[:44]}")
# changed tree state: run a repair first, then the caller goal
d=mk("after_repair")
rep=f"Repair the python source {d}/calc.py so that the unit test in {d}/test_calc.py passes, and save the report to {d}/r.json."
(d/"test_calc.py").write_text("import unittest\nfrom calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n")
r=adm.solve({"task_id":"R","goal":rep}); print("repair:", r.get("status")[:50])
r3=adm.solve({"task_id":"C","goal":G(d)}); print("callers after repair:", r3.get("status"))
