from canonical.runtime.bounded_predicate_argument_support_v1 import classify_support


def rel(claim, evidence):
    return classify_support(claim, evidence, evidence_id="E1")


def test_exact_active_support():
    out = rel("Alice must verify report", "Alice must verify report")
    assert out["status"] == "RESOLVED"
    assert out["relation"] == "SUPPORTS"


def test_active_passive_support():
    out = rel("Alice must verify report", "report must be verified by Alice")
    assert out["relation"] == "SUPPORTS"


def test_active_passive_conflict():
    out = rel("Alice must verify report", "report must not be verified by Alice")
    assert out["relation"] == "CONFLICTS"


def test_different_object_is_unrelated():
    out = rel("Alice must verify report", "Alice must verify invoice")
    assert out["relation"] == "UNRELATED"


def test_different_predicate_is_unrelated():
    out = rel("Alice must verify report", "Alice must archive report")
    assert out["relation"] == "UNRELATED"


def test_condition_support():
    out = rel(
        "If threshold holds, Alice must verify report",
        "If threshold holds, report must be verified by Alice",
    )
    assert out["relation"] == "SUPPORTS"


def test_condition_mismatch_unrelated():
    out = rel(
        "If threshold holds, Alice must verify report",
        "Unless threshold holds, Alice must verify report",
    )
    assert out["relation"] == "UNRELATED"


def test_coordination_fails_closed_to_unresolved():
    out = rel(
        "Alice must verify report",
        "Alice must verify report and archive invoice",
    )
    assert out["status"] == "UNRESOLVED"
    assert out["relation"] is None


def test_pronoun_fails_closed_to_unresolved():
    out = rel("Alice must verify report", "She must verify report")
    assert out["status"] == "UNRESOLVED"
    assert out["relation"] is None


def test_no_terminal_authority():
    out = rel("Alice must verify report", "report must be verified by Alice")
    assert out["terminal_authority"] is False
