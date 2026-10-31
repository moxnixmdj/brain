import json, sys, pathlib, subprocess, shutil
sys.path.insert(0,'.')
sandbox = pathlib.Path('.').resolve()
B = pathlib.Path("canonical/astra_runtime/tmp/layout"); 
if B.exists(): shutil.rmtree(B)
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as m

def mk(name, files):
    d = B/name
    for rel, txt in files.items():
        p = d/rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt)
    return d

CASES = {
 # flat module, sibling test, relative import (the corridor the suite measures)
 "flat": {"calc.py":"def add(a,b):\n    return a-b\n\n\ndef mul(a,b):\n    return a*b\n",
          "test_calc.py":"import unittest\nfrom calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"},
 # package layout, absolute import (standard src layout)
 "pkg_abs": {"pkg/__init__.py":"",
             "pkg/calc.py":"def add(a,b):\n    return a-b\n\n\ndef mul(a,b):\n    return a*b\n",
             "pkg/test_calc.py":"import unittest\nfrom pkg.calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"},
 # package layout, src/ dir (the most common real layout)
 "src_layout": {"src/app/__init__.py":"",
                "src/app/calc.py":"def add(a,b):\n    return a-b\n\n\ndef mul(a,b):\n    return a*b\n",
                "tests/test_calc.py":"import unittest\nfrom app.calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"},
}
for name, files in CASES.items():
    d = mk(name, files)
    src = d/("calc.py" if name=="flat" else "pkg/calc.py" if name=="pkg_abs" else "src/app/calc.py")
    test = d/("test_calc.py" if name=="flat" else "pkg/test_calc.py" if name=="pkg_abs" else "tests/test_calc.py")
    argv = [sys.executable, "-B", str(test.resolve())]
    args = {"capability_id":"python.patch.search.test_guided.ast.v1","source_path":str(src.resolve()),
            "test_paths":[str(test.resolve())], "test_argv":argv, "output_path":str((d/"report.json").resolve())}
    r = m.run(args, sandbox)
    p = subprocess.run(argv, capture_output=True, text=True, cwd=str(d))
    print(f"{name:11s} patches={len(r.get('patches') or [])} pass={r.get('pass')} applied={r.get('applied')} "
          f"| stated test alone rc={p.returncode} {(p.stderr.strip().splitlines()[-1] if p.stderr.strip() else '')[:60]}")
