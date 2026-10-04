from canonical.runtime import root2_closure_controller_v2 as r

def test_truth_fails_name_only():
    out=r.validate_comparator([{
      "predicate_id":"p","surface":"x","target":"1","model":"m","population":"pop",
      "harness":"h","scorer":"s","provenance":"src","name_only_equivalence":True}])
    assert out["status"]=="FAIL_CLOSED"

def test_finance_derived():
    out=r.derive_nodes(open_predicates=["FINANCE"], proved=["a","b"], derivations=[{
      "target":"FINANCE","premises":["a","b"],"monotone_or_implication_verified":True}])
    assert out["closed"]==["FINANCE"]

def test_fresh_blocked_before_fixed_point():
    out=r.compile_frontier([
      {"id":"truth","class":"TRUTH_REPAIR","closes":["p"],"incremental_spend_usd":0},
      {"id":"score","class":"BRAIN_SCORE","closes":["q"],"incremental_spend_usd":0},
    ],open_predicates=["p","q"],zero_reality_fixed_point=False)
    assert out["zero_reality_parallel"]==["truth"]
    assert out["fresh_reality_authorized"]==[]
    assert out["waiting"]==["score"]

def test_saturated_branch_deleted():
    out=r.compile_frontier([
      {"id":"dead","class":"FORMAL_DOMINANCE","closes":["p"],"incremental_spend_usd":0,"saturated":True},
    ],open_predicates=["p"])
    assert out["deleted"]==["dead"]

def test_fixed_point_authorizes_score():
    out=r.compile_frontier([
      {"id":"score","class":"BRAIN_SCORE","closes":["p"],"incremental_spend_usd":0},
    ],open_predicates=["p"],zero_reality_fixed_point=True)
    assert out["fresh_reality_authorized"]==["score"]


def test_governance_synthesis_residual_is_exact():
    import json
    from pathlib import Path
    p=Path(__file__).resolve().parents[1]/"governance"/"ROOT2_CLOSURE_CONTROLLER_V2.json"
    g=json.loads(p.read_text(encoding="utf-8"))
    s=g["algebraic_compression"]["synthesis"]
    assert s["root2_residuals"]==["metric:matched_quality","matched_quality_noninferiority"]
    assert s["required_claim_coverage"]["state"]=="PROVED_BY_INDEPENDENT_CEILING_PLUS_SUPERSET_SCOPE"
    assert g["exact_state"]=={
      "root2_only":16,"root2_and_root3":3,"root2_touching":19,
      "unique_fixed_bar_surfaces":14,"accepted_families":5,"proved_atomic":12,"unresolved_atomic":26}
