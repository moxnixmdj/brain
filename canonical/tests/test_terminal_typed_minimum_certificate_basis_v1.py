from canonical.runtime.terminal_typed_minimum_certificate_basis_v1 import compile_basis, current_counts_are_exact, required_dimensions, COMPARATOR_STRENGTH, SCOPE_COMPLETENESS

def test_counts():
    x=compile_basis()
    assert x["predicate_count"] == 26
    assert x["typed_obligation_count"] == 29
    assert current_counts_are_exact()

def test_dimensions():
    assert required_dimensions("LIVEBENCH_IF_GE_65_7") == (COMPARATOR_STRENGTH,)
    assert required_dimensions("FINANCE_UNCOVERED_SCOPE_AUDIT") == (SCOPE_COMPLETENESS,)
