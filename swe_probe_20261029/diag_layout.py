import sys, pathlib, shutil, json
sys.path.insert(0,'.')
from canonical.runtime import swe_typed_plan_v1 as tp, live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/dgl")
if B.exists(): shutil.rmtree(B)
BUG="def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n"
T=lambda imp:("import unittest\nfrom %s import add, mul\n\nclass T(unittest.TestCase):\n"
   "    def test_add(self):\n        self.assertEqual(add(2,3),5)\n" % imp)
LAY={"src_layout":({"src/app/__init__.py":"","src/app/calc.py":BUG,"tests/test_calc.py":T("app.calc")},"src/app/calc.py","tests/test_calc.py"),
     "root_pkg":({"app/__init__.py":"","app/calc.py":BUG,"tests/test_calc.py":T("app.calc")},"app/calc.py","tests/test_calc.py")}
for name,(files,src,test) in LAY.items():
    d=B/name
    for rel,txt in files.items():
        p=d/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt)
    g=f"Repair the python source {d}/{src} so that the unit test in {d}/{test} passes, and save the repair report to {d}/r.json."
    rep=tp.plan_report(g, pathlib.Path('.').resolve())
    print(name, '->', json.dumps(rep)[:400])
    r=adm.solve({"task_id":name,"goal":g})
    print('   ', r.get("status"), '|', r.get("compiled_capability_id"), '|', str(r.get("reason"))[:100])
