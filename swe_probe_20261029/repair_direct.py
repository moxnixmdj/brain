import json, sys, pathlib, subprocess
sys.path.insert(0,'.')
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as m
import inspect
print([n for n,o in inspect.getmembers(m, inspect.isfunction)])
D = pathlib.Path("canonical/astra_runtime/tmp/swe2/repair_full").resolve()
sandbox = pathlib.Path('.').resolve()
args = {"capability_id":"python.patch.search.test_guided.ast.v1",
        "source_path": str(D/"pkg/calc.py"),
        "test_paths": [str(D/"pkg/test_calc.py")],
        "test_argv": [sys.executable, "-B", str(D/"pkg/test_calc.py")],
        "output_path": str(D/"a2.json")}
r = m.run(args, sandbox)
print(json.dumps(r, indent=1, default=str)[:3000])
# now run the test as stated to see if the stated argv even works
p = subprocess.run(args["test_argv"], capture_output=True, text=True, cwd=str(D))
print("BASELINE TEST rc", p.returncode, p.stderr[-400:])
