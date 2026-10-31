import sys, pathlib, shutil, json
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/comp")
if B.exists(): shutil.rmtree(B)
d=B; d.mkdir(parents=True)
(d/"calc.py").write_text("def add(a,b):\n    return a+b\n\n\ndef mul(a,b):\n    return a*b\n")
GOALS=[
 f"Index the symbols in {d}/calc.py and write the index to {d}/symbols.json.",
 f"Find the callers of add in {d}/calc.py and then write them to {d}/c.json.",
 f"Run the tests in {d} and save a pass-rate report to {d}/rate.json.",
 f"Create a report of the functions in {d}/calc.py as JSON at {d}/f.json.",
]
for g in GOALS:
    r=adm.solve({"task_id":"C","goal":g})
    print(f"{r.get('pass')!s:5s} {str(r.get('status'))[:52]:54s} {str(r.get('compiled_capability_id'))[:40]}  :: {g.split(' and ')[0][:44]}")
