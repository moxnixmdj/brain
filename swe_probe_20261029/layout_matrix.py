import sys, pathlib, shutil, json
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
B = pathlib.Path("canonical/astra_runtime/tmp/lm")
if B.exists(): shutil.rmtree(B)
BUG = "def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n"
TESTSRC = ("import unittest\nfrom {imp} import add, mul\n\nclass T(unittest.TestCase):\n"
           "    def test_add(self):\n        self.assertEqual(add(2,3),5)\n    def test_mul(self):\n        self.assertEqual(mul(2,3),6)\n")
LAYOUTS = {
 "flat":        ({"calc.py": BUG, "test_calc.py": TESTSRC.format(imp="calc")}, "calc.py", "test_calc.py", ""),
 "package":     ({"pkg/__init__.py":"", "pkg/calc.py": BUG, "pkg/test_calc.py": TESTSRC.format(imp="pkg.calc")}, "pkg/calc.py", "pkg/test_calc.py", ""),
 "src_layout":  ({"src/app/__init__.py":"", "src/app/calc.py": BUG, "tests/test_calc.py": TESTSRC.format(imp="app.calc")}, "src/app/calc.py", "tests/test_calc.py", ""),
 "root_pkg":    ({"app/__init__.py":"", "app/calc.py": BUG, "tests/test_calc.py": TESTSRC.format(imp="app.calc")}, "app/calc.py", "tests/test_calc.py", ""),
}
def mk(n, files):
    d=B/n
    for rel,txt in files.items():
        p=d/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt)
    return d
def goal(task, d, src, test):
    S=f"{d}/{src}"; T=f"{d}/{test}"
    return {
     "repair": f"Repair the python source {S} so that the unit test in {T} passes, and save the repair report to {d}/r.json.",
     "find_callers": f"Find every caller of the function add in {S}",
     "rename": f"Rename the parameter a to x in the python module {S} and save the report to {d}/rn.json.",
     "write_test": f"Write a unit test for {S}",
     "lint": f"Lint the python file {S} and save the report to {d}/l.json.",
     "type_check": f"Type-check the file {S}",
    }[task]
results={}
for lname,(files,src,test,_) in LAYOUTS.items():
    row={}
    for task in ("repair","find_callers","rename","write_test","lint","type_check"):
        d=mk(f"{lname}_{task}", files)
        try:
            r=adm.solve({"task_id":f"{lname}_{task}","goal":goal(task,d,src,test)})
            ok = r.get("pass") is True
            row[task]=(ok, str(r.get("compiled_capability_id"))[:34])
        except Exception as e:
            row[task]=(False, "EXC:"+type(e).__name__)
    results[lname]=row
    print(f"{lname:11s} " + "  ".join(f"{t}:{'P' if row[t][0] else '.'}" for t in row))
print()
for t in ("repair","find_callers","rename","write_test","lint","type_check"):
    print(f"{t:13s} " + "  ".join(f"{l}:{'PASS' if results[l][t][0] else 'fail'}" for l in LAYOUTS))
json.dump({l:{t:list(v) for t,v in r.items()} for l,r in results.items()}, open('swe_probe_20261029/layout_matrix.json','w'), indent=1)
