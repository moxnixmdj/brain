import hashlib, json
from pathlib import Path
from canonical.runtime.counterexample_guided_causal_architecture_synthesizer_v1 import synthesize

ROOT=Path(__file__).resolve().parents[2]
CUT=ROOT/"canonical/governance/P3_SCOPE_COMPLETE_CAUSAL_CUT_20261007_V1.json"
INPUT=ROOT/"canonical/governance/P3_SCOPE_COMPLETE_CAUSAL_SYNTHESIS_INPUT_20261007_V1.json"

def blob(path):
    raw=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def test_exact_source_bindings():
    d=load(CUT)
    for row in d["source_bindings"].values():
        p=ROOT/row["path"]
        assert p.is_file(), row["path"]
        assert blob(p)==row["git_blob_sha"], (row["path"],blob(p),row["git_blob_sha"])

def test_exact_eight_component_synthesis_still_requires_new_effect():
    d=load(CUT)
    out=synthesize(load(INPUT))
    assert out["classification"]=="NEW_PRIMITIVE_REQUIRED",out
    assert out["frontier_component_count"]==8,out
    assert out["admissible_component_count"]==8,out
    assert out["architectures_evaluated"]==256,out
    assert set(out["missing_required_effects"])==set(d["exact_causal_synthesis_result"]["missing_required_effects"])

def test_bounded_reuse_mechanisms_do_not_claim_scope_complete_semantics():
    d=load(CUT)
    bounded=(ROOT/"canonical/runtime/bounded_claim_support.py").read_text()
    generic=(ROOT/"canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py").read_text()
    m4=load(ROOT/"canonical/capabilities/opus55/M4_DECISION_ROLE_RELEVANCE_001.json")
    semantic=(ROOT/"canonical/runtime/monotone_semantic_constraint_kernel_v1.py").read_text()
    assert "not general entailment" in bounded.lower()
    assert "semantic_entailment_status" in generic and '"UNVERIFIED"' in generic
    assert "NO_GENERAL_SEMANTIC_RELEVANCE_CLAIM" in set(m4["exclusions"])
    assert "NOT a natural-language semantic parser" in semantic
    truth=d["existing_reuse_scope_truth"]
    assert "NOT_WHOLE_OPEN_ENDED_CONTRACT_SCOPE" in truth["p3_information_safe_v3"]

def test_unified_effect_is_only_build_target_not_claimed_implemented():
    d=load(CUT)
    c=d["first_principles_collapse"]
    assert c["build_target_count"]==1
    assert c["unified_effect"]=="P3_SCOPE_COMPLETE_GROUNDED_AUDIENCE_CONDITIONED_POLICY_DOMINANCE"
    assert set(c["entails"])=={
      "P3_SCOPE_COMPLETE_SUPPORT_RELEVANCE_BINDING",
      "P3_INFORMATION_BOUNDARY_SOUND",
      "P3_SCOPE_COMPLETE_AUDIENCE_CONDITIONED_POLICY_ADEQUACY",
      "P3_WHOLE_SYNTHESIS_CONTEXT_DOMINANCE",
    }
    assert "NO_CLAIM_THE_UNIFIED_EFFECT_IS_IMPLEMENTED." in d["hard_nonclaims"]
    assert d["accounting"]["terminal_credit_delta"]==0

def test_no_external_target_information_or_general_nl_engine_false_necessity():
    d=load(CUT)
    assert "NO_CLAIM_A_GENERAL_NATURAL_LANGUAGE_SEMANTIC_ENGINE_IS_PROVED_NECESSARY." in d["hard_nonclaims"]
    assert "NO_CLAIM_EXTERNAL_TARGET_INFORMATION_IS_PROVED_NECESSARY." in d["hard_nonclaims"]

if __name__=="__main__":
    tests=[v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t(); print("PASS",t.__name__)
    print("PASS_COUNT",len(tests))
