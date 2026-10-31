import json, os, shutil, subprocess, sys, time, pathlib
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm

BASE = pathlib.Path("canonical/astra_runtime/tmp/swe12")
if BASE.exists(): shutil.rmtree(BASE)
BASE.mkdir(parents=True)

def make(n):
    d = BASE/n; (d/'pkg').mkdir(parents=True)
    (d/'pkg'/'__init__.py').write_text('')
    (d/'pkg'/'calc.py').write_text(
        "def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n\n\ndef broken(x):\n    return x/0\n")
    (d/'pkg'/'test_calc.py').write_text(
        "import unittest\nfrom pkg.calc import add, mul\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n    def test_mul(self):\n        self.assertEqual(mul(2,3),6)\n")
    (d/'pkg'/'util.py').write_text("def add(a,b):\n    return a+b\n\n\ndef caller():\n    return add(1,2)\n\n\ndef other():\n    return add(3,4)\n")
    return d

TASKS = [
 ("repair_full", "Repair the python source {D}/pkg/calc.py so that the unit test in {D}/pkg/test_calc.py passes, and save the repair report to {D}/a.json."),
 ("fix_broken", "the add function in {D}/pkg/calc.py is broken, fix it so its tests pass"),
 ("fix_short", "fix {D}/pkg/calc.py"),
 ("bug_report", "Bug: {D}/pkg/calc.py add() returns the wrong value. Failing test: {D}/pkg/test_calc.py."),
 ("rename_param", "Rename the parameter a to x in the python module {D}/pkg/util.py and save the report to {D}/r.json."),
 ("rename_callsites", "Rename the function add to plus everywhere it is used in {D}/pkg."),
 ("write_unit_test", "Write a unit test for {D}/pkg/util.py"),
 ("explain_fail", "Explain why the test in {D}/pkg/test_calc.py fails."),
 ("find_callers", "Find every caller of the function add in {D}/pkg/util.py"),
 ("refactor_extract", "Extract the body of add into a new helper function in {D}/pkg/util.py"),
 ("type_check", "Type-check the file {D}/pkg/util.py"),
 ("lint", "Lint the python file {D}/pkg/util.py"),
 ("git_log", "Show the last three git commits in this repository."),
 ("git_commit", "Commit the staged changes with the message 'wip' and show the resulting commit sha."),
]

root = pathlib.Path('.').resolve()
out=[]
for name, tmpl in TASKS:
    d = make(name)
    goal = tmpl.format(D=str(d))
    t0=time.time()
    try:
        r = adm.solve({"task_id":name,"goal":goal,"root":str(root)})
    except Exception as e:
        r={"status":"EXCEPTION","error":repr(e)[:200]}
    dt=(time.time()-t0)*1000
    out.append({"task":name,"status":r.get("status"),"cap":r.get("compiled_capability_id") or r.get("selected_capability"),
                "ms":round(dt),"reason":(r.get("reason") or "")[:90]})
    print(f"{name:18s} {str(r.get('status'))[:44]:46s} {str(r.get('compiled_capability_id'))[:40]:42s} {round(dt):5d}ms")
json.dump(out, open('.arena_probe/swe12.json','w'), indent=1)
npass=sum(1 for o in out if o['status']=='PASS')
print(f"\nPASS {npass}/{len(out)}  mean {round(sum(o['ms'] for o in out)/len(out))}ms")
