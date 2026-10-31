import sys, pathlib, shutil, json
sys.path.insert(0,'.')
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as A
sandbox=pathlib.Path('.').resolve()
B=pathlib.Path("canonical/astra_runtime/tmp/ap")
if B.exists(): shutil.rmtree(B)
BUG="def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n"
def mk(n, files):
    d=B/n
    for rel,txt in files.items():
        p=d/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt)
    return d
CASES={
 "flat":{"calc.py":BUG,"test_calc.py":"import unittest\nfrom calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"},
 "pkg":{"pkg/__init__.py":"","pkg/calc.py":BUG,"pkg/test_calc.py":"import unittest\nfrom pkg.calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"},
 "src":{"src/app/__init__.py":"","src/app/calc.py":BUG,"tests/test_calc.py":"import unittest\nfrom app.calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"},
}
for name,files in CASES.items():
    d=mk(name,files)
    src = d/("calc.py" if name=="flat" else "pkg/calc.py" if name=="pkg" else "src/app/calc.py")
    root = d/("." if name=="flat" else "pkg" if name=="pkg" else "src")
    before=src.read_text()
    args={"capability_id":"python.software.repair.apply.verified.v1",
          "source_root":str(root.resolve()),"output_path":str((d/"repair.json").resolve()),
          "timeout_s":120}
    try:
        r=A.run(args, sandbox)
        print(f"{name:5s} pass={r.get('pass')} status={r.get('status')} applied={r.get('applied')} "
              f"pre_rc={r.get('pre_apply_test_returncode')} post_rc={r.get('post_apply_test_returncode')} "
              f"source_changed={src.read_text()!=before}")
    except Exception as e:
        print(f"{name:5s} RAISED {type(e).__name__}:{e}")
