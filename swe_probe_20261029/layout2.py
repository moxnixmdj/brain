import sys, pathlib, shutil, json
sys.path.insert(0,'.')
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as m
sandbox = pathlib.Path('.').resolve()
B = pathlib.Path("canonical/astra_runtime/tmp/layout2")
if B.exists(): shutil.rmtree(B)
CASES = {
 "flat_naive": ({"calc.py":"def add(a,b):\n    return a-b\n\n\ndef mul(a,b):\n    return a*b\n",
   "test_calc.py":"import unittest\nfrom calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"}, "calc.py","test_calc.py"),
 "flat_loader": (None, None, None),
 "pkg_abs": ({"pkg/__init__.py":"",
   "pkg/calc.py":"def add(a,b):\n    return a-b\n\n\ndef mul(a,b):\n    return a*b\n",
   "pkg/test_calc.py":"import unittest\nfrom pkg.calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"}, "pkg/calc.py","pkg/test_calc.py"),
 "src_layout": ({"src/app/__init__.py":"",
   "src/app/calc.py":"def add(a,b):\n    return a-b\n\n\ndef mul(a,b):\n    return a*b\n",
   "tests/test_calc.py":"import unittest\nfrom app.calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"}, "src/app/calc.py","tests/test_calc.py"),
 "root_layout": ({"app/__init__.py":"",
   "app/calc.py":"def add(a,b):\n    return a-b\n\n\ndef mul(a,b):\n    return a*b\n",
   "tests/test_calc.py":"import unittest\nfrom app.calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"}, "app/calc.py","tests/test_calc.py"),
}
def mk(name, files):
    d=B/name
    for rel,txt in files.items():
        p=d/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt)
    return d
for name,(files,sp,tp) in CASES.items():
    if files is None:  # same flat tree, but the LOADER argv the machine already has
        d=B/"flat_naive"; sp="calc.py"; tp="test_calc.py"
    else:
        d=mk(name,files)
    src=(d/sp).resolve(); test=(d/tp).resolve()
    for kind,argv in (("file",[sys.executable,"-B",str(test)]),
                      ("loader",m.suite_argv(sys.executable,str(test)))):
        args={"capability_id":"python.patch.search.test_guided.ast.v1","source_path":str(src),
              "test_paths":[str(test)],"test_argv":argv,"output_path":str((d/f"rep_{kind}.json").resolve())}
        try:
            r=m.run(args,sandbox)
            print(f"{name:12s} argv={kind:6s} -> pass={r.get('pass')} patches={len(r.get('patches') or [])} status={r.get('status')}")
        except Exception as e:
            print(f"{name:12s} argv={kind:6s} -> RAISED {type(e).__name__}:{e}")
