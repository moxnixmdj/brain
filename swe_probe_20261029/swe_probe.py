import json, shutil, sys, time, pathlib
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm

BASE = pathlib.Path("canonical/astra_runtime/tmp/swe2")
if BASE.exists(): shutil.rmtree(BASE)
BASE.mkdir(parents=True, exist_ok=True)

SRC = "def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n"
TEST = ("import unittest\nfrom pkg.calc import add, mul\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(2,3),5)\n    def test_mul(self):\n        self.assertEqual(mul(2,3),6)\n")
UTIL = "def add(a,b):\n    return a+b\n\n\ndef caller():\n    return add(1,2)\n\n\ndef other():\n    return add(3,4)\n"

def make(n):
    d = BASE/n; (d/'pkg').mkdir(parents=True, exist_ok=True)
    (d/'pkg'/'__init__.py').write_text('')
    (d/'pkg'/'calc.py').write_text(SRC)
    (d/'pkg'/'test_calc.py').write_text(TEST)
    (d/'pkg'/'util.py').write_text(UTIL)
    return d

TASKS = [
 ("repair_full",  "Repair the python source {D}/pkg/calc.py so that the unit test in {D}/pkg/test_calc.py passes, and save the repair report to {D}/a.json.", "src_fixed"),
 ("fix_broken",   "the add function in {D}/pkg/calc.py is broken, fix it so its tests pass", "src_fixed"),
 ("fix_short",    "fix {D}/pkg/calc.py", "src_fixed"),
 ("bug_report",   "Bug: {D}/pkg/calc.py add() returns the wrong value. Failing test: {D}/pkg/test_calc.py.", "src_fixed"),
 ("rename_param", "Rename the parameter a to x in the python module {D}/pkg/util.py and save the report to {D}/r.json.", "renamed"),
 ("rename_calls", "Rename the function add to plus everywhere it is used in {D}/pkg.", "renamed"),
 ("write_test",   "Write a unit test for {D}/pkg/util.py", "test_written"),
 ("explain_fail", "Explain why the test in {D}/pkg/test_calc.py fails.", "explained"),
 ("find_callers", "Find every caller of the function add in {D}/pkg/util.py", "artifact"),
 ("extract_fn",   "Extract the body of add into a new helper function in {D}/pkg/util.py", "refactored"),
 ("type_check",   "Type-check the file {D}/pkg/util.py", "reported"),
 ("lint",         "Lint the python file {D}/pkg/util.py", "reported"),
 ("git_log",      "Show the last three git commits in this repository.", "listed"),
 ("git_commit",   "Commit the staged changes with the message 'wip' and show the resulting commit sha.", "committed"),
 ("debug_test",   "Run {D}/pkg/test_calc.py under a debugger and tell me where add fails.", "debugged"),
 ("profile",      "Profile {D}/pkg/calc.py and tell me which function is slowest.", "profiled"),
 ("multi_file",   "Add a subtract(a,b) function to {D}/pkg/calc.py and a matching passing test in {D}/pkg/test_calc.py.", "multi"),
 ("dep_add",      "Add requests as a dependency to the project and pin its version.", "dep"),
]

def run(name, tmpl):
    d = make(name)
    goal = tmpl.format(D=str(d))
    t0 = time.time()
    try:
        r = adm.solve({"task_id": name, "goal": goal})
    except Exception as e:
        r = {"status": "EXCEPTION", "pass": False, "reason": repr(e)[:150]}
    dt = (time.time()-t0)*1000
    # independent oracle: did the world actually change correctly?
    src = (d/'pkg'/'calc.py').read_text()
    util = (d/'pkg'/'util.py').read_text()
    artifacts = sorted(p.name for p in d.rglob('*') if p.is_file() and p.name not in {'calc.py','util.py','test_calc.py','__init__.py'})
    world = {"add_fixed": "def add(a, b):\n    return a + b" in src,
             "renamed": "def plus(" in util or "def add(x" in util,
             "new_files": artifacts}
    return dict(task=name, status=r.get("status"), pass_=r.get("pass"),
                cap=r.get("compiled_capability_id") or (r.get("typed_swe_retry") or {}).get("selected_capability"),
                ms=round(dt), world=world, reason=str(r.get("reason"))[:100])

rows = [run(n,t) for n,t,_ in TASKS]
for r in rows:
    print(f"{r['task']:14s} pass={str(r['pass_']):5s} {str(r['status'])[:46]:48s} {str(r['cap'])[:38]:40s} {r['ms']:5d}ms  world={r['world']}")
json.dump(rows, open('swe_probe_20261029/swe2.json','w'), indent=1)
print("\nPASS", sum(1 for r in rows if r['pass_'] is True), "/", len(rows), " mean ms", round(sum(r['ms'] for r in rows)/len(rows)))
