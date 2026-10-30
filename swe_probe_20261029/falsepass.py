import sys, pathlib, shutil, json, subprocess
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/fp")
if B.exists(): shutil.rmtree(B)
d=B/"c"; d.mkdir(parents=True)
(d/"calc.py").write_text("def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n")
test=d/"test_calc.py"
test.write_text("import unittest\nfrom calc import add, mul\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n    def test_mul(self):\n        self.assertEqual(mul(2,3),6)\n")
g=f"Repair the python source {d}/calc.py so that the unit test in {test} passes, and save the repair report to {d}/r.json."
r=adm.solve({"task_id":"FP","goal":g})
p=subprocess.run([sys.executable,"-m","unittest","test_calc","-v"],cwd=str(d),capture_output=True,text=True)
print("door verdict :", r.get("status"))
print("door pass    :", r.get("pass"))
print("STATED ACCEPTANCE on the real tree -> unittest rc =", p.returncode)
print((p.stderr or "").strip().splitlines()[-3:])
