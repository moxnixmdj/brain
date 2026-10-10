import copy, json
from pathlib import Path
from canonical.runtime import professional_r5_evaluator_reference_semantic_certificate_v1 as s

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"canonical/governance/GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_20261008_V1.json"
VER=ROOT/"canonical/verification/GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_SPRITE_VERIFICATION_20261008_V1.json"
BIND=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_R5_EVALUATOR_REFERENCE_SEMANTIC_SCOPE_20261010_V1.json"

def docs():
    return tuple(json.loads(p.read_text()) for p in (SRC,VER,BIND))

def test_current_exact_sources_pass_bounded_semantics_only():
    src,ver,b=s.docs() if False else docs()
    out=s.certify(src,ver,b)
    assert out["pass"] is True, out
    assert out["status"]=="PASS__BOUNDED_HYBRID_EVALUATOR_REFERENCE_SEMANTICS"
    assert out["semantic_leaf_credit"] is False
    assert out["global_leaf_closure"] is False
    assert out["domain_semantic_closure"] is False
    assert out["quality_authority"] is False
    assert out["terminal_authority"] is False

def test_definition_drift_fails_closed():
    src,ver,b=docs()
    src["definitions"]["Uhat"]="FORGED"
    out=s.certify(src,ver,b)
    assert out["pass"] is False
    assert any(x.startswith("DEFINITION_INVALID:Uhat") for x in out["errors"])

def test_public_rubric_cannot_be_promoted_into_allowed_semantic_class():
    src,ver,b=docs()
    src["soundness_firewall"]["admissible_decomposition_proof_classes"].append("PUBLIC_RUBRIC_ONLY")
    out=s.certify(src,ver,b)
    assert out["pass"] is False
    assert "ALLOWED_PROOF_CLASSES_DRIFT" in out["errors"]

def test_current_evaluator_membership_overclaim_fails_closed():
    src,ver,b=docs()
    b["boundaries"]["true_current_evaluator_membership_proved"]=True
    out=s.certify(src,ver,b)
    assert out["pass"] is False
    assert "BOUNDARY_OVERCLAIM:true_current_evaluator_membership_proved" in out["errors"]

def test_historical_prompt_current_semantics_overclaim_fails_closed():
    src,ver,b=docs()
    b["boundaries"]["historical_prompt_is_current_owner_semantics"]=True
    out=s.certify(src,ver,b)
    assert out["pass"] is False
    assert "BOUNDARY_OVERCLAIM:historical_prompt_is_current_owner_semantics" in out["errors"]

def test_source_digest_mutation_fails_closed():
    src,ver,b=docs()
    src["problem"]+=" MUTATED"
    out=s.certify(src,ver,b)
    assert out["pass"] is False
    assert "SOURCE_DIGEST_MISMATCH" in out["errors"]

def test_verification_digest_mutation_fails_closed():
    src,ver,b=docs()
    ver["replay"]["tests_passed"]=10
    out=s.certify(src,ver,b)
    assert out["pass"] is False
    assert "VERIFY_REPLAY_INVALID" in out["errors"]
    assert "VERIFY_DIGEST_MISMATCH" in out["errors"]

def test_outside_reference_class_must_remain_unclaimed():
    src,ver,b=docs()
    b["boundaries"]["outside_declared_reference_class_stays_unclaimed"]=False
    out=s.certify(src,ver,b)
    assert out["pass"] is False
    assert "OUTSIDE_CLASS_BOUNDARY_MISSING" in out["errors"]
