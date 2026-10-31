import sys, pathlib, shutil, json, hashlib
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
B = pathlib.Path("canonical/astra_runtime/tmp/det")
SRC="def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n"
TEST=("import unittest\nfrom calc import add, mul\n\nclass T(unittest.TestCase):\n"
      "    def test_add(self):\n        self.assertEqual(add(2,3),5)\n")
def mk(n):
    d=B/n; d.mkdir(parents=True, exist_ok=True)
    (d/"calc.py").write_text(SRC); (d/"test_calc.py").write_text(TEST)
    return d
GOALS={
 "a": "Repair the python source {D}/calc.py so that the unit test in {D}/test_calc.py passes, and save the report to {D}/r.json.",
 "b": "fix {D}/calc.py",
 "c": "Lint the python file {D}/calc.py and save the report to {D}/l.json.",
 "d": "Find every caller of the function add in {D}/calc.py",
 "e": "Commit the staged changes with the message 'wip' and show the resulting commit sha.",
}
runs={}
for k,t in GOALS.items():
    seen=[]
    for i in (1,2,3):
        if B.exists(): pass
        d=mk(f"{k}{i}")
        try:
            r=adm.solve({"task_id":f"{k}{i}","goal":t.format(D=str(d))})
            seen.append((r.get("status"), r.get("compiled_capability_id")))
        except Exception as e:
            seen.append(("EXC", repr(e)[:60]))
    uniq=len(set(seen))
    print(f"{k}: {uniq} distinct verdict(s) over 3 identical clean trees -> {set(seen)}")
