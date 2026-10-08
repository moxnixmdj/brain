"""Deterministic replay for P3 V11 source-positive selection and routing."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

import canonical.tests.test_p3_source_positive_selection_cell_v1 as cell
import canonical.tests.test_p3_real_context_v3_admission_v11 as front

mods=[cell,front]
tests=[]
for m in mods:
    tests.extend((m.__name__+"."+n,f) for n,f in vars(m).items() if n.startswith("test_") and callable(f))
failed=[]
for name,fn in tests:
    try:
        fn()
        print("PASS",name)
    except Exception as exc:
        failed.append((name,repr(exc)))
        print("FAIL",name,repr(exc))
print("RESULT",len(tests)-len(failed),"/",len(tests))
if failed:
    raise SystemExit(1)
