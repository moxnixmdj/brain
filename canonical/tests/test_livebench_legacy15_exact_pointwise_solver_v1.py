import re

from canonical.runtime import livebench_legacy15_exact_pointwise_solver_v1 as s


def c(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def test_end_to_end_binding_uses_exact_checker_seam(monkeypatch):
    monkeypatch.setattr(
        s.exact,
        "verify_pinned_source",
        lambda root: {
            "schema": s.exact.SCHEMA,
            "status": "PASS__EXACT_PINNED_CHECKER_SOURCE_BOUND",
            "registry_git_blob_sha": s.exact.PINNED_REGISTRY_BLOB,
            "instructions_git_blob_sha": s.exact.PINNED_INSTRUCTIONS_BLOB,
            "terminal_data_used": False,
        },
    )

    def checker_for_root(root):
        def checker(response, contracts):
            assert len(contracts) == 1
            return [re.search(r"\bomega\b", response, re.I) is None]
        return checker

    monkeypatch.setattr(s.exact, "checker_for_root", checker_for_root)

    out = s.solve(
        [c("keywords:forbidden_words", forbidden_words=["omega"])],
        "/synthetic/pinned/livebench",
        max_per_subset=2,
        max_total=32,
    )
    assert out["status"] == "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED"
    assert out["pointwise_optimal"] is True
    assert out["best_candidate"]["checker_results"] == [True]
    assert out["pinned_checker_source"]["status"].startswith("PASS__")
    assert out["terminal_data_used"] is False
    assert out["hidden_kwargs_used"] is False
    assert out["acceptance_credit"] is False
