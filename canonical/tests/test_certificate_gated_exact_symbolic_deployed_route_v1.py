from canonical.runtime.certificate_gated_exact_symbolic_deployed_route_v1 import run


def test_router_is_in_real_accepted_exact_symbolic_execution_path():
    out = run()

    assert out["router_selected"] is True
    assert out["context_digest"] == "sha256:38460d8e0a4886575743a50829e19b8aee02911962b3b668f38867883338e76f"
    assert out["cell_id"] == "OBS-EXACT-SYMBOLIC-001"
    assert out["route_id"] == "accepted.exact_symbolic"
    assert out["pass_count"] == 12
    assert out["fail_count"] == 0
    assert out["exact_correctness"] == 1.0
    assert out["incremental_spend_usd"] == 0


def test_deployed_entry_has_no_suite_or_route_override_surface():
    import inspect
    from canonical.runtime import certificate_gated_exact_symbolic_deployed_route_v1 as deployed

    assert tuple(inspect.signature(deployed.run).parameters) == ()
