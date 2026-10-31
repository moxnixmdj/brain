import sys, pathlib, shutil, json
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/rc")
if B.exists(): shutil.rmtree(B)
BUG="def add(a, b):\n    return a - b\n"
def mk(n):
    d=B/n; d.mkdir(parents=True)
    (d/"calc.py").write_text(BUG)
    (d/"test_calc.py").write_text("import unittest\nfrom calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n")
    return d
PAIRS=[
 ("rename", "Rename the parameter a to x in the python module {S}.", "Rename the parameter a to x in the python module {S} and save the report to {D}/r.json."),
 ("repair", "Repair {S} so the unit test in {T} passes.", "Repair {S} so the unit test in {T} passes, and save the repair report to {D}/r.json."),
 ("find_callers", "Find every caller of the function add in {S}.", "Find every caller of the function add in {S} and save the result to {D}/c.json."),
]
for name, a, b in PAIRS:
    for label, tmpl in (("no-report", a), ("with-report", b)):
        d=mk(f"{name}_{label}")
        g=tmpl.format(S=f"{d}/calc.py", T=f"{d}/test_calc.py", D=str(d))
        r=adm.solve({"task_id":f"{name}_{label}","goal":g})
        print(f"{name:13s} {label:12s} pass={str(r.get('pass')):5s} {str(r.get('status'))[:44]:46s} {str(r.get('compiled_capability_id'))[:34]}")
