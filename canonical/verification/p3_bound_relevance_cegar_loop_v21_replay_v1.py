"""Deterministic V21 delta replay on stale independent carriers.

Historical predecessors are isolated at module interfaces. The exact V21 runtime
and tests execute normally; each test explicitly patches predecessor outcomes.
"""
from pathlib import Path
import sys, types

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

m1=types.ModuleType("canonical.runtime.p3_robust_policy_adequacy_cegar_v1")
m1.solve=lambda problem: {"pass":False,"status":"FAIL_CLOSED","reason":"REPLAY_STUB"}
sys.modules[m1.__name__]=m1

m2=types.ModuleType("canonical.runtime.selected_semantic_truth_certificate_v1")
m2.evaluate=lambda payload: {"pass":False,"status":"UNKNOWN__REPLAY_STUB","predicate_truth":"UNKNOWN","truthful_precommitment_observation":False}
sys.modules[m2.__name__]=m2

m3=types.ModuleType("canonical.runtime.p3_source_positive_selection_cell_v1")
m3.evaluate=lambda payload,repo_root=None: {"pass":False,"status":"FAIL_CLOSED","reason":"REPLAY_STUB"}
sys.modules[m3.__name__]=m3

m4=types.ModuleType("canonical.runtime.p3_real_context_v3_admission_v11")
m4.evaluate=lambda payload,repo_root=None: {
    "pass":False,
    "nonbinding_capacity_reason":"CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY",
    "terminal_authority":False,
    "terminal_credit_delta":0,
}
sys.modules[m4.__name__]=m4

import canonical.tests.test_p3_bound_relevance_cegar_loop_v1 as t1
import canonical.tests.test_p3_real_context_v3_admission_v12 as t2

tests=[]
for t in (t1,t2):
    tests.extend((t.__name__+"."+n,f) for n,f in vars(t).items() if n.startswith("test_") and callable(f))
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
