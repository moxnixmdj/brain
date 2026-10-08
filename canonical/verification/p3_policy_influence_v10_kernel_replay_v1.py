"""Deterministic exact-function replay for P3 policy-influence V10 kernel tests."""
import canonical.tests.test_p3_policy_influence_relevance_cell_v1 as m

tests=[(n,f) for n,f in vars(m).items() if n.startswith("test_") and callable(f)]
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
