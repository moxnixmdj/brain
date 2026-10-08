from canonical.runtime.bounded_exact_set_membership_support_v1 import classify_support

def test_positive_contains_supports_named_member():
    out=classify_support(
        "alpha is a member of Approved products.",
        "Policy states that Approved products contains alpha.",
    )
    assert out["status"]=="RESOLVED" and out["relation"]=="SUPPORTS"
    assert out["proof"]["rule"]=="EXPLICIT_POSITIVE_SET_MEMBERSHIP"

def test_positive_contains_cannot_prove_absence_of_other_member():
    out=classify_support(
        "beta is a member of Approved products.",
        "Approved products contains alpha.",
    )
    assert out["status"]=="RESOLVED" and out["relation"]=="UNRELATED"
    assert out["proof"]["rule"]=="OPEN_WORLD_POSITIVE_MEMBERSHIP_DOES_NOT_PROVE_ABSENCE"

def test_complete_enumeration_supports_present_member():
    out=classify_support(
        "beta is a member of Approved products.",
        "The complete members of Approved products are {alpha, beta, gamma}.",
    )
    assert out["relation"]=="SUPPORTS"
    assert out["proof"]["membership"] is True

def test_complete_enumeration_conflicts_with_absent_member():
    out=classify_support(
        "delta is a member of Approved products.",
        "The complete members of Approved products are {alpha, beta, gamma}.",
    )
    assert out["relation"]=="CONFLICTS"
    assert out["proof"]["membership"] is False

def test_empty_complete_set_proves_nonmembership():
    out=classify_support(
        "alpha is a member of Approved products.",
        "The complete members of Approved products are {}.",
    )
    assert out["relation"]=="CONFLICTS"

def test_different_set_is_unrelated():
    out=classify_support(
        "alpha is a member of Approved products.",
        "The complete members of Rejected products are {alpha}.",
    )
    assert out["relation"]=="UNRELATED"

def test_duplicate_complete_members_fail_closed():
    out=classify_support(
        "alpha is a member of Approved products.",
        "The complete members of Approved products are {alpha, alpha}.",
    )
    assert out["status"]=="FAIL_CLOSED" and out["relation"]=="UNKNOWN"

def test_taxonomic_claim_remains_unknown():
    out=classify_support(
        "sparrow is a bird.",
        "Birds contains sparrow.",
    )
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN"

def test_uncontrolled_natural_language_remains_unknown():
    out=classify_support(
        "alpha is a member of Approved products.",
        "Alpha appears among the things we normally approve.",
    )
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN"

def test_zero_terminal_authority():
    out=classify_support(
        "alpha is a member of Approved products.",
        "Approved products contains alpha.",
    )
    assert out["terminal_authority"] is False
