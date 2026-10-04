from canonical.runtime.terminal_minimum_causal_depth_policy_v1 import (
    validate_live_state, route_admissible, filter_routes, compile_waves, dominance_prune
)
import pytest

STATE={
"accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
"total_families":19,"total_atomic":38,"root1_positive_gaps":0,"root2_only":16,
"root3_only":7,"root2_and_root3":3,"terminal":False,
}

def test_live_state_exact():
    validate_live_state(STATE)
    bad=dict(STATE); bad["proved_atomic"]=13
    with pytest.raises(ValueError):
        validate_live_state(bad)

def test_relative_elo_rejects_pure_absolute_without_bridge():
    assert route_admissible("PROWORK_GDPVAL_GE_1846","FORMAL_ENTAILMENT") is False
    assert route_admissible("PROWORK_GDPVAL_GE_1846","FORMAL_ENTAILMENT",explicit_relative_bridge=True) is True
    assert route_admissible("PROWORK_GDPVAL_GE_1846","OWNER_RESULT") is True

def test_non_elo_absolute_route_remains_possible():
    assert route_admissible("LIVEBENCH_IF_GE_65_7","FORMAL_ENTAILMENT") is True

def test_fresh_reality_is_blocked_without_both_gates():
    routes=[
      {"predicate_id":"LIVEBENCH_IF_GE_65_7","route_kind":"FIXED_BAR_SCORE"},
      {"predicate_id":"FINANCE_ACCOUNTING_INDEX_GE_61","route_kind":"EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE"},
    ]
    out=compile_waves(STATE,routes,generic_isolation_proved=True,fresh_reality_authorized=False)
    assert out["wave2"]["actions"] == []
    assert len(out["wave2"]["blocked_actions"]) == 1
    assert len(out["wave0"]["typed_evidence_collapse"]) == 1

def test_fresh_reality_requires_isolation_too():
    routes=[{"predicate_id":"LIVEBENCH_IF_GE_65_7","route_kind":"FIXED_BAR_SCORE"}]
    out=compile_waves(STATE,routes,generic_isolation_proved=False,fresh_reality_authorized=True)
    assert out["wave2"]["fresh_reality_authorized"] is False

def test_relative_invalid_route_is_pruned_not_promoted():
    routes=[
      {"predicate_id":"PROWORK_AA_BRIEFCASE_GE_1822","route_kind":"SCOPE_SAFE_STRONGER_PROOF"},
      {"predicate_id":"PROWORK_AA_BRIEFCASE_GE_1822","route_kind":"RELATIVE_SCORE_BRIDGE"},
    ]
    out=filter_routes(routes)
    assert [x["route_kind"] for x in out] == ["RELATIVE_SCORE_BRIDGE"]

def test_dominance_prunes_only_known_mechanical_case():
    actions=[
      {"id":"a","phase":"zero","covers":["p1"],"critical_path_seconds":10,"information_class":1},
      {"id":"b","phase":"zero","covers":["p1","p2"],"critical_path_seconds":9,"information_class":1},
      {"id":"unknown","phase":"zero","covers":["p3"],"critical_path_seconds":None,"information_class":99},
    ]
    ids={x["id"] for x in dominance_prune(actions)}
    assert ids == {"b","unknown"}
