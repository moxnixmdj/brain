import sys, pathlib, shutil
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
B=pathlib.Path("/tmp/outside_project")
if B.exists(): shutil.rmtree(B)
B.mkdir(parents=True)
(B/"calc.py").write_text("def add(a, b):\n    return a - b\n")
(B/"test_calc.py").write_text("import unittest\nfrom calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n")
g=f"Repair the python source {B}/calc.py so that the unit test in {B}/test_calc.py passes, and save the report to {B}/r.json."
r=adm.solve({"task_id":"OUT","goal":g, "root": str(B)})
print("status:", r.get("status"), "| cap:", r.get("compiled_capability_id"), "| reason:", str(r.get("reason"))[:120])
print("accepted 'root' kwarg?", 'root' in __import__('inspect').signature(adm.solve).parameters)
