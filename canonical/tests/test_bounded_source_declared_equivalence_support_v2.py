from canonical.runtime.bounded_source_declared_equivalence_support_v2 import classify_support

def test_nested_definition_counterexample_now_supports():
    out=classify_support(
      "The release date is June.",
      "Launch date means ship date. Ship date means release date. Report states that The launch date is June."
    )
    assert out["status"]=="RESOLVED" and out["relation"]=="SUPPORTS"
    paths=out["proof"]["resolution_paths"]
    assert paths["launch date"]==["launch date","ship date","release date"]

def test_reverse_surface_supports_same_terminal():
    out=classify_support(
      "The launch date is June.",
      "Launch date means ship date. Ship date means release date. Report states that The release date is June."
    )
    assert out["relation"]=="SUPPORTS"

def test_nested_denial_conflicts():
    out=classify_support(
      "The release date is June.",
      "Launch date means ship date. Ship date means release date. Report denies that The launch date is June."
    )
    assert out["relation"]=="CONFLICTS"

def test_nonatomic_nested_rhs_unknown():
    out=classify_support(
      "The release date is June.",
      "Launch date means ship date plus review. Ship date means release date. Report states that The launch date is June."
    )
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN"
    assert out["reason"]=="NESTED_NONATOMIC_DEFINITION_OUTSIDE_V2"

def test_conflicting_definitions_unknown():
    out=classify_support(
      "The release date is June.",
      "Launch date means ship date. Launch date means release date. Report states that The launch date is June."
    )
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN"

def test_cycle_unknown():
    out=classify_support(
      "The release date is June.",
      "Launch date means ship date. Ship date means launch date. Report states that The launch date is June."
    )
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN"

def test_unparsed_extra_sentence_unknown():
    out=classify_support(
      "The release date is June.",
      "Launch date means ship date. Ship date means release date. The schedule is complicated. Report states that The launch date is June."
    )
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN"

def test_mixed_polarity_unknown():
    out=classify_support(
      "The release date is June.",
      "Launch date means ship date. Ship date means release date. Report states that The launch date is June. Other denies that The release date is June."
    )
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN"

def test_simple_v1_shape_regression():
    out=classify_support(
      "The release date is June.",
      "Launch date means release date. Report states that The launch date is June."
    )
    assert out["relation"]=="SUPPORTS"

def test_zero_terminal_authority():
    out=classify_support(
      "The release date is June.",
      "Launch date means ship date. Ship date means release date. Report states that The launch date is June."
    )
    assert out["terminal_authority"] is False
