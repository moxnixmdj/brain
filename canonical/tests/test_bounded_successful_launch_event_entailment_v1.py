from canonical.runtime.bounded_successful_launch_event_entailment_v1 import classify_support

def test_current_p3_concrete_paraphrase_supports():
    out=classify_support(
        "The product launched in June.",
        "The June launch of the product succeeded.",
        evidence_id="E",
    )
    assert out["status"]=="RESOLVED"
    assert out["relation"]=="SUPPORTS"
    assert out["proof"]["rule"]=="EXISTENTIAL_CONJUNCTION_WEAKENING"
    assert out["proof"]["checked_subset"] is True
    assert out["proof"]["dropped_atoms"]==["succeeded(e)"]

def test_entity_mismatch_is_unrelated_not_conflict():
    out=classify_support(
        "The product launched in June.",
        "The June launch of the service succeeded.",
    )
    assert out["status"]=="RESOLVED" and out["relation"]=="UNRELATED"

def test_time_mismatch_is_unrelated_not_conflict():
    out=classify_support(
        "The product launched in June.",
        "The July launch of the product succeeded.",
    )
    assert out["status"]=="RESOLVED" and out["relation"]=="UNRELATED"

def test_planned_launch_is_not_silently_promoted():
    out=classify_support(
        "The product launched in June.",
        "The June launch of the product was planned.",
    )
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN"

def test_failed_launch_is_not_silently_promoted():
    out=classify_support(
        "The product launched in June.",
        "The June launch of the product failed.",
    )
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN"

def test_general_nominalization_outside_scope_unknown():
    out=classify_support(
        "The company expanded in June.",
        "The June expansion of the company succeeded.",
    )
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN"

def test_case_and_whitespace_normalization_only():
    out=classify_support(
        "The Product launched in June.",
        "  The   June launch of the product succeeded. ",
    )
    assert out["relation"]=="SUPPORTS"

def test_zero_terminal_authority():
    out=classify_support(
        "The product launched in June.",
        "The June launch of the product succeeded.",
    )
    assert out["terminal_authority"] is False
