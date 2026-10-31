import sys, pathlib, shutil, json
sys.path.insert(0,'.')
from canonical.runtime import swe_typed_plan_v1 as tp, live_brain_route_admission_v1 as adm
B=pathlib.Path("canonical/astra_runtime/tmp/dgr")
if B.exists(): shutil.rmtree(B)
(B/"pkg").mkdir(parents=True)
(B/"pkg/util.py").write_text("def add(a,b):\n    return a+b\n\n\ndef caller():\n    return add(1,2)\n")
(B/"pkg/test_util.py").write_text("import unittest\nfrom pkg.util import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(1,2),3)\n")
g=f"Rename the parameter a to x in the python module {B}/pkg/util.py and save the report to {B}/rn.json."
print("plan:", json.dumps(tp.plan_report(g, pathlib.Path('.').resolve()))[:300])
r=adm.solve({"task_id":"RN","goal":g})
print("status:", r.get("status"), "| cap:", r.get("compiled_capability_id"), "| reason:", str(r.get("reason"))[:120])
print("renamed:", "def add(x" in (B/"pkg/util.py").read_text(), "| files:", sorted(p.name for p in (B).rglob('*') if p.is_file()))
retry=(r.get("typed_swe_retry") or {})
print("retry:", json.dumps(retry)[:200])
