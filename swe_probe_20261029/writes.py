import sys, pathlib, shutil, json, hashlib
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/wr")
if B.exists(): shutil.rmtree(B)
def mk(n):
    d=B/n; d.mkdir(parents=True)
    (d/"calc.py").write_text("def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n")
    (d/"test_calc.py").write_text("import unittest\nfrom calc import add, mul\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n    def test_mul(self):\n        self.assertEqual(mul(2,3),6)\n")
    return d
d=mk("fix1")
before=(d/"calc.py").read_text()
g=f"Repair the python source {d}/calc.py so that the unit test in {d}/test_calc.py passes, and save the repair report to {d}/r.json."
r=adm.solve({"task_id":"FIX","goal":g})
after=(d/"calc.py").read_text()
print("status:", r.get("status"))
print("SOURCE CHANGED BY THE MACHINE:", before!=after)
print("source after:", repr(after))
print("report exists:", (d/"r.json").exists(), "| files:", sorted(p.name for p in d.iterdir()))
if (d/"r.json").exists():
    rep=json.loads((d/"r.json").read_text())
    print("report keys:", list(rep)[:14])
    print("report status:", rep.get("status"), "| applied:", rep.get("applied"), "| patches:", len(rep.get("patches") or []))
