from canonical.runtime.h0_persistent_capability_information_falsifier_v1 import (
    compile_h0_falsification,
    repaired_accounting_contract,
    representation_laundering_counterexample,
)


def test_representation_laundering_kills_learned_byte_metric():
    out = representation_laundering_counterexample()
    assert out["capability_information_preserved"] is True
    assert out["learned_representation_declared_learned_bytes"] > 0
    assert out["source_constant_declared_learned_bytes"] == 0
    assert out["learned_byte_metric_representation_invariant"] is False


def test_repaired_accounting_counts_code_laundering_surfaces():
    out = repaired_accounting_contract()
    assert out["external_capability_laundering_forbidden"] is True
    assert out["resource_semantics_load_bearing"] is True
    for required in (
        "SOURCE_CONSTANTS",
        "LOOKUP_TABLES",
        "HANDWRITTEN_RULES",
        "TARGET_SPECIFIC_PROGRAMS",
        "VERIFIED_CAPABILITY_LIBRARY_ENTRIES",
    ):
        assert required in out["counts"]


def test_h0_is_repaired_not_declared_true_or_false():
    out = compile_h0_falsification()
    assert out["learned_byte_metric_falsified"] is True
    assert out["h0_zero_learned_not_decidable_from_that_metric"] is True
    assert out["repaired_hypothesis"] == "H0_ZERO_INCREMENTAL_PERSISTENT_CAPABILITY_INFORMATION"
    assert out["next_falsifier"] == "F_TARGET_RELEVANT_IRREDUCIBLE_CAPABILITY_INFORMATION"
    assert out["terminal_credit"] is False
