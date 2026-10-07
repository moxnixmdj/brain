from canonical.runtime.terminal_closure_reducer import evaluate_manifest


def test_universal_route_requires_explicit_proof():
    out = evaluate_manifest({})
    assert out["achieved"] is False
