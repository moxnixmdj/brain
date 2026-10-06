from canonical.runtime.k6_positive_cover_semantic_residual_v4_verifier import verify
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/K6_POSITIVE_COVER_SEMANTIC_RESIDUAL_PROJECTION_20261006_V4.json"

def load(): return json.loads(P.read_text())

def test_source_bound_projection_passes():
    out=verify(); assert out["pass"] is True, out; assert out["terminal_credit_delta"]==0

def test_complete_f_requirement_deleted():
    d=load()
    assert d["truth_repair"]["deleted_overstrong_requirement"].startswith("COMPLETE_PER_WORLD_ENUMERATION")
    assert "COMPLETE_ENUMERATION_OF_ALL_TRUE_ADEQUATE_POLICIES" in d["remaining_unbound_residual"]["excludes"]

def test_generic_k6_mechanism_not_reopened():
    d=load()
    assert d["candidate_global_compression"]["current_generic_unbound_preproof_implementation_generator_count"]==0
    assert d["execution_authority"] is False
