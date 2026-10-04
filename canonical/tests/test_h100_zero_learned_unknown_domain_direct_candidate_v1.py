from __future__ import annotations

from canonical.runtime.h100_zero_learned_unknown_domain_direct_candidate_v1 import step
from canonical.runtime.unknown_domain_direct_execution_harness_v1 import execute_case
from canonical.runtime.unknown_domain_direct_hidden_generator_v1 import generate_test_fixture_population
from canonical.runtime.unknown_domain_direct_hidden_scorer_v1 import aggregate, TRANSFER, ABSTAIN


def run_fixture():
    population = generate_test_fixture_population()
    hidden = {row["case_id"]: row for row in population["hidden_records"]}
    results = []
    executions = []
    for visible in population["visible_cases"]:
        out = execute_case(
            candidate_step=step,
            case_visible=visible,
            hidden_record=hidden[visible["case_id"]],
        )
        executions.append(out)
        results.append(out["scorer_result"])
    return population, executions, aggregate(results)


def test_all_27_test_only_cases_pass():
    population, executions, agg = run_fixture()
    assert population["production"] is False
    assert population["case_count"] == 27
    assert agg["all_27_cases_pass"] is True
    assert agg["transfer_leaf_pass"] is True
    assert agg["abstention_leaf_pass"] is True
    assert agg["status"] == "TWO_FROZEN_LEAVES_PASS"
    assert sum(x["leaf_id"] == TRANSFER for x in executions) == 12
    assert sum(x["leaf_id"] == ABSTAIN for x in executions) == 15


def test_transfer_uses_one_probe_not_full_rediscovery():
    _, executions, _ = run_fixture()
    transfer = [x for x in executions if x["leaf_id"] == TRANSFER]
    assert transfer
    assert all(x["probe_count"] == 1 for x in transfer)


def test_candidate_never_receives_hidden_record_argument():
    # Interface-level regression: only two positional concepts are exposed.
    import inspect
    sig = inspect.signature(step)
    assert list(sig.parameters) == ["case_visible", "transcript"]


def test_candidate_has_zero_learned_runtime_dependencies():
    import canonical.runtime.h100_zero_learned_unknown_domain_direct_candidate_v1 as m
    source = inspect_source = __import__("inspect").getsource(m)
    forbidden = [
        "transformers", "torch", "tensorflow", "openai", "anthropic",
        "unknown_domain_direct_hidden_scorer_v1",
        "unknown_domain_direct_hidden_generator_v1",
    ]
    for token in forbidden:
        assert token not in source
