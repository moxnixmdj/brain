"""Deterministic replay for the P3 V11 delta.

The already-verified source-positive adequacy primitive is replaced only at its
module interface so stale Sprite snapshots need not materialize its historical
dependency chain. Exact V11 kernel/front-door bytes execute normally; tests
control the predecessor result explicitly.
"""
from pathlib import Path
import sys
import types

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

stub=types.ModuleType("canonical.runtime.source_positive_adequacy_db_admission_v1")
stub.evaluate=lambda payload: {
    "pass":False,
    "status":"UNRESOLVED__REPLAY_STUB_DEFAULT",
    "db_admission_authorized":False,
}
sys.modules["canonical.runtime.source_positive_adequacy_db_admission_v1"]=stub

import canonical.tests.test_p3_source_positive_selection_cell_v1 as cell
import canonical.tests.test_p3_real_context_v3_admission_v11 as front

tests=[]
for m in (cell,front):
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
